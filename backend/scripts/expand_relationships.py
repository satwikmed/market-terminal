"""Expand relationship graph so every S&P 500 company has connections.

Keeps curated supplier/customer/partner/competitor edges, then adds
industry-peer competitor links so smaller names are not orphans.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data"

sp500 = json.loads((DATA / "sp500.json").read_text())
curated = json.loads((DATA / "relationships.json").read_text())

by_industry: dict[str, list[dict]] = defaultdict(list)
by_sector: dict[str, list[dict]] = defaultdict(list)
for c in sp500:
    by_industry[c["industry"]].append(c)
    by_sector[c["sector"]].append(c)

tickers = {c["ticker"] for c in sp500}
# Drop curated edges that point outside the universe
edges: list[dict] = []
seen: set[tuple[str, str, str]] = set()


def add(src: str, tgt: str, rtype: str, plain: str) -> None:
    if src not in tickers or tgt not in tickers or src == tgt:
        return
    a, b = sorted([src, tgt])
    key = (a, b, rtype)
    # allow both competitor and supplier between same pair, but not duplicate same type
    if key in seen:
        return
    # also skip exact reverse duplicate of curated text edges
    rev = (b, a, rtype)
    if rev in seen and rtype == "competitor":
        return
    seen.add(key)
    edges.append(
        {
            "source": src,
            "target": tgt,
            "type": rtype,
            "plain_english": plain,
        }
    )


for r in curated:
    add(r["source"], r["target"], r["type"], r["plain_english"])

# Industry peers — every company gets up to 4 neighbors in same sub-industry
for industry, members in by_industry.items():
    members = sorted(members, key=lambda x: x["ticker"])
    n = len(members)
    if n < 2:
        continue
    for i, c in enumerate(members):
        # connect to next peers in a ring + one skip for denser local graph
        for offset in (1, 2):
            if n <= offset:
                continue
            other = members[(i + offset) % n]
            if other["ticker"] == c["ticker"]:
                continue
            plain = (
                f"{c['name']} and {other['name']} are both in {industry} — "
                f"they compete for similar customers and investor attention."
            )
            add(c["ticker"], other["ticker"], "competitor", plain)

# Sector fallback for singleton industries — link to 2 same-sector peers
for c in sp500:
    industry_mates = by_industry[c["industry"]]
    if len(industry_mates) >= 2:
        continue
    sector_mates = [x for x in by_sector[c["sector"]] if x["ticker"] != c["ticker"]]
    sector_mates = sorted(sector_mates, key=lambda x: x["ticker"])[:3]
    for other in sector_mates:
        plain = (
            f"{c['name']} and {other['name']} sit in the {c['sector']} sector — "
            f"their stocks often move with the same economic themes."
        )
        add(c["ticker"], other["ticker"], "competitor", plain)

out = DATA / "relationships.json"
out.write_text(json.dumps(edges, indent=2) + "\n")

covered = set()
for e in edges:
    covered.add(e["source"])
    covered.add(e["target"])
print(f"Wrote {len(edges)} relationships covering {len(covered)} / {len(tickers)} companies")
missing = sorted(tickers - covered)
print(f"Uncovered: {len(missing)} {missing[:10]}")
