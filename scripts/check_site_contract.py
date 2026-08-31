#!/usr/bin/env python3
"""Fail CI if the DSI-WEBSITE-1B site contract is broken.

The other checkers cover claim wording, link resolution and release provenance. THIS one holds
the structural and governance rulings that a later content edit could silently undo:

  * canonical route uniqueness and sitemap parity
  * redirect completeness, resolvable targets, no loops
  * maturity labels present where a tier is asserted
  * the Pluraxis watermark and caption
  * retired C-001 wording stays retired
  * DSI Audit is never described as a public release
  * the human-validation boundary is present verbatim
  * the GCB-2 public claim stays withheld, and appears exactly once
  * the privacy page states the verified edge-analytics position

Usage: python scripts/check_site_contract.py [root]   (default root = cwd)
Exit 1 on any breach, 0 if clean.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "https://decisionspaceintegrity.com"

C001 = ("DSI is a local, stateless assurance sidecar. It audits a supplied response; it does not "
        "generate one. It measures configured expected-path visibility")

HUMAN_VALIDATION = (
    "Independent human validation has not yet been conducted. Internal annotation, adjudication "
    "and calibration informed instrument development, but the lexical instruments remain "
    "self-validated. These activities do not establish independent agreement or accuracy.")

GCB2_WITHHELD = ("PUBLIC CLAIM WITHHELD — ORIGINAL INVALIDATED; "
                 "SUCCESSOR DID NOT RESOLVE THE CONTRAST")

PLURAXIS_WATERMARK = "TARGET ARCHITECTURE &#183; UNDER ACTIVE DEVELOPMENT"
PLURAXIS_CAPTION = ("Conceptual target architecture. Individual components exist at different "
                    "maturity levels; the integrated system and its effect on decision quality "
                    "are not established.")

# DSI Audit must never be described in public-release terms.
PUBLIC_RELEASE_BANNED = [
    re.compile(r"public(?:ly)?\s+(?:available|downloadable|released)\s+(?:build|release|version|artefact|artifact)", re.I),
    re.compile(r"download\s+DSI\s+Audit", re.I),
    re.compile(r"DSI Audit is (?:a |the )?public release", re.I),
]


def html_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.html") if ".git" not in p.parts)


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else Path(".").resolve()
    errors: list[str] = []
    pages = html_files(root)
    text = {p: p.read_text(encoding="utf-8", errors="replace") for p in pages}

    # ---- 1. canonical uniqueness -------------------------------------------------
    canon: dict[str, Path] = {}
    for p, s in text.items():
        m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if not m:
            errors.append(f"{p.relative_to(root)}: no canonical URL")
            continue
        c = m.group(1)
        if c in canon:
            errors.append(f"canonical {c} claimed by both {canon[c].name} and {p.name}")
        canon[c] = p

    # ---- 2. redirects: parse, targets resolve, no loops ---------------------------
    redirects: dict[str, str] = {}
    rf = root / "_redirects"
    if not rf.exists():
        errors.append("_redirects is missing")
    else:
        for ln, line in enumerate(rf.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                errors.append(f"_redirects:{ln}: malformed rule {line!r}")
                continue
            redirects[parts[0]] = parts[1]
        for src, dst in redirects.items():
            if dst in redirects:
                errors.append(f"_redirects: {src} -> {dst} -> {redirects[dst]} (chain/loop)")
            if src == dst:
                errors.append(f"_redirects: {src} redirects to itself")
            target = dst.lstrip("/") or "index"
            if not ((root / f"{target}.html").exists() or (root / target).exists()):
                errors.append(f"_redirects: target {dst} does not resolve to a page")
        # a retired route must not still exist as a page
        for src in redirects:
            stem = src.lstrip("/")
            if stem.endswith(".html") and (root / stem).exists():
                errors.append(f"_redirects: {src} is redirected but {stem} still exists")

    # ---- 3. sitemap parity -------------------------------------------------------
    sm = root / "sitemap.xml"
    if not sm.exists():
        errors.append("sitemap.xml is missing")
    else:
        locs = set(re.findall(r"<loc>(.*?)</loc>", sm.read_text(encoding="utf-8")))
        for loc in sorted(locs):
            path = loc.replace(SITE, "") or "/"
            stem = path.strip("/") or "index"
            if not (root / f"{stem}.html").exists():
                errors.append(f"sitemap lists {path} but {stem}.html does not exist")
            if path in redirects or f"{path}.html" in redirects:
                errors.append(f"sitemap lists {path}, which is a redirect source")
        if f"{SITE}/404" in locs:
            errors.append("sitemap must not list the 404 route")
        for required in ("/", "/dsc", "/dsi", "/audit", "/pluraxis", "/evidence", "/research", "/articles"):
            want = SITE + ("" if required == "/" else required)
            if required == "/":
                want = SITE + "/"
            if want not in locs:
                errors.append(f"sitemap is missing the canonical route {required}")

    # ---- 4. retired C-001 --------------------------------------------------------
    for p, s in text.items():
        if C001 in s:
            errors.append(f"{p.relative_to(root)}: retired C-001 sidecar definition is present")

    # ---- 5. maturity labels where a tier is asserted ------------------------------
    audit = root / "audit.html"
    if audit.exists():
        s = text[audit]
        if "Research implementation" not in s or "Private evaluation access" not in s:
            errors.append("audit.html: must carry both 'Research implementation' and "
                          "'Private evaluation access' maturity labels")
        if "no self-service public repository" not in s:
            errors.append("audit.html: must state that there is no self-service public repository")
    else:
        errors.append("audit.html is missing")

    plx = root / "pluraxis.html"
    if plx.exists():
        s = text[plx]
        if "<title>Pluraxis (target architecture)" not in s:
            errors.append("pluraxis.html: title must carry the target-architecture tier")
        if PLURAXIS_WATERMARK not in s:
            errors.append("pluraxis.html: maturity watermark missing from the image slot")
        if PLURAXIS_CAPTION not in s:
            errors.append("pluraxis.html: required diagram caption missing")
        # the revised diagram must be published, with a text equivalent
        if "/assets/diagrams/pluraxis-architecture.png" not in s:
            errors.append("pluraxis.html: revised architecture diagram is not referenced")
        else:
            img = re.search(r'<img[^>]*pluraxis-architecture\.png[^>]*>', s)
            if not img or 'alt="' not in img.group(0) or len(img.group(0)) < 200:
                errors.append("pluraxis.html: architecture diagram needs a descriptive alt text equivalent")
        # the unrevised owner-supplied source must never be published.
        # Local build inputs are legitimate on disk; only files git would publish are policed,
        # so anything named in .gitignore is skipped.
        ignored = set()
        gi = root / ".gitignore"
        if gi.exists():
            ignored = {ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()
                       if ln.strip() and not ln.startswith("#")}
        for stray in root.glob("assets/diagrams/*"):
            rel = stray.relative_to(root).as_posix()
            if stray.name != "pluraxis-architecture.png" and rel not in ignored:
                errors.append(f"{rel}: only the revised diagram may be published "
                              f"(the unrevised source is a build input)")
    else:
        errors.append("pluraxis.html is missing")

    # navigation label must carry the tier on every page.
    # Compare on rendered text, not raw markup: the tier suffix is wrapped in a <span> for
    # typographic treatment, which must not be mistaken for the tier having been dropped.
    detag = re.compile(r"<[^>]+>")
    for p, s in text.items():
        if 'href="/pluraxis"' in s:
            rendered = detag.sub("", s)
            if "Pluraxis (target architecture)" not in rendered:
                errors.append(f"{p.relative_to(root)}: Pluraxis nav label must carry its tier")

    # ---- 6. no public-release language for DSI Audit ------------------------------
    # A denial ("there is no publicly downloadable release") is exactly the wording this pack
    # requires, so a hit only counts when no negation precedes it on the same line.
    NEG = re.compile(r"\b(?:no|not|never|without|nor|neither)\b", re.I)
    for p, s in text.items():
        for line in s.splitlines():
            for rx in PUBLIC_RELEASE_BANNED:
                m = rx.search(line)
                if m and not NEG.search(line[:m.start()]):
                    errors.append(f"{p.relative_to(root)}: public-release language for DSI Audit: "
                                  f"{line.strip()[:110]}")

    # ---- 7. boundary wording present ---------------------------------------------
    hv = [p.name for p, s in text.items() if HUMAN_VALIDATION in s]
    if not hv:
        errors.append("the human-validation boundary paragraph appears on no page")

    g2 = [p.name for p, s in text.items() if GCB2_WITHHELD in s]
    if len(g2) != 1:
        errors.append(f"the GCB-2 withheld statement must appear on exactly one page, found {len(g2)}")
    for p, s in text.items():
        if re.search(r"GCB-?2", s) and GCB2_WITHHELD not in s:
            errors.append(f"{p.relative_to(root)}: mentions GCB-2 without the withheld statement")

    priv = root / "privacy.html"
    if priv.exists() and "injects a Web Analytics beacon script into every page at the edge" not in text[priv]:
        errors.append("privacy.html: verified edge-analytics position is missing")

    # ---- report ------------------------------------------------------------------
    if errors:
        print("SITE CONTRACT: FAIL")
        for e in errors:
            print(f"  {e}")
        print(f"\n{len(errors)} breach(es).")
        return 1
    print(f"SITE CONTRACT: PASS — {len(pages)} pages, {len(redirects)} redirects, "
          f"canonical/sitemap parity and all governance wording intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
