from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha1

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import AICache


FALLBACK_RESPONSES = {
    "earnings": (
        "AI analysis is not configured. Add OPENAI_API_KEY (or ANTHROPIC_API_KEY) "
        "to the backend environment, then retry."
    ),
    "filing": (
        "AI analysis is not configured. No translation was generated."
    ),
    "why_move": (
        "AI analysis is not configured, so the app will not invent a reason for this move."
    ),
    "weekly_brief": (
        "AI analysis is not configured. Add a provider key to generate this week's brief."
    ),
}


async def get_cached(db: AsyncSession, cache_key: str) -> AICache | None:
    return (
        await db.execute(select(AICache).where(AICache.cache_key == cache_key))
    ).scalar_one_or_none()


async def set_cached(
    db: AsyncSession,
    *,
    cache_key: str,
    kind: str,
    content: str,
    ticker: str | None = None,
) -> AICache:
    existing = await get_cached(db, cache_key)
    if existing:
        existing.content = content
        existing.created_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    row = AICache(
        cache_key=cache_key,
        kind=kind,
        ticker=ticker,
        content=content,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def run_model(prompt: str, system: str) -> tuple[str, str | None]:
    settings = get_settings()
    provider = settings.resolved_ai_provider
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            instructions=system,
            input=prompt,
            max_output_tokens=1200,
        )
        return response.output_text.strip(), "openai"

    if provider != "anthropic":
        return "", None

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1200,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = []
    for block in msg.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts).strip(), "anthropic"


SYSTEM = (
    "You are Plain English Terminal, an educator for complete finance beginners. "
    "Explain like the reader is smart but has zero finance background. "
    "Use concrete analogies. Never give investment advice. "
    "When discussing historical patterns, clearly say they are tendencies, not guarantees. "
    "Use hedging language for causes (likely, possible, may have contributed)."
)


async def summarize_earnings(
    db: AsyncSession, ticker: str, company_name: str, context: str = ""
) -> dict:
    provider = get_settings().resolved_ai_provider
    cache_key = f"earnings:{provider}:{ticker}:{datetime.utcnow().strftime('%Y-%W')}"
    cached = await get_cached(db, cache_key)
    if cached:
        return {
            "ticker": ticker,
            "cached": True,
            "available": True,
            "provider": provider,
            "summary": cached.content,
        }

    prompt = (
        f"Summarize the latest earnings picture for {company_name} ({ticker}) in plain English. "
        f"Cover: beat/miss vs expectations (if unknown, say so), what drove results, and what management "
        f"signaled about the future. Keep it under 220 words.\n\nContext:\n{context or 'Use general knowledge; note uncertainty.'}"
    )
    text, provider = await run_model(prompt, SYSTEM)
    if not text:
        return {
            "ticker": ticker,
            "cached": False,
            "available": False,
            "provider": None,
            "summary": FALLBACK_RESPONSES["earnings"],
        }
    await set_cached(db, cache_key=cache_key, kind="earnings", content=text, ticker=ticker)
    return {
        "ticker": ticker,
        "cached": False,
        "available": True,
        "provider": provider,
        "summary": text,
    }


async def translate_filing(
    db: AsyncSession,
    ticker: str,
    filing_type: str,
    excerpt: str,
    *,
    source: dict | None = None,
) -> dict:
    digest = sha1(excerpt[:2000].encode("utf-8")).hexdigest()[:12]
    provider = get_settings().resolved_ai_provider
    cache_key = f"filing:{provider}:{ticker}:{filing_type}:{digest}"
    citation = source or {}
    base = {
        "ticker": ticker,
        "filing_type": filing_type,
        "source": citation.get("source", "User-supplied text"),
        "source_url": citation.get("source_url"),
        "filing_date": citation.get("filing_date"),
        "section_label": citation.get("section_label"),
        "excerpt_characters": len(excerpt),
        "excerpt_preview": excerpt[:400],
    }

    cached = await get_cached(db, cache_key)
    if cached:
        return {**base, "cached": True, "available": True, "provider": provider, "translation": cached.content}

    prompt = (
        f"Translate this excerpt from {ticker}'s {filing_type} filing"
        + (f" ({citation['section_label']}, filed {citation.get('filing_date')})" if citation.get("section_label") else "")
        + " into plain English for a curious beginner.\n\n"
        "Rules: keep every important fact, drop the legal boilerplate, and do not add anything "
        "that is not in the excerpt. Open with a one-sentence takeaway, then 3-6 short bullet "
        "points. If the excerpt is mostly generic risk boilerplate, say so plainly rather than "
        "making it sound more alarming or more meaningful than it is.\n\n"
        f"Excerpt:\n{excerpt[:12000]}"
    )
    text, provider = await run_model(prompt, SYSTEM)
    if not text:
        return {
            **base,
            "cached": False,
            "available": False,
            "provider": None,
            "translation": FALLBACK_RESPONSES["filing"],
        }
    await set_cached(db, cache_key=cache_key, kind="filing", content=text, ticker=ticker)
    return {**base, "cached": False, "available": True, "provider": provider, "translation": text}


