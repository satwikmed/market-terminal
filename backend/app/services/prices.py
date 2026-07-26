"""Live S&P 500 quotes + fundamentals via Yahoo Finance (curl_cffi + crumb)."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd
from curl_cffi import requests as cffi_requests
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Company, PriceBar, QuoteSnapshot
from app.services.market_hours import get_market_session

logger = logging.getLogger(__name__)

YF_ALIASES = {
    "BRK.B": "BRK-B",
    "BF.B": "BF-B",
}

# Benchmark index proxy stored alongside company bars for relative metrics.
BENCHMARK_TICKER = "SPY"

UA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def to_yahoo(ticker: str) -> str:
    return YF_ALIASES.get(ticker, ticker.replace(".", "-"))


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class YahooSession:
    """Authenticated Yahoo session using chrome TLS impersonation + crumb."""

    def __init__(self) -> None:
        self.session = cffi_requests.Session(impersonate="chrome")
        self.crumb: str | None = None

    def warm(self, attempts: int = 5) -> None:
        """Establish a crumbed session, backing off through Yahoo's rate limiting.

        A cold deploy often gets 429s on the first few tries because the host IP
        is shared, so a single failure must not abort the whole market load.
        """
        last: str | None = None
        for attempt in range(attempts):
            if attempt:
                # 3s, 9s, 27s, 81s — long enough for a shared-IP 429 to clear.
                time.sleep(min(3 ** attempt, 90))
                self.session = cffi_requests.Session(impersonate="chrome")
            try:
                self.session.get("https://finance.yahoo.com/", headers=UA_HEADERS, timeout=30)
                r = self.session.get(
                    "https://query1.finance.yahoo.com/v1/test/getcrumb",
                    headers=UA_HEADERS,
                    timeout=30,
                )
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {exc}"
                continue
            if r.status_code != 200:
                last = f"{r.status_code} {r.text[:120]}"
                logger.warning("Yahoo crumb attempt %s failed: %s", attempt + 1, last)
                continue
            crumb = r.text.strip()
            if not crumb or "<" in crumb:
                last = f"invalid crumb {crumb!r}"
                continue
            self.crumb = crumb
            return
        raise RuntimeError(f"Failed to get Yahoo crumb after {attempts} attempts: {last}")

    def quote_batch(self, tickers: list[str]) -> list[dict[str, Any]]:
        if not self.crumb:
            self.warm()
        yahoo = [to_yahoo(t) for t in tickers]
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {"symbols": ",".join(yahoo), "crumb": self.crumb}
        r = self.session.get(url, params=params, headers=UA_HEADERS, timeout=45)
        if r.status_code == 401:
            self.warm()
            params["crumb"] = self.crumb
            r = self.session.get(url, params=params, headers=UA_HEADERS, timeout=45)
        if r.status_code == 429:
            time.sleep(2)
            r = self.session.get(url, params=params, headers=UA_HEADERS, timeout=45)
        if r.status_code != 200:
            raise RuntimeError(f"Yahoo quote error {r.status_code}: {r.text[:200]}")
        return r.json().get("quoteResponse", {}).get("result", []) or []

    def chart_history(self, ticker: str, range_: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        yt = to_yahoo(ticker)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yt}"
        r = self.session.get(
            url,
            params={"range": range_, "interval": interval},
            headers=UA_HEADERS,
            timeout=45,
        )
        if r.status_code != 200:
            return pd.DataFrame()
        result = (r.json().get("chart") or {}).get("result") or []
        if not result:
            return pd.DataFrame()
        block = result[0]
        ts = block.get("timestamp") or []
        quote = (block.get("indicators") or {}).get("quote") or [{}]
        q0 = quote[0] if quote else {}
        if not ts:
            return pd.DataFrame()
        df = pd.DataFrame(
            {
                "Open": q0.get("open"),
                "High": q0.get("high"),
                "Low": q0.get("low"),
                "Close": q0.get("close"),
                "Volume": q0.get("volume"),
            },
            index=pd.to_datetime(ts, unit="s"),
        )
        return df.dropna(subset=["Close"], how="any")


def fetch_all_market_data(tickers: list[str], batch_size: int = 50) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, Any]]]:
    """Return (quotes, fundamentals) for all tickers via Yahoo v7 quote API."""
    ys = YahooSession()
    ys.warm()

    reverse = {to_yahoo(t): t for t in tickers}
    quotes: dict[str, dict[str, float]] = {}
    fundamentals: dict[str, dict[str, Any]] = {}

    for i, batch in enumerate(_chunk(tickers, batch_size)):
        try:
            rows = ys.quote_batch(batch)
        except Exception as exc:  # noqa: BLE001
            logger.warning("quote batch %s failed: %s", i, exc)
            time.sleep(1.5)
            try:
                ys.warm()
                rows = ys.quote_batch(batch)
            except Exception as exc2:  # noqa: BLE001
                logger.error("quote batch %s retry failed: %s", i, exc2)
                continue

        for q in rows:
            yt = q.get("symbol")
            if not yt:
                continue
            ticker = reverse.get(yt)
            if not ticker:
                # try direct match
                ticker = yt if yt in tickers else None
            if not ticker:
                continue

            price = q.get("regularMarketPrice")
            if price is None:
                continue
            price = float(price)
            prev = q.get("regularMarketPreviousClose")
            prev = float(prev) if prev is not None else price
            change = q.get("regularMarketChange")
            change = float(change) if change is not None else (price - prev)
            change_pct = q.get("regularMarketChangePercent")
            change_pct = float(change_pct) if change_pct is not None else (
                (change / prev * 100.0) if prev else 0.0
            )

            quotes[ticker] = {
                "price": price,
                "previous_close": prev,
                "change": change,
                "change_pct": change_pct,
            }

            pe = q.get("trailingPE")
            dividend_yield_percent = q.get("dividendYield")
            dividend_yield_fraction = q.get("trailingAnnualDividendYield")
            eps = q.get("epsTrailingTwelveMonths")
            de = q.get("debtToEquity")  # often absent on quote endpoint
            mc = q.get("marketCap")
            revenue = q.get("revenue")  # often absent

            fund: dict[str, Any] = {}
            if mc is not None:
                fund["market_cap"] = float(mc)
            if pe is not None:
                try:
                    fund["pe_ratio"] = float(pe)
                except (TypeError, ValueError):
                    pass
            if eps is not None:
                try:
                    fund["eps"] = float(eps)
                except (TypeError, ValueError):
                    pass
            if dividend_yield_percent is not None:
                try:
                    # Yahoo's dividendYield quote field is expressed as a percent
                    # (0.95 means 0.95%), while our database stores a fraction.
                    fund["dividend_yield"] = float(dividend_yield_percent) / 100.0
                except (TypeError, ValueError):
                    pass
            elif dividend_yield_fraction is not None:
                try:
                    fund["dividend_yield"] = float(dividend_yield_fraction)
                except (TypeError, ValueError):
                    pass
            if de is not None:
                try:
                    def_ = float(de)
                    fund["debt_to_equity"] = def_ / 100.0 if def_ > 10 else def_
                except (TypeError, ValueError):
                    pass
            if revenue is not None:
                try:
                    fund["revenue"] = float(revenue)
                except (TypeError, ValueError):
                    pass
            name = q.get("shortName") or q.get("longName")
            if name:
                fund["yahoo_name"] = name
            if fund:
                fundamentals[ticker] = fund

        time.sleep(0.25)  # be polite

    return quotes, fundamentals


def fetch_all_quotes(tickers: list[str], batch_size: int = 50) -> dict[str, dict[str, float]]:
    quotes, _ = fetch_all_market_data(tickers, batch_size=batch_size)
    return quotes


def fetch_fundamentals(tickers: list[str], workers: int = 8) -> dict[str, dict[str, Any]]:
    del workers  # bulk quote path — workers unused
    _, fundamentals = fetch_all_market_data(tickers)
    return fundamentals


def fetch_history_batch(tickers: list[str], period: str = "6mo") -> dict[str, pd.DataFrame]:
    ys = YahooSession()
    ys.warm()
    frames: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            df = ys.chart_history(t, range_=period)
            if not df.empty:
                frames[t] = df
        except Exception as exc:  # noqa: BLE001
            logger.debug("history failed for %s: %s", t, exc)
        time.sleep(0.05)
    return frames


async def upsert_quotes(db: AsyncSession, quotes: dict[str, dict[str, float]]) -> int:
    session = get_market_session()
    updated = 0
    for ticker, q in quotes.items():
        existing = (
            await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == ticker))
        ).scalar_one_or_none()
        if existing:
            existing.price = q["price"]
            existing.change = q["change"]
            existing.change_pct = q["change_pct"]
            existing.previous_close = q["previous_close"]
            existing.label = session.label
            existing.session_state = session.state
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                QuoteSnapshot(
                    ticker=ticker,
                    price=q["price"],
                    change=q["change"],
                    change_pct=q["change_pct"],
                    previous_close=q["previous_close"],
                    label=session.label,
                    session_state=session.state,
                    updated_at=datetime.utcnow(),
                )
            )
        updated += 1
    await db.commit()
    return updated


async def apply_fundamentals(db: AsyncSession, fundamentals: dict[str, dict[str, Any]]) -> int:
    updated = 0
    for ticker, f in fundamentals.items():
        row = (
            await db.execute(select(Company).where(Company.ticker == ticker))
        ).scalar_one_or_none()
        if not row:
            continue
        changed = False
        if f.get("market_cap") is not None:
            row.market_cap = float(f["market_cap"])
            changed = True
        # Never retain synthetic seed values when the live source omits a field.
        # "Unavailable" is more trustworthy than an invented number.
        row.pe_ratio = (
            float(f["pe_ratio"]) if f.get("pe_ratio") is not None else None
        )
        row.eps = float(f["eps"]) if f.get("eps") is not None else None
        row.revenue = (
            float(f["revenue"]) if f.get("revenue") is not None else None
        )
        row.debt_to_equity = (
            float(f["debt_to_equity"])
            if f.get("debt_to_equity") is not None
            else None
        )
        row.dividend_yield = (
            float(f["dividend_yield"])
            if f.get("dividend_yield") is not None
            else None
        )
        changed = True
        if f.get("description"):
            row.description = str(f["description"])[:4000]
            changed = True
        if changed:
            row.updated_at = datetime.utcnow()
            updated += 1
    await db.commit()
    return updated


async def upsert_history(db: AsyncSession, frames: dict[str, pd.DataFrame]) -> int:
    bars = 0
    for ticker, hist in frames.items():
        await db.execute(delete(PriceBar).where(PriceBar.ticker == ticker))
        for idx, row in hist.iterrows():
            try:
                o = float(row["Open"])
                h = float(row["High"])
                low = float(row["Low"])
                c = float(row["Close"])
                v = float(row["Volume"]) if "Volume" in row and pd.notna(row["Volume"]) else 0.0
            except Exception:  # noqa: BLE001
                continue
            if any(pd.isna(x) for x in (o, h, low, c)):
                continue
            bar_date = idx.date() if hasattr(idx, "date") else pd.Timestamp(idx).date()
            db.add(
                PriceBar(
                    ticker=ticker,
                    bar_date=bar_date,
                    open=o,
                    high=h,
                    low=low,
                    close=c,
                    volume=v,
                )
            )
            bars += 1
    await db.commit()
    return bars


async def refresh_universe(
    db: AsyncSession,
    *,
    with_fundamentals: bool = True,
    with_history: bool = True,
    history_period: str = "6mo",
) -> dict[str, Any]:
    companies = (await db.execute(select(Company))).scalars().all()
    tickers = [c.ticker for c in companies]
    if not tickers:
        return {"mode": "empty", "quotes": 0}

    quotes, fundamentals = fetch_all_market_data(tickers)
    n_quotes = await upsert_quotes(db, quotes)
    n_funds = await apply_fundamentals(db, fundamentals) if with_fundamentals else 0

    n_bars = 0
    failed_batches = 0
    if with_history:
        # History for all names via chart API (batched politely), plus the SPY
        # benchmark used for beta, correlation, and portfolio backtests.
        # Each batch is committed as it arrives so a mid-run rate limit or a
        # redeploy leaves the bars already fetched intact.
        for batch in _chunk([*tickers, BENCHMARK_TICKER], 40):
            try:
                frames = fetch_history_batch(batch, period=history_period)
                n_bars += await upsert_history(db, frames)
            except Exception as exc:  # noqa: BLE001
                failed_batches += 1
                logger.warning("history batch failed (%s); continuing", exc)

    session = get_market_session()
    sample = {t: quotes[t] for t in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "ACN") if t in quotes}
    return {
        "mode": "yahoo_v7",
        "quotes": n_quotes,
        "fundamentals": n_funds,
        "history_bars": n_bars,
        "failed_history_batches": failed_batches,
        "session": session.label,
        "sample": sample,
        "sample_market_caps": {
            t: fundamentals[t].get("market_cap")
            for t in ("AAPL", "MSFT", "NVDA", "ACN")
            if t in fundamentals
        },
    }
