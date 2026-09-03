#!/usr/bin/env python3
"""Fail CI if the DSI-WEBSITE-1B site contract is broken.

The other checkers cover claim wording, link resolution and release provenance. THIS one holds
the structural and governance rulings that a later content edit could silently undo:

  * canonical route uniqueness and sitemap parity
  * redirect completeness, resolvable targets, no loops
  * maturity labels present where a tier is asserted
  * the v1 product boundary: no Pluraxis, no GATE, no retired /pluraxis route
  * retired C-001 wording stays retired
  * DSI Audit is never described as a public release
  * the human-validation boundary is present verbatim
  * the GCB-2 public claim stays withheld, and appears exactly once
  * the privacy page records the full verified analytics history: the prior beacon
    observation, that the injection varied by request characteristics, the disable,
    how absence was verified, and the distinction from ordinary hosting processing
  * repository internals stay out of the published asset set (.assetsignore)

Usage: python scripts/check_site_contract.py [root]   (default root = cwd)
Exit 1 on any breach, 0 if clean.
"""
from __future__ import annotations

import json
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

# Approved primary navigation: understand -> evaluate -> verify.
# Home is provided by the site mark; Articles is footer material.
NAV_SEQUENCE = ["/dsc", "/dsi", "/audit", "/applications", "/evidence", "/research"]

C001 = ("DSI is a local, stateless assurance sidecar. It audits a supplied response; it does not "
        "generate one. It measures configured expected-path visibility")

HUMAN_VALIDATION = (
    "Independent human validation has not yet been conducted. Internal annotation, adjudication "
    "and calibration informed instrument development, but the lexical instruments remain "
    "self-validated. These activities do not establish independent agreement or accuracy.")

