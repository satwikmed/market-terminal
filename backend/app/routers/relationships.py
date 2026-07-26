from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Company, CompanyRelationship, QuoteSnapshot
from app.schemas import RelationshipOut

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.get("/{ticker}", response_model=list[RelationshipOut])
async def relationships_for(ticker: str, db: AsyncSession = Depends(get_db)):
    t = ticker.upper()
    rels = (
        await db.execute(
            select(CompanyRelationship).where(
                or_(
                    CompanyRelationship.source_ticker == t,
                    CompanyRelationship.target_ticker == t,
                )
            )
        )
    ).scalars().all()

    companies = {
        c.ticker: c for c in (await db.execute(select(Company))).scalars().all()
    }
    quotes = {
        q.ticker: q for q in (await db.execute(select(QuoteSnapshot))).scalars().all()
    }

    out: list[RelationshipOut] = []
    seen: set[str] = set()
    for r in rels:
        if r.source_ticker == t:
            other = r.target_ticker
            plain = r.plain_english
            rtype = r.relationship_type
        else:
            other = r.source_ticker
            # Flip perspective lightly
            plain = r.plain_english
            flip = {
                "supplier": "customer",
                "customer": "supplier",
                "competitor": "competitor",
                "partner": "partner",
            }
            rtype = flip.get(r.relationship_type, r.relationship_type)
        if other in seen:
            continue
        seen.add(other)
        c = companies.get(other)
        if not c:
            continue
        q = quotes.get(other)
        out.append(
            RelationshipOut(
                target_ticker=other,
                target_name=c.name,
                relationship_type=rtype,
                plain_english=plain,
                target_sector=c.sector,
                target_change_pct=q.change_pct if q else None,
            )
        )
    if not out and t not in companies:
        raise HTTPException(404, "Ticker not found")
    return out
