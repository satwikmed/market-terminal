import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.models.entities import Company
from app.services.prices import apply_fundamentals, fetch_fundamentals


async def main() -> None:
    async with SessionLocal() as db:
        tickers = [r[0] for r in (await db.execute(select(Company.ticker))).all()]
        print(f"Re-fetching fundamentals for {len(tickers)} tickers…")
        funds = fetch_fundamentals(tickers, workers=8)
        n = await apply_fundamentals(db, funds)
        print(f"Updated {n}")
        rows = (
            await db.execute(
                select(Company).order_by(Company.market_cap.desc().nullslast()).limit(12)
            )
        ).scalars().all()
        for c in rows:
            mc = (c.market_cap or 0) / 1e12
            print(f"  {c.ticker:6} ${mc:.2f}T  pe={c.pe_ratio}")


if __name__ == "__main__":
    asyncio.run(main())
