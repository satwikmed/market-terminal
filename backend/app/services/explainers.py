"""Reusable plain-English translations for financial metrics."""

from __future__ import annotations

from typing import Any


def _fmt_money(n: float | None) -> str:
    if n is None:
        return "an unknown amount"
    abs_n = abs(n)
    if abs_n >= 1_000_000_000_000:
        return f"${n / 1_000_000_000_000:.2f} trillion"
    if abs_n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.1f} billion"
    if abs_n >= 1_000_000:
        return f"${n / 1_000_000:.1f} million"
    return f"${n:,.0f}"


def explain_metric(metric: str, value: Any) -> dict[str, str]:
    """Return {metric, value_display, plain_english} for a known metric key."""
    key = metric.lower().strip()

    if value is None:
        return {
            "metric": metric,
            "value_display": "—",
            "plain_english": "We don't have this number right now.",
        }

    try:
        num = float(value)
    except (TypeError, ValueError):
        num = None

    if key in {"pe", "pe_ratio", "p/e", "price_to_earnings"}:
        return {
            "metric": "P/E Ratio",
            "value_display": f"{num:.1f}" if num is not None else str(value),
            "plain_english": (
                f"Investors are currently paying ${num:.0f} for every $1 this company "
                f"makes in profit each year."
                if num and num > 0
                else "This company isn't currently profitable, so a normal P/E doesn't apply."
            ),
        }

    if key in {"debt_to_equity", "d/e", "de"}:
        return {
            "metric": "Debt-to-Equity",
            "value_display": f"{num:.2f}" if num is not None else str(value),
            "plain_english": (
                f"For every $1 the company owns, it owes ${num:.2f} to lenders."
                if num is not None
                else "We couldn't translate this debt figure."
            ),
        }

    if key in {"market_cap", "marketcap"}:
        return {
            "metric": "Market Cap",
            "value_display": _fmt_money(num),
            "plain_english": (
                f"If you could buy the whole company today, it would cost about {_fmt_money(num)}."
            ),
        }

    if key in {"eps", "earnings_per_share"}:
        return {
            "metric": "EPS",
            "value_display": f"${num:.2f}" if num is not None else str(value),
            "plain_english": (
                f"For each share of stock, the company earned about ${num:.2f} in profit "
                f"over the last year."
                if num is not None
                else "Earnings per share isn't available."
            ),
        }

    if key in {"dividend_yield", "div_yield"}:
        pct = num * 100 if num is not None and abs(num) < 1 else num
        return {
            "metric": "Dividend Yield",
            "value_display": f"{pct:.2f}%" if pct is not None else str(value),
            "plain_english": (
                f"If you owned $100 of this stock, the company would currently pay you "
                f"about ${pct:.2f} a year in cash dividends."
                if pct is not None
                else "Dividend yield isn't available."
            ),
        }

    if key in {"revenue", "sales"}:
        return {
            "metric": "Revenue",
            "value_display": _fmt_money(num),
            "plain_english": (
                f"Customers paid the company about {_fmt_money(num)} over the last reported year."
            ),
        }

    if key in {"change_pct", "pct_change"}:
        direction = "up" if (num or 0) >= 0 else "down"
        return {
            "metric": "Today's Change",
            "value_display": f"{num:+.2f}%" if num is not None else str(value),
            "plain_english": (
                f"The stock is {direction} about {abs(num):.2f}% compared with yesterday's close."
                if num is not None
                else "Change isn't available."
            ),
        }

    if key in {"unemployment", "unrate"}:
        return {
            "metric": "Unemployment Rate",
            "value_display": f"{num:.1f}%" if num is not None else str(value),
            "plain_english": (
                f"About {num:.1f} out of every 100 people who want a job currently don't have one."
                if num is not None
                else "Unemployment data isn't available."
            ),
        }

    if key in {"cpi", "inflation"}:
        return {
            "metric": "Inflation (CPI)",
            "value_display": f"{num:.1f}%" if num is not None else str(value),
            "plain_english": (
                f"A typical basket of everyday stuff costs about {num:.1f}% more than it did a year ago."
                if num is not None
                else "Inflation data isn't available."
            ),
        }

    if key in {"fed_funds", "ffr", "fed_rate"}:
        return {
            "metric": "Fed Funds Rate",
            "value_display": f"{num:.2f}%" if num is not None else str(value),
            "plain_english": (
                f"The Federal Reserve's main interest-rate target is about {num:.2f}%. "
                f"When this goes up, borrowing (mortgages, credit cards) usually gets more expensive."
                if num is not None
                else "Fed rate isn't available."
            ),
        }

    if key in {"gdp"}:
        return {
            "metric": "GDP Growth",
            "value_display": f"{num:.1f}%" if num is not None else str(value),
            "plain_english": (
                f"The whole US economy grew (or shrank) by about {num:.1f}% at an annualized pace."
                if num is not None
                else "GDP data isn't available."
            ),
        }

    if key in {"consumer_confidence", "umcsent"}:
        return {
            "metric": "Consumer Confidence",
            "value_display": f"{num:.1f}" if num is not None else str(value),
            "plain_english": (
                "This score reflects how optimistic everyday people feel about the economy and their jobs. "
                "Higher usually means people are more willing to spend."
            ),
        }

    if key in {"yield_spread", "2s10s"}:
        return {
            "metric": "2s10s Yield Spread",
            "value_display": f"{num:.2f}%" if num is not None else str(value),
            "plain_english": (
                "This compares what the government pays to borrow for 2 years vs 10 years. "
                "When the short-term rate is higher than the long-term rate (an 'inverted' curve), "
                "it has historically often shown up before recessions — but it's a pattern, not a guarantee."
            ),
        }

    return {
        "metric": metric,
        "value_display": str(value),
        "plain_english": "This number helps describe the company or economy; hover metrics across the app for kid-friendly explanations.",
    }