async def why_did_this_move(
    db: AsyncSession,
    ticker: str,
    company_name: str,
    change_pct: float,
    as_of: str,
    *,
    bundle: dict,
) -> dict:
    """Explain a move strictly from pre-computed evidence.

    The evidence bundle is deterministic, so the endpoint stays useful (and
    honest) even with no AI provider configured — the model only ever rewrites
    evidence it was handed, and never supplies causes of its own.
    """
    provider = get_settings().resolved_ai_provider
    base = {
        "ticker": ticker,
        "as_of": as_of,
        "change_pct": change_pct,
        "evidence": bundle["evidence"],
        "attribution": bundle["attribution"],
        "stats": bundle["stats"],
        "methodology": (
            "Every claim below is derived from quotes, price history, SEC EDGAR filings, and the "
            "economic calendar stored in this app. The AI layer may only rephrase this evidence."
        ),
    }

    if provider is None:
        return {
            **base,
            "cached": False,
            "available": False,
            "provider": None,
            "narrative": bundle["narrative"],
            "narrative_source": "deterministic",
            "drivers": _drivers_from_evidence(bundle),
        }

    fingerprint = sha1(
        json.dumps(bundle["evidence"], sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    cache_key = f"why:{provider}:{ticker}:{as_of}:{fingerprint}"
    cached = await get_cached(db, cache_key)
    if cached:
        try:
            payload = json.loads(cached.content)
        except json.JSONDecodeError:
            payload = {"narrative": cached.content, "drivers": []}
        return {**base, "cached": True, "available": True, "provider": provider, "narrative_source": "ai", **payload}

    from app.services.move_evidence import to_prompt

    text, provider = await run_model(to_prompt(company_name, ticker, change_pct, as_of, bundle), SYSTEM)
    if not text:
        return {
            **base,
            "cached": False,
            "available": False,
            "provider": None,
            "narrative": bundle["narrative"],
            "narrative_source": "deterministic",
            "drivers": _drivers_from_evidence(bundle),
        }

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        payload = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        payload = {"narrative": text, "drivers": []}
    if not payload.get("drivers"):
        payload["drivers"] = _drivers_from_evidence(bundle)

    await set_cached(db, cache_key=cache_key, kind="why_move", content=json.dumps(payload), ticker=ticker)
    return {**base, "cached": False, "available": True, "provider": provider, "narrative_source": "ai", **payload}


def _drivers_from_evidence(bundle: dict) -> list[dict]:
    """Rank evidence into drivers without a model.

    Confidence reflects how directly each kind of evidence can be tied to a
    single day's move, not how certain we are about the cause.
    """
    confidence_by_kind = {"filing": 65, "sector": 55, "market": 60, "macro": 40, "volatility": 80}
    hedge_by_kind = {
        "filing": "Timing overlap only — the filing may not be what moved the price.",
        "sector": "Correlation, not proof of a shared cause.",
        "market": "Correlation, not proof of a shared cause.",
        "macro": "Macro releases affect stocks unevenly and with a lag.",
        "volatility": "Statistical context, not a cause.",
    }
    drivers = []
    for item in bundle["evidence"]:
        drivers.append(
            {
                "title": item["title"],
                "explanation": item["detail"],
                "confidence": confidence_by_kind.get(item["kind"], 50),
                "hedge": hedge_by_kind.get(item["kind"], "Interpret with caution."),
                "source": item["source"],
                "source_url": item["source_url"],
            }
        )
    return sorted(drivers, key=lambda d: d["confidence"], reverse=True)


async def weekly_brief(db: AsyncSession, *, snapshot: dict) -> dict:
    """Weekly narrative grounded in the app's own market and macro snapshot."""
    week = datetime.utcnow().strftime("%Y-%W")
    provider = get_settings().resolved_ai_provider
    base = {"week": week, "snapshot": snapshot}

    if provider is None:
        return {
            **base,
            "cached": False,
            "available": False,
            "provider": None,
            "brief": FALLBACK_RESPONSES["weekly_brief"],
        }

    fingerprint = sha1(json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
    cache_key = f"weekly_brief:{provider}:{week}:{fingerprint}"
    cached = await get_cached(db, cache_key)
    if cached:
        return {**base, "cached": True, "available": True, "provider": provider, "brief": cached.content}

    prompt = (
        "Write a weekly 'state of the market' brief for a complete beginner (280-350 words), "
        "using ONLY the snapshot below. One flowing narrative, not a bullet dump. Explain what the "
        "numbers mean in everyday terms, connect the market picture to the macro picture, and be "
        "explicit about what the data does not tell us. No investment advice, no predictions, and "
        "no events that are not in the snapshot.\n\n"
        f"SNAPSHOT AS OF {snapshot.get('as_of')}:\n"
        f"{json.dumps(snapshot, indent=2, default=str)}"
    )
    text, provider = await run_model(prompt, SYSTEM)
    if not text:
        return {
            **base,
            "cached": False,
            "available": False,
            "provider": None,
            "brief": FALLBACK_RESPONSES["weekly_brief"],
        }
    await set_cached(db, cache_key=cache_key, kind="weekly_brief", content=text)
    return {**base, "cached": False, "available": True, "provider": provider, "brief": text}
