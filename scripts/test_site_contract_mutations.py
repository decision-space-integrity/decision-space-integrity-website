#!/usr/bin/env python3
"""Pinned mutation suite for check_site_contract.py.

A contract check is only worth its green tick if it fails when the contract is broken.
Each case below breaks one rule, asserts the checker rejects it, and restores the file.
Cases deliberately cover all three representations that have hidden a defect before:

  * plain visible copy
  * body text SPLIT BY MARKUP (a substring scan on raw HTML misses this)
  * tag ATTRIBUTES - title/meta/OG/Twitter (a scan on rendered text misses this)
  * implementation verbs attributed to bare DSI

Usage: python scripts/test_site_contract_mutations.py [root]
Exit 1 if any mutation is NOT caught, 0 if every one is.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(".").resolve()
CHECK = ROOT / "scripts" / "check_site_contract.py"

# (name, file, find, replace)
CASES = [
    ("verb: bare DSI installs (visible copy)", "getting-started.html",
     "DSI Audit installs as an ordinary Python package", "DSI installs as an ordinary Python package"),
    ("verb: bare DSI audits (visible copy)", "security.html",
     "DSI Audit audits a supplied prompt/response pair.", "DSI audits a supplied prompt/response pair."),
    ("verb: bare DSI phones home (visible copy)", "security.html",
     "DSI Audit phones nothing home.", "DSI phones nothing home."),
    ("verb: bare DSI runs (visible copy)", "deployment.html",
     "DSI Audit runs in offline", "DSI runs in offline"),
    ("verb: bare DSI takes (visible copy)", "example-audit.html",
     "DSI Audit takes this as input", "DSI takes this as input"),
    ("body text SPLIT BY MARKUP", "dsc.html",
     "<h1 style=\"max-width:20ch;\">Decision-Space Collapse.</h1>",
     "<h1 style=\"max-width:20ch;\">Decision-Space Collapse.</h1><p>DSI is a <em>self-hosted</em> assurance tool.</p>"),
    ("METADATA: DSI defined as implementation", "dsi.html",
     '<meta name="description" content="Decision-Space Integrity is the measurement',
     '<meta name="description" content="DSI is a self-hosted, stateless assurance tool. Integrity is the measurement'),
    ("METADATA: DSI Product mislabel", "audit.html",
     'content="DSI Audit is the current local implementation',
     'content="DSI Product is the current local implementation'),
    ("stale: Decision-Space Integrity Product", "release-notes.html",
     "DSI Audit 0.2.1", "Decision-Space Integrity Product 0.2.1"),
    ("stale: v0.2.1 product candidate", "andrew-j-cousins.html",
     "is the current local implementation of it", "is a v0.2.1 product candidate of it"),
    ("stale: human-validation packet wording", "paper.html",
     "Independent human validation has not yet been conducted.",
     "Human-validation packet prepared; independent validation not yet complete."),
    ("stale: currently released v0.2.1 product", "research.html",
     "private-evaluation DSI Audit v0.2.1 build", "currently released v0.2.1 product"),
    ("applications: unsupported 'Current' claim", "applications.html",
     '<span class="tier tier-research">Research implementation</span>',
     '<span class="statusflag">Current</span>'),
    ("chip: programme chip removed", "dsc.html",
     "Research &amp; engineering programme", "v0.2.1 &#183; evaluation &amp; pilot"),
    ("chip: Audit-surface chip removed", "audit.html",
     "DSI Audit v0.2.1 &#183; private evaluation", "Research &amp; engineering programme"),
    ("homepage: stale metadata returns", "index.html",
     "AI can give a good answer and still narrow the decision. Decision-Space Integrity measures",
     "A self-hosted assurance system that measures. Decision-Space Integrity measures"),
    # --- v1 product boundary. Pluraxis and GATE are deliberately unsupported in v1
    # (DSI-V1 docs/CLAIM_BOUNDARIES.md); the site is the account of the product line, not
    # the programme archive. GATE is matched case-sensitively and word-bounded, so
    # "request-gated", "delegated" and "Aggregate" stay legal.
    ("boundary: Pluraxis returns to a page", "dsi.html",
     "<h1", "<h1 data-note=\"Pluraxis\""),
    ("boundary: GATE returns to a page", "dsi.html",
     "Measurement is separate from disposition",
     "GATE governs disposition. Measurement is separate from disposition"),
    ("boundary: the retired /pluraxis route is linked again", "index.html",
     'href="/applications"', 'href="/pluraxis"'),
    ("boundary: Applications drops out of the primary navigation", "index.html",
     '<a href="/applications">Applications</a>', ''),
    # The contextual rule has a POSITIVE side: bounded disclosure must survive. Deleting a
    # not-established finding along with the programme material would itself be a claim.
    ("boundary: the not-established deliberation-loop finding is deleted", "evidence.html",
     "Deliberation-loop efficacy", "Deliberation loop"),
    ("boundary: programme history stops saying the work is excluded from v1", "research.html",
     "preserved in the governed repositories and excluded from", "described in"),
    # a disclosure page may carry the words, but never in a heading
    ("boundary: Pluraxis promoted into a heading on a disclosure page", "research.html",
     "<h2>How the work has unfolded.</h2>", "<h2>Pluraxis and how the work has unfolded.</h2>"),
    # the retired route must land somewhere real
    ("boundary: the /pluraxis redirect anchor is broken", "research.html",
     'id="programme-history"', 'id="programme-timeline"'),
    # --- final identity closure: bare uppercase DSI in the main content of a
    # product/runtime surface. These are the exact residuals that survived two
    # amendments because the contract enumerated verbs instead of closing the rule.
    ("bare DSI: 'DSI returns'", "getting-started.html",
     "; DSI Audit returns configured expected-path visibility.",
     "; DSI returns configured expected-path visibility."),
    ("bare DSI: 'DSI honestly reports'", "getting-started.html",
     "so DSI Audit reports the result as <em>instrument-limited</em>",
     "so DSI honestly reports it as <em>instrument-limited</em>"),
    ("bare DSI: 'DSI does not redact'", "security.html",
     "DSI Audit does not redact them for you.", "DSI does not redact them for you."),
    ("bare DSI: \"DSI's finance example bundle\"", "example-audit.html",
     "taken from DSI Audit's finance example bundle", "taken from DSI's finance example bundle"),
    ("bare DSI: 'What DSI does'", "example-audit.html",
     '<p class="eyebrow reveal-up">What DSI Audit does</p>',
     '<p class="eyebrow reveal-up">What DSI does</p>'),
    # an UNRECOGNISED verb: the whole point of the rule change. No verb list contains
    # "orchestrates"; the contract must reject it anyway.
    ("bare DSI: previously unrecognised verb", "deployment.html",
     "DSI Audit runs in offline", "DSI orchestrates and runs in offline"),
    # architecture surface, retired formulation (not covered by the main-content rule)
    ("retired: 'DSI is offered for evaluation'", "research.html",
     "DSI Audit is available for <strong>private evaluation</strong>",
     "DSI is offered for <strong>evaluation</strong>"),
    # applications: either illustrative profile left unclassified
    ("applications: illustrative profile unclassified", "applications.html",
     '          <div><span class="k">Application validity</span>'
     '<span class="ev ev-not">Not established</span></div>\n', ''),
    # --- version identity. v0.2.1 is the AVAILABLE EVALUATION BUILD; 0.3.0 is the
    # unreleased development line and must never read as an available identity.
    ("version: 'advertised build' label returns", "audit.html",
     "<dt>Available evaluation build</dt>", "<dt>Advertised build</dt>"),
    # --- option 2: two public identities. v0.2.1 available by request; DSI v1
    # forthcoming, separately lineaged, unqualified, unavailable. 0.3.0 is off the site.
    ("version: the forthcoming v1 identity disappears", "audit.html",
     "<dt>Forthcoming</dt>", "<dt>Notes</dt>"),
    ("version: v1 stops being marked unqualified", "audit.html",
     "<strong>unqualified</strong>, not released", "ready, not released"),
    ("version: v1 stops being marked unavailable", "audit.html",
     "not released and not downloadable", "not yet widely promoted"),
    ("version: availability wording migrates to v1", "audit.html",
     "<strong>DSI v1</strong> &#183; separately lineaged",
     "<strong>DSI v1</strong> &#183; supplied by request, separately lineaged"),
    ("version: lineage blurred between 0.3.0 and v1", "audit.html",
     "It inherits the measurand of the evaluation build's predecessor",
     "It is the 0.3.0 line renamed, and inherits the measurand of the predecessor"),
    ("version: subordinate pages stop being scoped to v0.2.1", "audit.html",
     "describes <strong>v0.2.1</strong>", "describes the current product"),
    # the approved navigation sequence encodes the journey; order is asserted
    ("nav: primary sequence reordered", "index.html",
     '<a href="/applications">Applications</a>\n      <a href="/evidence">Evidence</a>',
     '<a href="/evidence">Evidence</a>\n      <a href="/applications">Applications</a>'),
    # --- surface classes. A v1 surface may not carry a v0.2.1 capability at all; a
    # v0.2.1 surface may, but only while it says so; /dsi must positively carry v1's four.
    ("surface: a v0.2.1 capability appears on a v1 surface", "dsi.html",
     "<h2>Four capabilities, and their boundaries.</h2>",
     "<h2>Four capabilities, regression comparison, and their boundaries.</h2>"),
    ("surface: fingerprints promoted onto /applications", "applications.html",
     "<h2>AI summary assurance.</h2>",
     "<h2>AI summary assurance, with a reproducible fingerprint.</h2>"),
    ("surface: a v0.2.1 page drops its scope marker", "deployment.html",
     "This page documents the <strong>v0.2.1</strong> evaluation build.",
     "This page documents the current build."),
    ("surface: /dsi loses a v1 capability", "dsi.html",
     "<span class=\"mono\">omitted_safety_critical</span>", "<span class=\"mono\">findings</span>"),
    ("surface: /dsi loses a governed status", "dsi.html",
     "negated, collapsed into other", "negated"),
    ("version: 'supplied by request' dropped", "audit.html",
     "&#183; supplied by request. This is the only build available",
     "&#183; the current product version. This is the only build available"),
    # a "v" prefix would imply a tagged release; the newest product tag is v0.2.1
    # stacked maturity badges must keep their row gap when they wrap
    ("badges: evidence tierstack removed", "evidence.html",
     '<span class="tierstack"><span class="tier tier-research">Research implementation</span>'
     '<span class="tier tier-research">Private evaluation access</span></span>',
     '<span class="tier tier-research">Research implementation</span> '
     '<span class="tier tier-research">Private evaluation access</span>'),
    # The programme history must stay reachable by its anchor. check_links.py strips the
    # fragment, so only the contract can catch a link pointing at a deleted anchor.
    ("anchor: programme-history id removed", "research.html",
     '<section class="reveal" id="programme-history">', '<section class="reveal">'),
    ("anchor: in-page jump link broken", "research.html",
     'href="#programme-history">Programme history', 'href="#programme-timeline">Programme history'),
    ("anchor: evidence link points at a dead anchor", "evidence.html",
     'href="/research#programme-history"', 'href="/research#history"'),
    ("anchor: homepage link points at a dead anchor", "index.html",
     'href="/research#programme-history"', 'href="/research#the-timeline"'),
    ("anchor: sticky-header offset removed", "styles.css",
     "main section[id] { scroll-margin-top:84px; }", ""),
    # Workers config: unknown routes must serve 404.html, not an empty body.
    ("wrangler: not_found_handling downgraded", "wrangler.jsonc",
     '"not_found_handling": "404-page"', '"not_found_handling": "none"'),
    ("wrangler: asset root changed", "wrangler.jsonc",
     '"directory": ".",', '"directory": "./dist",'),
    ("wrangler: a Worker entrypoint appears", "wrangler.jsonc",
     '  "assets": {', '  "main": "src/index.js",\n  "assets": {'),
    ("assetsignore: wrangler.jsonc wrongly published", ".assetsignore",
     "\nwrangler.jsonc\n", "\n"),
    # Routes stay dashboard-owned. Omitting workers_dev defaults it to TRUE, which would
    # publish a *.workers.dev endpoint; a top-level route/routes would override the
    # dashboard-managed custom domain on the next deploy.
    ("wrangler: workers_dev removed", "wrangler.jsonc",
     '  "workers_dev": false,\n', ''),
    ("wrangler: workers_dev set true", "wrangler.jsonc",
     '"workers_dev": false', '"workers_dev": true'),
    # Preview URLs are public when enabled, and are a separate control from workers_dev.
    ("wrangler: preview_urls removed", "wrangler.jsonc",
     '  "preview_urls": false,\n', ''),
    ("wrangler: preview_urls set true", "wrangler.jsonc",
     '"preview_urls": false', '"preview_urls": true'),
    ("wrangler: top-level route introduced", "wrangler.jsonc",
     '  "workers_dev": false,',
     '  "workers_dev": false,\n  "route": "decisionspaceintegrity.com/*",'),
    ("wrangler: top-level routes introduced", "wrangler.jsonc",
     '  "workers_dev": false,',
     '  "workers_dev": false,\n  "routes": ["decisionspaceintegrity.com/*"],'),
    # Repository internals must not re-enter the published asset set. The asset
    # directory is the repository root, so a dropped exclusion silently republishes
    # /docs/, /scripts/ or /.github/ on the production domain.
    ("assetsignore: docs/ exclusion dropped", ".assetsignore", "\ndocs/\n", "\n"),
    ("assetsignore: scripts/ exclusion dropped", ".assetsignore", "\nscripts/\n", "\n"),
    ("assetsignore: .github/ exclusion dropped", ".assetsignore", "\n.github/\n", "\n"),
    # _headers and _redirects are consumed by the platform and must stay uploaded
    ("assetsignore: _headers wrongly excluded", ".assetsignore",
     "\n.assetsignore\n", "\n.assetsignore\n_headers\n"),
    # --- release hardening: the analytics position and the published asset surface.
    # The beacon injection varied by request characteristics, so the page must keep the
    # whole verified history rather than a bare "no analytics" conclusion.
    ("privacy: prior beacon observation removed", "privacy.html",
     "Cloudflare was injecting a Web Analytics beacon script",
     "Cloudflare has never injected any script"),
    ("privacy: browser-equivalent verification removed", "privacy.html",
     "once with a default command-line agent and once with a "
     "<strong>browser-equivalent</strong> agent",
     "with a command-line agent"),
    ("privacy: hosting-processing distinction removed", "privacy.html",
     "ordinary request processing every web host performs",
     "nothing at all is processed"),
    ("privacy: CSP offered as evidence of absence", "privacy.html",
     "defence in depth", "conclusive proof"),
]


def run_check() -> int:
    r = subprocess.run([sys.executable, str(CHECK), str(ROOT)],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode


def _snapshot_tracked():
    """Bytes of every tracked file, plus the set of paths, taken before any mutation."""
    r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    snap = {}
    for rel in (x for x in r.stdout.split("\0") if x):
        f = ROOT / rel
        if f.is_file():
            snap[rel] = f.read_bytes()
    return snap


def _restore_snapshot(snap):
    """Force the tree back to the snapshot and PROVE it. Returns the still-dirty paths."""
    if snap is None:
        return ["(snapshot unavailable)"]
    for rel, data in snap.items():
        f = ROOT / rel
        try:
            if (not f.exists()) or f.read_bytes() != data:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(data)
        except OSError as exc:
            return [f"{rel}: {exc}"]
    # verification pass: a write that did not land must not be reported as cleanup
    stubborn = []
    for rel, data in snap.items():
        f = ROOT / rel
        try:
            if (not f.exists()) or f.read_bytes() != data:
                stubborn.append(rel)
        except OSError as exc:
            stubborn.append(f"{rel}: {exc}")
    return stubborn


def _digest(path: pathlib.Path):
    """Content digest, or None when the file is absent. Absence is a real state."""
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _worktree_state():
    """The whole working tree as git sees it. Compared before and after the run."""
    r = subprocess.run(["git", "status", "--porcelain"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout


def _git(*args) -> tuple[int, str]:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stderr or "").strip()


def main() -> int:
    if run_check() != 0:
        print("BASELINE FAIL: the contract does not pass before mutation; fix that first.")
        return 1
    start_rc, start_state = _worktree_state()
    if start_rc != 0:
        print("BASELINE FAIL: could not read the working tree state from git.")
        return 1
    baseline_bytes = _snapshot_tracked()
    if baseline_bytes is None:
        print("BASELINE FAIL: could not snapshot the tracked tree.")
        return 1
    print(f"baseline clean · {len(CASES) + 2} mutations\n")
    try:
        return _run(start_state, baseline_bytes)
    finally:
        # OUTERMOST cleanup. Per-case restoration is not enough on a filesystem where a
        # write can be reported as done without landing; this re-writes and re-verifies.
        stubborn = _restore_snapshot(baseline_bytes)
        if stubborn:
            print("\nCLEANUP FAILED - these files could not be restored:")
            for f_ in stubborn:
                print(f"  {f_}")


def _run(start_state, baseline_bytes) -> int:

    missed = []
    unrestored = []

    for name, fname, find, repl in CASES:
        f = ROOT / fname
        # Restore from the ORIGINAL BYTES. read_text performs universal-newline
        # translation, so writing the decoded string back would rewrite a CRLF working
        # copy as LF. Matching uses a normalised view so "\n" anchors work regardless.
        raw = f.read_bytes()
        before = hashlib.sha256(raw).hexdigest()
        original = raw.decode("utf-8").replace("\r\n", "\n")
        if find not in original:
            missed.append((name, "anchor absent - mutation could not be applied"))
            print(f"  ANCHOR?  {name}")
            continue
        rc = None
        try:
            f.write_text(original.replace(find, repl, 1), encoding="utf-8", newline="")
            rc = run_check()
        finally:
            # ALWAYS restore, even if run_check raised. Without this an exception left
            # the file mutated and the next run started from a corrupted tree.
            f.write_bytes(raw)
            if _digest(f) != before:
                unrestored.append(fname)
        if rc is None:
            missed.append((name, "the contract check raised before returning a result"))
            print(f"  ERROR    {name}")
        elif rc == 0:
            missed.append((name, "checker passed a broken contract"))
            print(f"  MISSED   {name}")
        else:
            print(f"  caught   {name}")

    # Tracked-tree case: staging ANY diagram must be rejected. Under the v1 product
    # boundary the target-architecture diagram is outside the published asset set
    # entirely. CI checks out only tracked files, so the real asset is absent there and
    # this case would be silently skipped - leaving the fail-closed tracked-tree rule
    # unproven on exactly the runs that gate the branch. Synthesise a stand-in.
    stray = "assets/diagrams/pluraxis-architecture.png"
    stray_path = ROOT / stray
    created_file = False
    created_dir = not stray_path.parent.exists()
    rc_t = None
    if not stray_path.exists():
        stray_path.parent.mkdir(parents=True, exist_ok=True)
        stray_path.write_bytes(bytes([137, 80, 78, 71, 13, 10, 26, 10]) + bytes(32))
        created_file = True
    add_rc, add_err = _git("add", "-f", stray)
    try:
        if add_rc != 0:
            missed.append(("tracked target-architecture diagram",
                           f"could not stage the probe, so the rule was never exercised: {add_err[:120]}"))
            print("  ERROR    tracked target-architecture diagram (git add failed)")
        else:
            rc_t = run_check()
    finally:
        # unstage unconditionally; an unchecked failure here is how index residue survived
        rm_rc, rm_err = _git("rm", "-q", "--cached", "--ignore-unmatch", stray)
        if rm_rc != 0:
            unrestored.append(f"{stray} (still staged: {rm_err[:100]})")
        if created_file:
            stray_path.unlink(missing_ok=True)
        if created_dir and stray_path.parent.exists():
            try:
                stray_path.parent.rmdir()
            except OSError:
                pass                      # not empty; leave it rather than delete content
    if rc_t is not None:
        if rc_t == 0:
            missed.append(("tracked target-architecture diagram", "checker passed a broken contract"))
            print("  MISSED   tracked target-architecture diagram")
        else:
            print("  caught   tracked target-architecture diagram"
                  + (" (synthesised stand-in)" if created_file else ""))

    # The retired page must not return.
    retired = ROOT / "pluraxis.html"
    if retired.exists():
        missed.append(("retired page present", "pluraxis.html exists in the working tree"))
        print("  ERROR    pluraxis.html is present before the case runs")
    else:
        rc_r = None
        try:
            retired.write_text("<!doctype html><title>x</title><p>x</p>\n", encoding="utf-8")
            rc_r = run_check()
        finally:
            retired.unlink(missing_ok=True)
            if retired.exists():
                unrestored.append("pluraxis.html (probe not removed)")
        if rc_r is None:
            missed.append(("retired page restored", "the contract check raised"))
            print("  ERROR    retired /pluraxis page restored")
        elif rc_r == 0:
            missed.append(("retired page restored", "checker passed a broken contract"))
            print("  MISSED   retired /pluraxis page restored")
        else:
            print("  caught   retired /pluraxis page restored")

    print()
    if unrestored:
        print(f"MUTATION SUITE: FAIL — {len(unrestored)} file(s) not restored byte-exactly")
        for u in unrestored:
            print(f"  {u}")
        return 1

    # The claim is "every file restored", so prove it against git rather than asserting it.
    stubborn = _restore_snapshot(baseline_bytes)
    if stubborn:
        print(f"MUTATION SUITE: FAIL — {len(stubborn)} file(s) could not be restored")
        for f_ in stubborn:
            print(f"  {f_}")
        return 1
    end_rc, end_state = _worktree_state()
    if end_rc != 0 or end_state != start_state:
        print("MUTATION SUITE: FAIL — the working tree did not come back to its starting state")
        for line in sorted(set(end_state.splitlines()) ^ set(start_state.splitlines())):
            print(f"  {line}")
        return 1

    if missed:
        print(f"MUTATION SUITE: FAIL — {len(missed)} not caught")
        for n, why in missed:
            print(f"  {n}: {why}")
        return 1
    if run_check() != 0:
        print("MUTATION SUITE: FAIL — the contract does not pass after restoration")
        return 1
    print("MUTATION SUITE: PASS — every mutation was rejected, every file restored "
          "byte-exactly, and the working tree is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