def analogy_for_market_cap(market_cap: float | None, company_name: str) -> dict[str, Any]:
    if not market_cap or market_cap <= 0:
        return {
            "headline": f"We don't have a market-cap analogy for {company_name} yet.",
            "comparisons": [],
            "share_text": "",
        }

    median_us_home = 420_000
    houses = market_cap / median_us_home
    iceland_gdp = 31_000_000_000  # rough USD
    vermont_gdp = 43_000_000_000
    nfl_franchise = 5_000_000_000

    comparisons = [
        {
            "label": "Median US homes",
            "value": f"{houses:,.0f}",
            "sentence": f"That's roughly the price of {houses:,.0f} typical American homes.",
        },
        {
            "label": "Iceland's annual GDP",
            "value": f"{market_cap / iceland_gdp:.1f}×",
            "sentence": f"You could buy Iceland's entire yearly economic output about {market_cap / iceland_gdp:.1f} times over.",
        },
        {
            "label": "Vermont's GDP",
            "value": f"{market_cap / vermont_gdp:.1f}×",
            "sentence": f"That's about {market_cap / vermont_gdp:.1f}× Vermont's annual economy.",
        },
        {
            "label": "NFL team valuations",
            "value": f"{market_cap / nfl_franchise:.0f}",
            "sentence": f"It's worth roughly {market_cap / nfl_franchise:.0f} average modern NFL franchises.",
        },
    ]

    top = comparisons[0]["sentence"]
    share_text = (
        f"{company_name} is worth {_fmt_money(market_cap)}. {top} "
        f"— via Plain English Terminal"
    )

    return {
        "headline": f"{company_name} is worth {_fmt_money(market_cap)}",
        "comparisons": comparisons,
        "share_text": share_text,
    }


METRIC_CATALOG = [
    {"key": "pe_ratio", "label": "P/E Ratio"},
    {"key": "debt_to_equity", "label": "Debt-to-Equity"},
    {"key": "market_cap", "label": "Market Cap"},
    {"key": "eps", "label": "EPS"},
    {"key": "dividend_yield", "label": "Dividend Yield"},
    {"key": "revenue", "label": "Revenue"},
]
