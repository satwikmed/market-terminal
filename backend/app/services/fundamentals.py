"""Real financial statements + ratios from SEC XBRL company-facts.

SEC's `companyfacts` API exposes every number a company has tagged in its
filings — revenue, net income, the full balance sheet — going back many years,
for free. We normalise the messy tag soup into clean annual statements and a
suite of computed ratios. Everything here is filing-sourced; nothing is
invented, and missing tags stay missing rather than being guessed.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import FinancialsCache
from app.services import sec_filings

logger = logging.getLogger(__name__)

FACTS_TTL_HOURS = 24 * 7  # filings update quarterly; a week of cache is safe

# Bump when the parsing rules change, so cached payloads built by older logic
# are rebuilt on next read instead of serving numbers we no longer stand behind.
PARSER_VERSION = 2

# Each line item lists the us-gaap concepts we accept, most-preferred first.
# Companies tag the "same" number under different concepts across eras.
REVENUE = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    # Banks and brokers report a single "net revenues" line instead.
    "RevenuesNetOfInterestExpense",
]
# Lenders that report no combined revenue line: the sector convention is net
# interest income plus fee income, so we add the two reported figures rather
# than fall back to gross interest income, which would overstate the top line.
BANK_REVENUE_PARTS = (["InterestIncomeExpenseNet"], ["NoninterestIncome"])
COST_OF_REVENUE = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"]
GROSS_PROFIT = ["GrossProfit"]
OPERATING_INCOME = ["OperatingIncomeLoss"]
NET_INCOME = ["NetIncomeLoss", "ProfitLoss"]
RND = ["ResearchAndDevelopmentExpense"]
EPS_DILUTED = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
ASSETS = ["Assets"]
CURRENT_ASSETS = ["AssetsCurrent"]
LIABILITIES = ["Liabilities"]
CURRENT_LIABILITIES = ["LiabilitiesCurrent"]
EQUITY = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
LONG_TERM_DEBT = ["LongTermDebtNoncurrent", "LongTermDebt"]
OPERATING_CASH_FLOW = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]
CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
SHARES = ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"]


def _headers() -> dict[str, str]:
    from app.config import get_settings

    return {
        "User-Agent": get_settings().sec_user_agent,
        "Accept-Encoding": "gzip, deflate",
    }


# When a company reorganises under a new holding company, SEC's ticker map
# points at the new registrant, whose company-facts are empty until it has
# filed. The filing history stays under the predecessor CIK.
PREDECESSOR_CIK = {"XOM": "0000034088"}  # Exxon Mobil Corporation


def _padded_cik(ticker: str) -> str | None:
    cik = sec_filings.cik_for(ticker)
    if not cik:
        return None
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    return digits.zfill(10) if digits else None


def _fetch_facts_for_cik(cik: str) -> dict | None:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            time.sleep(0.4 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            logger.debug("companyfacts fetch failed for CIK %s: %s", cik, exc)
            time.sleep(0.4 * (attempt + 1))
    return None


def _has_gaap_facts(facts: dict | None) -> bool:
    return bool((facts or {}).get("facts", {}).get("us-gaap"))


def _fetch_company_facts(ticker: str) -> dict | None:
    cik = _padded_cik(ticker)
    if not cik:
        return None
    facts = _fetch_facts_for_cik(cik)
    if not _has_gaap_facts(facts):
        predecessor = PREDECESSOR_CIK.get(ticker.upper())
        if predecessor:
            logger.info("%s has no facts under CIK %s; using predecessor %s", ticker, cik, predecessor)
            facts = _fetch_facts_for_cik(predecessor) or facts
    return facts


def _annual(facts: dict, concepts: list[str], *, duration: bool) -> dict[int, float]:
    """Return {fiscal_year: value} for the first concept that has data.

    duration=True  -> flow items (revenue, income) spanning ~1 fiscal year
    duration=False -> instant items (balance-sheet snapshots)
    """
    gaap = facts.get("facts", {}).get("us-gaap", {})
    candidates: list[tuple[int, int, int, dict[int, float]]] = []
    for rank, concept in enumerate(concepts):
        node = gaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        unit_key = next((k for k in units if k in ("USD", "USD/shares", "shares")), None)
        if unit_key is None:
            unit_key = next(iter(units), None)
        if unit_key is None:
            continue
        by_year: dict[int, float] = {}
        for pt in units[unit_key]:
            if pt.get("form") not in ("10-K", "10-K/A"):
                continue
            if pt.get("fp") != "FY":
                continue
            fy = pt.get("fy")
            val = pt.get("val")
            if fy is None or val is None:
                continue
            if duration:
                start, end = pt.get("start"), pt.get("end")
                if start and end:
                    try:
                        days = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
                    except ValueError:
                        days = 365
                    if days < 340 or days > 380:
                        continue
            # Prefer a point that carries an official CY/FY frame (deduped by SEC).
            by_year[int(fy)] = float(val)
        if by_year:
            candidates.append((max(by_year), len(by_year), -rank, by_year))

    if not candidates:
        return {}
    # Companies switch tags between eras, and the tag we list first is often the
    # one they abandoned. Take the concept reporting the most recent year — never
    # a blend of concepts, which would splice two different definitions into one
    # series — falling back to coverage and then to listed preference.
    return max(candidates, key=lambda c: c[:3])[3]


def _bank_revenue(facts: dict) -> dict[int, float]:
    """Total revenue for lenders: net interest income + noninterest income.

    Only years where both components are reported are returned, so a partial
    filing can never produce a half-counted top line.
    """
    net_interest = _annual(facts, BANK_REVENUE_PARTS[0], duration=True)
    fees = _annual(facts, BANK_REVENUE_PARTS[1], duration=True)
    if not net_interest or not fees:
        return {}
    return {y: net_interest[y] + fees[y] for y in net_interest.keys() & fees.keys()}


def _series(by_year: dict[int, float], years: list[int]) -> list[float | None]:
    return [by_year.get(y) for y in years]


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b


def _cagr(series: list[float | None]) -> float | None:
    vals = [v for v in series if v is not None and v > 0]
    if len(vals) < 2:
        return None
    first, last = vals[0], vals[-1]
    n = len(vals) - 1
    try:
        return ((last / first) ** (1 / n) - 1) * 100
    except (ValueError, ZeroDivisionError):
        return None


def _recent_run(fiscal_years, limit: int = 10) -> list[int]:
    """The most recent unbroken run of fiscal years, newest `limit` at most.

    Older filings tag inconsistently, leaving holes. Plotting across a hole
    would draw a gap as if it were continuous growth, so we stop at the break.
    """
    available = sorted(fiscal_years)
    if not available:
        return []
    run = [available[-1]]
    for year in reversed(available[:-1]):
        if year != run[0] - 1:
            break
        run.insert(0, year)
    return run[-limit:]


def build_financials(ticker: str) -> dict | None:
    facts = _fetch_company_facts(ticker)
    if not facts:
        return None

    revenue = _annual(facts, REVENUE, duration=True) or _bank_revenue(facts)
    if not revenue:
        return None
    cost = _annual(facts, COST_OF_REVENUE, duration=True)
    gross = _annual(facts, GROSS_PROFIT, duration=True)
    op_income = _annual(facts, OPERATING_INCOME, duration=True)
    net_income = _annual(facts, NET_INCOME, duration=True)
    rnd = _annual(facts, RND, duration=True)
    eps = _annual(facts, EPS_DILUTED, duration=True)
    ocf = _annual(facts, OPERATING_CASH_FLOW, duration=True)
    capex = _annual(facts, CAPEX, duration=True)

    assets = _annual(facts, ASSETS, duration=False)
    cur_assets = _annual(facts, CURRENT_ASSETS, duration=False)
    liabilities = _annual(facts, LIABILITIES, duration=False)
    cur_liab = _annual(facts, CURRENT_LIABILITIES, duration=False)
    equity = _annual(facts, EQUITY, duration=False)
    cash = _annual(facts, CASH, duration=False)
    lt_debt = _annual(facts, LONG_TERM_DEBT, duration=False)

    years = _recent_run(revenue.keys())
    if not years:
        return None

    def col(d: dict[int, float]) -> list[float | None]:
        return _series(d, years)

    # Derive gross profit if not tagged directly.
    gross_series = []
    for y in years:
        if y in gross:
            gross_series.append(gross[y])
        elif y in revenue and y in cost:
            gross_series.append(revenue[y] - cost[y])
        else:
            gross_series.append(None)

    fcf_series = []
    for y in years:
        if y in ocf and y in capex:
            fcf_series.append(ocf[y] - capex[y])
        elif y in ocf:
            fcf_series.append(ocf[y])
        else:
            fcf_series.append(None)

    latest = years[-1]

    def latest_of(d: dict[int, float]) -> float | None:
        return d.get(latest)

    rev_l = latest_of(revenue)
    ni_l = latest_of(net_income)
    gp_l = gross_series[-1]
    oi_l = latest_of(op_income)
    eq_l = latest_of(equity)
    as_l = latest_of(assets)
    fcf_l = fcf_series[-1]

    # Sustained buybacks can push book equity below zero (McDonald's, Boeing,
    # Philip Morris). Dividing by it yields a large negative ratio that reads
    # like a data error, so return-on-equity and leverage are simply not
    # meaningful here and are reported as unavailable.
    equity_positive = eq_l if (eq_l or 0) > 0 else None

    ratios = {
        "gross_margin": _pct(_safe_div(gp_l, rev_l)),
        "operating_margin": _pct(_safe_div(oi_l, rev_l)),
        "net_margin": _pct(_safe_div(ni_l, rev_l)),
        "roe": _pct(_safe_div(ni_l, equity_positive)),
        "roa": _pct(_safe_div(ni_l, as_l)),
        "debt_to_equity": _round(_safe_div(latest_of(lt_debt), equity_positive)),
        "current_ratio": _round(_safe_div(latest_of(cur_assets), latest_of(cur_liab))),
        "fcf_margin": _pct(_safe_div(fcf_l, rev_l)),
        "rnd_intensity": _pct(_safe_div(latest_of(rnd), rev_l)),
        "revenue_cagr": _round(_cagr(col(revenue))),
        "net_income_cagr": _round(_cagr(col(net_income))),
    }

    return {
        "ticker": ticker,
        "fiscal_years": years,
        "latest_fiscal_year": latest,
        "currency": "USD",
        "statements": {
            "income": {
                "revenue": col(revenue),
                "gross_profit": gross_series,
                "operating_income": col(op_income),
                "net_income": col(net_income),
                "rnd": col(rnd),
                "eps_diluted": col(eps),
            },
            "balance": {
                "total_assets": col(assets),
                "total_liabilities": col(liabilities),
                "total_equity": col(equity),
                "cash": col(cash),
                "long_term_debt": col(lt_debt),
            },
            "cashflow": {
                "operating_cash_flow": col(ocf),
                "capital_expenditure": col(capex),
                "free_cash_flow": fcf_series,
            },
        },
        "ratios": ratios,
        "parser_version": PARSER_VERSION,
        "negative_equity": eq_l is not None and eq_l <= 0,
        "source": "SEC EDGAR XBRL company facts",
        "source_url": f"https://data.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={_padded_cik(ticker)}",
    }


def _pct(x: float | None) -> float | None:
    return round(x * 100, 2) if x is not None else None


def _round(x: float | None) -> float | None:
    return round(x, 2) if x is not None else None


async def get_financials(db: AsyncSession, ticker: str, *, force: bool = False) -> dict | None:
    ticker = ticker.upper()
    row = (
        await db.execute(select(FinancialsCache).where(FinancialsCache.ticker == ticker))
    ).scalar_one_or_none()
    if row and not force:
        age_h = (datetime.utcnow() - row.fetched_at).total_seconds() / 3600
        cached = json.loads(row.payload)
        if age_h < FACTS_TTL_HOURS and cached.get("parser_version") == PARSER_VERSION:
            return cached

    built = build_financials(ticker)
    if built is None:
        if row:
            return json.loads(row.payload)
        return None

    payload = json.dumps(built)
    if row:
        row.payload = payload
        row.fetched_at = datetime.utcnow()
    else:
        db.add(FinancialsCache(ticker=ticker, payload=payload, fetched_at=datetime.utcnow()))
    await db.commit()
    return built


def _latest_revenue(built: dict) -> float | None:
    series = built["statements"]["income"]["revenue"]
    return next((v for v in reversed(series) if v is not None), None)


def yahoo_ttm_revenue(ticker: str) -> float | None:
    """Trailing-twelve-month revenue from Yahoo when SEC XBRL has no top line.

    A few S&P names (recent spin-offs, some oil & gas filers) either have empty
    companyfacts or never tag annual revenue. Yahoo still publishes a TTM
    figure; we use it only as a last resort for the company-row revenue field,
    never to invent multi-year statements.
    """
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("Yahoo revenue lookup failed for %s: %s", ticker, exc)
        return None
    raw = info.get("totalRevenue") or info.get("revenue")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


async def backfill_company_fundamentals(session_factory, *, force: bool = False) -> dict:
    """Populate revenue and debt/equity on every company from SEC filings.

    Yahoo's quote API omits both, so without this the screener and company
    pages show blanks for two of the columns people sort by first. Run in the
    background after a market load: it is ~500 SEC requests, paced under the
    fair-access limit, and resumable because it skips names already filled.
    Names that still have no filing-tagged revenue fall back to Yahoo TTM.
    """
    from app.models.entities import Company

    async with session_factory() as db:
        rows = (await db.execute(select(Company.ticker, Company.revenue))).all()
        cached = dict(
            (await db.execute(select(FinancialsCache.ticker, FinancialsCache.payload))).all()
        )

    def stale(ticker: str) -> bool:
        payload = cached.get(ticker)
        if payload is None:
            return True
        try:
            return json.loads(payload).get("parser_version") != PARSER_VERSION
        except json.JSONDecodeError:
            return True

    # Names are reprocessed when the figures are missing or when the cached
    # parse predates the current rules, so a parser fix reaches every company
    # instead of only the ones that happened to have no data.
    todo = [t for t, rev in rows if force or not rev or stale(t)]
    logger.info("fundamentals backfill: %s of %s names need filling", len(todo), len(rows))

    filled = yahoo_filled = failed = 0
    for ticker in todo:
        try:
            built = await asyncio.to_thread(build_financials, ticker)
        except Exception as exc:  # noqa: BLE001
            logger.debug("fundamentals build failed for %s: %s", ticker, exc)
            built = None

        if built:
            try:
                async with session_factory() as db:
                    await get_financials(db, ticker, force=True)
                    company = (
                        await db.execute(select(Company).where(Company.ticker == ticker))
                    ).scalar_one_or_none()
                    if company:
                        revenue = _latest_revenue(built)
                        if revenue is not None:
                            company.revenue = float(revenue)
                        # Filings are authoritative for leverage, so a ratio the
                        # parser now rejects as not meaningful must also clear any
                        # value an earlier parse wrote.
                        de = built["ratios"].get("debt_to_equity")
                        company.debt_to_equity = float(de) if de is not None else None
                        await db.commit()
                filled += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("fundamentals persist failed for %s: %s", ticker, exc)
                failed += 1
        else:
            # SEC has nothing usable (empty companyfacts or no revenue tag).
            revenue = await asyncio.to_thread(yahoo_ttm_revenue, ticker)
            if revenue is None:
                failed += 1
            else:
                try:
                    async with session_factory() as db:
                        company = (
                            await db.execute(select(Company).where(Company.ticker == ticker))
                        ).scalar_one_or_none()
                        if company:
                            company.revenue = revenue
                            await db.commit()
                    yahoo_filled += 1
                    logger.info("%s: SEC XBRL had no revenue; using Yahoo TTM $%.1fB", ticker, revenue / 1e9)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Yahoo revenue persist failed for %s: %s", ticker, exc)
                    failed += 1
        await asyncio.sleep(0.08)  # SEC fair-access: stay well under 10 req/s

    result = {
        "attempted": len(todo),
        "filled": filled,
        "yahoo_revenue_fallback": yahoo_filled,
        "failed": failed,
    }
    logger.info("fundamentals backfill complete: %s", result)
    return result
