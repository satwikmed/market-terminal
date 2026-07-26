from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import backtest as backtest_service

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class Holding(BaseModel):
    ticker: str
    weight: float = 1.0


class BacktestRequest(BaseModel):
    holdings: list[Holding]


@router.post("/backtest")
async def backtest(body: BacktestRequest, db: AsyncSession = Depends(get_db)):
    if not body.holdings:
        raise HTTPException(400, "Add at least one holding.")
    if len(body.holdings) > 15:
        raise HTTPException(400, "Keep the basket to 15 names or fewer.")
    result = await backtest_service.run_backtest(
        db, [{"ticker": h.ticker, "weight": h.weight} for h in body.holdings]
    )
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result
