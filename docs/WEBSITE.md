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
  static/          copied verbatim (favicon.svg, og.png)
  og.html          source for static/og.png (regenerate command inside)
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

## Design tokens (source of truth: `site_src/tokens.yaml`; swatches at `/styleguide/`)

| Token | Light | Dark | Use |
|---|---|---|---|
| bg / bg-alt | #ffffff / #f7f5ef | #0f1520 / #141c29 | page / warm "parchment" bands |
| surface / surface-strong | #f2f4f8 / #e4e9f1 | #1a2331 / #243046 | panels, card icon tiles, chips |
| text / muted | #14181f / #3d4654 | #f2f4f8 / #c3cad6 | body (17.8:1) / secondary (>= 8.6:1) |
| heading = brand | #1b2f5b | #c4d5f7 | headings, primary buttons |
| brand-ink | #ffffff | #0f1520 | text on brand (13:1) |
| accent | #a3202e | #f5a3ab | flag red: kickers, myth borders, stars. Never alarm UI |
| link | #17488f | #a8caff | >= 7:1 on every background |
| ok / warn | #1e6b3c / #7a4f00 | #8fd6a6 / #f0c674 | mockup status chips, fact callouts |
| line / line-strong | #c5ccd8 / #6b778c | #36435a / #8794ab | decorative / 3:1 borders |
| focus / focus-inner | #f2b705 / #14181f | #f2b705 / #f2f4f8 | 3px gold outline + 2px contrasting inner ring |
| footer-bg / footer-text | #1b2f5b / #e8edf6 | #0a0f18 / #dfe5ee | navy civic footer |

Contrast pairs and minimums live in `tokens.yaml` `pairs` (body text 7:1, everything else >= 4.5:1, borders
3:1) and are checked on every build in both themes.

- Type: base `html { font-size: 125% }` = 20px, follows browser zoom. Scale steps -1 (17px) to 4
  (`clamp(1.8rem, 1.35rem + 2.2vw, 2.85rem)`). Body: system UI stack. h1/h2: system serif stack
  (Charter, Sitka, Cambria, Georgia, Noto Serif) for a dignified "civic" feel. No web fonts.
- Space: 3xs .25rem to 2xl `clamp(3rem, 2rem + 4vw, 5rem)`. Radius 6/10/16px/pill. Shadows: two soft levels.
- Layout: `--wrap` 60rem container, `--measure` 36rem prose, `--tap` 3rem (60px) minimum control height.
- Theme: `light-dark()` + `color-scheme`; `data-theme="light|dark"` on `<html>` overrides the system
  setting. Browsers without `light-dark()` get an `@supports not` fallback with the same values.
- Motif: flag bar (navy/white/red thirds), small red star in kickers, a three-star rule between sections,
  a large faint star in the hero. No stock photos.

## CSS architecture

`@layer reset, tokens, base, layout, components, pages, utilities;` then a print block. Logical properties
throughout; container queries for card grids and the trust panel; `:has()` for whole-card links;
`:focus-visible`; `text-wrap: balance` (headings) / `pretty` (body); cross-document View Transitions only
under `prefers-reduced-motion: no-preference`; reduced motion disables all animation.
Native CSS nesting is deliberately **not** used: older iPhones (iOS 16) are common in this audience and
would drop nested rules. Revisit when iOS 16 traffic is negligible.

## Components (live examples at `/styleguide/`)

| Component | Class / partial | Notes |
|---|---|---|
| Skip link | `.skip-link` | first focusable element |
| Flag bar | `.flagbar` | decorative, aria-hidden |
| Header + nav | `partials/header.html` | wide nav >= 62em; below that a no-JS `<details class="menu">` |
| Brand | `.brand`, `partials/brand-mark.svg` | check-in-square mark + gold star |
| Buttons | `.btn`, `--secondary`, `--lg`, `--small`, `.btn-row` | >= 60px tall; primary is navy, never red |
| Kicker | `.kicker` | red eyebrow line with a star icon |
| Hero | `.hero`, `partials/hero-stars.svg`, `partials/mockup.html` | mockup = HTML drawing, fake data, role="img" |
| Cards | `.card`, `.card-grid(--3)`, `.card--link`, `.card__icon` | container-query columns |
| Trust panel | `partials/trust.html` | wording from docs/BRAND.md |
| Steps | `.steps(--big)` | CSS counters, one idea per step |
| Callouts | `.callout`, `--gold`, `--myth`, `--fact` | gold = safety/caveat |
| Checklists | `.checklist--yes/--no` | does / doesn't |
| Breadcrumbs | `partials/crumbs.html` | plus BreadcrumbList JSON-LD |
| FAQ | `.faq details` | native disclosure, works without JS |
| SmartScreen drawing | `partials/smartscreen.html` | drawing, not a screenshot; real screenshots are a launch item |
| Download card | `.download-card`, `.facts`, `.hash` | version/size/SHA256 from `data/release.yaml` |
| Guide list | `.guide-list` | guides index |
| Footer | `partials/footer.html` | trust panel, "not a government service", no-tracking line |

## Page inventory

| URL | Status | Notes |
|---|---|---|
| `/` | built | hero + mockup, promises, the post, 3 steps, does/doesn't, helping a parent, short FAQ, CTA |
| `/how-it-works/` | built | four steps, three tiers, safety list |
| `/download/` | built | download card, SmartScreen steps with drawings, genuine-download check, uninstall |
| `/privacy/` | built | never-ask list, where data lives, update feed, this website (why no cookie banner) |
| `/faq/` | built | myth vs. fact + all questions, FAQPage JSON-LD |
| `/guides/` + `/guides/<name>/` | built | 29 guides from the public sample registry |
| `/i-do-not-consent/` | built | explainer, plain Facebook share link |
| `/styleguide/` | built, noindex | living style guide |
| `/404.html` | built, noindex | absolute links (served at any depth) |
| `/download.html`, `/faq.html`, `/how-it-works.html`, `/privacy.html` | redirect stubs | meta refresh + canonical, noindex |
| For families and helpers | not built | needs HELPER_GUIDE / fridge-card content decisions |
| Who's buying your data? | not built | citations not verified yet |
| Pricing | do not build | paid tier not announced |

## Checks (`tools/site_check.py`)

Per page: `lang`, CSP + referrer meta, title <= 60, description <= 155, canonical under base_url, og:image
exists, exactly one h1, no `style=""`, no inline handlers, no forms/iframes, no non-JSON-LD inline script,
no cross-origin or `data:` assets, every internal link and #anchor resolves, every `<img>` has alt/width/height.
Site: sitemap lists exactly the indexable pages, robots.txt has a Sitemap line, CSS has no external `url()`
or `@import`, no full-registry-only values, no mention of `registry.yaml`.
