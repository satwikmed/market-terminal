"""Background refresh jobs so a deployed instance stays current without manual pokes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.services.market_hours import get_market_session

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

LAST_RUN: dict[str, dict[str, Any]] = {}


def _record(job: str, status: str, detail: Any = None) -> None:
    LAST_RUN[job] = {
        "status": status,
        "detail": detail,
        "at": datetime.utcnow().isoformat() + "Z",
    }


async def refresh_quotes_job() -> None:
    """Quotes only — cheap enough to run on a tight loop while markets are open."""
    session = get_market_session()
    if session.state in {"weekend", "closed"}:
        _record("quotes", "skipped", f"market {session.state}")
        return
    from app.services.prices import fetch_all_quotes, upsert_quotes

    try:
        async with SessionLocal() as db:
            from sqlalchemy import select

            from app.models.entities import Company

            tickers = list((await db.execute(select(Company.ticker))).scalars().all())
            import asyncio

            quotes = await asyncio.to_thread(fetch_all_quotes, tickers)
            count = await upsert_quotes(db, quotes)
        _record("quotes", "ok", f"{count} quotes")
        logger.info("scheduled quote refresh: %s quotes", count)
    except Exception as exc:  # noqa: BLE001
        _record("quotes", "error", str(exc))
        logger.warning("scheduled quote refresh failed: %s", exc)


async def refresh_daily_job() -> None:
    """Fundamentals plus price history, once per day after the close."""
    from app.services.prices import refresh_universe

    try:
        async with SessionLocal() as db:
            result = await refresh_universe(
                db, with_fundamentals=True, with_history=True, history_period="2y"
            )
        _record("daily_market", "ok", {k: result[k] for k in ("quotes", "fundamentals", "history_bars") if k in result})
        logger.info("scheduled daily refresh: %s", result)
    except Exception as exc:  # noqa: BLE001
        _record("daily_market", "error", str(exc))
        logger.warning("scheduled daily refresh failed: %s", exc)


async def refresh_macro_job() -> None:
    from app.services.macro_data import refresh_fred

    try:
        async with SessionLocal() as db:
            count = await refresh_fred(db)
        _record("macro", "ok", f"{count} observations")
        logger.info("scheduled macro refresh: %s observations", count)
    except Exception as exc:  # noqa: BLE001
        _record("macro", "error", str(exc))
        logger.warning("scheduled macro refresh failed: %s", exc)


def start_scheduler() -> AsyncIOScheduler | None:
    global _scheduler
    settings = get_settings()
    if not settings.enable_scheduler or _scheduler is not None:
        return _scheduler

    scheduler = AsyncIOScheduler(timezone="America/New_York")
    scheduler.add_job(
        refresh_quotes_job,
        IntervalTrigger(minutes=settings.quote_refresh_minutes),
        id="quotes",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        refresh_daily_job,
        CronTrigger(day_of_week="mon-fri", hour=17, minute=15),
        id="daily_market",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        refresh_macro_job,
        CronTrigger(hour=8, minute=30),
        id="macro",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler started (quotes every %s min)", settings.quote_refresh_minutes)
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def scheduler_status() -> dict[str, Any]:
    settings = get_settings()
    if _scheduler is None:
        return {"enabled": settings.enable_scheduler, "running": False, "jobs": [], "last_run": LAST_RUN}
    return {
        "enabled": True,
        "running": _scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in _scheduler.get_jobs()
        ],
        "last_run": LAST_RUN,
    }