GCB2_WITHHELD = ("PUBLIC CLAIM WITHHELD — ORIGINAL INVALIDATED; "
                 "SUCCESSOR DID NOT RESOLVE THE CONTRAST")


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
            # a redirect may target a fragment (/research#programme-history); resolve
            # the page, then require the anchor to exist on it
            dst_path, _, dst_frag = dst.partition("#")
            target = dst_path.lstrip("/") or "index"
            tgt_file = root / f"{target}.html"
            if not (tgt_file.exists() or (root / target).exists()):
                errors.append(f"_redirects: target {dst} does not resolve to a page")
            elif dst_frag and tgt_file.exists():
                if f'id="{dst_frag}"' not in tgt_file.read_text(encoding="utf-8"):
                    errors.append(f"_redirects: target {dst} resolves to a page, but the "
                                  f"anchor #{dst_frag} does not exist on it")
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
        for required in ("/", "/dsc", "/dsi", "/audit", "/applications", "/evidence", "/research", "/articles"):
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
        # Version identity: v0.2.1 is the AVAILABLE EVALUATION BUILD, not "the product
        # version". The development line is stated separately and must never read as an
        # available or downloadable identity, because no 0.3.0 release exists.
        if "Available evaluation build" not in s:
            errors.append("audit.html: v0.2.1 must be labelled the available evaluation "
                          "build, not an advertised or current product version")
        if "supplied by request" not in s:
            errors.append("audit.html: the evaluation build must state that it is "
                          "supplied by request")
        # Option 2: two public identities only. 0.3.0 was an internal predecessor
        # development line, not the lineage that becomes v1, so it is off the public site.
        if "DSI v1" not in s or "Forthcoming" not in s:
            errors.append("audit.html: DSI v1 must be stated separately as forthcoming")
        for needed, why in (
            ("separately lineaged", "v1 must be marked separately lineaged"),
            ("unqualified", "v1 must be marked unqualified"),
            ("not released and not downloadable", "v1 must be marked unavailable"),
        ):
            if needed not in s:
                errors.append(f"audit.html: {why} ({needed!r} missing)")
        if "describes <strong>v0.2.1</strong>" not in s:
            errors.append("audit.html: the site's subordinate pages (installation, "
                          "deployment, security, release notes) must be stated as "
                          "describing v0.2.1")
        # v1 is forthcoming. Availability wording belongs to v0.2.1 and must never
        # migrate into the v1 definition, which is the subtlest way this could go wrong.
        fc = re.search(r"<dt>Forthcoming</dt>\s*<dd>(.*?)</dd>", s, re.S)
        if fc:
            # "evaluation build" is deliberately NOT here: the v1 entry legitimately
            # refers to the evaluation build's predecessor when stating its lineage.
            AVAILABILITY = ("supplied by request", "available for", "download", "obtain")
            for a in AVAILABILITY:
                if a in fc.group(1).lower() and a != "download":
                    errors.append(f"audit.html: the DSI v1 entry carries availability "
                                  f"wording ({a!r}); v1 is forthcoming and unavailable")
                elif a == "download" and re.search(r"(?<!not )downloadab", fc.group(1), re.I):
                    errors.append("audit.html: the DSI v1 entry reads as downloadable")
    else:
        errors.append("audit.html is missing")

    # The unreleased development line must never acquire a release identity. A "v"
    # prefix would read as a tagged release, and no 0.3.0 release exists: the product
    # repository's newest tag is v0.2.1 while pyproject declares 0.3.0 in development.
    for p, s in text.items():
        # 0.3.0 is an INTERNAL predecessor development line, not the lineage that becomes
        # v1. It is off the public site entirely, which also removes any opportunity to
        # imply that it becomes v1.
        if re.search(r"\b0\.3\.0\b", s):
            errors.append(f"{p.relative_to(root)}: 0.3.0 is an internal predecessor "
                          f"development line and must not appear in published copy")
        if re.search(r"\bv0\.3\.0\b", s):
            errors.append(f"{p.relative_to(root)}: 'v0.3.0' implies a tagged release; "
                          f"no 0.3.0 release exists - the development line is '0.3.0'")
        if re.search(r"0\.3\.0[^.]{0,60}?\b(?:download|available for|obtain|supplied by "
                     r"request|evaluation build)\b", s, re.I):
            errors.append(f"{p.relative_to(root)}: 0.3.0 is presented as available; it is "
                          f"an unreleased development line and v0.2.1 is the evaluation build")
        # 0.3.0 is an internal predecessor line, NOT the lineage that becomes v1. Saying so
        # publicly would be an unsupported lineage claim, which is why it is off the site.
        if re.search(r"0\.3\.0[^.]{0,80}?\bv1\b|\bv1\b[^.]{0,80}?0\.3\.0", s, re.I):
            errors.append(f"{p.relative_to(root)}: implies 0.3.0 becomes v1; they are "
                          f"separately lineaged and 0.3.0 is not published at all")

    # Stacked maturity badges in a register cell need a real row gap, not line-height.
    ev = root / "evidence.html"
    if ev.exists():
        for cell in re.findall(r"<td\b[^>]*>.*?</td>", text[ev], re.S):
            if cell.count('class="tier ') >= 2 and "tierstack" not in cell:
                errors.append("evidence.html: a register cell stacks two maturity badges "
                              "without .tierstack, so they lose their row gap when they "
                              "wrap onto a second line")

    # ---- 5b. the v1 product boundary: no Pluraxis, no GATE -------------------------
    # These rules previously asserted Pluraxis PRESENCE - watermark, caption, diagram,
    # alt text, efficacy limitations. Retiring the page made every one of them silently
    # skip, because they were guarded by `if pluraxis.html exists`. Absence is asserted
    # directly instead, so the retirement cannot be quietly undone.
    #
    # The site is the public account of the DSI v1 product line. Pluraxis and GATE are
    # listed as deliberately unsupported in v1 (DSI-V1 docs/CLAIM_BOUNDARIES.md); they
    # remain preserved in the governed repositories, not on the website.
    if (root / "pluraxis.html").exists():
        errors.append("pluraxis.html: retired from the published site; it must not return")

    # GATE is matched case-sensitively and word-bounded ON PURPOSE. Ordinary English on
    # this site contains "gates", "delegated", "request-gated", "investigated" and
    # "aggregate"; a loose scan would fire on all of them and would be turned off.
    #
    # The boundary is CONTEXTUAL, not lexical. An earlier draft of this rule demanded zero
    # references, which was wrong: deleting a negative finding is itself a claim. Pluraxis
    # and GATE carry no promotion, navigation, application profile or v1-capability
    # representation - but they remain permitted as bounded evidence and programme-history
    # disclosure, because "deliberation-loop efficacy: not established" has to survive.
    PLURAXIS_RX = re.compile(r"Pluraxis", re.I)
    GATE_RX = re.compile(r"(?<![\w-])GATE(?![\w-])")
    DISCLOSURE_PAGES = {"research.html", "evidence.html"}
    TITLE_RX = re.compile(r"<title>(.*?)</title>", re.S | re.I)
    META_RX = re.compile(r'<meta[^>]+content="([^"]*)"', re.I)
    HEAD_RX = re.compile(r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>", re.S | re.I)
    CARD_RX = re.compile(r'<span class="idx">(.*?)</span>', re.S | re.I)

    for p_, s_ in text.items():
        name = p_.relative_to(root).as_posix()
        nav_m = re.search(r'<nav[^>]*class="nav"[^>]*>(.*?)</nav>', s_, re.S)
        zones = [("primary navigation", nav_m.group(1) if nav_m else ""),
                 ("page title", " ".join(TITLE_RX.findall(s_))),
                 ("metadata", " ".join(META_RX.findall(s_))),
                 ("a heading", " ".join(HEAD_RX.findall(s_))),
                 ("an application or capability card", " ".join(CARD_RX.findall(s_)))]
        for rx, what in ((PLURAXIS_RX, "Pluraxis"), (GATE_RX, "GATE")):
            # (a) never in a promotional / navigational / capability position, any page
            for zone_name, zone in zones:
                if zone and rx.search(zone):
                    errors.append(f"{name}: {what} appears in {zone_name}; the v1 boundary "
                                  f"permits it only as bounded evidence or programme history")
            # (b) elsewhere, only on the two disclosure surfaces
            if name not in DISCLOSURE_PAGES and rx.search(s_):
                m = rx.search(s_)
                frag = " ".join(s_[max(0, m.start() - 60):m.end() + 60].split())
                errors.append(f"{name}: {what} is outside the v1 product boundary. Bounded "
                              f"disclosure belongs on /research or /evidence: ...{frag}...")
        if "/pluraxis" in s_:
            errors.append(f"{name}: links to the retired /pluraxis route")

    # The negative finding must survive the retirement - removing it would itself be a claim.
    ev_ = root / "evidence.html"
    if ev_.exists() and "Deliberation-loop efficacy" not in text[ev_]:
        errors.append("evidence.html: 'Deliberation-loop efficacy' must remain in the "
                      "register; a not-established finding is not removed with the "
                      "programme material it came from")

    # The programme history must say the wider work is preserved AND excluded from v1.
    res_ = root / "research.html"
    if res_.exists():
        r_ = text[res_]
        if "preserved in the governed repositories and excluded from" not in r_:
            errors.append("research.html: the programme-history section must state that the "
                          "wider work is preserved in the governed repositories and excluded "
                          "from DSI v1")

    # Applications took Pluraxis's place in the primary navigation. Assert its presence,
    # or the promotion could be reverted with no gate objecting - the same silent-skip
    # failure the retired Pluraxis rules had.
    NAV_RX = re.compile(r'<nav[^>]*class="nav"[^>]*>(.*?)</nav>', re.S)
    for p_, s_ in text.items():
        name = p_.relative_to(root).as_posix()
        nav = NAV_RX.search(s_)
        if not nav:
            errors.append(f"{name}: no primary navigation")
            continue
        # The approved sequence encodes the journey: understand -> evaluate -> verify.
        # Order is asserted, not merely membership - a reordering would change the story
        # the navigation tells while every link still resolved.
        seq = re.findall(r'<a href="(/[a-z-]*)"[^>]*>', nav.group(1))
        if seq != NAV_SEQUENCE:
            errors.append(f"{name}: primary navigation must be exactly "
                          f"{' -> '.join(NAV_SEQUENCE)}, found {' -> '.join(seq) or '(empty)'}")

    # The target-architecture diagram must not be in the published asset set at all.
    # Inspect the tracked tree: an untracked file cannot deploy, but a tracked one does
    # regardless of any ignore rule.
    try:
        out = subprocess.run(["git", "ls-files", "-z", "assets/diagrams"],
                             cwd=root, capture_output=True, text=True, timeout=20)
        # FAIL CLOSED: a nonzero exit must not read as "nothing is tracked".
        if out.returncode != 0:
            errors.append(f"git ls-files failed (rc={out.returncode}); cannot prove the "
                          f"target-architecture diagram is unpublished: "
                          f"{out.stderr.strip()[:160]}")
        for t in sorted(t for t in out.stdout.split("\0") if t):
            errors.append(f"{t}: tracked in git, but the target-architecture diagram is "
                          f"outside the v1 product boundary and must not be published")
    except Exception as exc:                      # never pass silently on an unknown state
        errors.append(f"could not inspect the tracked tree for assets/diagrams: {exc}")

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

    # Privacy: the analytics position must record the whole verified history, not just a
    # conclusion. The beacon injection VARIED BY REQUEST CHARACTERISTICS - a default
    # command-line client saw no beacon while a browser-equivalent client did - so a page
    # that simply asserts "no analytics" is not supported by a single clean fetch. The
    # page must carry the prior observation, the disable, the verification method, and
    # the distinction from ordinary hosting request processing.
    priv = root / "privacy.html"
    if priv.exists():
        pv = text[priv]
        required = {
            "the prior beacon observation":
                "Cloudflare was injecting a Web Analytics beacon script",
            "the beacon identity":
                "static.cloudflareinsights.com/beacon.min.js",
            "that injection varied by request characteristics":
                "varied by request characteristics",
            "the disable":
                "Web Analytics was <strong>disabled</strong>",
            "how absence was verified (both agents, not just a default client)":
                "once with a default command-line agent and once with a "
                "<strong>browser-equivalent</strong> agent",
            "the distinction from ordinary hosting request processing":
                "ordinary request processing every web host performs",
        }
        for what, needle in required.items():
            if needle not in pv:
                errors.append(f"privacy.html: the analytics position must record {what} "
                              f"(missing: {needle!r})")
        # CSP must not be offered as the basis of the absence claim
        if "script-src 'none'" in pv and "defence in depth" not in pv:
            errors.append("privacy.html: CSP is defence in depth, not evidence the beacon "
                          "is absent; the page must say so")

    # ---- 6b. surface classes: what a page is FOR decides what it may claim ----------
    # This replaces an earlier proximity rule that only fired when a withheld capability
    # sat near the literal string "DSI v1". A page could foreground regression,
    # fingerprints and comparability from top to bottom and never trip it. The boundary
    # is structural instead.
    #
    #   v1 surfaces        speak for the product. The withheld capabilities are absent,
    #                      and /dsi must POSITIVELY carry the four authorised ones.
    #   v0.2.1 surfaces    document the evaluation build. The withheld capabilities are
    #                      legitimate there, but the page must say so verbatim.
    #   disclosure         evidence and programme history; governed by their own rules.
    V1_SURFACES = ("index.html", "dsi.html", "applications.html")
    V021_SURFACES = ("audit.html", "getting-started.html", "deployment.html",
                     "security.html", "release-notes.html", "example-audit.html")
    SCOPE_MARKER = "This page documents the <strong>v0.2.1</strong> evaluation build."

    # Implemented in the evaluation build, NOT in v1. Multi-word where the single word is
    # ordinary English: "evidence" is fine, "evidence bundle" is a capability claim.
    WITHHELD = ("regression", "evidence bundle", "fingerprint", "provenance", "replay",
                "comparability", "readiness", "stateless", "revision", "intervention",
                "remediation")

    for name in V1_SURFACES:
        p_ = root / name
        if not p_.exists():
            errors.append(f"{name}: v1 surface is missing")
            continue
        src = re.sub(r"<(script|style)\b.*?</\1>", " ", text[p_], flags=re.S | re.I)
        # CONTEXTUAL EXCEPTION: an evidence-status section is disclosure wherever it
        # appears. A v1 surface may carry "comparability ... not established" as a
        # recorded negative finding - deleting it would itself be a claim. Sections
        # carrying an evidence chip are excluded from the capability scan.
        # Bounded to the CARD or ROW carrying the chip, not the whole section: exempting
        # a section would have exempted its heading too, and a capability claim promoted
        # into a heading beside an unrelated evidence badge would have passed.
        for pat in (r'<div class="card"[^>]*>(?:(?!</div>\s*</div>).)*?class="ev '
                    r'(?:(?!</div>\s*</div>).)*?</div>\s*</div>',
                    r'<tr\b(?:(?!</tr>).)*?class="ev (?:(?!</tr>).)*?</tr>'):
            src = re.sub(pat, " ", src, flags=re.S)
        body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", src)).lower()
        for w in WITHHELD:
            if w in body:
                i = body.index(w)
                errors.append(f"{name}: {w!r} is a v0.2.1 capability and must not appear on "
                              f"a v1 surface: ...{body[max(0, i - 60):i + 70]}...")

    for name in V021_SURFACES:
        p_ = root / name
        if not p_.exists():
            errors.append(f"{name}: v0.2.1 surface is missing")
            continue
        if SCOPE_MARKER not in text[p_]:
            errors.append(f"{name}: documents evaluation-build functionality, so it must "
                          f"carry the scope marker verbatim: {SCOPE_MARKER!r}")

    # /dsi must positively carry v1's authorised capabilities and the governed statuses -
    # otherwise gutting the page would satisfy the absence rules above.
    dsi_ = root / "dsi.html"
    if dsi_.exists():
        d = text[dsi_]
        for needed, why in (
            ("governed reference", "the reference the audit compares against"),
            ("coverage", "coverage over the applicable counted population"),
            ("omitted_safety_critical", "the orthogonal safety finding"),
        ):
            if needed.lower() not in d.lower():
                errors.append(f"dsi.html: v1 capability missing - {why} ({needed!r})")
        # The seven statuses must appear in the CAPABILITY TABLE, not merely somewhere on
        # the page. Several also occur in the pipeline diagram, so a page-wide search would
        # still pass after the governed partition itself had been gutted.
        STATUSES = ("surfaced", "partially surfaced", "omitted", "discouraged", "negated",
                    "collapsed into other", "warning-required-missing")
        tbl = re.search(r'<table class="reg">.*?</table>', d, re.S)
        if not tbl:
            errors.append("dsi.html: the capability table is missing")
        else:
            partition = tbl.group(0).lower()
            for st in STATUSES:
                if st.lower() not in partition:
                    errors.append(f"dsi.html: governed status {st!r} is missing from the "
                                  f"capability table; the seven-value partition is the "
                                  f"single authority for trajectory status")

    # ---- 7a. in-page anchors must resolve --------------------------------------------
    # check_links.py strips the fragment before resolving, so it proves the PAGE exists
    # but never that the anchor does. A link to /research#programme-history would keep
    # passing after the id was deleted, landing the reader at the top of the page with
    # no error anywhere. Every internal fragment link is resolved against the real ids.
    ids = {p: set(re.findall(r'\bid="([^"]+)"', s)) for p, s in text.items()}
    for p, s in text.items():
        name = p.relative_to(root).as_posix()
        for href in re.findall(r'href="([^"]*#[^"]+)"', s):
            if href.startswith(("http://", "https://", "//", "mailto:")):
                continue
            path, _, frag = href.partition("#")
            if not frag:
                continue
            target = p if path in ("", ".") else None
            if target is None:
                stem = path.strip("/") or "index"
                cand = root / (stem if stem.endswith(".html") else f"{stem}.html")
                if not cand.exists():
                    continue                      # check_links.py already reports this
                target = cand
            if frag not in ids.get(target, set()):
                errors.append(f"{name}: link {href!r} points at an anchor that does not "
                              f"exist on {target.relative_to(root).as_posix()}")

    # An anchored section must clear the sticky header, or the deep link lands with
    # the section heading hidden behind it.
    css = root / "styles.css"
    if css.exists() and "scroll-margin-top" not in css.read_text(encoding="utf-8"):
        errors.append("styles.css: anchored sections need scroll-margin-top, or a "
                      "deep link scrolls the heading behind the sticky header")

    # the programme history must stay reachable by its anchor
    res = root / "research.html"
    if res.exists() and "programme-history" not in ids.get(res, set()):
        errors.append("research.html: the programme-history anchor is missing; the "
                      "homepage and evidence register link to /research#programme-history")

    # ---- 7b. published asset surface ------------------------------------------------
    # The asset directory is the repository root, so without .assetsignore the whole
    # repository is published: /docs/, /scripts/, /.github/ and /README.md all returned
    # HTTP 200 on the production domain. Nothing there is secret, but none of it is the
    # site. These exclusions must not silently disappear.
    ASSETS_IGNORE_REQUIRED = (".github/", "docs/", "scripts/", "README.md",
                              ".gitattributes", ".gitignore", ".assetsignore",
                              "wrangler.jsonc")
    # ...and these must never be excluded: the platform consumes the first two and the
    # site links to the third.
    ASSETS_IGNORE_FORBIDDEN = ("_headers", "_redirects", "release_manifest.json",
                               "styles.css", "sitemap.xml", "robots.txt",
                               "assets/", "articles/")
    # Workers configuration. This file exists solely so unknown routes serve 404.html
    # instead of an empty body; not_found_handling is a Wrangler field, not a dashboard
    # option. It must stay a STATIC deployment: no "main" entry, and the asset directory
    # is the repository root (which is why .assetsignore is load-bearing).
    wr = root / "wrangler.jsonc"
    if not wr.exists():
        errors.append("wrangler.jsonc: missing - unknown routes would return an empty "
                      "body instead of the 404 page")
    else:
        # Parse it rather than pattern-match: only a parse can tell a TOP-LEVEL key from
        # the same word nested somewhere harmless. Strip whole-line // comments (jsonc);
        # a trailing comment after a value is left alone deliberately, so a value that
        # legitimately contains "//" is never mangled.
        raw_w = wr.read_text(encoding="utf-8")
        try:
            cfg = json.loads(re.sub(r"^\s*//.*$", "", raw_w, flags=re.M))
        except Exception as exc:
            cfg = None
            errors.append(f"wrangler.jsonc: does not parse as JSON once comments are "
                          f"stripped: {exc}")
        if cfg is not None:
            assets = cfg.get("assets") or {}
            if assets.get("not_found_handling") != "404-page":
                errors.append('wrangler.jsonc: assets.not_found_handling must be '
                              '"404-page" so unknown routes serve 404.html with a 404 '
                              f'status (found {assets.get("not_found_handling")!r})')
            if assets.get("directory") != ".":
                errors.append('wrangler.jsonc: assets.directory must be "." to match the '
                              f'deployed asset root (found {assets.get("directory")!r})')
            if "main" in cfg:
                errors.append("wrangler.jsonc: declares a Worker entrypoint; this "
                              "deployment is deliberately static with no Worker script")
            # Routes stay dashboard-owned. Cloudflare's documented pattern for that is to
            # omit route/routes AND set workers_dev false - omitting workers_dev defaults
            # it to TRUE and would publish a *.workers.dev endpoint.
            if cfg.get("workers_dev") is not False:
                errors.append('wrangler.jsonc: "workers_dev": false is required; omitting '
                              "it defaults to true and would publish a *.workers.dev "
                              "endpoint, widening the deployment surface")
            # Preview URLs are a SEPARATE control and are public when enabled. Cloudflare
            # documents the default as preview_urls = workers_dev, but that did not hold
            # here: with workers_dev false the build still published a versioned and a
            # branch-aliased preview URL, both serving the whole site with HTTP 200.
            if cfg.get("preview_urls") is not False:
                errors.append('wrangler.jsonc: "preview_urls": false is required; when '
                              "enabled they are public, and the documented default of "
                              "preview_urls = workers_dev was not applied in practice")
            for key in ("route", "routes"):
                if key in cfg:
                    errors.append(f"wrangler.jsonc: top-level {key!r} would override the "
                                  f"dashboard-managed custom domain on the next deploy; "
                                  f"routes stay owned by the dashboard")

    ai = root / ".assetsignore"
    if not ai.exists():
        errors.append(".assetsignore: missing - the repository root is the asset "
                      "directory, so every internal path would be published")
    else:
        lines = [ln.strip() for ln in ai.read_text(encoding="utf-8").splitlines()]
        entries = [ln for ln in lines if ln and not ln.startswith("#")]
        for req in ASSETS_IGNORE_REQUIRED:
            if req not in entries:
                errors.append(f".assetsignore: must exclude {req!r} from the published "
                              f"asset set")
        for forb in ASSETS_IGNORE_FORBIDDEN:
            if forb in entries:
                errors.append(f".assetsignore: must NOT exclude {forb!r} - the platform "
                              f"consumes it or the site depends on it")

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

    MAIN_RX = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)

    # ---- PRIMARY IDENTITY INVARIANT -------------------------------------------------
    # On a page that describes the executable thing, uppercase DSI must always read
    # "DSI Audit". An enumerated verb list is NOT a durable invariant: whichever verb
    # the copy reaches for next opens another hole, which is exactly how "DSI returns",
    # "DSI honestly reports", "DSI does not redact" and "What DSI does" survived two
    # amendments. This rule is closed by construction instead.
    #
    # Permitted on these surfaces:
    #   - "DSI Audit"                    - the implementation
    #   - "Decision-Space Integrity"     - the architecture, written in full
    #   - lowercase identifiers: dsi, dsi-product, imports, CLI commands (the pattern
    #     is case-sensitive and word-bounded, so these are untouched)
    # Only <main> is scanned: the shared nav and footer chrome legitimately carry the
    # architecture name and are governed by the chip and footer rules below.
    PRODUCT_SURFACES = ("getting-started.html", "example-audit.html", "deployment.html",
                        "security.html", "release-notes.html", "contact.html",
                        "applications.html")
    # "DSI Audit" and "DSI v1" are both named product identities and are allowed. Anything
    # else uppercase and bare is the architecture being used as if it were the executable.
    BARE_DSI = re.compile(r"(?<![\w-])DSI(?![\w-])(?!\s+(?:Audit|v1)\b)")
    for _name in PRODUCT_SURFACES:
        _p = root / _name
        if not _p.exists():
            errors.append(f"{_name}: product/runtime surface is missing")
            continue
        _m = MAIN_RX.search(text[_p])
        if not _m:
            errors.append(f"{_name}: no <main> element, so the identity rule cannot be "
                          f"applied to its main content")
            continue
        _body = rendered(_m.group(1))
        for _hit in BARE_DSI.finditer(_body):
            _frag = _body[max(0, _hit.start() - 60): _hit.end() + 60].strip()
            errors.append(f"{_name}: bare 'DSI' in main content - on a product/runtime "
                          f"surface the executable actor is 'DSI Audit', or name the "
                          f"architecture in full: ...{_frag}...")

    # Secondary net, for the pages where bare DSI is legitimate (architecture surfaces):
    # implementation verbs must still never be attributed to bare DSI. Two allowances:
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
        # retired at the final identity closure. "DSI is offered for evaluation" and
        # "DSI is an experimental system" sit on /research, an architecture surface the
        # main-content rule does not cover, so they are retired by name instead.
        "DSI is offered for",
        "DSI is an experimental system",
        "See the product",
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

    # Application profiles must not assert "Current" without a governing authority, and
    # a page that presents itself "by maturity" must classify every profile it shows.
    # The two illustrative profiles - AI-summary assurance and the policy-assurance
    # report - are classed on both axes: the maturity of the underlying comparison, and
    # whether the application itself is established. Advisory and Regression Audit carry
    # the implementation tier.
    apps = root / "applications.html"
    if apps.exists():
        a = text[apps]
        if re.search(r'class="statusflag">\s*Current\s*</span>', a):
            errors.append("applications.html: application profiles must carry a maturity "
                          "tier, not an unsupported 'Current' claim")
        n_axes = a.count('class="axes"')
        if n_axes < 2:
            errors.append(f"applications.html: the illustrative profiles (AI-summary "
                          f"assurance, policy-assurance report) must each be classified on "
                          f"both axes; found {n_axes} two-axis block(s), expected 2")
        if a.count('<span class="ev ev-not">Not established</span>') < 2:
            errors.append("applications.html: each illustrative profile must record "
                          "application validity as 'Not established'")
        # three profiles remain: advisory audit and the two illustrative ones. Regression
        # comparison was removed - it is a v0.2.1 capability, not a v1 application.
        if a.count('<span class="tier tier-research">Research implementation</span>') < 3:
            errors.append("applications.html: every profile must carry a maturity tier "
                          "(advisory audit and both illustrative profiles)")
        if "does not establish the completeness or authority of the policy-obligation set" not in a:
            errors.append("applications.html: the policy-assurance illustration must state "
                          "that executing an expected-point comparison does not establish "
                          "the completeness or authority of the obligation set, policy-"
                          "assurance validity, or compliance")

    # the human-validation limitation must be one click from the concise statement
    aud = root / "audit.html"
    if aud.exists():
        a = text[aud]
        _i = a.find("Independent human validation has not yet been conducted")
        if _i >= 0 and 'href="/evidence"' not in a[_i:_i + 300]:
            errors.append("audit.html: the human-validation statement must link directly "
                          "to /evidence so the full approved limitation is one click away")

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
