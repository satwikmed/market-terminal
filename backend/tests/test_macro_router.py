import asyncio

from app.routers import macro


def reset_cache(monkeypatch):
    monkeypatch.setattr(macro, "_fomc_cache", None)
    monkeypatch.setattr(macro, "_fomc_cached_at", 0.0)


def test_fomc_calendar_is_cached(monkeypatch):
    reset_cache(monkeypatch)
    calls = 0

    async def fake_calendar():
        nonlocal calls
        calls += 1
        return {
            "date": "2026-09-16",
            "days_until": 52,
            "source": "Federal Reserve FOMC calendar",
            "source_url": "https://www.federalreserve.gov/",
        }

    monkeypatch.setattr(macro, "next_fomc_meeting", fake_calendar)
    first = asyncio.run(macro._cached_fomc())
    second = asyncio.run(macro._cached_fomc())

    assert first == second
    assert calls == 1


def test_fomc_failure_is_cached_as_unavailable(monkeypatch):
    reset_cache(monkeypatch)
    calls = 0

    async def failed_calendar():
        nonlocal calls
        calls += 1
        raise TimeoutError

    monkeypatch.setattr(macro, "next_fomc_meeting", failed_calendar)
    first = asyncio.run(macro._cached_fomc())
    second = asyncio.run(macro._cached_fomc())

    assert first["date"] is None
    assert "temporarily unavailable" in first["source"]
    assert second == first
    assert calls == 1
