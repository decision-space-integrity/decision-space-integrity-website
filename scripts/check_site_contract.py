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
        # Version identity: v0.2.1 is the AVAILABLE EVALUATION BUILD, not "the product
        # version". The development line is stated separately and must never read as an
        # available or downloadable identity, because no 0.3.0 release exists.
        if "Available evaluation build" not in s:
            errors.append("audit.html: v0.2.1 must be labelled the available evaluation "
                          "build, not an advertised or current product version")
        if "supplied by request" not in s:
            errors.append("audit.html: the evaluation build must state that it is "
                          "supplied by request")
        if "Current development line" not in s or "unreleased" not in s:
            errors.append("audit.html: the current development line must be stated "
                          "separately and marked unreleased")
    else:
        errors.append("audit.html is missing")

    # The unreleased development line must never acquire a release identity. A "v"
    # prefix would read as a tagged release, and no 0.3.0 release exists: the product
    # repository's newest tag is v0.2.1 while pyproject declares 0.3.0 in development.
    for p, s in text.items():
        if re.search(r"\bv0\.3\.0\b", s):
            errors.append(f"{p.relative_to(root)}: 'v0.3.0' implies a tagged release; "
                          f"no 0.3.0 release exists - the development line is '0.3.0'")
        if re.search(r"0\.3\.0[^.]{0,60}?\b(?:download|available for|obtain|supplied by "
                     r"request|evaluation build)\b", s, re.I):
            errors.append(f"{p.relative_to(root)}: 0.3.0 is presented as available; it is "
                          f"an unreleased development line and v0.2.1 is the evaluation build")

    # Stacked maturity badges in a register cell need a real row gap, not line-height.
    ev = root / "evidence.html"
    if ev.exists():
        for cell in re.findall(r"<td\b[^>]*>.*?</td>", text[ev], re.S):
            if cell.count('class="tier ') >= 2 and "tierstack" not in cell:
                errors.append("evidence.html: a register cell stacks two maturity badges "
                              "without .tierstack, so they lose their row gap when they "
                              "wrap onto a second line")

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
    BARE_DSI = re.compile(r"(?<![\w-])DSI(?![\w-])(?!\s+Audit\b)")
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
        if a.count('<span class="tier tier-research">Research implementation</span>') < 4:
            errors.append("applications.html: every profile must carry a maturity tier "
                          "(advisory, regression, and both illustrative profiles)")
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
