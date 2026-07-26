"""Portfolio construction + historical backtest against the S&P 500 (SPY).

Given target weights, we rebalance to those weights on day one and let them
drift (buy-and-hold), then measure the basket's realised return, volatility,
drawdown, beta, and each holding's contribution — all from stored daily bars.
This is a historical simulation for education, not a forecast.
"""

from __future__ import annotations

import math
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import PriceBar
from app.services.quant import BENCHMARK, RISK_FREE_ANNUAL, TRADING_DAYS, _beta, _max_drawdown, _returns, _stdev


async def _closes(db: AsyncSession, ticker: str) -> dict[date, float]:
    rows = (
        await db.execute(
            select(PriceBar.bar_date, PriceBar.close)
            .where(PriceBar.ticker == ticker)
            .order_by(PriceBar.bar_date.asc())
        )
    ).all()
    return {r[0]: float(r[1]) for r in rows}


async def run_backtest(db: AsyncSession, holdings: list[dict]) -> dict:
    """holdings: [{"ticker": "AAPL", "weight": 0.5}, ...] weights need not sum to 1."""
    tickers = [h["ticker"].upper() for h in holdings]
    raw_weights = [max(0.0, float(h.get("weight", 0))) for h in holdings]
    total_w = sum(raw_weights) or 1.0
    weights = {t: w / total_w for t, w in zip(tickers, raw_weights)}

    close_maps = {t: await _closes(db, t) for t in tickers}
    bench_map = await _closes(db, BENCHMARK)

    # Align on the dates every holding (and the benchmark) share.
    common: set[date] | None = None
    for t in tickers:
        ds = set(close_maps[t].keys())
        common = ds if common is None else (common & ds)
    if bench_map:
        common = common & set(bench_map.keys()) if common else set(bench_map.keys())
    dates = sorted(common) if common else []
    if len(dates) < 30:
        return {"error": "Not enough overlapping price history for these tickers."}

    # Normalised price paths (start = 1.0) per holding.
    norm = {t: [close_maps[t][d] / close_maps[t][dates[0]] for d in dates] for t in tickers}
    port_curve = []
    for i in range(len(dates)):
        val = sum(weights[t] * norm[t][i] for t in tickers)
        port_curve.append(val)

    bench_curve = [bench_map[d] / bench_map[dates[0]] for d in dates] if bench_map else []

    port_rets = _returns(port_curve)
    bench_rets = _returns(bench_curve) if bench_curve else []

    ann_vol = _stdev(port_rets) * math.sqrt(TRADING_DAYS)
    total_return = port_curve[-1] - 1
    years = len(dates) / TRADING_DAYS
    cagr = (port_curve[-1]) ** (1 / years) - 1 if years > 0 else 0.0
    sharpe = round((cagr - RISK_FREE_ANNUAL) / ann_vol, 2) if ann_vol > 0 else None

    bench_total = (bench_curve[-1] - 1) if bench_curve else None

    # Per-holding contribution to total return.
    contributions = []
    for t in tickers:
        holding_return = norm[t][-1] - 1
        contributions.append(
            {
                "ticker": t,
                "weight_pct": round(weights[t] * 100, 1),
                "return_pct": round(holding_return * 100, 1),
                "contribution_pct": round(weights[t] * holding_return * 100, 1),
            }
        )
    contributions.sort(key=lambda c: c["contribution_pct"], reverse=True)

    # Downsample the equity curve for a clean chart (~180 points).
    step = max(1, len(dates) // 180)
    curve = [
        {
            "date": dates[i].isoformat(),
            "portfolio": round(port_curve[i], 4),
            "benchmark": round(bench_curve[i], 4) if bench_curve else None,
        }
        for i in range(0, len(dates), step)
    ]
    if curve and curve[-1]["date"] != dates[-1].isoformat():
        curve.append(
            {
                "date": dates[-1].isoformat(),
                "portfolio": round(port_curve[-1], 4),
                "benchmark": round(bench_curve[-1], 4) if bench_curve else None,
            }
        )

    return {
        "start_date": dates[0].isoformat(),
        "end_date": dates[-1].isoformat(),
        "trading_days": len(dates),
        "holdings": [{"ticker": t, "weight_pct": round(weights[t] * 100, 1)} for t in tickers],
        "metrics": {
            "total_return_pct": round(total_return * 100, 1),
            "cagr_pct": round(cagr * 100, 1),
            "annualized_volatility_pct": round(ann_vol * 100, 1),
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": round(_max_drawdown(port_curve) * 100, 1),
            "beta_vs_spy": _beta(port_rets, bench_rets) if bench_rets else None,
            "benchmark_total_return_pct": round(bench_total * 100, 1) if bench_total is not None else None,
            "excess_return_pct": round((total_return - bench_total) * 100, 1) if bench_total is not None else None,
        },
        "contributions": contributions,
        "curve": curve,
        "benchmark": BENCHMARK,
        "note": "Buy-and-hold simulation from stored daily closes. Educational, not advice.",
    }
