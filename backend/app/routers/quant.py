from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import quant as quant_service

router = APIRouter(prefix="/api/quant", tags=["quant"])


@router.get("/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    return await quant_service.risk_leaderboard(db)


@router.get("/correlation")
async def correlation(
    tickers: str = Query(..., description="Comma separated tickers"),
    db: AsyncSession = Depends(get_db),
):
    names = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(names) < 2:
        raise HTTPException(400, "Provide at least two tickers.")
    return await quant_service.correlation_matrix(db, names)


@router.get("/{ticker}")
async def risk(ticker: str, db: AsyncSession = Depends(get_db)):
    data = await quant_service.risk_metrics(db, ticker)
    if data is None:
        raise HTTPException(
            404,
            "Not enough price history to compute risk metrics for this ticker.",
        )
    return data
