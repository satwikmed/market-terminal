"""Manual data-refresh trigger, so recovering a failed load never needs a redeploy."""

import asyncio
import logging

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_refresh_task: asyncio.Task | None = None


@router.post("/refresh")
async def trigger_refresh(x_admin_token: str = Header(default="")):
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(503, "Manual refresh is disabled (ADMIN_TOKEN is not set).")
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token.")

    global _refresh_task
    from app.main import BOOTSTRAP, _full_refresh

    if _refresh_task and not _refresh_task.done():
        return {"started": False, "reason": "a refresh is already running", "state": BOOTSTRAP}

    _refresh_task = asyncio.create_task(_full_refresh())
    logger.info("manual market refresh triggered")
    return {"started": True, "note": "Refresh runs in the background; poll /api/status."}
