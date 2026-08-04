#!/usr/bin/env python3
"""Release-provenance check (owner-required after the v0.2.0/v0.2.1 worked-example
mismatch): every public audit id, classifier identity and current-version chip on the
site must match the pinned release_manifest.json. File existence and claim wording are
covered by the other checkers; THIS one catches a page quoting evidence from a
different release than the one the site says it documents."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))

AUDIT_ID = re.compile(r"audit_[0-9a-f]{16}")
CLASSIFIER = re.compile(r"(?:expected-map-)?lexical-precision-v\d+")
# The version chip pattern used on every page ("v0.2.1 · evaluation & pilot").
VERSION_CHIP = re.compile(r"(v\d+\.\d+\.\d+)\s*(?:·|&#183;|&middot;)\s*evaluation")

def main() -> int:
    errors: list[str] = []
    allowed_ids = set(MANIFEST["public_audit_ids"])
    superseded = set(MANIFEST.get("superseded_audit_ids", []))
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in (".html", ".js", ".md", ".xml"):
            continue
        if any(part in (".git", "scripts") for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in AUDIT_ID.findall(text):
            if match in superseded:
                errors.append(f"{rel}: SUPERSEDED audit id {match} — regenerate from "
                              f"the {MANIFEST['current_version']} release bundle")
            elif match not in allowed_ids:
                errors.append(f"{rel}: audit id {match} is not in release_manifest.json")
        for match in CLASSIFIER.findall(text):
            if not MANIFEST["classifier_version"].endswith(match) and \
                    match != MANIFEST["classifier_version"]:
                errors.append(f"{rel}: classifier identity {match!r} != pinned "
                              f"{MANIFEST['classifier_version']!r}")
        for match in VERSION_CHIP.findall(text):
            if match != MANIFEST["current_version"]:
                errors.append(f"{rel}: version chip {match} != pinned "
                              f"{MANIFEST['current_version']}")
    if errors:
        print("RELEASE-PROVENANCE FAILURES:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"release provenance ok: version {MANIFEST['current_version']}, "
          f"classifier {MANIFEST['classifier_version']}, "
          f"{len(allowed_ids)} public audit id(s)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
