"""Refresh all live quotes + market caps from Yahoo."""

import asyncio

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models.entities import Company, QuoteSnapshot
from app.services.prices import refresh_universe
from app.services.seed import seed_companies, seed_macro, seed_relationships


async def main() -> None:
    await init_db()
    async with SessionLocal() as db:
        await seed_companies(db)
        await seed_relationships(db)
        await seed_macro(db)
        print("Fetching live Yahoo quotes + market caps…")
        result = await refresh_universe(
            db, with_fundamentals=True, with_history=True, history_period="6mo"
        )
        print(result)
        rows = (
            await db.execute(
                select(Company).order_by(Company.market_cap.desc().nullslast()).limit(10)
            )
        ).scalars().all()
        print("Top market caps:")
        for c in rows:
            q = (
                await db.execute(select(QuoteSnapshot).where(QuoteSnapshot.ticker == c.ticker))
            ).scalar_one_or_none()
            px = q.price if q else None
            print(f"  {c.ticker:6} ${ (c.market_cap or 0)/1e12:.2f}T  price={px}")


if __name__ == "__main__":
    asyncio.run(main())
