"""Quantitative risk & technical metrics computed from stored price history.

Everything here is derived from the daily bars already in the database — no
external calls. Beta and correlations are measured against SPY, which we store
as a benchmark price series. All metrics annualise from daily data using the
252-trading-day convention.
"""

from __future__ import annotations

import math
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Company, PriceBar, QuoteSnapshot

BENCHMARK = "SPY"
TRADING_DAYS = 252
# Risk-free proxy for the Sharpe ratio. Kept explicit and conservative rather
# than pulled live, so the number is reproducible.
RISK_FREE_ANNUAL = 0.04


async def _closes(db: AsyncSession, ticker: str) -> list[tuple[date, float]]:
    rows = (
        await db.execute(
            select(PriceBar.bar_date, PriceBar.close)
            .where(PriceBar.ticker == ticker)
            .order_by(PriceBar.bar_date.asc())
        )
    ).all()
    return [(r[0], float(r[1])) for r in rows]


def _returns(closes: list[float]) -> list[float]:
    out = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev:
            out.append(closes[i] / prev - 1)
    return out


def _stdev(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return math.sqrt(var)


def _max_drawdown(closes: list[float]) -> float:
    peak = closes[0] if closes else 0.0
    mdd = 0.0
    for c in closes:
        peak = max(peak, c)
        if peak:
            mdd = min(mdd, c / peak - 1)
    return mdd


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 1)


def _sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def _beta(asset_ret: list[float], bench_ret: list[float]) -> float | None:
    """Beta from pre-aligned, equal-length daily return series."""
    n = min(len(asset_ret), len(bench_ret))
    if n < 30:
        return None
    a = asset_ret[-n:]
    b = bench_ret[-n:]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / (n - 1)
    var_b = sum((x - mean_b) ** 2 for x in b) / (n - 1)
    if var_b == 0:
        return None
    return round(cov / var_b, 2)


def _aligned_returns(
    asset: list[tuple[date, float]], bench_by_date: dict[date, float]
) -> tuple[list[float], list[float]]:
    """Daily returns for asset and benchmark over their shared trading dates.

    Aligning on matched dates (rather than by position) is what keeps beta and
    correlation correct for names with partial history, like recent spin-offs.
    """
    shared = [(d, c) for d, c in asset if d in bench_by_date]
    if len(shared) < 2:
        return [], []
    a_ret, b_ret = [], []
    for i in range(1, len(shared)):
        pd, pc = shared[i - 1]
        cd, cc = shared[i]
        bp, bc = bench_by_date[pd], bench_by_date[cd]
        if pc and bp:
            a_ret.append(cc / pc - 1)
            b_ret.append(bc / bp - 1)
    return a_ret, b_ret


