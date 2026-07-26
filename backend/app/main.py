import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models.entities import MacroObservation, QuoteSnapshot
from app.routers import (
    ai,
    bubble,
    companies,
    filings,
    fundamentals,
    macro,
    ownership,
    portfolio,
    quant,
    relationships,
    screener,
    status,
    ticker,
)
from app.services.scheduler import shutdown_scheduler, start_scheduler
from app.services.seed import seed_companies, seed_macro, seed_quotes, seed_relationships

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.startup")


BOOTSTRAP: dict[str, object] = {"state": "pending", "detail": None}


async def _full_refresh() -> None:
    """Pull the whole universe. Slow (minutes), so it never blocks startup."""
    BOOTSTRAP.update(state="running", detail="fetching quotes, fundamentals, and history")
    from app.services.prices import refresh_universe

    try:
        async with SessionLocal() as db:
            result = await refresh_universe(
                db, with_fundamentals=True, with_history=True, history_period="2y"
            )
        BOOTSTRAP.update(state="complete", detail=result)
        logger.info("initial market load complete: %s", result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("initial market load failed (%s); seeding synthetic quotes", exc)
        try:
            async with SessionLocal() as db:
                await seed_quotes(db)
            BOOTSTRAP.update(state="fallback", detail=str(exc))
        except Exception as seed_exc:  # noqa: BLE001
            BOOTSTRAP.update(state="failed", detail=str(seed_exc))


async def _plan_market_bootstrap(db) -> bool:
    """Decide whether a full refresh is needed. Returns True if one should run."""
    settings = get_settings()
    if settings.demo_mode:
        await seed_quotes(db)
        BOOTSTRAP.update(state="complete", detail="demo mode: synthetic quotes")
        return False

    # Synthetic seed prices were typically under $100, so a realistic mega-cap
    # price is a reliable signal that the cached quotes came from the live feed.
    aapl = (
        await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == "AAPL"))
    ).scalar_one_or_none()
    existing = (await db.execute(select(func.count()).select_from(QuoteSnapshot))).scalar_one()
    if aapl and aapl.price > 100 and existing >= 400:
        logger.info("using cached live quotes (AAPL=$%.2f, n=%s)", aapl.price, existing)
        BOOTSTRAP.update(state="complete", detail=f"{existing} cached live quotes")
        return False

    if not settings.startup_refresh:
        logger.info("startup refresh disabled; leaving %s cached quotes in place", existing)
        BOOTSTRAP.update(state="skipped", detail="startup_refresh disabled")
        return False

    return True


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with SessionLocal() as db:
        await seed_companies(db)
        await seed_relationships(db)

        macro_count = (
            await db.execute(select(func.count()).select_from(MacroObservation))
        ).scalar_one()
        if macro_count == 0:
            await seed_macro(db)

        needs_refresh = await _plan_market_bootstrap(db)

    # Detached so the app can answer health checks immediately. A cold database
    # takes several minutes to populate, which would otherwise fail the deploy.
    task = asyncio.create_task(_full_refresh()) if needs_refresh else None

    start_scheduler()
    try:
        yield
    finally:
        if task and not task.done():
            task.cancel()
        shutdown_scheduler()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description=(
        "Plain-English market data for beginners. Live quotes from Yahoo Finance, filings from "
        "SEC EDGAR, macro series from FRED, and an AI layer that is only allowed to explain "
        "evidence this API computed itself."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(ticker.router)
app.include_router(bubble.router)
app.include_router(relationships.router)
app.include_router(ai.router)
app.include_router(macro.router)
app.include_router(ownership.router)
app.include_router(filings.router)
app.include_router(fundamentals.router)
app.include_router(quant.router)
app.include_router(screener.router)
app.include_router(portfolio.router)
app.include_router(status.router)


@app.get("/api/health")
async def health():
    from app.services.market_hours import get_market_session

    session = get_market_session()
    return {
        "status": "ok",
        "app": settings.app_name,
        "market": {"state": session.state, "label": session.label, "is_live": session.is_live},
        "demo_mode": settings.demo_mode,
        "data_load": BOOTSTRAP["state"],
    }
