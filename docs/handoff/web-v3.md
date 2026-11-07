# web v3 handoff (branch `site-v3`, never pushed, not merged)

Status (2026-11-07): SWITCH-OVER PREPARED on site-v3 (merge of main + switch commit; orchestrator fast-forwards main
and pushes). R7 PASS with P3s, R8 PASS (re-checks c55bf51, eb6e2d5). `.github/workflows/pages.yml` now builds web/ and
deploys web/dist; the v2 publisher is kept inactive as `pages-v2.yml.draft`. Origin and base path come from
site_src/site.yaml (freemyid.org at `/`) in astro.config.mjs, check-site.mjs and content_check.py.
P3 backlog: WR-53, 55, 58, 60; SEC-62, 65, 66, 67; popover stays open on tab-out (WR-51 note); React-free CopyHash
(/download/ JS 78.3 KiB of 80 KiB); Dependabot for github-actions + npm (devops, after merge).

Rollback to v2 (site_src/, tools/build_site.py and site/ stay in the repo; build.yml still rebuilds site/ after releases):

```
git mv -f .github/workflows/pages-v2.yml.draft .github/workflows/pages.yml
git commit -m "Site: roll back to v2 publisher" -- .github/workflows/pages.yml .github/workflows/pages-v2.yml.draft
git push origin main          # Pages redeploys site/ (or: gh workflow run pages.yml --ref main)
```

## v0.2 developer page + owner rule (2026-11-07, Leo Hart; commits b65b927, c4912b9; not pushed)
- `/developers/` (web/src/pages/developers/index.astro, pages.yaml id `developers`, `v3_only: true` so tools/build_site.py
  skips it). Install (pipx, Docker compose, source), first run, systemd/launchd/cron + enable-linger, headless secrets,
  JSON/exit codes (links docs/CLI.md on GitHub, which 404s until the orchestrator commits it), contribute, security.
  EVERY v0.2 section carries the "Coming in v0.2" Badge and future-tense copy. When v0.2 ships: drop badges only for
  what shipped, check the compose against packaging/docker/compose.example.yaml and the image name, and the secrets copy
  against src/freemyid/secret_backends.py. WR-69 (Pro line) is on HOLD: no paid tier or price on the site.
  Art: WR-64 SVGs copied to site_src/static/assets/art/, swapped with `<picture>` + prefers-color-scheme.
  Linked from the footer (Project column, like other secondary pages), the sitemap, /download/ ("Using Linux or macOS?")
  and /safety/#open-source. 6.4 KiB gzip HTML, no JS. tools/site_shots.py DEFAULT_PAGES includes it.
- Owner rule (ROADMAP principle 6: no account, no github.com for regular users): home feedback link is
  `site.support_mailto` (mailto:support@freemyid.org?subject=Free%20My%20ID%20question, no body) + "No account needed:
  just send an email." GitHub releases links removed from download/families/safety; release notes live at
  /download/#release-notes from release.yaml (renders an optional `notes:` list when someone adds one). Home "Read the source
  code" now goes to /safety/#open-source, which points to /developers/. Footer: one quiet "Source code" link; AGPL is plain
  text. GitHub issues/releases links only on /developers/. Remaining github.com hrefs on user pages: the Download button
  (direct asset) until devops ships https://freemyid.org/get/windows (TODO in site.yaml; then change download_url only).
- The v2 templates (site_src/templates, site/) still have the old issues/releases links; v2 is the rollback only.

## Build and check

