from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Company
from app.services import fundamentals as fundamentals_service

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])


@router.get("/{ticker}")
async def company_financials(ticker: str, db: AsyncSession = Depends(get_db)):
    ticker = ticker.upper()
    company = (
        await db.execute(select(Company).where(Company.ticker == ticker))
    ).scalar_one_or_none()
    if not company:
        raise HTTPException(404, f"{ticker} is not in the S&P 500 universe.")

    data = await fundamentals_service.get_financials(db, ticker)
    if data is None:
        raise HTTPException(
            502,
            "SEC XBRL financial facts are unavailable for this company right now.",
        )

    # Peer percentile for a couple of headline ratios, within the same sector.
    peers = (
        await db.execute(select(Company).where(Company.sector == company.sector))
    ).scalars().all()
    data["peer_context"] = {
        "sector": company.sector,
        "peer_count": len(peers),
    }
    data["company_name"] = company.name
    return data
