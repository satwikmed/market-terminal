from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import screener as screener_service

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("")
async def screen(db: AsyncSession = Depends(get_db)):
    return await screener_service.screen(db)
