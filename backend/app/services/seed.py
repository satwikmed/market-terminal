from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import (
    Company,
    CompanyRelationship,
    EconomicEvent,
    MacroObservation,
    PriceBar,
    QuoteSnapshot,
)
from app.services.data_loader import load_macro_seed, load_relationships, load_sp500
from app.services.market_hours import get_market_session, now_et

# Deterministic pseudo-random for demo prices
SECTOR_BIAS = {
    "Information Technology": 1.15,
    "Health Care": 1.05,
    "Financials": 0.95,
    "Consumer Discretionary": 1.0,
    "Communication Services": 1.1,
    "Industrials": 0.9,
    "Consumer Staples": 0.85,
    "Energy": 0.8,
    "Utilities": 0.7,
    "Real Estate": 0.75,
    "Materials": 0.85,
}


def _stable_float(seed: str, lo: float, hi: float) -> float:
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    return lo + (h / 0xFFFFFFFF) * (hi - lo)


def synthesize_fundamentals(ticker: str, sector: str) -> dict[str, float]:
    bias = SECTOR_BIAS.get(sector, 1.0)
    market_cap = _stable_float(f"{ticker}-mc", 8e9, 3.2e12) * bias
    # Mega-caps override
    mega = {
        "AAPL": 3.4e12,
        "MSFT": 3.1e12,
        "NVDA": 2.8e12,
        "GOOGL": 2.1e12,
        "GOOG": 2.1e12,
        "AMZN": 2.0e12,
        "META": 1.4e12,
        "BRK-B": 1.0e12,
        "LLY": 7.5e11,
        "AVGO": 9.0e11,
        "TSLA": 9.5e11,
        "JPM": 6.0e11,
        "V": 5.5e11,
        "UNH": 4.5e11,
        "XOM": 4.8e11,
        "MA": 4.4e11,
        "COST": 3.8e11,
        "PG": 3.7e11,
        "JNJ": 3.6e11,
        "HD": 3.5e11,
        "ABBV": 3.3e11,
        "WMT": 6.5e11,
    }
    if ticker in mega:
        market_cap = mega[ticker]
    pe = _stable_float(f"{ticker}-pe", 8, 55)
    eps = _stable_float(f"{ticker}-eps", 0.5, 25)
    revenue = market_cap * _stable_float(f"{ticker}-rev", 0.15, 0.9)
    de = _stable_float(f"{ticker}-de", 0.05, 2.8)
    div = _stable_float(f"{ticker}-div", 0.0, 0.045)
    price = _stable_float(f"{ticker}-px", 25, 650)
    return {
        "market_cap": market_cap,
        "pe_ratio": pe,
        "eps": eps,
        "revenue": revenue,
        "debt_to_equity": de,
        "dividend_yield": div,
        "price": price,
    }


def synthesize_change(ticker: str) -> float:
    # Daily % change roughly -4% to +4%
    return _stable_float(f"{ticker}-chg-{now_et().date().isoformat()}", -3.8, 3.8)


async def seed_companies(db: AsyncSession) -> int:
    companies = load_sp500()
    existing = {r[0] for r in (await db.execute(select(Company.ticker))).all()}
    added = 0
    for c in companies:
        ticker = c["ticker"]
        if ticker in existing:
            row = (
                await db.execute(select(Company).where(Company.ticker == ticker))
            ).scalar_one()
            # Never overwrite live fundamentals/prices — only keep constituent metadata fresh
            row.name = c["name"]
            row.sector = c["sector"]
            row.industry = c["industry"]
            if not row.description:
                row.description = (
                    f"{c['name']} is an S&P 500 company in the {c['sector']} sector, "
                    f"specifically {c['industry']}."
                )
        else:
            fundamentals = synthesize_fundamentals(ticker, c["sector"])
            db.add(
                Company(
                    ticker=ticker,
                    name=c["name"],
                    sector=c["sector"],
                    industry=c["industry"],
                    market_cap=fundamentals["market_cap"],
                    pe_ratio=fundamentals["pe_ratio"],
                    eps=fundamentals["eps"],
                    revenue=fundamentals["revenue"],
                    debt_to_equity=fundamentals["debt_to_equity"],
                    dividend_yield=fundamentals["dividend_yield"],
                    description=(
                        f"{c['name']} is an S&P 500 company in the {c['sector']} sector, "
                        f"specifically {c['industry']}."
                    ),
                    updated_at=datetime.utcnow(),
                )
            )
            added += 1
    await db.commit()
    return added


