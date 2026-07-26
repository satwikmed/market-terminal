"""US equity market hours helpers (Eastern Time)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


@dataclass
class MarketSession:
    state: str  # open | closed_weekday | weekend | premarket
    label: str
    is_live: bool


def now_et() -> datetime:
    return datetime.now(ET)


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def regular_session_open(dt: datetime) -> bool:
    if not is_weekday(dt):
        return False
    t = dt.time()
    return time(9, 30) <= t < time(16, 0)


def get_market_session(dt: datetime | None = None) -> MarketSession:
    dt = dt or now_et()
    weekday = dt.weekday()  # Mon=0 ... Sun=6
    t = dt.time()

    if weekday >= 5:  # Saturday / Sunday
        return MarketSession(
            state="weekend",
            label="Friday's Close",
            is_live=False,
        )

    if t < time(9, 30):
        if t >= time(4, 0):
            return MarketSession(
                state="premarket",
                label="Pre-Market",
                is_live=False,
            )
        return MarketSession(
            state="closed_weekday",
            label="Previous Close",
            is_live=False,
        )

    if time(9, 30) <= t < time(16, 0):
        return MarketSession(state="open", label="Live", is_live=True)

    # After 4pm ET on a weekday
    return MarketSession(
        state="closed_weekday",
        label="Today's Close",
        is_live=False,
    )


def last_trading_day(dt: datetime | None = None) -> datetime:
    """Return the most recent weekday date at/before dt (ET)."""
    dt = dt or now_et()
    d = dt
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d
