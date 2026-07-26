"""Warm the XBRL financials cache for every name and backfill Company.revenue
and Company.debt_to_equity from real filings (Yahoo omits these on the quote API).

Run:  PYTHONPATH=. .venv/bin/python scripts/backfill_fundamentals.py
"""

import asyncio
import time

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models.entities import Company
from app.services.fundamentals import build_financials, get_financials


async def main() -> None:
    await init_db()
    async with SessionLocal() as db:
        tickers = list((await db.execute(select(Company.ticker))).scalars().all())
    print(f"backfilling fundamentals for {len(tickers)} names")

    ok = revenue_set = de_set = 0
    for i, t in enumerate(tickers):
        try:
            # Warm the DB cache (parsed statements + ratios) for instant page loads.
            data = await asyncio.to_thread(build_financials, t)
        except Exception:
            data = None
        if not data:
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(tickers)} · ok={ok}")
            continue
        ok += 1
        async with SessionLocal() as db:
            # Persist into FinancialsCache via the service (force refresh path).
            await get_financials(db, t, force=True)
            company = (await db.execute(select(Company).where(Company.ticker == t))).scalar_one_or_none()
            if company:
                rev = data["statements"]["income"]["revenue"]
                latest_rev = next((v for v in reversed(rev) if v is not None), None)
                if latest_rev is not None:
                    company.revenue = float(latest_rev)
                    revenue_set += 1
                de = data["ratios"].get("debt_to_equity")
                if de is not None:
                    company.debt_to_equity = float(de)
                    de_set += 1
                await db.commit()
        time.sleep(0.08)  # SEC fair-access: stay well under 10 req/s
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(tickers)} · ok={ok} rev={revenue_set} de={de_set}")

    print(f"done: financials cached for {ok} names · revenue set {revenue_set} · debt/equity set {de_set}")


if __name__ == "__main__":
    asyncio.run(main())
