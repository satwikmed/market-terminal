"""A factual market + macro snapshot, computed from data this app already stores."""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Company, EconomicEvent, MacroObservation, QuoteSnapshot
from app.services.market_hours import get_market_session, now_et


async def market_snapshot(db: AsyncSession, *, movers: int = 5) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(
                QuoteSnapshot.ticker,
                QuoteSnapshot.change_pct,
                QuoteSnapshot.price,
                QuoteSnapshot.updated_at,
                Company.name,
                Company.sector,
                Company.market_cap,
            ).join(Company, Company.ticker == QuoteSnapshot.ticker)
        )
    ).all()

    session = get_market_session()
    snapshot: dict[str, Any] = {
        "as_of": now_et().isoformat(),
        "session": session.label,
        "universe_size": len(rows),
    }
    if not rows:
        return snapshot

    moves = [r.change_pct for r in rows if r.change_pct is not None]
    advancers = sum(1 for m in moves if m > 0)
    snapshot["breadth"] = {
        "median_move_pct": round(statistics.median(moves), 3),
        "advancers": advancers,
        "decliners": len(moves) - advancers,
        "advance_decline_ratio": round(advancers / max(len(moves) - advancers, 1), 2),
    }

    # Cap-weighted move is a closer stand-in for the index than a plain average.
    weighted = [(r.change_pct, r.market_cap) for r in rows if r.change_pct is not None and r.market_cap]
    total_cap = sum(cap for _, cap in weighted)
    if total_cap:
        snapshot["breadth"]["cap_weighted_move_pct"] = round(
            sum(pct * cap for pct, cap in weighted) / total_cap, 3
        )

    by_sector: dict[str, list[float]] = {}
    for r in rows:
        if r.change_pct is not None:
            by_sector.setdefault(r.sector, []).append(r.change_pct)
    sector_moves = {s: round(statistics.median(v), 3) for s, v in by_sector.items() if len(v) >= 3}
    ranked = sorted(sector_moves.items(), key=lambda kv: kv[1], reverse=True)
    snapshot["sectors"] = {
        "best": ranked[:3],
        "worst": ranked[-3:][::-1],
    }

    ordered = sorted((r for r in rows if r.change_pct is not None), key=lambda r: r.change_pct)
    snapshot["movers"] = {
        "gainers": [
            {"ticker": r.ticker, "name": r.name, "change_pct": round(r.change_pct, 2), "sector": r.sector}
            for r in ordered[::-1][:movers]
        ],
        "losers": [
            {"ticker": r.ticker, "name": r.name, "change_pct": round(r.change_pct, 2), "sector": r.sector}
            for r in ordered[:movers]
        ],
    }

    stamps = [r.updated_at for r in rows if r.updated_at]
    if stamps:
        newest = max(stamps)
        snapshot["quote_freshness"] = {
            "updated_at": newest.isoformat() + "Z",
            "age_minutes": round((datetime.utcnow() - newest).total_seconds() / 60, 1),
        }

    macro_rows = (
        (
            await db.execute(
                select(MacroObservation).order_by(MacroObservation.obs_date.desc()).limit(400)
            )
        )
        .scalars()
        .all()
    )
    latest_by_series: dict[str, MacroObservation] = {}
    for row in macro_rows:
        if row.series_id not in latest_by_series:
            latest_by_series[row.series_id] = row
    snapshot["macro"] = {
        series: {"value": row.value, "as_of": row.obs_date.isoformat()}
        for series, row in sorted(latest_by_series.items())
    }

    events = (
        (
            await db.execute(
                select(EconomicEvent).order_by(EconomicEvent.event_date.desc()).limit(5)
            )
        )
        .scalars()
        .all()
    )
    snapshot["recent_events"] = [
        {"date": e.event_date.isoformat(), "title": e.title, "category": e.category} for e in events
    ]

    return snapshot