async def seed_quotes(db: AsyncSession) -> int:
    session = get_market_session()
    companies = (await db.execute(select(Company))).scalars().all()
    count = 0
    for c in companies:
        fund = synthesize_fundamentals(c.ticker, c.sector)
        price = fund["price"]
        chg_pct = synthesize_change(c.ticker)
        change = price * (chg_pct / 100)
        prev = price - change
        existing = (
            await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == c.ticker))
        ).scalar_one_or_none()
        if existing:
            existing.price = price
            existing.change = change
            existing.change_pct = chg_pct
            existing.previous_close = prev
            existing.label = session.label
            existing.session_state = session.state
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                QuoteSnapshot(
                    ticker=c.ticker,
                    price=price,
                    change=change,
                    change_pct=chg_pct,
                    previous_close=prev,
                    label=session.label,
                    session_state=session.state,
                    updated_at=datetime.utcnow(),
                )
            )
        count += 1
    await db.commit()
    return count


async def seed_price_history(db: AsyncSession, days: int = 120) -> int:
    """Synthetic OHLCV for chart demos — replaceable by yfinance refresh job."""
    companies = (await db.execute(select(Company))).scalars().all()
    # Only store history for a manageable subset + any with relationships focus
    priority = {
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
        "JPM",
        "XOM",
        "JNJ",
        "UNH",
        "V",
        "WMT",
        "PG",
        "MA",
        "HD",
        "CVX",
        "KO",
        "PEP",
        "DIS",
        "NFLX",
        "AMD",
        "INTC",
        "BA",
        "CAT",
    }
    tickers = [c for c in companies if c.ticker in priority] or companies[:40]
    bars = 0
    today = now_et().date()
    for c in tickers:
        base = synthesize_fundamentals(c.ticker, c.sector)["price"]
        await db.execute(delete(PriceBar).where(PriceBar.ticker == c.ticker))
        px = base * 0.85
        for i in range(days, 0, -1):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:
                continue
            drift = _stable_float(f"{c.ticker}-{d}-d", -0.025, 0.028)
            open_p = px
            close_p = max(1.0, px * (1 + drift))
            high_p = max(open_p, close_p) * (1 + _stable_float(f"{c.ticker}-{d}-h", 0, 0.015))
            low_p = min(open_p, close_p) * (1 - _stable_float(f"{c.ticker}-{d}-l", 0, 0.015))
            vol = _stable_float(f"{c.ticker}-{d}-v", 5e6, 8e7)
            db.add(
                PriceBar(
                    ticker=c.ticker,
                    bar_date=d,
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=vol,
                )
            )
            px = close_p
            bars += 1
    await db.commit()
    return bars


async def seed_relationships(db: AsyncSession) -> int:
    valid = {r[0] for r in (await db.execute(select(Company.ticker))).all()}
    await db.execute(delete(CompanyRelationship))
    added = 0
    for rel in load_relationships():
        src, tgt = rel["source"], rel["target"]
        if src not in valid or tgt not in valid:
            continue
        db.add(
            CompanyRelationship(
                source_ticker=src,
                target_ticker=tgt,
                relationship_type=rel["type"],
                plain_english=rel["plain_english"],
            )
        )
        added += 1
    await db.commit()
    return added


async def seed_macro(db: AsyncSession) -> int:
    data = load_macro_seed()
    await db.execute(delete(MacroObservation))
    await db.execute(delete(EconomicEvent))
    count = 0
    for series_id, points in data.get("series", {}).items():
        for p in points:
            db.add(
                MacroObservation(
                    series_id=series_id,
                    obs_date=date.fromisoformat(p["date"]),
                    value=float(p["value"]),
                )
            )
            count += 1
    for ev in data.get("events", []):
        db.add(
            EconomicEvent(
                event_date=date.fromisoformat(ev["date"]),
                title=ev["title"],
                category=ev["category"],
                plain_english=ev["plain_english"],
            )
        )
        count += 1
    await db.commit()
    return count


async def refresh_live_quotes_yfinance(
    db: AsyncSession,
    sample: int = 50,
    *,
    full: bool = True,
) -> dict[str, Any]:
    """Pull real quotes (and optionally fundamentals/history) from yfinance."""
    settings = get_settings()
    from app.services.prices import fetch_all_quotes, refresh_universe, upsert_quotes

    if settings.demo_mode:
        n = await seed_quotes(db)
        return {"mode": "demo", "updated": n, "warning": "DEMO_MODE=true: using synthetic prices"}

    try:
        if full:
            return await refresh_universe(db, with_fundamentals=True, with_history=True)
        companies = (await db.execute(select(Company))).scalars().all()
        tickers = [c.ticker for c in companies]
        priority = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "XOM", "JNJ"]
        others = [t for t in tickers if t not in priority]
        random.shuffle(others)
        subset = priority + others[: max(0, sample - len(priority))]
        quotes = fetch_all_quotes(subset)
        updated = await upsert_quotes(db, quotes)
        return {"mode": "yfinance", "updated": updated, "quotes": updated}
    except Exception as exc:  # noqa: BLE001
        return {"mode": "error", "error": str(exc), "updated": 0}
