import asyncio
import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import MacroObservation
from app.schemas import MacroIndicator
from app.services.data_loader import load_macro_seed
from app.services.explainers import explain_metric
from app.services.macro_data import next_fomc_meeting, refresh_fred

router = APIRouter(prefix="/api/macro", tags=["macro"])

_fomc_cache: dict | None = None
_fomc_cached_at = 0.0
FOMC_CACHE_SECONDS = 6 * 60 * 60


async def _cached_fomc() -> dict:
    global _fomc_cache, _fomc_cached_at
    if _fomc_cache and time.monotonic() - _fomc_cached_at < FOMC_CACHE_SECONDS:
        return _fomc_cache
    try:
        value = await asyncio.wait_for(next_fomc_meeting(), timeout=3)
    except Exception:  # noqa: BLE001
        value = {
            "date": None,
            "days_until": None,
            "source": "Federal Reserve FOMC calendar (temporarily unavailable)",
            "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        }
    _fomc_cache = value
    _fomc_cached_at = time.monotonic()
    return value


SERIES_META = {
    "CPIAUCSL_YOY": ("Inflation (CPI YoY)", "%", "cpi"),
    "UNRATE": ("Unemployment Rate", "%", "unemployment"),
    "FEDFUNDS": ("Fed Funds Rate", "%", "fed_funds"),
    "A191RL1Q225SBEA": ("Real GDP Growth", "%", "gdp"),
    "UMCSENT": ("Consumer Confidence", "index", "consumer_confidence"),
    "T10Y2Y": ("2s10s Yield Spread", "%", "yield_spread"),
    "RECESSION_PROB": ("Recession Probability", "%", "recession"),
}


@router.get("/dashboard")
async def macro_dashboard(db: AsyncSession = Depends(get_db)):
    indicators: list[MacroIndicator] = []
    freshness: dict[str, str] = {}
    for series_id, (label, unit, explain_key) in SERIES_META.items():
        rows = (
            await db.execute(
                select(MacroObservation)
                .where(MacroObservation.series_id == series_id)
                .order_by(MacroObservation.obs_date.asc())
            )
        ).scalars().all()
        if not rows:
            continue
        latest = rows[-1]
        freshness[series_id] = latest.obs_date.isoformat()
        explained = explain_metric(explain_key, latest.value)
        if explain_key == "recession":
            explained = {
                "metric": "Recession Probability",
                "value_display": f"{latest.value:.0f}%",
                "plain_english": (
                    f"About {latest.value:.0f}%: a public model estimate of recession odds. "
                    "This moves with jobs, spending, and yield curve data. It's a weather forecast for the economy, not destiny."
                ),
            }
        indicators.append(
            MacroIndicator(
                id=series_id,
                label=label,
                value=latest.value,
                as_of=latest.obs_date,
                unit=unit,
                plain_english=explained["plain_english"],
                history=[{"date": r.obs_date.isoformat(), "value": r.value} for r in rows],
            )
        )

    seed = load_macro_seed()
    basket = []
    for key, label in [
        ("CPI_HOUSING", "Housing"),
        ("CPI_FOOD", "Food"),
        ("CPI_ENERGY", "Energy"),
        ("CPI_TRANSPORT", "Transportation"),
        ("CPI_MEDICAL", "Medical"),
        ("CPI_OTHER", "Core (less food & energy)"),
    ]:
        row = (
            await db.execute(
                select(MacroObservation)
                .where(MacroObservation.series_id == key)
                .order_by(MacroObservation.obs_date.desc())
            )
        ).scalars().first()
        if row:
            basket.append({"component": label, "value": row.value})

    # FRED refreshes belong to the scheduler, not this request path. The
    # calendar is the only live lookup left here and must never hold the whole
    # economy page hostage when the Fed site is slow.
    fomc = await _cached_fomc()

    events = []
    if fomc["date"]:
        events.append(
            {
                "date": fomc["date"],
                "title": "FOMC Interest Rate Decision",
                "category": "fed",
                "plain_english": (
                    "The Federal Reserve will decide whether to raise, cut, or hold "
                    "its main interest rate target."
                ),
                "source": fomc["source"],
            }
        )

    return {
        "indicators": [i.model_dump() for i in indicators],
        "inflation_basket": basket,
        "fed": {
            "next_fomc": fomc["date"],
            "days_until": fomc["days_until"],
            # Do not present made-up probabilities. A licensed futures source is
            # required before this field can be populated honestly.
            "probabilities": {"cut": None, "hold": None, "hike": None},
            "probabilities_available": False,
            "source": fomc["source"],
            "source_url": fomc["source_url"],
            "plain_english": (
                "When the Fed cuts rates, mortgages, credit cards, and business loans often get cheaper over time. "
                "When it hikes, borrowing usually gets more expensive and savings rates can rise. "
                "Market implied odds are intentionally hidden until a reliable licensed source is connected."
            ),
        },
        "events": events,
        "rate_sensitivity": seed.get("rate_sensitivity", {}),
        "data_sources": {
            "macro": "Federal Reserve Bank of St. Louis (FRED), live CSV feeds",
            "macro_url": "https://fred.stlouisfed.org/",
            "fomc": fomc["source"],
            "freshness": freshness,
            "rate_sensitivity": (
                "Educational historical sensitivity estimate; not a live predictive model"
            ),
        },
        "yield_curve_note": (
            "When the 2 year yield is higher than the 10 year (negative spread), the curve is 'inverted'. "
            "Historically that pattern has often appeared before recessions: a tendency, not a guarantee."
        ),
    }


@router.get("/rate-sensitivity")
async def rate_sensitivity():
    seed = load_macro_seed()
    return {
        "description": (
            "Historical correlation style sensitivity of sectors to rising Fed rates "
            "(negative = tended to weaken when rates rose). Educational estimate for the bubble map overlay."
        ),
        "sectors": seed.get("rate_sensitivity", {}),
        "disclaimer": "Historical tendency only: not a prediction for any future rate move.",
    }


@router.post("/fred/refresh")
async def fred_refresh(db: AsyncSession = Depends(get_db)):
    """Refresh live public FRED feeds; no API key required."""
    return await refresh_fred(db)
