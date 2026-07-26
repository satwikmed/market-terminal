from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Company, QuoteSnapshot
from app.schemas import QuoteOut, TickerTapeResponse
from app.services.market_hours import get_market_session
from app.services.seed import refresh_live_quotes_yfinance

router = APIRouter(prefix="/api/ticker", tags=["ticker"])


@router.get("/tape", response_model=TickerTapeResponse)
async def ticker_tape(db: AsyncSession = Depends(get_db)):
    session = get_market_session()
    quotes = (await db.execute(select(QuoteSnapshot).order_by(QuoteSnapshot.ticker))).scalars().all()
    companies = {
        c.ticker: c.name
        for c in (await db.execute(select(Company))).scalars().all()
    }
    # Rotate a readable subset for the tape; still S&P 500 only
    ordered = sorted(quotes, key=lambda q: abs(q.change_pct), reverse=True)
    top_movers = ordered[:40]
    mega = [q for q in quotes if q.ticker in {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "V", "XOM"}]
    seen = set()
    selected: list[QuoteSnapshot] = []
    for q in mega + top_movers + quotes[:80]:
        if q.ticker in seen:
            continue
        seen.add(q.ticker)
        selected.append(q)
        if len(selected) >= 120:
            break

    return TickerTapeResponse(
        session_label=session.label,
        session_state=session.state,
        is_live=session.is_live,
        quotes=[
            QuoteOut(
                ticker=q.ticker,
                price=q.price,
                change=q.change,
                change_pct=q.change_pct,
                previous_close=q.previous_close,
                label=session.label,
                session_state=session.state,
                name=companies.get(q.ticker),
            )
            for q in selected
        ],
    )


@router.post("/refresh")
async def refresh_quotes(full: bool = False, db: AsyncSession = Depends(get_db)):
    # Default: quotes-only refresh (fast). full=true also refreshes fundamentals/history.
    return await refresh_live_quotes_yfinance(db, full=full)