def _corr(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 30:
        return None
    a = a[-n:]
    b = b[-n:]
    sa, sb = _stdev(a), _stdev(b)
    if sa == 0 or sb == 0:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
    return round(cov / (sa * sb), 2)


async def risk_metrics(db: AsyncSession, ticker: str) -> dict | None:
    ticker = ticker.upper()
    series = await _closes(db, ticker)
    if len(series) < 30:
        return None
    closes = [c for _, c in series]
    rets = _returns(closes)

    bench_series = await _closes(db, BENCHMARK)
    bench_by_date = {d: c for d, c in bench_series}
    asset_ret_aligned, bench_ret_aligned = _aligned_returns(series, bench_by_date)

    daily_vol = _stdev(rets)
    ann_vol = daily_vol * math.sqrt(TRADING_DAYS)
    mean_daily = sum(rets) / len(rets) if rets else 0.0
    ann_return = (1 + mean_daily) ** TRADING_DAYS - 1
    sharpe = None
    if ann_vol > 0:
        sharpe = round((ann_return - RISK_FREE_ANNUAL) / ann_vol, 2)

    hi = max(closes)
    lo = min(closes)
    last = closes[-1]
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    cross = None
    if sma50 is not None and sma200 is not None:
        cross = "golden" if sma50 > sma200 else "death"

    return {
        "ticker": ticker,
        "as_of": series[-1][0].isoformat(),
        "observations": len(closes),
        "price": round(last, 2),
        "annualized_return_pct": round(ann_return * 100, 1),
        "annualized_volatility_pct": round(ann_vol * 100, 1),
        "sharpe_ratio": sharpe,
        "beta": _beta(asset_ret_aligned, bench_ret_aligned),
        "max_drawdown_pct": round(_max_drawdown(closes) * 100, 1),
        "rsi_14": _rsi(closes),
        "sma_50": round(sma50, 2) if sma50 else None,
        "sma_200": round(sma200, 2) if sma200 else None,
        "ma_cross": cross,
        "week52_high": round(hi, 2),
        "week52_low": round(lo, 2),
        "pct_from_high": round((last / hi - 1) * 100, 1) if hi else None,
        "pct_off_low": round((last / lo - 1) * 100, 1) if lo else None,
        "risk_free_pct": RISK_FREE_ANNUAL * 100,
        "benchmark": BENCHMARK,
    }


async def correlation_matrix(db: AsyncSession, tickers: list[str]) -> dict:
    tickers = [t.upper() for t in tickers][:12]
    ret_map: dict[str, list[float]] = {}
    date_map: dict[str, dict[date, float]] = {}
    for t in tickers:
        series = await _closes(db, t)
        date_map[t] = {d: c for d, c in series}

    # Align on the shared trading calendar so correlations use matched dates.
    common: set[date] | None = None
    for t in tickers:
        ds = set(date_map[t].keys())
        common = ds if common is None else (common & ds)
    ordered = sorted(common) if common else []
    for t in tickers:
        closes = [date_map[t][d] for d in ordered]
        ret_map[t] = _returns(closes)

    matrix = []
    for a in tickers:
        row = []
        for b in tickers:
            if a == b:
                row.append(1.0)
            else:
                row.append(_corr(ret_map.get(a, []), ret_map.get(b, [])))
        matrix.append(row)

    return {"tickers": tickers, "matrix": matrix, "observations": len(ordered)}


async def risk_leaderboard(db: AsyncSession, limit: int = 500) -> dict:
    """Market-wide risk snapshot: rank names by volatility, beta, momentum.

    Powers the flagship risk dashboard. Uses SPY-relative beta and each name's
    own return distribution over the stored window.
    """
    bench_series = await _closes(db, BENCHMARK)
    bench_by_date = {d: c for d, c in bench_series}

    companies = (await db.execute(select(Company))).scalars().all()
    quotes = {
        q.ticker: q for q in (await db.execute(select(QuoteSnapshot))).scalars().all()
    }
    meta = {c.ticker: c for c in companies}

    rows = []
    # Pull all bars once, grouped by ticker, to avoid N queries.
    all_bars = (
        await db.execute(
            select(PriceBar.ticker, PriceBar.bar_date, PriceBar.close).order_by(
                PriceBar.ticker, PriceBar.bar_date.asc()
            )
        )
    ).all()
    grouped: dict[str, list[tuple[date, float]]] = {}
    for t, d, c in all_bars:
        grouped.setdefault(t, []).append((d, float(c)))

    for t, series in grouped.items():
        if t == BENCHMARK or t not in meta or len(series) < 30:
            continue
        closes = [c for _, c in series]
        rets = _returns(closes)
        vol = _stdev(rets) * math.sqrt(TRADING_DAYS)
        mdd = _max_drawdown(closes)
        a_ret, b_ret = _aligned_returns(series, bench_by_date)
        rows.append(
            {
                "ticker": t,
                "name": meta[t].name,
                "sector": meta[t].sector,
                "market_cap": meta[t].market_cap,
                "change_pct": quotes[t].change_pct if t in quotes else None,
                "beta": _beta(a_ret, b_ret),
                "volatility_pct": round(vol * 100, 1),
                "max_drawdown_pct": round(mdd * 100, 1),
                "rsi_14": _rsi(closes),
                "return_window_pct": round((closes[-1] / closes[0] - 1) * 100, 1),
            }
        )
    return {
        "benchmark": BENCHMARK,
        "count": len(rows),
        "rows": rows[:limit],
    }
