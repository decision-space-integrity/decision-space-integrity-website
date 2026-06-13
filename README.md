# decisionspaceintegrity.com

Website for **DSI** — a local, stateless decision-space assurance sidecar for advisory AI.

A static site: plain HTML + one CSS file. **No frameworks, no JavaScript, no build step.**

## Pages

```
index.html      Home
product.html    Product
research.html   Research
contact.html    Contact
styles.css      styling (one file)
_headers        Cloudflare Pages edge headers (security)
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
