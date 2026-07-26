"""Cross-sectional screener over the whole S&P 500.

Combines database fundamentals (market cap, P/E, EPS, dividend yield) with
momentum computed from stored price bars, so the user can rank and filter all
503 names on real numbers.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Company, PriceBar, QuoteSnapshot


def _pct_change(closes: list[float], lookback: int) -> float | None:
    if len(closes) <= lookback:
        return None
    old = closes[-lookback - 1]
    if not old:
        return None
    return round((closes[-1] / old - 1) * 100, 1)


async def screen(db: AsyncSession) -> dict:
    companies = (await db.execute(select(Company))).scalars().all()
    quotes = {q.ticker: q for q in (await db.execute(select(QuoteSnapshot))).scalars().all()}

    all_bars = (
        await db.execute(
            select(PriceBar.ticker, PriceBar.close).order_by(PriceBar.ticker, PriceBar.bar_date.asc())
        )
    ).all()
    grouped: dict[str, list[float]] = {}
    for t, c in all_bars:
        grouped.setdefault(t, []).append(float(c))

    rows = []
    for c in companies:
        closes = grouped.get(c.ticker, [])
        q = quotes.get(c.ticker)
        rows.append(
            {
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "industry": c.industry,
                "price": q.price if q else None,
                "change_pct": q.change_pct if q else None,
                "market_cap": c.market_cap,
                "pe_ratio": c.pe_ratio,
                "eps": c.eps,
                "dividend_yield_pct": round(c.dividend_yield * 100, 2) if c.dividend_yield is not None else None,
                "mom_1m_pct": _pct_change(closes, 21),
                "mom_3m_pct": _pct_change(closes, 63),
                "mom_6m_pct": _pct_change(closes, 126),
            }
        )

    sectors = sorted({c.sector for c in companies})
    return {"count": len(rows), "sectors": sectors, "rows": rows}
