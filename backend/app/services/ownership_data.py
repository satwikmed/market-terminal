"""Live institutional ownership and insider transactions from Yahoo Finance.

Yahoo aggregates institutional filings and Form 4 transactions. Every response
includes the upstream report date so the UI can communicate freshness.
"""

from __future__ import annotations

import time
from typing import Any

from app.services.prices import UA_HEADERS, YahooSession, to_yahoo

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_SECONDS = 60 * 60


def _raw(value: Any, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get("raw", default)
    return value if value is not None else default


def _fetch(ticker: str) -> dict[str, Any]:
    cached = _CACHE.get(ticker)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]

    yahoo = YahooSession()
    yahoo.warm()
    response = yahoo.session.get(
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{to_yahoo(ticker)}",
        params={
            "modules": "majorHoldersBreakdown,institutionOwnership,insiderTransactions",
            "crumb": yahoo.crumb,
        },
        headers=UA_HEADERS,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Yahoo ownership request failed ({response.status_code})")
    results = response.json().get("quoteSummary", {}).get("result") or []
    if not results:
        raise RuntimeError("No ownership data returned")
    result = results[0]
    _CACHE[ticker] = (time.time(), result)
    return result


def institutional_ownership(ticker: str) -> dict[str, Any]:
    data = _fetch(ticker.upper())
    ownership = data.get("institutionOwnership", {})
    breakdown = data.get("majorHoldersBreakdown", {})
    holders = []
    report_dates: list[str] = []

    for row in ownership.get("ownershipList", [])[:10]:
        pct = float(_raw(row.get("pctHeld"), 0) or 0) * 100
        report_date = row.get("reportDate", {}).get("fmt")
        if report_date:
            report_dates.append(report_date)
        denominator = round(100 / pct) if pct > 0 else None
        plain = (
            f"{row.get('organization', 'This institution')} owns about "
            f"{pct:.1f}% of the company"
        )
        if denominator:
            plain += f", roughly 1 in every {denominator} shares."
        else:
            plain += "."
        holders.append(
            {
                "name": row.get("organization", "Unknown institution"),
                "pct": pct,
                "shares": int(_raw(row.get("position"), 0) or 0),
                "value": float(_raw(row.get("value"), 0) or 0),
                "report_date": report_date,
                "plain": plain,
            }
        )

    return {
        "ticker": ticker.upper(),
        "source": "Yahoo Finance institutional ownership (derived from regulatory filings)",
        "source_url": f"https://finance.yahoo.com/quote/{to_yahoo(ticker)}/holders/",
        "as_of": max(report_dates) if report_dates else None,
        "note": (
            "Institutional positions are reported periodically, not in real time. "
            "A recent stock price does not make the holdings themselves current."
        ),
        "summary": {
            "institutional_percent": float(
                _raw(breakdown.get("institutionsPercentHeld"), 0) or 0
            )
            * 100,
            "insider_percent": float(
                _raw(breakdown.get("insidersPercentHeld"), 0) or 0
            )
            * 100,
            "institution_count": int(
                _raw(breakdown.get("institutionsCount"), 0) or 0
            ),
        },
        "holders": holders,
    }


def insider_activity(ticker: str) -> dict[str, Any]:
    data = _fetch(ticker.upper())
    transactions = data.get("insiderTransactions", {}).get("transactions", [])
    activity = []

    for row in transactions[:20]:
        transaction = str(row.get("transactionText") or "Transaction")
        lower = transaction.lower()
        action = (
            "buy"
            if "purchase" in lower or "buy" in lower
            else "sell"
            if "sale" in lower or "sell" in lower
            else "other"
        )
        person = row.get("filerName") or "Company insider"
        relation = row.get("filerRelation") or "Insider"
        shares = int(_raw(row.get("shares"), 0) or 0)
        date = row.get("startDate", {}).get("fmt")
        context = (
            "A purchase uses the insider's own money, but it is still not a reliable forecast."
            if action == "buy"
            else "Insiders sell for many reasons, including taxes and diversification; a sale alone is not a bearish signal."
            if action == "sell"
            else "This may be an award, grant, transfer, or another non-market transaction."
        )
        activity.append(
            {
                "person": person,
                "relation": relation,
                "action": action,
                "shares": shares,
                "value": float(_raw(row.get("value"), 0) or 0),
                "date": date,
                "transaction": transaction,
                "plain": f"{person} ({relation}) reported {transaction.lower()} {context}",
            }
        )

    dates = [row["date"] for row in activity if row["date"]]
    return {
        "ticker": ticker.upper(),
        "source": "Yahoo Finance insider transactions (derived from Form 4 filings)",
        "source_url": f"https://finance.yahoo.com/quote/{to_yahoo(ticker)}/insider-transactions/",
        "as_of": max(dates) if dates else None,
        "disclaimer": (
            "Not investment advice. Insider transactions are noisy and should never "
            "be treated as a reliable prediction."
        ),
        "activity": activity,
    }
