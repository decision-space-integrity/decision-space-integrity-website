# WEB-META-1 — homepage metadata identity: pre-registration and decision record

Date: 22 August 2026
Base: `origin/main` @ `b6408499fbce7f254080cb96c025f5a7b3580b61`, tree `62cf1c80…`
Scope: **browser/social metadata on the homepage only.** This is not authority to change the product
proposition, research claims, article prose, release status or evidence.

## Why

The homepage's browser and social titles still describe an older, narrower DSI:

> Decision-Space Integrity — Audit Expected-Path Visibility in AI Outputs

The public research story now covers two layers: measuring preservation/omission against governed
expectations, **and** governing changes to the measurement instrument and its authorities. The
owner-approved conceptual line is:

> **Measuring What's Preserved. Governing What Changes.**

"What's preserved" is deliberate. It is **not** "what matters": DSI does not independently establish
that a governed expected map contains everything that matters.

## Frozen copy (pre-registered before implementation)

**Browser title, `og:title`, `twitter:title`** — one string, no divergence:

```
Decision-Space Integrity — Measuring What's Preserved. Governing What Changes.
```

Measured length **78 characters** (incumbent: 71). Both exceed the ~60-character SERP display
guideline, so this is a 7-character increase on a title the site already runs; it was judged not
*materially* unsuitable and the owner wording was implemented verbatim. Search engines may clip the
tail in results listings; the browser tab, social cards and the `<title>` element itself are
unaffected. **Smallest alternative offered for owner ruling, not implemented:**
`DSI — Measuring What's Preserved. Governing What Changes.` (57 characters).

**Description, `og:description`, `twitter:description`** — one string:

```
A self-hosted assurance system that measures which governed expected elements an AI output
preserved, with evidence of what changed when the instrument changes.
```

Measured length **160 characters** (incumbent: 137), within the ~160 meta-description guideline.

Boundaries this wording holds: self-hosted · assurance/measurement · governed expected elements ·
AI outputs · instrument change · evidence. It asserts **no** claim that DSI determines what
objectively matters, **no** independent validation, **no** regulatory certification, and **no**
universal semantic measurement.

## What is deliberately NOT changed

- **The visible hero — "See what your AI answer left out."** Retained. It is the concrete product
  proposition and complements the broader metadata rather than competing with it.
- **`og:image:alt` / `twitter:image:alt` on every page.** The shared social card
  (`assets/og/dsi-og-image.png`) *literally renders the words* "Audit expected-path visibility in AI
  model outputs". The alt text is therefore an **accurate description of the image**, not stale site
  identity. Rewriting it would make the alt text wrong and would be an accessibility regression.
- **The phrase "expected-path visibility" generally.** It remains a valid description of part of
  what DSI does and appears throughout the site as technical explanation.
- Research story, article prose, paper, privacy content, release manifest, versions, classifier
  identity, audit IDs, DOI/citation material and replication links.

## Known residual inconsistency (flagged, not actioned)

The OG image still carries the older positioning in its rendered text. After this pack the social
card and the social *title* say different things. Regenerating the image is an asset/design change
outside this pack's scope and would alter a file every page references. **Owner decision required**
if the card should be re-cut to match the new line.

## Governance check

`scripts/check_release_provenance.py` pins **audit ids, classifier identity and version chips only**
— it does not pin titles or descriptions. Changing this metadata therefore requires no change to any
governed release or evidence identity, and `release_manifest.json` stays byte-identical.
