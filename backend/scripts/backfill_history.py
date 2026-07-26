"""One-off: backfill 2 years of daily bars for every name + the SPY benchmark.

Run from the backend directory:  .venv/bin/python -m scripts.backfill_history
"""

import asyncio

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models.entities import Company
from app.services.prices import BENCHMARK_TICKER, _chunk, fetch_history_batch, upsert_history


async def main() -> None:
    await init_db()
    async with SessionLocal() as db:
        tickers = list((await db.execute(select(Company.ticker))).scalars().all())
    all_syms = [*tickers, BENCHMARK_TICKER]
    print(f"backfilling 2y history for {len(all_syms)} symbols (incl {BENCHMARK_TICKER})")

    total = 0
    for i, batch in enumerate(_chunk(all_syms, 40)):
        frames = await asyncio.to_thread(fetch_history_batch, batch, "2y")
        async with SessionLocal() as db:
            n = await upsert_history(db, frames)
        total += n
        print(f"  batch {i + 1}: {len(frames)} symbols, {n} bars (running total {total})")
    print(f"done: {total} bars")


if __name__ == "__main__":
    asyncio.run(main())
