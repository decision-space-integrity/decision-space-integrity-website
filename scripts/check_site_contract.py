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

import pathlib
import re
import subprocess
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
        # The unrevised owner-supplied source must never be published. .gitignore is NOT
        # proof of that: an already-tracked file keeps publishing regardless of ignore rules.
        # Inspect the actual tracked tree instead.
        tracked = set()
        try:
            out = subprocess.run(["git", "ls-files", "-z", "assets/diagrams"],
                                 cwd=root, capture_output=True, text=True, timeout=20)
            # FAIL CLOSED: a nonzero exit must not read as "nothing is tracked".
            if out.returncode != 0:
                errors.append(f"git ls-files failed (rc={out.returncode}); cannot prove the "
                              f"unrevised diagram is untracked: {out.stderr.strip()[:160]}")
            tracked = {t for t in out.stdout.split("\0") if t}
        except Exception as exc:                      # never pass silently on an unknown state
            errors.append(f"could not inspect the tracked tree for assets/diagrams: {exc}")
        for t in sorted(tracked):
            if pathlib.PurePosixPath(t).name != "pluraxis-architecture.png":
                errors.append(f"{t}: tracked in git, but only the revised diagram may be "
                              f"published (the unrevised source is a build input)")

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

    # ---- 8. identity assertions, over TWO representations -------------------------
    # RAW      : the source, so title/meta/OG/Twitter attribute text is visible.
    # RENDERED : scripts and styles removed, then tags stripped, so markup can no longer
    #            split a phrase and hide it from a substring scan.
    SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
    TAG = re.compile(r"<[^>]+>")

    def rendered(src: str) -> str:
        t = SCRIPT_STYLE.sub(" ", src)
        t = TAG.sub(" ", t)
        t = t.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#160;", " ")
        t = t.replace("&mdash;", "-").replace("&#8212;", "-").replace("\u2014", "-")
        return re.sub(r"\s+", " ", t)

    # Implementation verbs must never be attributed to bare DSI. Two allowances:
    #   - "DSI Audit <verb>" is correct and is excluded by the negative lookahead;
    #   - a denial ("DSI is not a ... sidecar") and genuine architecture subjects are
    #     allowed explicitly, rather than by weakening the pattern.
    IMPL_VERBS = ("installs?", "runs?", "audits?", "takes?", "checks?", "recommends?",
                  "re-runs?", "re-audits?", "provides?", "phones?", "generates?", "emits?",
                  "is run", "is at v", "installs")
    VERB_RX = re.compile(r"\bDSI\s+(?!Audit\b)(?:" + "|".join(IMPL_VERBS) + r")\b", re.I)
    IMPL_DEF_RX = re.compile(
        r"\bDSI\b[^.]{0,70}?\b(?:self-hosted|stateless|sidecar|assurance tool|"
        r"product candidate|local product)\b", re.I)
    ALLOWED_ARCH = (
        "DSI is not a Python package, an audit product or a sidecar",   # explicit denial
        "See how DSI works",                                            # link to the architecture
        "Where DSI fits",                                               # architecture positioning
    )

    STALE_PHRASES = (
        "Decision-Space Integrity Product",
        "Decision-Space Integrity 0.2.1",
        "v0.2.1 product candidate",
        "Public release notes",
        "currently released v0.2.1 product",
        "Human-validation packet prepared",
        "DSI never writes the advice",
        "See DSI work",
        "DSI is at v0.2.1",
        "a self-hosted, stateless assurance tool",
    )

    for p, s_ in text.items():
        name = p.relative_to(root).as_posix()
        ren = rendered(s_)
        raw_flat = re.sub(r"\s+", " ", s_)

        for label, hay in (("visible copy", ren), ("metadata/raw", raw_flat)):
            for m in VERB_RX.finditer(hay):
                frag = hay[max(0, m.start() - 70): m.end() + 70]
                if any(a in frag for a in ALLOWED_ARCH):
                    continue
                errors.append(f"{name}: implementation verb attributed to bare DSI "
                              f"({label}): {m.group(0).strip()!r}")
            for m in IMPL_DEF_RX.finditer(hay):
                frag = hay[max(0, m.start() - 70): m.end() + 70]
                if any(a in frag for a in ALLOWED_ARCH) or "is not" in frag or "not a " in frag:
                    continue
                errors.append(f"{name}: DSI defined as the implementation ({label}): "
                              f"{m.group(0).strip()[:70]!r}")

        for phrase in STALE_PHRASES:
            if phrase.lower() in ren.lower() or phrase.lower() in raw_flat.lower():
                errors.append(f"{name}: stale wording present: {phrase!r}")

    # the executable implementation is DSI Audit, never "DSI Product" or bare "DSI vX.Y.Z"
    mislabel = re.compile(r"DSI [Pp]roduct\b|\bDSI v?\d+\.\d+\.\d+")
    for p, s_ in text.items():
        for m in mislabel.finditer(re.sub(r"\s+", " ", s_)):
            errors.append(f"{p.relative_to(root)}: implementation mislabelled: {m.group(0)!r} "
                          f"(use 'DSI Audit')")

    # application profiles must not assert "Current" without a governing authority
    apps = root / "applications.html"
    if apps.exists() and re.search(r'class="statusflag">\s*Current\s*</span>', text[apps]):
        errors.append("applications.html: application profiles must carry a maturity tier, "
                      "not an unsupported 'Current' claim")

    # ---- 9. chip scope, metadata freshness, Pluraxis limits ------------------------
    AUDIT_SURFACES = {"audit.html", "getting-started.html", "deployment.html",
                      "security.html", "release-notes.html", "example-audit.html"}
    for p, s_ in text.items():
        name = p.relative_to(root).as_posix()
        foot = re.search(r'<footer class="site-foot">.*?</footer>', s_, re.S)
        if not foot:
            errors.append(f"{name}: no site footer"); continue
        chip = re.search(r'class="statusflag">([^<]*)</span>', foot.group(0))
        if not chip:
            errors.append(f"{name}: footer has no status chip"); continue
        val = chip.group(1).strip()
        if name in AUDIT_SURFACES:
            if "DSI Audit" not in val or "private evaluation" not in val:
                errors.append(f"{name}: Audit-surface chip must read "
                              f"'DSI Audit v... private evaluation', found {val!r}")
        elif "Research &amp; engineering programme" not in val:
            errors.append(f"{name}: global chip must read "
                          f"'Research & engineering programme', found {val!r}")

    HV_BANNED = ("challenge-tested only",
                 "possible future route to stronger human-anchored claims",
                 "Designed, Not Commissioned", "no annotations collected",
                 "human validation is planned", "recruitment is planned")
    for p, s_ in text.items():
        for b in HV_BANNED:
            if b.lower() in s_.lower():
                errors.append(f"{p.relative_to(root)}: legacy human-validation wording: {b!r}")

    idx = root / "index.html"
    if idx.exists():
        if "A self-hosted assurance system" in text[idx]:
            errors.append("index.html: stale 'A self-hosted assurance system' metadata is present")
        if "AI can give a good answer and still narrow the decision." not in text[idx]:
            errors.append("index.html: programme-level metadata positioning is missing")

    if plx.exists():
        s_ = text[plx]
        # Require the SPECIFIC limitation statements, not merely the words "not established"
        # somewhere on the page: a page with several such phrases would otherwise still pass
        # after the load-bearing one was removed.
        for needed, why in (
            ("Efficacy: not established", "efficacy badge"),
            ("effect it may have on decision quality, are <strong>not established</strong>",
             "decision-quality limitation"),
            ("its effect on decision quality are not established", "diagram caption limitation"),
        ):
            if needed not in s_:
                errors.append(f"pluraxis.html: {why} is missing ({needed[:52]!r})")
        if "integrated system" not in s_.lower():
            errors.append("pluraxis.html: integrated-system limitation is missing")

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
