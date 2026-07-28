"""Live SEC EDGAR filings: index, document fetch, and section extraction.

EDGAR is free and requires no API key, but it does require a descriptive
User-Agent and enforces a 10 requests/second ceiling per client.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _headers() -> dict[str, str]:
    from app.config import get_settings

    return {
        "User-Agent": get_settings().sec_user_agent,
        "Accept-Encoding": "gzip, deflate",
    }

SUBMISSIONS_TTL = 60 * 60 * 6  # EDGAR indexes update daily; 6h is plenty
DOCUMENT_TTL = 60 * 60 * 24

_submissions_cache: dict[str, tuple[float, dict]] = {}
_document_cache: dict[str, tuple[float, str]] = {}
_cik_map: dict[str, str] | None = None

# EDGAR fair-access policy: stay comfortably under 10 requests/second.
_rate_lock = asyncio.Lock()
_last_request_at = 0.0
_MIN_INTERVAL = 0.15


FORM_GUIDE: dict[str, dict[str, str]] = {
    "10-K": {
        "label": "Annual report",
        "plain": "The company's once a year full report card: what it sells, how much money it made, and everything that could go wrong.",
    },
    "10-Q": {
        "label": "Quarterly report",
        "plain": "A shorter three month update on revenue, profit, and anything that changed since the annual report.",
    },
    "8-K": {
        "label": "Breaking news filing",
        "plain": "A 'something important just happened' notice: earnings releases, executive changes, big deals, or unexpected events.",
    },
    "DEF 14A": {
        "label": "Proxy statement",
        "plain": "The shareholder vote booklet: executive pay, board members, and the questions shareholders get to vote on.",
    },
    "S-1": {
        "label": "IPO registration",
        "plain": "The paperwork a company files when it wants to sell shares to the public for the first time.",
    },
}

# Section anchors. 10-K and 10-Q number their items differently, so each
# section lists every heading pattern we accept.
SECTION_PATTERNS: dict[str, dict[str, Any]] = {
    "risk_factors": {
        "label": "Risk Factors",
        "plain": "The company's own list of what could go wrong. Written by lawyers, so it is exhaustive and gloomy by design.",
        "start": [r"Item\s*1A\.?\s*[\u2014\u2013\-:]?\s*Risk\s+Factors"],
        "end": [
            r"Item\s*1B\.?\s*[\u2014\u2013\-:]?\s*Unresolved",
            r"Item\s*2\.?\s*[\u2014\u2013\-:]?\s*Propert",
            r"Item\s*6\.?\s*[\u2014\u2013\-:]?\s*Exhibit",
        ],
    },
    "mda": {
        "label": "Management's Discussion & Analysis",
        "plain": "Management explaining, in their own words, why the numbers came out the way they did.",
        "start": [
            r"Item\s*7\.?\s*[\u2014\u2013\-:]?\s*Management.{0,3}s\s+Discussion",
            r"Item\s*2\.?\s*[\u2014\u2013\-:]?\s*Management.{0,3}s\s+Discussion",
        ],
        "end": [
            r"Item\s*7A\.?\s*[\u2014\u2013\-:]?\s*Quantitative",
            r"Item\s*3\.?\s*[\u2014\u2013\-:]?\s*Quantitative",
            r"Item\s*8\.?\s*[\u2014\u2013\-:]?\s*Financial\s+Statements",
        ],
    },
    "business": {
        "label": "Business Overview",
        "plain": "A description of what the company actually does day to day, in its own words.",
        "start": [r"Item\s*1\.?\s*[\u2014\u2013\-:]?\s*Business"],
        "end": [r"Item\s*1A\.?\s*[\u2014\u2013\-:]?\s*Risk\s+Factors"],
    },
}


class SECError(RuntimeError):
    """Raised when EDGAR is unreachable or returns something unusable."""


@dataclass
class Filing:
    form: str
    filing_date: str
    report_date: str | None
    accession: str
    document_url: str
    index_url: str
    description: str

    def as_dict(self) -> dict[str, Any]:
        guide = FORM_GUIDE.get(self.form, {"label": self.form, "plain": "An SEC disclosure document."})
        return {
            "form": self.form,
            "form_label": guide["label"],
            "form_plain_english": guide["plain"],
            "filing_date": self.filing_date,
            "report_date": self.report_date,
            "accession": self.accession,
            "document_url": self.document_url,
            "index_url": self.index_url,
            "description": self.description,
        }


def load_cik_map() -> dict[str, str]:
    global _cik_map
    if _cik_map is None:
        path = DATA_DIR / "sec_cik_map.json"
        try:
            _cik_map = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("CIK map unavailable: %s", exc)
            _cik_map = {}
    return _cik_map


def cik_for(ticker: str) -> str | None:
    return load_cik_map().get(ticker.upper())


def _blocking_get(url: str, attempts: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                encoding = resp.headers.get("Content-Encoding")
            if encoding == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as exc:
            last = exc
            # EDGAR throttles with 403/429 rather than queuing; back off and retry.
            if exc.code not in (403, 429) or attempt == attempts - 1:
                raise SECError(f"EDGAR returned {exc.code} for {url}") from exc
            time.sleep(1.5 * (attempt + 1))
        except OSError as exc:
            raise SECError(f"Could not reach EDGAR: {exc}") from exc
    raise SECError(f"EDGAR request failed for {url}: {last}")


async def _get(url: str) -> str:
    global _last_request_at
    async with _rate_lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = time.monotonic()
    return await asyncio.to_thread(_blocking_get, url)


async def _submissions(cik: str) -> dict:
    hit = _submissions_cache.get(cik)
    if hit and time.time() - hit[0] < SUBMISSIONS_TTL:
        return hit[1]
    body = await _get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SECError("EDGAR returned malformed submission data") from exc
    _submissions_cache[cik] = (time.time(), payload)
    return payload


async def recent_filings(
    ticker: str,
    forms: tuple[str, ...] = ("10-K", "10-Q", "8-K", "DEF 14A"),
    limit: int = 12,
) -> dict[str, Any]:
    cik = cik_for(ticker)
    if not cik:
        raise SECError(f"No SEC CIK mapping for {ticker}")

    payload = await _submissions(cik)
    recent = (payload.get("filings") or {}).get("recent") or {}
    stripped_cik = str(int(cik))

    filings: list[Filing] = []
    for i, form in enumerate(recent.get("form", [])):
        if form not in forms:
            continue
        accession = recent["accessionNumber"][i]
        folder = accession.replace("-", "")
        primary = recent.get("primaryDocument", [])[i] or ""
        base = f"https://www.sec.gov/Archives/edgar/data/{stripped_cik}/{folder}"
        filings.append(
            Filing(
                form=form,
                filing_date=recent["filingDate"][i],
                report_date=(recent.get("reportDate") or [None] * (i + 1))[i] or None,
                accession=accession,
                document_url=f"{base}/{primary}" if primary else f"{base}/",
                index_url=f"{base}/{accession}-index.htm",
                description=(recent.get("primaryDocDescription") or [""] * (i + 1))[i] or form,
            )
        )
        if len(filings) >= limit:
            break

    return {
        "ticker": ticker.upper(),
        "company_name": payload.get("name"),
        "cik": cik,
        "filings": [f.as_dict() for f in filings],
        "source": "SEC EDGAR",
        "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=include&count=40",
    }


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "table"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _find_last(text: str, patterns: list[str], after: int = 0) -> int | None:
    """Return the offset of the last heading match, skipping table-of-contents hits."""
    best: int | None = None
    for pattern in patterns:
        for match in re.finditer(pattern, text[after:], re.IGNORECASE):
            pos = after + match.start()
            if best is None or pos > best:
                best = pos
    return best


def extract_section(text: str, section: str) -> str | None:
    spec = SECTION_PATTERNS.get(section)
    if not spec:
        return None
    start = _find_last(text, spec["start"])
    if start is None:
        return None
    end = _find_last(text, spec["end"], after=start + 200)
    body = text[start:end] if end and end > start else text[start : start + 40_000]
    body = body.strip()
    return body if len(body) > 400 else None


async def filing_text(
    ticker: str,
    accession: str,
    section: str = "risk_factors",
    max_chars: int = 12_000,
) -> dict[str, Any]:
    index = await recent_filings(ticker, forms=("10-K", "10-Q", "8-K", "DEF 14A"), limit=40)
    match = next(
        (f for f in index["filings"] if f["accession"] == accession),
        None,
    )
    if not match:
        raise SECError(f"Filing {accession} not found in recent {ticker} filings")

    url = match["document_url"]
    cached = _document_cache.get(url)
    if cached and time.time() - cached[0] < DOCUMENT_TTL:
        text = cached[1]
    else:
        text = _html_to_text(await _get(url))
        _document_cache[url] = (time.time(), text)

    spec = SECTION_PATTERNS.get(section, SECTION_PATTERNS["risk_factors"])
    body = extract_section(text, section)
    resolved_section = section
    if body is None:
        # 8-Ks and exhibits have no numbered items; fall back to the whole document.
        body = text
        resolved_section = "full_document"
        spec = {
            "label": "Full filing text",
            "plain": "This filing has no standard numbered sections, so the full document text is shown.",
        }

    truncated = len(body) > max_chars
    return {
        "ticker": ticker.upper(),
        "accession": accession,
        "form": match["form"],
        "form_label": match["form_label"],
        "filing_date": match["filing_date"],
        "section": resolved_section,
        "section_label": spec["label"],
        "section_plain_english": spec.get("plain", ""),
        "excerpt": body[:max_chars],
        "characters": len(body),
        "truncated": truncated,
        "source": "SEC EDGAR",
        "source_url": url,
    }


async def latest_filing_of_type(ticker: str, form: str) -> dict[str, Any] | None:
    index = await recent_filings(ticker, forms=(form,), limit=1)
    filings = index["filings"]
    return filings[0] if filings else None
