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
    ("pluraxis: watermark removed", "pluraxis.html",
     "TARGET ARCHITECTURE &#183; UNDER ACTIVE DEVELOPMENT", "PRODUCTION READY"),
    ("pluraxis: efficacy badge removed", "pluraxis.html",
     "Efficacy: not established", "Efficacy: established"),
    ("pluraxis: decision-quality limitation removed", "pluraxis.html",
     "effect it may have on decision quality, are <strong>not established</strong>",
     "effect it may have on decision quality, are <strong>well proven</strong>"),
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
    ("pluraxis: diagram caption limitation removed", "pluraxis.html",
     "Conceptual target architecture. Individual components exist at different maturity levels; "
     "the integrated system and its effect on decision quality are not established.",
     "Conceptual target architecture, fully validated end to end."),
]


def run_check() -> int:
    r = subprocess.run([sys.executable, str(CHECK), str(ROOT)],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode


def main() -> int:
    if run_check() != 0:
        print("BASELINE FAIL: the contract does not pass before mutation; fix that first.")
        return 1
    print(f"baseline clean · {len(CASES) + 1} mutations\n")

    missed = []
    for name, fname, find, repl in CASES:
        f = ROOT / fname
        original = f.read_text(encoding="utf-8")
        if find not in original:
            missed.append((name, "anchor absent - mutation could not be applied"))
            print(f"  ANCHOR?  {name}")
            continue
        f.write_text(original.replace(find, repl, 1), encoding="utf-8", newline="")
        rc = run_check()
        f.write_text(original, encoding="utf-8", newline="")
        if rc == 0:
            missed.append((name, "checker passed a broken contract"))
            print(f"  MISSED   {name}")
        else:
            print(f"  caught   {name}")

    # Tracked-tree case: staging the unrevised source must be rejected.
    # CI checks out only TRACKED files, so the real build input is absent there and
    # this case would be silently skipped - leaving the fail-closed tracked-tree rule
    # unproven on exactly the runs that gate the branch. Synthesise a stand-in when
    # the real file is absent so the case is exercised everywhere, then remove it.
    stray = "assets/diagrams/Pluraxis Architecture.PNG"
    stray_path = ROOT / stray
    created = False
    if not stray_path.exists():
        stray_path.parent.mkdir(parents=True, exist_ok=True)
        stray_path.write_bytes(bytes([137, 80, 78, 71, 13, 10, 26, 10]) + bytes(32))
        created = True
    try:
        subprocess.run(["git", "add", "-f", stray], cwd=ROOT, capture_output=True)
        rc = run_check()
    finally:
        subprocess.run(["git", "rm", "-q", "--cached", stray], cwd=ROOT, capture_output=True)
        if created:
            stray_path.unlink(missing_ok=True)
    if rc == 0:
        missed.append(("tracked unrevised diagram", "checker passed a broken contract"))
        print("  MISSED   tracked unrevised diagram")
    else:
        print("  caught   tracked unrevised diagram"
              + (" (synthesised stand-in)" if created else ""))

    print()
    if missed:
        print(f"MUTATION SUITE: FAIL — {len(missed)} not caught")
        for n, why in missed:
            print(f"  {n}: {why}")
        return 1
    if run_check() != 0:
        print("MUTATION SUITE: FAIL — files were not restored cleanly")
        return 1
    print("MUTATION SUITE: PASS — every mutation was rejected and every file restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
