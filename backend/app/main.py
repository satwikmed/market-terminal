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
    macro,
    ownership,
    relationships,
    status,
    ticker,
)
from app.services.scheduler import shutdown_scheduler, start_scheduler
from app.services.seed import seed_companies, seed_macro, seed_quotes, seed_relationships

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.startup")


async def _bootstrap_market_data(db) -> None:
    settings = get_settings()
    if settings.demo_mode:
        await seed_quotes(db)
        logger.info("demo mode: seeded synthetic quotes")
        return

    from app.services.prices import refresh_universe

    # Synthetic seed prices were typically under $100, so a realistic mega-cap
    # price is a reliable signal that the cached quotes came from the live feed.
    aapl = (
        await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == "AAPL"))
    ).scalar_one_or_none()
    existing = (await db.execute(select(func.count()).select_from(QuoteSnapshot))).scalar_one()
    if aapl and aapl.price > 100 and existing >= 400:
        logger.info("using cached live quotes (AAPL=$%.2f, n=%s)", aapl.price, existing)
        return

    if not settings.startup_refresh:
        logger.info("startup refresh disabled; leaving %s cached quotes in place", existing)
        return

    try:
        result = await refresh_universe(
            db, with_fundamentals=True, with_history=True, history_period="6mo"
        )
        logger.info("full live market refresh: %s", result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("live refresh failed (%s); falling back to synthetic quotes", exc)
        await seed_quotes(db)


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

        await _bootstrap_market_data(db)

    start_scheduler()
    try:
        yield
    finally:
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
    }
