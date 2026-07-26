from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Company, PriceBar, QuoteSnapshot
from app.schemas import CompanyDetail, CompanyListItem, ExplainedMetric, PricePoint
from app.services.explainers import METRIC_CATALOG, analogy_for_market_cap, explain_metric

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyListItem])
async def list_companies(
    q: str | None = None,
    sector: str | None = None,
    limit: int = Query(600, le=600),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Company)
    if sector:
        stmt = stmt.where(Company.sector == sector)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Company.ticker.ilike(like)) | (Company.name.ilike(like)))
    stmt = stmt.order_by(Company.market_cap.desc().nullslast()).limit(limit)
    companies = (await db.execute(stmt)).scalars().all()
    quotes = {
        q.ticker: q
        for q in (await db.execute(select(QuoteSnapshot))).scalars().all()
    }
    return [
        CompanyListItem(
            ticker=c.ticker,
            name=c.name,
            sector=c.sector,
            industry=c.industry,
            market_cap=c.market_cap,
            change_pct=quotes[c.ticker].change_pct if c.ticker in quotes else None,
            price=quotes[c.ticker].price if c.ticker in quotes else None,
        )
        for c in companies
    ]


@router.get("/sectors")
async def list_sectors(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Company.sector).distinct().order_by(Company.sector))).all()
    return [r[0] for r in rows]


@router.get("/explain/{metric}")
async def explain(metric: str, value: float | None = None):
    return explain_metric(metric, value)


@router.get("/{ticker}", response_model=CompanyDetail)
async def get_company(ticker: str, db: AsyncSession = Depends(get_db)):
    c = (
        await db.execute(select(Company).where(Company.ticker == ticker.upper()))
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(404, f"{ticker} is not in the S&P 500 universe for this app.")
    quote = (
        await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == c.ticker))
    ).scalar_one_or_none()

    metrics: list[ExplainedMetric] = []
    mapping = {
        "pe_ratio": c.pe_ratio,
        "debt_to_equity": c.debt_to_equity,
        "market_cap": c.market_cap,
        "eps": c.eps,
        "dividend_yield": c.dividend_yield,
        "revenue": c.revenue,
    }
    for item in METRIC_CATALOG:
        explained = explain_metric(item["key"], mapping.get(item["key"]))
        metrics.append(ExplainedMetric(**explained))
    if quote:
        metrics.append(ExplainedMetric(**explain_metric("change_pct", quote.change_pct)))

    return CompanyDetail(
        ticker=c.ticker,
        name=c.name,
        sector=c.sector,
        industry=c.industry,
        description=c.description,
        market_cap=c.market_cap,
        pe_ratio=c.pe_ratio,
        eps=c.eps,
        revenue=c.revenue,
        debt_to_equity=c.debt_to_equity,
        dividend_yield=c.dividend_yield,
        price=quote.price if quote else None,
        change=quote.change if quote else None,
        change_pct=quote.change_pct if quote else None,
        quote_label=quote.label if quote else None,
        metrics=metrics,
    )


@router.get("/{ticker}/history", response_model=list[PricePoint])
async def price_history(ticker: str, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(PriceBar)
            .where(PriceBar.ticker == ticker.upper())
            .order_by(PriceBar.bar_date.asc())
        )
    ).scalars().all()
    return [
        PricePoint(
            date=r.bar_date,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
        )
        for r in rows
    ]


@router.get("/{ticker}/analogy")
async def market_cap_analogy(ticker: str, db: AsyncSession = Depends(get_db)):
    c = (
        await db.execute(select(Company).where(Company.ticker == ticker.upper()))
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Company not found")
    return analogy_for_market_cap(c.market_cap, c.name)
