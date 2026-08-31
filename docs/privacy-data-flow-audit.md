# Privacy data-flow audit — decision-space-integrity-website

Date: 22 August 2026
Scope: every tracked HTML/JS/CSS/configuration file in this repository at the commit that
carries this document. This is a repository-backed audit: it records what the committed
site can be shown to do. Behaviour that only exists at the deployment layer (Cloudflare
account settings, edge logging configuration) is not visible in this repository and is
recorded as UNKNOWN rather than invented.

Method: pattern scan of all HTML/JS/CSS for cookies, `document.cookie`, `localStorage`,
`sessionStorage`, IndexedDB, `sendBeacon`, analytics/advertising identifiers, pixels,
`fetch(`, `XMLHttpRequest`, `WebSocket`, `<iframe`, `<form`, external `src`/`href`
resources, `mailto:` links; manual read of `_headers`, `assets/example-audit.js`,
`README.md`, `robots.txt`, `.github/workflows/validate.yml`.

Note on scan hygiene: a naive scan for the analytics vendor "Plausible" matches the
ordinary English word "plausible", which appears in four content sentences. Those are
false positives, verified by reading each line. No analytics reference exists.

## Findings

### F1 — Google Fonts stylesheets
- Component: `<link href="https://fonts.googleapis.com/css2?...">` on every HTML page
- Data potentially involved: visitor IP address, user agent, requested URL (sent by the
  browser to Google when the stylesheet is fetched)
- Purpose: typography (Fraunces, Hanken Grotesk, IBM Plex Mono)
- Recipient / third party: Google LLC
- Browser storage / cookie: none set by this markup; Google-side logging is outside the
  repository — UNKNOWN
- Essential / non-essential: non-essential resource (presentation); not a cookie or
  storage mechanism, so no consent banner is triggered by it under PECR cookie rules,
  but it is a third-party disclosure the privacy notice must state
- Repo evidence: `<link rel="preconnect" href="https://fonts.googleapis.com">` and the
  css2 stylesheet link in the head of every page; CSP `style-src` allowlists
  `https://fonts.googleapis.com` in `_headers`
- Proposed disclosure/action: disclose in privacy.html (done)

### F2 — Google Fonts font files
- Component: font files loaded from `https://fonts.gstatic.com` by the F1 stylesheet
- Data potentially involved: visitor IP address, user agent
- Purpose: typography
- Recipient / third party: Google LLC
- Browser storage / cookie: none in repo; UNKNOWN Google-side
- Essential / non-essential: non-essential (presentation)
- Repo evidence: `preconnect` to `fonts.gstatic.com`; CSP `font-src` allowlists it
- Proposed disclosure/action: disclose in privacy.html (done)

### F3 — Email enquiry links
- Component: `mailto:enquire@decisionspaceintegrity.com` links (contact.html and others)
- Data potentially involved: sender's email address, name if given, and whatever the
  sender writes; sent through the visitor's own mail client, not through the site
- Purpose: receiving evaluation, pilot, research and general enquiries
- Recipient / third party: the site operator's mailbox. The mail hosting provider is not
  identifiable from this repository — UNKNOWN
- Browser storage / cookie: none
- Essential / non-essential: essential to the stated purpose of the page
- Repo evidence: `mailto:` hrefs in contact.html, index.html and other pages
- Proposed disclosure/action: disclose correspondence processing, lawful basis and
  criteria-based retention in privacy.html (done)

### F4 — Hosting and security request processing (Cloudflare Pages)
- Component: static hosting on Cloudflare Pages; `_headers` applies edge security headers
- Data potentially involved: IP address, user agent and request metadata that any web
  request necessarily transmits; processed to deliver pages and protect the service
- Purpose: hosting, delivery, security
- Recipient / third party: Cloudflare, Inc.
- Browser storage / cookie: none configured in this repository. Whether the deployment
  layer sets any Cloudflare cookie (e.g. bot-mitigation) is not visible here — UNKNOWN
- Essential / non-essential: essential (the site cannot be served without processing
  the request)
- Repo evidence: `_headers` ("Cloudflare Pages headers. Applied at the edge on deploy");
  README.md "Deploy — Cloudflare Pages"
- Proposed disclosure/action: disclose hosting processing in privacy.html without
  claiming knowledge of deployment-only logging specifics (done)

### F5 — First-party script on the example-audit page only
- Component: `assets/example-audit.js` (53 lines), loaded only by `example-audit.html`
- Data potentially involved: none — it animates on-page reveal and count-up via
  IntersectionObserver; no network call, no cookie, no storage, no input handling
