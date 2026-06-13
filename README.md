# decisionspaceintegrity.com

Website for **DSI** — a local, stateless decision-space assurance sidecar for advisory AI.

A static site: plain HTML + one CSS file. **No frameworks, no JavaScript, no build step.**

## Pages

```
index.html      Home
product.html    Product
research.html   Research
paper.html      Preprint hub (Decision-Space Collapse)
applications.html  Applications (positioning)
contact.html    Contact
articles/       Articles index (articles/index.html) + article pages
styles.css      styling (one file)
robots.txt      crawl directives + sitemap pointer
sitemap.xml     canonical URL list for search engines
_headers        Cloudflare Pages edge headers (security)
assets/papers/   preprint PDF
assets/og/       social preview image (Open Graph / Twitter Card)
assets/icons/    favicon + Apple touch icon
assets/articles/ article cover images
```

## Preview locally

```bash
python -m http.server 8080   # then open http://127.0.0.1:8080/
```

(Opening `index.html` directly also works.)

## Deploy — Cloudflare Pages

Connect this repository in Cloudflare Pages and set:

- **Framework preset:** None
- **Build command:** *(leave empty)*
- **Build output directory:** `/` (repository root)

Cloudflare serves `index.html` at the root and applies `_headers` at the edge. Internal links use
relative `.html` paths, which Cloudflare also serves as clean URLs (e.g. `/product`).

The site is fully responsive and renders with JavaScript disabled.

## Search indexing

The site ships with the static files search engines expect:

- **`robots.txt`** — allows all crawlers and points to the sitemap.
- **`sitemap.xml`** — lists the eight canonical URLs (`/`, `/product.html`, `/research.html`,
  `/paper.html`, `/applications.html`, `/articles`, `/articles/ai-brilliance-human-capability`,
  `/contact.html`), all on `https://decisionspaceintegrity.com`.
- **`paper.html`** — a dedicated hub for the *Decision-Space Collapse in Advisory Language Models*
  preprint (PDF, public replication repository, and OSF DOI), linked from `research.html`.
- **Canonical URLs** — every page declares `<link rel="canonical">` plus a unique title and meta
  description, so search engines index the `https://decisionspaceintegrity.com` form.

`paper.html` also embeds a JSON-LD `ScholarlyArticle` block (non-executable structured data, read by
crawlers). The `_headers` Content-Security-Policy keeps `script-src 'none'` — JSON-LD is data, not a
script, so no executable JavaScript is introduced and the policy is unchanged.

### Post-deployment checklist (Google Search Console)

Once the domain is live on Cloudflare Pages, in
[Google Search Console](https://search.google.com/search-console):

1. **Verify domain ownership** — add `decisionspaceintegrity.com` as a *Domain* property and
   complete the DNS TXT verification (Cloudflare dashboard → DNS → add the TXT record Google gives you).
2. **Submit the sitemap** — Search Console → *Sitemaps* → enter `sitemap.xml` → Submit
   (full URL: `https://decisionspaceintegrity.com/sitemap.xml`).
3. **Request indexing** for each canonical URL via the *URL Inspection* tool → *Request indexing*:
   - `https://decisionspaceintegrity.com/`
   - `https://decisionspaceintegrity.com/product.html`
   - `https://decisionspaceintegrity.com/research.html`
   - `https://decisionspaceintegrity.com/paper.html`
   - `https://decisionspaceintegrity.com/applications.html`
   - `https://decisionspaceintegrity.com/articles`
   - `https://decisionspaceintegrity.com/articles/ai-brilliance-human-capability`
   - `https://decisionspaceintegrity.com/contact.html`
4. **Monitor** whether queries such as *Decision-Space Integrity*, *Decision-Space Collapse*, and
   *Andrew J Cousins DSI* begin surfacing the site over the following weeks.

Sitemap submission and indexing requests are manual dashboard actions — they require the Google
account that owns the verified property and cannot be automated from this repo.

### Cloudflare managed robots.txt

Cloudflare has a zone-level **AI Crawl Control / "Managed robots.txt"** feature that, when enabled,
**overlays** the `robots.txt` in this repo: it prepends a Cloudflare-managed block (content signals
plus `Disallow: /` for AI crawlers such as `GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot`,
`Bytespider`) and appends the repo file below it. When that happens the served `robots.txt` differs
from the committed one — search-engine indexing (Googlebot/Bingbot) and the `Sitemap:` line still
work, but the live file contains two `User-agent: *` groups.

This setting is **disabled** for this zone, so the live `robots.txt` is served verbatim from this
repo (a single `User-agent: *` group). To change it: Cloudflare dashboard → the zone →
**AI Crawl Control / Manage robots.txt**. If it is re-enabled in future, expect the overlay described
above — that is a Cloudflare edge behavior, not a change to this repo. If the goal is to keep AI
crawlers out, prefer enabling the managed block over editing this file, since the managed block is
maintained as crawler names change.

## Rich previews

When the site is shared in iMessage, Slack, LinkedIn, WhatsApp, or X, the link unfurls into a card
built from the page metadata and a social image:

- **`assets/og/dsi-og-image.png`** (1200×630) is the Open Graph and Twitter Card image. Every page
  references it via `og:image` and `twitter:image`.
- Every page sets `twitter:card = summary_large_image` plus per-page `twitter:title` / `twitter:description`
  mirroring its Open Graph tags.
- Favicons (`assets/icons/favicon.svg` + 32/16 PNG fallbacks) and an `apple-touch-icon.png` (180×180)
  are linked from every page. All icon and OG assets are **same-origin**, so the `_headers` CSP
  (`img-src 'self' data:`) already allows them — no CSP change and no JavaScript were needed.

The image and icons are generated from scripts in `.fonttmp/` (not committed) using the site's own
fonts and palette; re-run them if the brand assets change.

### Testing previews after deploy

Preview caches are aggressive — a card can take hours or days to refresh, and a stale iMessage card
is often Apple-side caching rather than a site problem. After deploying:

- Confirm the assets serve: `…/assets/og/dsi-og-image.png`, `…/assets/icons/favicon.svg`,
  `…/assets/icons/apple-touch-icon.png` (each should return `200` with an image content-type).
- Validate the unfurl with the [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/),
  [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/), and an X Card validator.
- For iMessage, send the link to a **new** conversation/thread; to force a cache-busted re-fetch you
  can temporarily test `https://decisionspaceintegrity.com/?v=preview1` — do not use query-string
  variants as official URLs, they are only a cache test.
