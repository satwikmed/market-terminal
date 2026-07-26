from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ExplainedMetric(BaseModel):
    metric: str
    value_display: str
    plain_english: str


class QuoteOut(BaseModel):
    ticker: str
    price: float
    change: float
    change_pct: float
    previous_close: float | None = None
    label: str
    session_state: str
    name: str | None = None


class TickerTapeResponse(BaseModel):
    session_label: str
    session_state: str
    is_live: bool
    quotes: list[QuoteOut]


class CompanyListItem(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: float | None
    change_pct: float | None = None
    price: float | None = None


class CompanyDetail(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    description: str | None
    market_cap: float | None
    pe_ratio: float | None
    eps: float | None
    revenue: float | None
    debt_to_equity: float | None
    dividend_yield: float | None
    price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    quote_label: str | None = None
    metrics: list[ExplainedMetric] = Field(default_factory=list)


class BubbleNode(BaseModel):
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: float
    change_pct: float
    price: float


class BubbleMapResponse(BaseModel):
    nodes: list[BubbleNode]
    sectors: list[str]


class RelationshipOut(BaseModel):
    target_ticker: str
    target_name: str
    relationship_type: str
    plain_english: str
    target_sector: str | None = None
    target_change_pct: float | None = None


class PricePoint(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class MacroIndicator(BaseModel):
    id: str
    label: str
    value: float
    as_of: date
    unit: str
    plain_english: str
    history: list[dict]


class AnalogyResponse(BaseModel):
    headline: str
    comparisons: list[dict]
    share_text: str


class FilingTranslateRequest(BaseModel):
    filing_type: str = "10-K"
    # Leave excerpt empty to have the server pull the real section from SEC EDGAR.
    excerpt: str = ""
    accession: str | None = None
    section: str = "risk_factors"


class EarningsRequest(BaseModel):
    context: str = ""


class WhyMoveRequest(BaseModel):
    as_of: str | None = None
    change_pct: float | None = None
