# web v3 handoff (branch `site-v3`, never pushed, not merged)

Status (2026-11-07): content parity with v2 done, checks pass. Waiting on web-qa + qa-security before any switch-over.
v2 (`site_src/`, `tools/build_site.py`, `site/`, `pages.yml`) untouched and still the live site.

## Build and check

```
cd web
pnpm install --frozen-lockfile
pnpm build                                   # gen-tokens -> astro build -> tighten-csp (output web/dist)
pnpm check                                   # scripts/check-site.mjs: meta, CSP, links, anchors, img, sitemap, budgets
python scripts/content_check.py dist         # tools/site_check.py: copy rules + leak scans (filters only hashed island scripts)
python scripts/content_check.py dist --tools <main checkout>/tools   # with the private host-hash list (leak scan ON)
node scripts/gen-tokens.mjs --check          # tokens.css/theme.css up to date (CI)
```
Preview: serve a folder that holds a `freemyid -> web/dist` symlink (`python -m http.server`), open `/freemyid/`.
Build is deterministic (two clean builds, identical sha256 for every file).

## Data: one source of truth
`web/src/lib/site.ts` reads `site_src/site.yaml`, `pages.yaml` (titles, descriptions, JSON-LD kinds), `data/faq.yaml`,
`data/release.yaml`, `data/icons.yaml`, `data/guide_intros.yaml` and `brokers/registry.sample.yaml` (same refusal guard as
build_site.py: never the private registry). `publicDir` = `site_src/static` (favicons, screenshots, fridge card, og.png).
FAQ answers: jinja `url()` and `release.version` if/else are expanded, then HTML is parsed with a tag/attribute allowlist and
rendered as elements (`lib/rich.ts`, `RichText.astro`): no set:html on data. Merging main later picks up content changes for free.

## Theme
`site_src/tokens.yaml` -> `web/src/styles/tokens.css` (framework-neutral `--fmi-*` custom properties, light-dark(),
data-theme override, pre-2024 fallback; the desktop app can import this file) + `theme.css` (Tailwind `@theme inline` mapping).
Contrast pairs from tokens.yaml are checked at generation (fails the build). Both generated files are committed.
brand/v3 SVGs are inlined by `Art.astro` without their `<style>` (CSP); their classes live in global.css under `.fmi-art`,
fed from the theme. style="" attributes in the SVGs are turned into presentation attributes.

## Components (where they're used)
| Piece | Source library | File | Used on |
|---|---|---|---|
| Button (buttonVariants, cva) | shadcn/ui | components/ui/button-variants.ts, button.tsx | every CTA (static `<a>` with the variants); React Button in CopyHash |
| Card, Badge, Alert | shadcn/ui (Astro ports, same classes, no React) | components/ui/*.astro | all pages |
| Accordion look | shadcn/ui style on native `<details>` (works with JS off) | components/FaqList.astro | home FAQ, /faq/, download checksum |
| Border Beam | Magic UI (CSS-only port) | components/magicui/BorderBeam.astro | hero Download, download page button |
| Marquee | Magic UI (CSS-only port, Pause checkbox, hover/focus pause) | components/magicui/Marquee.astro | home "What it removes" (guide site names, plain text) |
| Blur Fade | Magic UI idea, done as scroll-driven CSS (`.reveal`) | global.css | cards and section heads |
| Timeline | Aceternity UI (static list + beam) | components/aceternity/Timeline*.astro | CSS scroll-driven beam on how it works, download, families, I-do-not-consent, guides. The motion island (TimelineBeam.tsx, `beam="island"`) is kept in source but unused (orchestrator ruling: not worth ~95 KB JS) |
| CopyHash | own island with shadcn Button | components/CopyHash.tsx | download checksum panel (loads only when the panel opens) |
Islands: only `client:visible`, and only CopyHash ships (lazy, inside the closed checksum panel). Every other page has zero JS. All motion is off under prefers-reduced-motion and in print.

## Dependencies (exact, pnpm 10.32.1, node 24)
astro 7.4.7, @astrojs/react 7.1.4, react 19.3.1, react-dom 19.3.1, tailwindcss 4.3.5, @tailwindcss/vite 4.3.5,
motion 14.10.1, clsx 2.1.1, tailwind-merge 3.7.0, class-variance-authority 0.7.1, @radix-ui/react-slot 1.5.0, yaml 2.9.1.

## Security / privacy
- CSP meta from Astro `security.csp`, then `scripts/tighten-csp.mjs` rewrites each page: `script-src 'none'` on pages with no
  scripts (all but one), `'self'` + the exact sha256 of Astro's inline island bootstrap on /download/;
  `style-src 'self'` + hash of Astro's one `astro-island{display:contents}` style. No unsafe-inline/eval. check-site.mjs verifies.
- Redirect pages (privacy.html, privacy/, *.html) are hand-built with the v2 CSP and `script-src 'none'`.
- No third-party requests (Playwright logged zero non-local requests on every page), no forms, no cookies, system fonts.
- JSON-LD via `set:html` of our own JSON.stringify output with `<` escaped; the guide HTML source comment is filtered to safe chars.

## Budgets (gzip, measured by pnpm check)
Home: HTML 12.9 KB + CSS 8.5 KB + JS 0 = 21.4 KB first view (screenshots are lazy). CSS 8.5 KB on every page.
/download/: JS 78.6 KB (React + CopyHash), loaded only after the checksum panel is opened (0 KB before). /how-it-works/: 14.6 KB, no JS.
All other pages 11-15 KB, no JS.

## Header on phones
Port of v2 52-chrome.css (WR/D1): the Download button always stays in the header. Under 34em the menu toggle is
icon-only (50x50, label kept for screen readers) and the CTA is compact (102x50, "Download" + hidden "Free My ID for
Windows"); at 336px or below the brand is logo-only (accessible name kept). Rules are unlayered at the end of global.css.

## Open items (orchestrator rulings 2026-11-07)
1. DONE: /how-it-works/ uses the CSS beam; React only in the lazy checksum island.
2. Leak scan in CI: same as v2, leave it.
3. Switch-over: rename `.github/workflows/pages-v3.yml.draft` to pages.yml after web-qa + qa-security pass. Styleguide not needed.
4. Base path is set in astro.config.mjs (`site`, `base`) and site.yaml base_url: change both when freemyid.org exists.
5. astro check: skipped for now.
6. og-download.png already carries the "Nothing is sent to us" wording; re-copy from brand/v3/og if it is re-rendered again.
7. DONE: header Download visible on phones (see above).

Screenshots (not committed): scratchpad shots/final (360/768/1280 x light/dark, full page, reduced motion), shots/hdr
(header at 320/336/360/544), shots/w320, shots/nojs, shots/keys.
