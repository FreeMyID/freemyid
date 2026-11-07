# Free My ID website: design system and page inventory

Owner: web-developer. Live preview: `.venv/bin/python -m http.server -d site 8000`, then open http://localhost:8000/
(the 404 page uses absolute `/freemyid/` links, so it only looks right on Pages).

## Platform and build

- GitHub Pages, static files only. No server, forms, analytics, cookies, third-party requests or JavaScript.
- Source: `site_src/`. Output: `site/` (committed, published as-is by `.github/workflows/pages.yml`).
- `tools/build_site.py` (stdlib + jinja2 + PyYAML) renders templates and data into `site/`, then runs
  `tools/site_check.py`. `--check` (used in CI) fails if committed `site/` differs from a fresh build,
  a token contrast pair falls below its minimum, or site_check finds a problem.
- Deterministic: sorted inputs, no build timestamps. The only dates come from data (`registry.sample.yaml`
  `updated`, per-broker `last_verified`, `data/release.yaml`).
- Broker data: **only** `brokers/registry.sample.yaml` (CC BY-NC 4.0, attributed on every guide). site_check
  fails if a value that exists only in the private `brokers/registry.yaml` appears in the output.

```
site_src/
  site.yaml        base_url, base_path, repo/download URLs, old-URL redirects
  tokens.yaml      colors [light, dark], contrast pairs, space/type/radius scales, fonts, shadows
  pages.yaml       page manifest: out folder, template, label, title, description, jsonld, noindex
  css/*.css        concatenated in name order into site/style.css; tokens layer generated after 00-layers.css
  data/faq.yaml    FAQ (Questions page, home subset with home: true, FAQPage JSON-LD)
  data/release.yaml version/date/size/sha256 for the download page (orchestrator fills per release)
  data/icons.yaml  hand-drawn 24px line icons
  data/guide_intros.yaml  first sentence for "other"-category guides
  templates/       base.html, redirect.html, partials/, pages/
  static/          copied verbatim (favicons, og.png = brand/social/og-default.png, assets/screenshots/*.webp)
  og.html          old interim source for og.png (superseded by the brand image; kept for reference)
```

Add a page: write `templates/pages/<name>.html` (extend `base.html`, fill `{% block main %}`, start with
`{% include "partials/crumbs.html" %}` and one `<h1>`), add a `pages.yaml` entry, run the build. Use
`{{ url('path/') }}` for every internal link (relative, so it works under `/freemyid/` and on a custom
domain) and `{{ icon('name') }}` for icons. Nav and footer links appear only for pages in the manifest.

Domain switch (when freemyid.org exists and the orchestrator says so): change `base_url` and `base_path`
in `site.yaml`, add `site_src/static/CNAME`, rebuild.

## Security and privacy (in `<meta>`, since Pages can't set headers)

CSP: `default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self'; font-src 'self';
connect-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'`, plus
`<meta name="referrer" content="no-referrer">`. Consequences: no `style=""` attributes and no `data:` URIs
(site_check enforces both); JSON-LD is fine (not executed).
Not possible via meta: `frame-ancestors` (clickjacking protection), `report-uri`, HSTS. Pages serves HTTPS.
External links (broker removal pages, GitHub, a Facebook share link) are plain links: nothing loads until clicked.

## Design system v2 (redesign 2026-11-07; decisions D1-D10 and the component contract: `docs/WEBSITE_REDESIGN.md`)

Direction (D6): a clean product look. One system sans-serif stack, 20px base, navy family with red only as a
small accent, one thin flag bar as the only flag motif (no star rows, stripes or hero stars), calm
white/off-white bands, soft-elevation cards, real product screenshots with made-up data. No web fonts, no JS.

### Tokens (source of truth: `site_src/tokens.yaml`; swatches at `/styleguide/`)

| Token | Light | Dark | Use |
|---|---|---|---|
| bg / bg-alt | #ffffff / #f4f6f9 | #0d131d / #121a26 | page / calm alternate bands |
| card | #ffffff | #172131 | raised cards, trust bar, FAQ items, price card |
| surface / surface-strong | #eef2f7 / #e1e8f2 | #1a2434 / #25334b | quiet panels, table header / icon tiles, chips |
| text / muted | #151b26 / #414b5c | #eef1f6 / #c0c8d5 | body / secondary, both >= 7:1 on every background |
| heading | #14264a | #dde7fb | headings |
| brand / brand-ink / brand-soft | #1b3366 / #fff / #e6edf8 | #a9c3f3 / #0d131d / #1d2b45 | primary buttons, step numbers / text on brand / icon tiles, info callout |
| band-brand / band-brand-ink | #1b2f5b / #fff | #162543 / #eef1f6 | the one deep navy band (final CTA) |
| accent | #a3202e | #f5a3ab | flag red, small accents only. Never alarm UI |
| link | #17488f | #a8caff | >= 7:1 on every background |
| ok / warn | #1c6639 / #7a4f00 | #8fd6a6 / #f0c674 | "yes" cells, ticks, does-column / "partial" cells |
| line / line-strong | #dbe1ea / #6b778c | #2a374d / #8794ab | hairlines / borders that must meet 3:1 |
| focus / focus-inner | #f2b705 / #151b26 | #f2b705 / #eef1f6 | 3px gold outline + contrasting inner ring |
| footer-bg / footer-text | #0f1c38 / #e8edf6 | #080c14 / #dfe5ee | footer |

All 39 contrast pairs in `tokens.yaml` `pairs` (body 7:1, other text 4.5:1, borders 3:1) are checked on every
build in both themes.

