"""Tests for the move-attribution engine and the deterministic narrative.

These cover the parts of the app that must stay correct without a network
connection or an AI provider.
"""

from app.services.ai import _drivers_from_evidence
from app.services.move_evidence import Evidence, _attribution, deterministic_narrative


def test_attribution_splits_a_pure_market_move():
    """A stock that moves exactly with the market is not company-specific news."""
    result = _attribution(1.0, {"market_median_pct": 1.0, "sector_median_pct": 1.0})
    assert result is not None
    assert result["company_specific_pct"] == 0.0
    assert result["sector_excess_pct"] == 0.0
    assert result["dominant"] == "market"
    assert result["shares"]["market"] == 100


def test_attribution_isolates_company_specific_move():
    result = _attribution(8.0, {"market_median_pct": 0.5, "sector_median_pct": 0.5})
    assert result["company_specific_pct"] == 7.5
    assert result["dominant"] == "company"
    assert result["shares"]["company"] > result["shares"]["market"]


def test_attribution_detects_sector_move():
    result = _attribution(-4.0, {"market_median_pct": 0.2, "sector_median_pct": -3.8})
    assert result["sector_excess_pct"] == -4.0
    assert result["dominant"] == "sector"


def test_attribution_needs_market_context():
    assert _attribution(2.0, {}) is None


def test_narrative_flags_absence_of_filings():
    narrative = deterministic_narrative("XYZ", "Example Co", 1.2, None, [])
    assert "No SEC filing landed" in narrative
    assert "not a proven cause" in narrative


def test_narrative_cites_filings_when_present():
    evidence = [
        Evidence(
            kind="filing",
            title="XYZ filed an 8-K",
            detail="Breaking news filing.",
            source="SEC EDGAR",
            source_url="https://sec.gov/example",
            numbers={"form": "8-K", "filed": "2026-07-24"},
        )
    ]
    narrative = deterministic_narrative("XYZ", "Example Co", -5.0, None, evidence)
    assert "8-K on 2026-07-24" in narrative
    assert "No SEC filing landed" not in narrative


def test_drivers_are_ranked_and_carry_sources():
    bundle = {
        "evidence": [
            {"kind": "macro", "title": "CPI", "detail": "d", "source": "FRED", "source_url": None},
            {
                "kind": "volatility",
                "title": "Big day",
                "detail": "d",
                "source": "computed",
                "source_url": None,
            },
        ]
    }
    drivers = _drivers_from_evidence(bundle)
    assert [d["confidence"] for d in drivers] == sorted(
        (d["confidence"] for d in drivers), reverse=True
    )
    assert drivers[0]["title"] == "Big day"
    assert all("hedge" in d and d["source"] for d in drivers)
