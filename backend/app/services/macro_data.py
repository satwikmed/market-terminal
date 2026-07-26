"""Live macroeconomic data from public FRED CSV feeds and the Federal Reserve."""

from __future__ import annotations

import asyncio
import csv
import io
import re
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import MacroObservation

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# App series -> (FRED series, transformation)
SERIES: dict[str, tuple[str, str]] = {
    "CPIAUCSL_YOY": ("CPIAUCSL", "yoy"),
    "UNRATE": ("UNRATE", "level"),
    "FEDFUNDS": ("FEDFUNDS", "level"),
    "A191RL1Q225SBEA": ("A191RL1Q225SBEA", "level"),
    "UMCSENT": ("UMCSENT", "level"),
    "T10Y2Y": ("T10Y2Y", "level"),
    "RECESSION_PROB": ("RECPROUSM156N", "level"),
    "CPI_HOUSING": ("CUSR0000SAH1", "yoy"),
    "CPI_FOOD": ("CPIUFDSL", "yoy"),
    "CPI_ENERGY": ("CPIENGSL", "yoy"),
    "CPI_TRANSPORT": ("CPITRNSL", "yoy"),
    "CPI_MEDICAL": ("CPIMEDSL", "yoy"),
    "CPI_OTHER": ("CPILFESL", "yoy"),
}


def _parse_csv(text: str, series_id: str) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    for row in csv.DictReader(io.StringIO(text)):
        value = row.get(series_id)
        if not value or value == ".":
            continue
        try:
            rows.append((date.fromisoformat(row["observation_date"]), float(value)))
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def _year_over_year(rows: list[tuple[date, float]]) -> list[tuple[date, float]]:
    by_month = {(d.year, d.month): value for d, value in rows}
    transformed: list[tuple[date, float]] = []
    for d, value in rows:
        prior = by_month.get((d.year - 1, d.month))
        if prior is None or prior == 0:
            continue
        transformed.append((d, (value / prior - 1) * 100))
    return transformed


async def refresh_fred(db: AsyncSession) -> dict[str, Any]:
    """Refresh all macro series without requiring a FRED API key."""
    updated = 0
    latest: dict[str, str] = {}
    failures: dict[str, str] = {}

    def download_one(
        app_id: str, fred_id: str, transform: str
    ) -> tuple[str, list[tuple[date, float]] | None, str | None]:
        try:
            url = f"{FRED_CSV}?{urllib.parse.urlencode({'id': fred_id})}"
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "PlainEnglishTerminal/1.0 educational portfolio"
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
            rows = _parse_csv(text, fred_id)
            if transform == "yoy":
                rows = _year_over_year(rows)
            rows = rows[-72:]
            if not rows:
                raise ValueError("no observations returned")
            return app_id, rows, None
        except Exception as exc:  # noqa: BLE001
            return app_id, None, str(exc)

    results = await asyncio.gather(
        *[
            asyncio.to_thread(download_one, app_id, fred_id, transform)
            for app_id, (fred_id, transform) in SERIES.items()
        ]
    )
    for app_id, rows, error in results:
        if error or not rows:
            failures[app_id] = error or "no observations returned"
            continue
        try:
            await db.execute(
                delete(MacroObservation).where(MacroObservation.series_id == app_id)
            )
            for observation_date, value in rows:
                db.add(
                    MacroObservation(
                        series_id=app_id,
                        obs_date=observation_date,
                        value=value,
                    )
                )
                updated += 1
            latest[app_id] = rows[-1][0].isoformat()
        except Exception as exc:  # noqa: BLE001
            failures[app_id] = str(exc)
    await db.commit()
    return {
        "mode": "live_fred_csv",
        "updated": updated,
        "latest": latest,
        "failures": failures,
    }


async def next_fomc_meeting() -> dict[str, Any]:
    """Read the official Federal Reserve calendar and return the next meeting."""
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "PlainEnglishTerminal/1.0 educational portfolio"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[date] = []
    for year in (date.today().year, date.today().year + 1):
        anchor = soup.find(string=lambda text: bool(text and f"{year} FOMC Meetings" in text))
        if not anchor:
            continue
        year_link = anchor.parent
        for meeting in year_link.find_all_next("div", class_="row fomc-meeting"):
            # Stop once the next year's section begins.
            prior_year_heading = meeting.find_previous(
                string=lambda text: bool(text and re.search(r"\d{4} FOMC Meetings", text))
            )
            if not prior_year_heading or str(year) not in str(prior_year_heading):
                break
            month_el = meeting.find("div", class_="fomc-meeting__month")
            date_el = meeting.find("div", class_="fomc-meeting__date")
            if not month_el or not date_el:
                continue
            month_name = month_el.get_text(" ", strip=True)
            day_text = date_el.get_text(" ", strip=True).replace("*", "")
            day_match = re.search(r"(\d+)(?:\s*-\s*(\d+))?", day_text)
            if not day_match:
                continue
            end_day = int(day_match.group(2) or day_match.group(1))
            try:
                meeting_date = datetime.strptime(
                    f"{month_name} {end_day} {year}", "%B %d %Y"
                ).date()
            except ValueError:
                continue
            if meeting_date >= date.today():
                candidates.append(meeting_date)

    next_date = min(candidates) if candidates else None
    return {
        "date": next_date.isoformat() if next_date else None,
        "days_until": (next_date - date.today()).days if next_date else None,
        "source": "Federal Reserve FOMC calendar",
        "source_url": url,
    }
