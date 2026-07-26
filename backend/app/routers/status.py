"""One endpoint that answers 'is this data real, and how old is it?' for every source."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.entities import (
    Company,
    EconomicEvent,
    FinancialsCache,
    MacroObservation,
    PriceBar,
    QuoteSnapshot,
)
from app.services import sec_filings
from app.services.market_hours import get_market_session
from app.services.scheduler import scheduler_status

router = APIRouter(prefix="/api/status", tags=["status"])


def _age_minutes(stamp: datetime | None) -> float | None:
    if stamp is None:
        return None
    return round((datetime.utcnow() - stamp).total_seconds() / 60, 1)


@router.get("")
async def status(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    session = get_market_session()

    companies = (await db.execute(select(func.count()).select_from(Company))).scalar_one()
    quotes = (await db.execute(select(func.count()).select_from(QuoteSnapshot))).scalar_one()
    bars = (await db.execute(select(func.count()).select_from(PriceBar))).scalar_one()
    newest_quote = (await db.execute(select(func.max(QuoteSnapshot.updated_at)))).scalar_one()
    newest_bar = (await db.execute(select(func.max(PriceBar.bar_date)))).scalar_one()
    macro_rows = (await db.execute(select(func.count()).select_from(MacroObservation))).scalar_one()
    newest_macro = (await db.execute(select(func.max(MacroObservation.obs_date)))).scalar_one()
    events = (await db.execute(select(func.count()).select_from(EconomicEvent))).scalar_one()

    with_fundamentals = (
        await db.execute(
            select(func.count()).select_from(Company).where(Company.pe_ratio.isnot(None))
        )
    ).scalar_one()
    financials_cached = (
        await db.execute(select(func.count()).select_from(FinancialsCache))
    ).scalar_one()

    provider = settings.resolved_ai_provider

    from app.main import BOOTSTRAP

    return {
        "app": settings.app_name,
        "server_time": datetime.utcnow().isoformat() + "Z",
        "market": {"state": session.state, "label": session.label, "is_live": session.is_live},
        "mode": "demo (synthetic quotes)" if settings.demo_mode else "live",
        "initial_load": dict(BOOTSTRAP),
        "sources": [
            {
                "id": "quotes",
                "label": "Stock quotes & fundamentals",
                "provider": "Yahoo Finance (unofficial endpoints)",
                "status": "live" if quotes and not settings.demo_mode else "synthetic",
                "records": quotes,
                "last_updated": newest_quote.isoformat() + "Z" if newest_quote else None,
                "age_minutes": _age_minutes(newest_quote),
                "notes": (
                    f"{with_fundamentals} of {companies} companies have a live P/E on file. "
                    f"Quotes refresh about every {settings.quote_refresh_minutes} minutes while "
                    "the session is open. This is Yahoo's last-sale feed — not SIP / Level 1 "
                    "institutional data. Rate limits are retried with backoff; numbers already "
                    "on disk are never replaced with synthetic filler. A handful of names without "
                    "usable SEC revenue tags fall back to Yahoo TTM revenue for the company row only."
                ),
            },
            {
                "id": "history",
                "label": "Daily price history",
                "provider": "Yahoo Finance chart API",
                "status": "live" if bars else "empty",
                "records": bars,
                "last_updated": newest_bar.isoformat() if newest_bar else None,
                "notes": "Two years of daily bars per company, plus the SPY benchmark, refreshed after the close. Powers all risk, correlation, and backtest math.",
            },
            {
                "id": "fundamentals",
                "label": "Financial statements & ratios",
                "provider": "SEC EDGAR XBRL company facts",
                "status": "live" if financials_cached else "on demand",
                "records": financials_cached,
                "notes": (
                    f"{financials_cached} companies have parsed income, balance-sheet, and cash-flow "
                    "statements plus 12 computed ratios, straight from filings — no estimates."
                ),
            },
            {
                "id": "filings",
                "label": "SEC filings",
                "provider": "SEC EDGAR",
                "status": "live" if sec_filings.load_cik_map() else "unavailable",
                "records": len(sec_filings.load_cik_map()),
                "notes": "Fetched on demand per company; no API key required.",
            },
            {
                "id": "macro",
                "label": "Macroeconomic indicators",
                "provider": "FRED (St. Louis Fed)",
                "status": "live" if macro_rows else "empty",
                "records": macro_rows,
                "last_updated": newest_macro.isoformat() if newest_macro else None,
                "notes": "Official series; the most recent observation lags the calendar by design.",
            },
            {
                "id": "events",
                "label": "Economic calendar",
                "provider": "Federal Reserve calendar + FRED release dates",
                "status": "live" if events else "empty",
                "records": events,
                "notes": "Rate-decision probabilities are withheld — no free, reliable source is wired up.",
            },
            {
                "id": "ai",
                "label": "Plain-English AI layer",
                "provider": provider or "not configured",
                "status": "live" if provider else "disabled",
                "records": None,
                "notes": (
                    "Grounded in SEC filings and computed evidence. Move explanations fall back to a "
                    "deterministic evidence summary when no key is set."
                ),
            },
        ],
        "database": {
            "companies": companies,
            "quotes": quotes,
            "price_bars": bars,
            "macro_observations": macro_rows,
            "economic_events": events,
        },
        "scheduler": scheduler_status(),
    }
