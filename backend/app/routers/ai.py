from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Company, QuoteSnapshot
from app.schemas import EarningsRequest, FilingTranslateRequest, WhyMoveRequest
from app.services import ai as ai_service
from app.services import move_evidence, sec_filings
from app.services.market_hours import now_et
from app.services.snapshot import market_snapshot

router = APIRouter(prefix="/api/ai", tags=["ai"])


async def _require_company(db: AsyncSession, ticker: str) -> Company:
    company = (
        await db.execute(select(Company).where(Company.ticker == ticker.upper()))
    ).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")
    return company


@router.post("/earnings/{ticker}")
async def earnings_summary(
    ticker: str,
    body: EarningsRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Summarise results using the company's own most recent 10-Q/10-K discussion."""
    company = await _require_company(db, ticker)

    context_parts: list[str] = []
    citation: dict | None = None
    if body and body.context:
        context_parts.append(body.context)

    fundamentals = {
        "market_cap": company.market_cap,
        "pe_ratio": company.pe_ratio,
        "eps": company.eps,
        "revenue": company.revenue,
        "dividend_yield": company.dividend_yield,
    }
    context_parts.append(
        "Reported fundamentals currently on file: "
        + ", ".join(f"{k}={v}" for k, v in fundamentals.items() if v is not None)
    )

    for form in ("10-Q", "10-K"):
        try:
            latest = await sec_filings.latest_filing_of_type(company.ticker, form)
            if not latest:
                continue
            section = await sec_filings.filing_text(
                company.ticker, latest["accession"], section="mda", max_chars=14_000
            )
        except sec_filings.SECError:
            continue
        if section["section"] == "full_document":
            continue
        citation = {
            "form": section["form"],
            "filing_date": section["filing_date"],
            "source": section["source"],
            "source_url": section["source_url"],
            "section_label": section["section_label"],
        }
        context_parts.append(
            f"Management's Discussion & Analysis from the {section['form']} filed "
            f"{section['filing_date']}:\n{section['excerpt']}"
        )
        break

    result = await ai_service.summarize_earnings(
        db, company.ticker, company.name, "\n\n".join(context_parts)
    )
    result["citation"] = citation
    result["grounded"] = citation is not None
    return result


@router.post("/filing/{ticker}")
async def translate_filing(
    ticker: str,
    body: FilingTranslateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Translate a real SEC filing section, or caller-supplied text as a fallback."""
    company = await _require_company(db, ticker)

    excerpt = body.excerpt.strip()
    source: dict | None = None

    if not excerpt:
        accession = body.accession
        try:
            if not accession:
                latest = await sec_filings.latest_filing_of_type(company.ticker, body.filing_type)
                if not latest:
                    raise HTTPException(
                        404, f"No recent {body.filing_type} on file for {company.ticker}"
                    )
                accession = latest["accession"]
            section = await sec_filings.filing_text(
                company.ticker, accession, section=body.section
            )
        except sec_filings.SECError as exc:
            raise HTTPException(502, str(exc)) from exc
        excerpt = section["excerpt"]
        source = {
            "source": section["source"],
            "source_url": section["source_url"],
            "filing_date": section["filing_date"],
            "section_label": section["section_label"],
        }
        body.filing_type = section["form"]

    if not excerpt:
        raise HTTPException(400, "No filing text available to translate.")

    return await ai_service.translate_filing(
        db, company.ticker, body.filing_type, excerpt, source=source
    )


@router.post("/why-move/{ticker}")
async def why_move(
    ticker: str,
    body: WhyMoveRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Explain a move from computed evidence; AI only rephrases what it is given."""
    company = await _require_company(db, ticker)
    quote = (
        await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == company.ticker))
    ).scalar_one_or_none()

    as_of_str = body.as_of if body and body.as_of else now_et().date().isoformat()
    try:
        as_of = date.fromisoformat(as_of_str)
    except ValueError as exc:
        raise HTTPException(400, "as_of must be an ISO date (YYYY-MM-DD)") from exc

    change = (
        body.change_pct
        if body and body.change_pct is not None
        else (quote.change_pct if quote else 0.0)
    )

    bundle = await move_evidence.gather(db, company, change, as_of)
    return await ai_service.why_did_this_move(
        db, company.ticker, company.name, change, as_of_str, bundle=bundle
    )


@router.get("/evidence/{ticker}")
async def move_evidence_only(ticker: str, db: AsyncSession = Depends(get_db)):
    """The raw evidence behind a move, with no AI involved at all."""
    company = await _require_company(db, ticker)
    quote = (
        await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == company.ticker))
    ).scalar_one_or_none()
    change = quote.change_pct if quote else 0.0
    bundle = await move_evidence.gather(db, company, change, now_et().date())
    return {"ticker": company.ticker, "change_pct": change, **bundle}


@router.post("/weekly-brief")
async def weekly_brief(db: AsyncSession = Depends(get_db)):
    snapshot = await market_snapshot(db)
    return await ai_service.weekly_brief(db, snapshot=snapshot)


@router.get("/health")
async def ai_health():
    from app.config import get_settings

    settings = get_settings()
    provider = settings.resolved_ai_provider
    return {
        "configured": provider is not None,
        "provider": provider,
        "model": (
            settings.openai_model
            if provider == "openai"
            else settings.anthropic_model
            if provider == "anthropic"
            else None
        ),
        "openai_configured": bool(settings.openai_api_key),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "mode": "live" if provider else "disabled",
        "grounding": (
            "Earnings summaries and filing translations are grounded in SEC EDGAR documents; "
            "move explanations are grounded in computed evidence and work without an AI key."
        ),
        "server_time": datetime.utcnow().isoformat() + "Z",
    }
