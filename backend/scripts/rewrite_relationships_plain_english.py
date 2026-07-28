"""Rewrite plain_english fields in relationships.json to remove dashes."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DASHES = re.compile(r"[\-–—−]")
WORD_HYPHEN = re.compile(r"([A-Za-z0-9])-([A-Za-z0-9])")


def rewrite_plain_english(s: str) -> str:
    if not s or not DASHES.search(s):
        return s
    out = s
    for pat, repl in [(r" — ", ": "), (r" – ", ": "), (r" − ", ": ")]:
        out = re.sub(pat, repl, out)
    for ch in ("—", "–", "−"):
        out = out.replace(ch, ": ")
    while WORD_HYPHEN.search(out):
        out = WORD_HYPHEN.sub(r"\1 \2", out)
    out = re.sub(r":\s*:", ":", out)
    out = re.sub(r":\s+and\b", " and", out, flags=re.I)
    out = re.sub(r"  +", " ", out)
    return out.strip()


def walk(o, *, counter: list[int]) -> None:
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "plain_english" and isinstance(v, str):
                new = rewrite_plain_english(v)
                if new != v:
                    o[k] = new
                    counter[0] += 1
            else:
                walk(v, counter=counter)
    elif isinstance(o, list):
        for x in o:
            walk(x, counter=counter)


def count_bad(o) -> int:
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "plain_english" and isinstance(v, str) and DASHES.search(v):
                n += 1
            else:
                n += count_bad(v)
    elif isinstance(o, list):
        for x in o:
            n += count_bad(x)
    return n


def main() -> int:
    path = Path(__file__).resolve().parents[1] / "app" / "data" / "relationships.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    counter = [0]
    walk(data, counter=counter)
    bad = count_bad(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"rewrote {counter[0]} plain_english values; remaining with dashes: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
