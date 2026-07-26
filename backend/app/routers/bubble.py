from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Company, QuoteSnapshot
from app.schemas import BubbleMapResponse, BubbleNode

router = APIRouter(prefix="/api/bubble", tags=["bubble"])


@router.get("/map", response_model=BubbleMapResponse)
async def bubble_map(db: AsyncSession = Depends(get_db)):
    companies = (await db.execute(select(Company))).scalars().all()
    quotes = {
        q.ticker: q for q in (await db.execute(select(QuoteSnapshot))).scalars().all()
    }
    nodes: list[BubbleNode] = []
    for c in companies:
        q = quotes.get(c.ticker)
        nodes.append(
            BubbleNode(
                ticker=c.ticker,
                name=c.name,
                sector=c.sector,
                industry=c.industry,
                market_cap=c.market_cap or 1e9,
                change_pct=q.change_pct if q else 0.0,
                price=q.price if q else 0.0,
            )
        )
    sectors = sorted({n.sector for n in nodes})
    return BubbleMapResponse(nodes=nodes, sectors=sectors)
