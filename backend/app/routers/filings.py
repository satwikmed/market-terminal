from fastapi import APIRouter, HTTPException, Query

from app.services import sec_filings

router = APIRouter(prefix="/api/filings", tags=["filings"])


@router.get("/{ticker}")
async def list_filings(ticker: str, limit: int = Query(12, ge=1, le=40)):
    try:
        return await sec_filings.recent_filings(ticker, limit=limit)
    except sec_filings.SECError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/{ticker}/{accession}/text")
async def filing_section(
    ticker: str,
    accession: str,
    section: str = Query("risk_factors"),
):
    if section not in sec_filings.SECTION_PATTERNS:
        raise HTTPException(
            400,
            f"Unknown section '{section}'. Choose from: {', '.join(sec_filings.SECTION_PATTERNS)}",
        )
    try:
        return await sec_filings.filing_text(ticker, accession, section=section)
    except sec_filings.SECError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/meta/sections")
async def sections():
    return {
        "sections": [
            {"id": key, "label": spec["label"], "plain_english": spec["plain"]}
            for key, spec in sec_filings.SECTION_PATTERNS.items()
        ],
        "forms": [
            {"form": form, "label": guide["label"], "plain_english": guide["plain"]}
            for form, guide in sec_filings.FORM_GUIDE.items()
        ],
    }
