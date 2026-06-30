#!/usr/bin/env python3
"""Fail if any LOCAL href/src in the site's HTML points at a missing file (broken link / missing asset).

External links (http/https///, mailto:, tel:), in-page anchors (#...), and data: URIs are not checked.
Clean-URL targets resolve against `<path>`, `<path>.html`, and `<path>/index.html`. Exit 1 on any break.

Usage: python scripts/check_links.py [root]   (default root = cwd)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ATTR = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)
SKIP_PREFIX = ("http://", "https://", "//", "mailto:", "tel:", "#", "data:", "javascript:")


def is_local(u: str) -> bool:
    u = u.strip()
    return bool(u) and not u.startswith(SKIP_PREFIX)


def resolve(target: str, page: Path, root: Path) -> list[Path]:
    t = target.split("#", 1)[0].split("?", 1)[0]
    if not t:
        return []
    base = root if t.startswith("/") else page.parent
    p = (base / t.lstrip("/")).resolve()
    return [p, p.with_suffix(".html"), p / "index.html"]


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path(".").resolve()
    broken = []
    pages = [p for p in sorted(root.rglob("*.html")) if ".git" not in p.parts]
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="ignore")
        for m in ATTR.finditer(text):
            u = m.group(1)
            if not is_local(u):
                continue
            candidates = resolve(u, page, root)
            if candidates and not any(c.exists() for c in candidates):
                broken.append((page.relative_to(root), u))
    if broken:
        print("LINK CHECK: FAIL — broken local links / missing assets:")
        for page, u in broken:
            print(f"  {page} -> {u}")
        return 1
    print(f"LINK CHECK: PASS — {len(pages)} HTML page(s), all local links/assets resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