- Type: `html { font-size: 125% }` = 20px, follows browser zoom. Steps -1 (0.85rem) to 5
  (`clamp(2.1rem, 1.5rem + 3vw, 3.4rem)`, the hero h1). One family for headings and body (system-ui, Segoe UI,
  Roboto, ...).
- Space: 3xs .25rem, 2xs .5, xs .75, s 1, m 1.5, l/xl/2xl/3xl fluid (`clamp`). Bands use `xl` (R6 tightened
  them from `2xl`; home went from ~12,000px to ~10,600px tall at 1280px). Section-head gap below: `l`.
- Radius sm 6 / md 10 / lg 16 / xl 24px / pill. Shadows 1-3 (soft, navy-tinted).
- Layout: `--wrap` 62rem, `--measure` 36rem, `--tap` 3rem (60px) minimum control height, fluid `--gutter`.
- Theme: `light-dark()` + `color-scheme`; `data-theme="light|dark"` on `<html>` overrides; `@supports not`
  fallback with the same values.

## CSS architecture

`@layer reset, tokens, base, layout, components, pages, utilities;` then print. Files in `site_src/css/`
are concatenated in name order: 10 reset, 30 base, 40 layout (wrap, bands, section-head), 50 base
components (kicker, buttons), 52 header/footer, 54 contract sections, 56 widgets (SmartScreen drawing,
download card, mockup), 60 pages, 80 utilities, 90 print. `51-legacy.css` (v1 classes) was deleted in R6
after every page moved to the contract. Logical properties, `:has()`, `:focus-visible`, `text-wrap`,
View Transitions under `prefers-reduced-motion: no-preference`. No native nesting (iOS 16).

## Components

The class names are a contract (table in `docs/WEBSITE_REDESIGN.md`); live examples at `/styleguide/`.
Summary: `section.band` (`--alt`, `--brand`, `--tight`) > `.wrap(--narrow)`; `.section-head` (kicker, h2,
lead; centered, left-aligned inside `.wrap--narrow`); `.hero` (text + `figure.hero__media`, 0.9fr/1.1fr
from 900px); `.btn--primary/--secondary/--ghost` + `--large/--small`; `ul.trustbar` (4 items, icon above
text from 60em, list below 30em); `ol.steps` > `li.step` > `span.step__num[aria-hidden]` (3 across) and
`ol.steps.steps--list` (vertical instructions, any content per step); `ul.cards(--3/--4)`; `figure.proof`
(max 40rem wide, image cropped to the top 30rem with a fade so it reads as a picture; width/height attributes
kept for CLS); `.table-scroll[tabindex=0][role=region][aria-labelledby]` > `table.compare`;
`aside.callout--info/--note`; `.dodont`; `.price-card` + `ul.checklist`; `.faq` > `details.faq__item`;
`section.cta-final`; header (`header.site-header`, `nav.site-nav`, no-JS `details.menu`, D5 CTA kept visible
on phones) and footer (four columns + legal row).
Other partials: `cta-download.html` (D5: one place decides "Download" vs "coming soon"), `crumbs.html`,
`smartscreen.html` (drawing, `ss_step` 1|2), `mockup.html` (fallback drawing), `brand-mark.svg`.
Callout mapping from v1: gold -> `--note`, fact -> `--info`, myth -> `--note` (with the x icon and "Myth:" label).

## Page inventory

| URL | Status | Notes |
|---|---|---|
| `/` | built (v2) | D10 order: hero + dashboard screenshot, trust bar, proof (report screenshot), 3 steps, what it removes, the post, comparison (R5 paid column), safety + does/doesn't, $0 card, helpers, 8 FAQs, final CTA |
| `/how-it-works/` | built | four steps (`steps--list`), three ways (cards), safety notes |
| `/guides/` + `/guides/<name>/` | built | 29 guides from the public sample registry |
| `/safety/` | built (v2, D2) | "Is it safe?": local + encrypted, never asks, open source, updates, verify, uninstall, limits, this website |
| `/families/` | built | helper guide, setup steps, fridge-card PDF |
| `/faq/` | built | myth vs. fact + all questions, FAQPage JSON-LD |
| `/download/` | built | "opens soon" state until `data/release.yaml` has a version; SmartScreen steps with drawings |
| `/i-do-not-consent/` | built | explainer, plain Facebook share link |
| `/styleguide/` | built, noindex | living style guide (every contract component) |
| `/404.html` | built, noindex | absolute links (served at any depth) |
| Redirect stubs (noindex, meta refresh + canonical) | built | `download.html`, `faq.html`, `how-it-works.html` -> their folders; `privacy.html` **and** `privacy/` -> `safety/` (both from `site.yaml` `redirects`; keys are output file paths, values page ids) |
| Who's buying your data? | not built | citations not verified yet |
| /free/, /compare/, /open-source/ | not built (D3) | live on home and /safety/ this round |
| Pricing | do not build | paid tier not announced |

Images: `site_src/static/assets/screenshots/*.webp` (copied from `brand/screenshots/`, alt text from
`brand/README.md`, captioned "Example with made-up data"). Home is the heaviest page: about 280 KB total
(7 KB HTML + 10 KB CSS gzip + 263 KB of WebP; the report image is lazy-loaded).

## Checks (`tools/site_check.py`)

Per page: `lang`, CSP + referrer meta, title <= 60, description <= 155, canonical under base_url, og:image
exists, exactly one h1, no `style=""`, no inline handlers, no forms/iframes, no non-JSON-LD inline script,
no cross-origin or `data:` assets, every internal link and #anchor resolves, every `<img>` has alt/width/height.
Site: sitemap lists exactly the indexable pages, robots.txt has a Sitemap line, CSS has no external `url()`
or `@import`, no full-registry-only values, no mention of `registry.yaml`.