- Purpose: presentation
- Recipient / third party: none
- Browser storage / cookie: none
- Essential / non-essential: non-essential presentation; collects nothing
- Repo evidence: the file itself; CSP gives every other path `script-src 'none'` and
  example-audit only `script-src 'self'`
- Proposed disclosure/action: none needed beyond the notice's general statement

### F6 — Cookies and browser storage: none in the repository
- Component: none. Zero occurrences of `document.cookie`, `localStorage`,
  `sessionStorage`, IndexedDB or `sendBeacon` in any tracked file
- Repo evidence: repository-wide pattern scan (this audit)
- Proposed disclosure/action: privacy.html states the site's own pages set no cookies
  and use no browser storage, with the deployment-layer caveat from F4. No cookie
  banner is required on this evidence (done — no banner added)

### F7 — Analytics, advertising, pixels: none
- Component: none. No analytics, tag manager, advertising or pixel reference exists
- Repo evidence: repository-wide pattern scan (this audit)
- Proposed disclosure/action: state plainly in privacy.html (done)

### F8 — Forms, iframes, XHR/fetch/WebSocket: none
- Component: none in any tracked file; CSP additionally sets `frame-ancestors 'none'`
  and `form-action 'self'`, and `script-src 'none'` on all but one path
- Repo evidence: repository-wide pattern scan; `_headers`
- Proposed disclosure/action: reflected in privacy.html's "what this site does not do"

### F9 — Outbound hyperlinks to external sites
- Component: navigation links to github.com, doi.org, arxiv.org, osf.io
- Data potentially involved: nothing until the visitor chooses to follow the link;
  the destination then processes the visit under its own terms
- Recipient / third party: the linked site, only on click
- Browser storage / cookie: none set by this site
- Essential / non-essential: content links
- Repo evidence: hrefs in research.html, paper.html, reading.html, contact.html
- Proposed disclosure/action: one-line note in privacy.html (done)

### F10 — Serverless functions / workers
- Component: none on the deployed branch. No functions directory, no worker script, no
  API endpoint exists on `main`. A remote branch named `cloudflare/workers-autoconfig`
  exists but is not part of `main`; whether anything from it is deployed is not
  determinable from this repository — UNKNOWN, assumed not deployed
- Repo evidence: tracked file inventory of `main`
- Proposed disclosure/action: none; re-audit if a worker is ever merged

### F11 — CI (GitHub Actions)
- Component: `.github/workflows/validate.yml` — runs claim/link/provenance/HTML checks
  on push and pull request
- Data potentially involved: repository content and commit metadata, processed by
  GitHub, Inc. as the repository host; no site-visitor data is involved
- Recipient / third party: GitHub, Inc. (development infrastructure, not the website)
- Proposed disclosure/action: none — not visitor-facing

## Conclusion

The committed site is a static, script-light property that sets no cookies, uses no
browser storage, runs no analytics, and hosts no forms. The visitor-facing processing
that exists is: (1) ordinary hosting/security request processing by Cloudflare;
(2) font requests to Google Fonts; (3) email correspondence the visitor initiates.
privacy.html discloses exactly these, labels deployment-only behaviour as such, and
adds no cookie banner because the repository evidences no non-essential cookie or
storage behaviour that would require one.

---

## Addendum — 22 August 2026: edge-injected analytics (DSI-WEBSITE-1A finding)

The audit above is **repository-backed** and remains accurate for the repository. Inspection of the
**deployed** site during DSI-WEBSITE-1A found behaviour the repository cannot show:

**F12 — Cloudflare Web Analytics beacon, injected at the edge**
- Component: a `<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js/…">`
  tag carrying a `data-cf-beacon` site token, appended after `</footer>` on **every page sampled**,
  including `privacy.html` itself.
- Repo evidence: **absent from source** — the tag appears only in the served response. Live bytes are
  otherwise identical to the committed file.
- Recipient: Cloudflare, Inc.
- Essential/non-essential: **non-essential analytics**.
- Mitigation in place: `_headers` sets `script-src 'none'` on `/*`, so a conforming browser should
  refuse to execute it. The tag and token are still served.
- Consequence: finding F7 ("Analytics, advertising, pixels: none") is true of the repository and
  **not** true of the deployed site.

**Owner action required before production release:** disable Cloudflare Web Analytics / Browser
Insights for this project, then re-verify that the injected script is absent. This is a hosting
dashboard change; no pack in this sequence has altered Cloudflare state.
