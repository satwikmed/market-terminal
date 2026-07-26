from fastapi import APIRouter, HTTPException

from app.services.ownership_data import insider_activity, institutional_ownership

router = APIRouter(prefix="/api/ownership", tags=["ownership"])


@router.get("/{ticker}/institutions")
async def institutions(ticker: str):
    try:
        return institutional_ownership(ticker)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Live ownership data is temporarily unavailable: {exc}",
        ) from exc


@router.get("/{ticker}/insiders")
async def insiders(ticker: str):
    try:
        return insider_activity(ticker)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Live insider data is temporarily unavailable: {exc}",
        ) from exc
