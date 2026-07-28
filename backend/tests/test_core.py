from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.config import Settings
from app.services.explainers import analogy_for_market_cap, explain_metric
from app.services.macro_data import _year_over_year
from app.services.market_hours import get_market_session

ET = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    ("moment", "state", "label", "is_live"),
    [
        (datetime(2026, 7, 25, 12, tzinfo=ET), "weekend", "Friday's Close", False),
        (datetime(2026, 7, 27, 10, tzinfo=ET), "open", "Yahoo · last sale", True),
        (
            datetime(2026, 7, 27, 17, tzinfo=ET),
            "closed_weekday",
            "Today's Close",
            False,
        ),
        (datetime(2026, 7, 27, 8, tzinfo=ET), "premarket", "Premarket", False),
    ],
)
def test_market_session(moment, state, label, is_live):
    session = get_market_session(moment)
    assert session.state == state
    assert session.label == label
    assert session.is_live is is_live


def test_plain_english_pe():
    result = explain_metric("pe_ratio", 25)
    assert result["value_display"] == "25.0"
    assert "$25" in result["plain_english"]
    assert "$1" in result["plain_english"]


def test_market_cap_analogy_is_shareable():
    result = analogy_for_market_cap(1_000_000_000_000, "Example Co")
    assert result["comparisons"]
    assert "Example Co" in result["share_text"]
    assert "Plain English Terminal" in result["share_text"]


def test_yoy_transformation():
    rows = [
        (datetime(2024, 1, 1).date(), 100.0),
        (datetime(2025, 1, 1).date(), 103.0),
    ]
    transformed = _year_over_year(rows)
    assert transformed == [(datetime(2025, 1, 1).date(), pytest.approx(3.0))]


def test_openai_provider_resolution():
    settings = Settings(
        openai_api_key="test-key",
        anthropic_api_key="",
        ai_provider="auto",
    )
    assert settings.resolved_ai_provider == "openai"


def test_no_provider_without_key():
    settings = Settings(
        openai_api_key="",
        anthropic_api_key="",
        ai_provider="auto",
    )
    assert settings.resolved_ai_provider is None
