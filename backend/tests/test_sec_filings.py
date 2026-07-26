"""Offline tests for SEC section parsing and deployment URL handling."""

from app.database import normalize_database_url
from app.services.sec_filings import cik_for, extract_section, load_cik_map

TEN_K = """
Table of Contents
Item 1A. Risk Factors
Item 1B. Unresolved Staff Comments

PART I
Item 1. Business
We design and sell widgets to customers around the world. Our widgets are
manufactured by third parties and sold through retail and online channels.
This section is long enough to clear the minimum length filter that guards
against matching a table-of-contents entry instead of the real section body.
We operate in three reportable segments and sell in over forty countries.
Our fiscal year ends on the last Saturday of September, and we employ roughly
twelve thousand people across manufacturing, engineering, and support roles.
Seasonality means a disproportionate share of revenue lands in the holiday
quarter, which is typical for consumer hardware businesses of our size.

Item 1A. Risk Factors
Our business faces competition, supply chain disruption, and regulatory change.
Any of these could materially and adversely affect our results of operations.
We also depend on a small number of suppliers for critical components, and the
loss of any one of them could delay production. This body text is deliberately
padded so the extractor treats it as a genuine section rather than noise.

Item 1B. Unresolved Staff Comments
None.
"""


def test_extract_section_skips_table_of_contents():
    """The first 'Item 1A' hit is a contents entry; the real section comes later."""
    body = extract_section(TEN_K, "risk_factors")
    assert body is not None
    assert body.startswith("Item 1A. Risk Factors")
    assert "competition, supply chain disruption" in body
    assert "Unresolved Staff Comments" not in body


def test_extract_section_stops_at_next_item():
    body = extract_section(TEN_K, "business")
    assert body is not None
    assert "We design and sell widgets" in body
    assert "supply chain disruption" not in body


def test_extract_section_returns_none_when_absent():
    assert extract_section("There are no numbered items in this 8-K.", "mda") is None


def test_cik_map_covers_the_universe():
    mapping = load_cik_map()
    assert len(mapping) > 490
    assert cik_for("aapl") == "0000320193"
    assert all(len(cik) == 10 and cik.isdigit() for cik in mapping.values())


def test_cik_lookup_is_none_for_unknown_ticker():
    assert cik_for("NOTATICKER") is None


def test_render_postgres_url_is_made_async():
    assert normalize_database_url("postgres://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"
    assert (
        normalize_database_url("postgresql://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"
    )


def test_sslmode_is_stripped_for_asyncpg():
    # asyncpg rejects libpq's sslmode parameter, which managed Postgres URLs include.
    assert "sslmode" not in normalize_database_url("postgres://u:p@host/db?sslmode=require")


def test_sqlite_url_is_untouched():
    url = "sqlite+aiosqlite:///./plain_english.db"
    assert normalize_database_url(url) == url