```
cd web
pnpm install --frozen-lockfile
pnpm build                                   # gen-tokens -> astro build -> tighten-csp (output web/dist); telemetry off
pnpm check                                   # scripts/check-site.mjs: meta, CSP, links, anchors, img, sitemap, budgets (KiB),
                                             # fails on any deployed .js no page loads
python scripts/content_check.py dist         # tools/site_check.py: copy rules + leak scans (filters only hashed island scripts)
python scripts/content_check.py dist --tools <main checkout>/tools   # with the private host-hash list (leak scan ON)
node scripts/gen-tokens.mjs --check          # tokens.css/theme.css up to date (CI)
```
Preview: `python -m http.server` inside web/dist, open `/` (origin and base path come from site_src/site.yaml; freemyid.org at the root since the switch-over).
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
| Timeline | Aceternity UI (static list + beam) | components/aceternity/Timeline*.astro | CSS scroll-driven beam on how it works, download, families, I-do-not-consent, guides. The motion island was deleted with the `motion` dependency (WR-52/SEC-63) |
| CopyHash | own island with shadcn Button | components/CopyHash.tsx | download checksum panel (loads only when the panel opens) |
Islands: only `client:visible`, and only CopyHash ships (lazy, inside the closed checksum panel). Every other page has zero JS. All motion is off under prefers-reduced-motion and in print.

## Dependencies (exact, pnpm 10.32.1, node 24)
astro 7.4.7, @astrojs/react 7.1.4, react 19.3.1, react-dom 19.3.1, tailwindcss 4.3.5, @tailwindcss/vite 4.3.5,
clsx 2.1.1, tailwind-merge 3.7.0, class-variance-authority 0.7.1, @radix-ui/react-slot 1.5.0, yaml 2.9.1.

## Security / privacy
- Astro telemetry is off: `ASTRO_TELEMETRY_DISABLED=1` prefixes every astro script in package.json and is set in the
  workflow env; the first CI step fails if it is unset or a script calls astro without it (SEC-60). Run astro only via
  `pnpm build`/`pnpm dev`/`pnpm preview`, never bare `pnpm exec astro build`. Dev machines can also run
  `pnpm exec astro telemetry disable` once (writes ~/.config, so agents don't).
- pages-v3.yml.draft: every action pinned to a full commit SHA with a `# vX.Y.Z` comment (pnpm/action-setup pinned to
  v4.3.0, what the floating v4 tag pointed to on 2026-11-07); checkout has `persist-credentials: false`.
- CSP meta from Astro `security.csp`, then `scripts/tighten-csp.mjs` rewrites each page: `script-src 'none'` on pages with no
  scripts (all but one), `'self'` + the exact sha256 of Astro's inline island bootstrap on /download/;
  `style-src 'self'` + hash of Astro's one `astro-island{display:contents}` style. No unsafe-inline/eval. check-site.mjs verifies.
- Redirect pages (privacy.html, privacy/, *.html) are hand-built with the v2 CSP and `script-src 'none'`.
- No third-party requests (Playwright logged zero non-local requests on every page), no forms, no cookies, system fonts.
- JSON-LD via `set:html` of our own JSON.stringify output with `<` escaped; the guide HTML source comment is filtered to safe chars.

## Budgets (gzip, measured by pnpm check)
Home: HTML 12.8 KiB + CSS 8.6 KiB + JS 0 = 21.4 KiB first view (screenshots are lazy). CSS 8.5 KB on every page.
/download/: JS 80,053 bytes gzip -9 = 78.2 KiB (React + CopyHash), loaded only after the checksum panel is opened
(0 before). Under the 80 KiB budget, 53 bytes over 80 kB decimal; a plain-script CopyHash would drop ~70 KiB (WR-52 idea). /how-it-works/: 14.6 KB, no JS.
All other pages 11-15 KB, no JS.

## Header on phones
Port of v2 52-chrome.css (WR/D1): the Download button always stays in the header. Under 34em the menu toggle is
icon-only (50x50, label kept for screen readers) and the CTA is compact (102x50, "Download" + hidden "Free My ID for
Windows"); at 336px or below the brand is logo-only (accessible name kept). Rules are unlayered at the end of global.css.
Menu (WR-50/51): a native popover (`button[popovertarget=site-menu]` + `ul#site-menu[popover]`), no script. It closes on
Escape and outside click and returns focus to the button. It sits in the top layer, fixed under the header at
`inset-inline-end: gutter`, width `min(20rem, 100vw - 2*gutter)`. Where `selector(:popover-open)` isn't supported
(iOS 16 and older), CSS shows the old `<details>` menu instead, anchored to the sticky header with the same width cap.
That fallback doesn't close on Escape or outside click. tools/site_shots.py's menu check handles both and fails if the menu doesn't open.

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
