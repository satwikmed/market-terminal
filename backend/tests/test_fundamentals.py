"""Parsing rules for SEC XBRL company-facts.

Each case here is a real filing pattern that produced a wrong number before:
tags abandoned mid-decade, banks with no combined revenue line, and gaps in
early filings that would otherwise be charted as continuous years.
"""

from app.services.fundamentals import _annual, _bank_revenue, _recent_run, yahoo_ttm_revenue


def facts(**concepts: list[dict]) -> dict:
    return {"facts": {"us-gaap": {k: {"units": {"USD": v}} for k, v in concepts.items()}}}


def fy(year: int, val: float) -> dict:
    return {
        "form": "10-K",
        "fp": "FY",
        "fy": year,
        "val": val,
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
    }


class TestRecentRun:
    def test_stops_at_a_gap(self):
        assert _recent_run([2013, 2015, 2016, 2022, 2023, 2024]) == [2022, 2023, 2024]

    def test_keeps_contiguous_years(self):
        assert _recent_run([2020, 2021, 2022]) == [2020, 2021, 2022]

    def test_caps_at_limit_keeping_newest(self):
        assert _recent_run(range(2000, 2026), limit=3) == [2023, 2024, 2025]

    def test_handles_empty_and_single(self):
        assert _recent_run([]) == []
        assert _recent_run([2025]) == [2025]


class TestAnnualConceptSelection:
    def test_prefers_the_concept_reporting_the_most_recent_year(self):
        # ExxonMobil's pattern: the preferred tag was abandoned after 2021.
        data = facts(
            RevenueFromContractWithCustomerExcludingAssessedTax=[fy(2020, 1.0), fy(2021, 2.0)],
            Revenues=[fy(2024, 9.0), fy(2025, 10.0)],
        )
        concepts = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]
        assert _annual(data, concepts, duration=True) == {2024: 9.0, 2025: 10.0}

    def test_falls_back_to_coverage_then_listed_order_when_recency_ties(self):
        data = facts(
            First=[fy(2025, 1.0)],
            Second=[fy(2023, 2.0), fy(2024, 2.0), fy(2025, 2.0)],
        )
        assert _annual(data, ["First", "Second"], duration=True) == {
            2023: 2.0,
            2024: 2.0,
            2025: 2.0,
        }

    def test_never_blends_two_concepts_into_one_series(self):
        data = facts(Old=[fy(2019, 1.0)], New=[fy(2025, 5.0)])
        assert _annual(data, ["Old", "New"], duration=True) == {2025: 5.0}

    def test_ignores_quarterly_durations_for_flow_items(self):
        quarter = {
            "form": "10-K",
            "fp": "FY",
            "fy": 2025,
            "val": 3.0,
            "start": "2025-01-01",
            "end": "2025-03-31",
        }
        assert _annual(facts(Revenues=[quarter]), ["Revenues"], duration=True) == {}

    def test_returns_empty_when_no_concept_matches(self):
        assert _annual(facts(Revenues=[fy(2025, 1.0)]), ["Missing"], duration=True) == {}


class TestBankRevenue:
    def test_sums_net_interest_and_fee_income(self):
        data = facts(
            InterestIncomeExpenseNet=[fy(2024, 14.0), fy(2025, 15.0)],
            NoninterestIncome=[fy(2024, 5.0), fy(2025, 6.0)],
        )
        assert _bank_revenue(data) == {2024: 19.0, 2025: 21.0}

    def test_skips_years_missing_either_component(self):
        data = facts(
            InterestIncomeExpenseNet=[fy(2024, 14.0), fy(2025, 15.0)],
            NoninterestIncome=[fy(2025, 6.0)],
        )
        assert _bank_revenue(data) == {2025: 21.0}

    def test_returns_nothing_for_a_non_bank(self):
        assert _bank_revenue(facts(Revenues=[fy(2025, 1.0)])) == {}


class TestYahooRevenueFallback:
    def test_reads_total_revenue(self, monkeypatch):
        class FakeTicker:
            info = {"totalRevenue": 8_370_999_808}

        monkeypatch.setattr("yfinance.Ticker", lambda _ticker: FakeTicker())
        assert yahoo_ttm_revenue("APA") == 8_370_999_808.0

    def test_returns_none_when_missing(self, monkeypatch):
        class FakeTicker:
            info = {}

        monkeypatch.setattr("yfinance.Ticker", lambda _ticker: FakeTicker())
        assert yahoo_ttm_revenue("ZZZZ") is None
