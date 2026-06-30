#!/usr/bin/env python3
"""Fail CI if a public-facing doc makes a forbidden positive claim.

Encodes the manual claim-discipline check. DSI does NOT certify quality/safety/compliance/correctness, is NOT
human-validated, and does NOT guarantee or prove safety. Those words may appear only in NEGATED form
("does not certify", "not human-validated"). This scanner flags a claim word only when **no negation precedes
it on the same line**.

Usage:
    python scripts/check_claim_discipline.py            # default: README.md + docs/
    python scripts/check_claim_discipline.py PATH ...
Exit 1 on any un-negated forbidden claim, 0 if clean.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:  # robust printing of non-ASCII snippets on Windows consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Forbidden positive claims (case-insensitive). Each is allowed ONLY if negated on the same line.
CLAIMS = [
    (re.compile(r"certif\w*", re.I), "certify/certification"),
    (re.compile(r"guarantee\w*", re.I), "guarantee"),
    (re.compile(r"proves?\s+safety", re.I), "proves safety"),
    (re.compile(r"human[\s-]validated", re.I), "human-validated"),
    (re.compile(r"measures?\s+(?:advice\s+)?(?:quality|safety|compliance|correctness|truth)", re.I),
     "measures quality/safety/compliance/correctness/truth"),
    (re.compile(r"ensures?\s+compliance", re.I), "ensures compliance"),
]
# A claim is allowed if a negation OR an explicit disclaimer marker appears in its context window.
NEGATION = re.compile(
    r"(?:\bnot\b|\bno\b|\bnever\b|\bcannot\b|\bwithout\b|n't|\bnor\b|\bneither\b|≠"
    r"|\bdo(?:es)?\s+not\b|\bout[\s-]of[\s-]scope\b|\bnot\s+handled\b)", re.I)
TEXT_EXT = {".md", ".markdown", ".txt", ".html", ".htm", ".rst"}
SELF = {"check_claim_discipline.py"}
DEFAULT_PATHS = ["README.md", "docs"]


def iter_files(args: list[str]) -> list[Path]:
    targets = args or DEFAULT_PATHS
    files: list[Path] = []
    for a in targets:
        p = Path(a)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [f for f in p.rglob("*") if f.is_file()]
    return files


def main(argv: list[str]) -> int:
    hits = []
    for f in iter_files(argv):
        if f.suffix.lower() not in TEXT_EXT or f.name in SELF:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            # Context = previous + current + next line, so cross-line negation (markdown wrapping,
            # question -> "No." answers, "X, not Y") is recognised. A claim is flagged only when no
            # negation appears anywhere in that window.
            context = " ".join(lines[max(0, i - 2): i + 1])
            negated = NEGATION.search(context) is not None
            for rx, label in CLAIMS:
                if rx.search(line) and not negated:
                    hits.append((f, i, label, line.strip()[:130]))
    if hits:
        print("CLAIM-DISCIPLINE SCAN: FAIL — un-negated forbidden claim(s) in public-facing docs:")
        for f, i, label, line in hits:
            print(f"  {f}:{i}  [{label}]  {line}")
        print(f"\n{len(hits)} claim(s). DSI measures omission coverage only — these must be negated or removed.")
        return 1
    print("CLAIM-DISCIPLINE SCAN: PASS — no un-negated forbidden claims.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
