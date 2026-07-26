from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_sp500() -> list[dict]:
    path = DATA_DIR / "sp500.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_relationships() -> list[dict]:
    path = DATA_DIR / "relationships.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_demo_quotes() -> dict[str, dict]:
    path = DATA_DIR / "demo_quotes.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_macro_seed() -> dict:
    path = DATA_DIR / "macro_seed.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)
