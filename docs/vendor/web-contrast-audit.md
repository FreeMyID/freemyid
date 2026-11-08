# Website contrast and keyboard-focus audit (WO-122, GP-03)

Author: Lucia Ferraro (Copilot web-designer). Notes only: nothing under `web/` was changed.
Scope: `web/src/styles/{tokens,global,theme}.css` and `web/src/components/**`, light and dark.
Out of scope: the families page (Codex WO-118), the FAQ and header-menu behaviour already covered by
`tests/test_web_faq_accessibility.py`, `tests/test_web_header_navigation.py` and `docs/handoff/web-qa.md` (R7 computed
text contrast on 8 pages and found no text below AA; this audit does not repeat that, it works from the tokens).

## Method and limits

- **computed**: WCAG 2.x relative luminance and ratio `(L1 + 0.05) / (L2 + 0.05)` from the hex values in
  `tokens.css`, run as SQL in the session database (no shell or browser was available in this session).
  Light and dark values are the two arms of each `light-dark()`. Thresholds: 4.5:1 text, 3:1 large text, icons and UI.
- **source reading**: which token pair a component uses, read from the `.astro` / `.css` source. Cascade conclusions
  (specificity, layers) are reasoning, not browser results.
- **not verified**: anything needing a rendered page (clipping, forced-colors, real focus behaviour, 200% zoom,
  360px). No browser was run. No page under `web/src/pages/` other than `index.astro` was read, so where a finding
  depends on how a page uses a component, the page use is listed as unverified.
- Ratios are rounded to two decimals. Owner for every fix: web-designer (in-house), as the fix touches `web/`.

## Summary

| ID | Sev | Where | Problem | Status |
|---|---|---|---|---|
| CA-1 | P2 | `button-variants.ts:19` | `onBrand` hover: dark text on a near-identical dark background, 1.15:1 in dark | computed + source |
| CA-2 | P2 | `Section.astro:25` | `tone="brand"` forces link colour on buttons inside the band: invisible or low-contrast buttons | computed + source; page use unverified |
| CA-3 | P3 | `global.css:40-43` | Light-mode focus ring only passes 3:1 as a pair; gold alone is 1.82:1 | computed; passes as designed |
| CA-4 | P3 | `CopyHash.astro:43,54` | Button is disabled during copy, so keyboard focus can drop to the page | source reading; unverified |
| CA-5 | P3 | `SmartScreen.astro:11,14` | Hard-coded colours; ink on the blue is fine, highlight ring is 4.31:1 | computed |
| CA-6 | P3 | `global.css` (whole file) | No `forced-colors` rules; the inner ring (box-shadow) disappears in Windows high contrast | unverified |
| CA-7 | note | `border-line` users | Card, table and header borders are 1.21 to 1.55:1 | computed; not a failure (decorative) |

Everything else audited passed (see "Passing pairs").

## Findings

### CA-1 (P2): `onBrand` button hover is unreadable in dark mode
- File: `web/src/components/ui/button-variants.ts:19` (`onBrand: "bg-band-brand-ink text-band-brand hover:bg-bg-alt"`),
  tokens `tokens.css:6,16,17`. Used by the final call to action, `web/src/pages/index.astro:316`, and anywhere
  `CtaDownload look="onBrand"` appears (other pages unverified).
- Colours (dark): text `band-brand` `#162543` on hover background `bg-alt` `#121a26`.
- Ratio (computed): **1.15:1** dark (needs 4.5:1). Light is fine: `#1b2f5b` on `#f4f6f9` = 12.09:1.
- At rest it passes in both themes: `#162543` on `#eef1f6` = 13.44:1 (dark), 13.09:1 (light).
- Effect: in dark mode, hovering the main call to action on the dark blue band turns it into a dark button with
  dark text. Hover only (touch and keyboard focus keep the resting look), so it is worst for mouse users.
- Proposed fix: keep the button light on hover in both themes, e.g. `hover:bg-band-brand-ink/90` (estimated about
  11:1 in dark, light unchanged in kind; unverified, re-compute after the change), or add a `band-brand-ink-hover`
  token. Do not reuse `bg-alt`, which is dark in dark mode.

### CA-2 (P2): `Section tone="brand"` overrides button text colours
- File: `web/src/components/Section.astro:25`:
  `[&_a]:text-band-brand-ink` has selector specificity (0,1,1) and beats the button utilities (0,1,0), so any
  button link inside a brand band takes the band's ink colour.
- Effects (computed, using the token values):
  - `onBrand` button (`bg-band-brand-ink`) becomes ink on ink: white on white (1:1) in light, `#eef1f6` on `#eef1f6` in dark.
  - `primary` button (`bg-brand text-brand-ink`) text becomes `band-brand-ink`: light 12.27:1 (ok) but the
    button `#1b3366` against the band `#1b2f5b` is **1.07:1**, so it has no visible edge (only `shadow-1`); dark,
    `#eef1f6` on `#a9c3f3` is **1.57:1** (fails 4.5:1).
  - `secondary`: `bg-card` with band-ink text: white on white in light.
- Unverified: whether any current page puts a button inside `tone="brand"`. The home page does not (its final
  band is a plain `<section>`, `index.astro:311`); I could not search the other pages in this session. Run
  `grep -rn 'tone="brand"' web/src/pages` before deciding urgency.
- Proposed fix: scope the rule to prose links (`[&_a:not([class*=inline-flex])]` or `.prose-fmid a`), or give
  buttons `!text-*` inside bands. Owner: web-designer (in-house).

### CA-3 (P3): light-mode focus ring depends on both rings
- File: `web/src/styles/global.css:40-43` (3px `--fmi-color-focus` outline, 3px offset, plus 3px
  `--fmi-color-focus-inner` box-shadow); tokens `tokens.css:24-25`.
- Computed ratios (gold `#f2b705` vs the surface it sits on): light `bg` **1.82:1**, `bg-alt` 1.68:1, `card` 1.82:1
  (each below 3:1 on its own); dark `bg` 10.24:1, `bg-alt` 9.61:1, `card` 8.90:1, `band-brand` 8.37:1.
- The inner ring `#151b26` is adjacent to the element and is 17.26:1 on `bg`, 15.94:1 on `bg-alt` (light), so the
  pair is clearly visible on every light surface. Gold vs inner ring: 9.49:1 (light). On the dark footer
  (`#0f1c38`) the inner ring is 1.02:1 but gold is 9.29:1, so it still passes. Brand band: gold 7.20:1 (light).
- Dark primary button: gold vs `brand` is 1.02:1 and inner `#eef1f6` vs `brand` 1.57:1; the ring still passes
  because it is judged against the page (10.24:1), not the button.
- Verdict: passes as designed (a 3px dark/light inner ring plus 3px gold outer ring, never relies on gold alone),
  agreeing with `web-qa.md` R7. Risk: anything that removes the inner ring (the `box-shadow` is `!important`
  today) would leave 1.82:1 gold in light mode. Proposed note in the token source: "do not remove the inner ring".
  No code change needed. Not verified in a browser; ring clipping by `overflow-hidden` ancestors was read, not
  tested (the home hero section and the screenshot figures have `overflow-hidden`; their focusable children sit
  at least 15px inside, more than the 6px ring).

### CA-4 (P3): Copy button is disabled while it works, which can drop keyboard focus
- File: `web/src/components/CopyHash.astro:43` (`button.disabled = true`) and `:54` (`button.disabled = false`).
- A disabled button cannot keep focus in some browsers, so a keyboard user who pressed Enter or Space may land
  back at the top of the page when the copy finishes. The status text is in an `aria-live` region, so the result
  is still announced.
- Status: source reading only; unverified in browsers.
- Proposed fix: use `aria-disabled="true"` and ignore clicks while pending, or restore focus to the button in
  `finally`. Owner: web-builder with web-designer (in-house).

### CA-5 (P3): SmartScreen drawing uses hard-coded colours
- File: `web/src/components/SmartScreen.astro:11` (gold ring `#f2b705`) and `:14` (`#0b5394` panel with `#fff`
  text, 0.85rem), `:25` ("Run anyway", `#0b5394` on `#fff`).
- Ratios (computed): white on `#0b5394` **7.84:1** (ok), `#0b5394` on white 7.84:1 (ok), gold highlight ring vs
  `#0b5394` **4.31:1** (ok for a 3:1 non-text mark), gold vs white 1.82:1 (the ring sits on the blue, so fine).
- No failure. Note only: these bypass the tokens, so a future token change will not reach them. Intentional
  (it imitates a Windows dialog), so no change proposed.

### CA-6 (P3): no `forced-colors` handling
- File: `web/src/styles/global.css` (no `@media (forced-colors: active)` anywhere).
- Windows high-contrast users (a plausible share of the older readers) get the outline (kept) but not the
  inner box-shadow ring. The 3px outline remains visible, so focus is still visible. Other risk: filled primary
  buttons and the number bubbles rely on background colour, which forced colours replace with system colours;
  buttons have no border. Not verified: no Windows or forced-colors emulation was run.
- Proposed fix: have the web-designer run Chromium with `forcedColors: "active"` (Playwright `forced_colors`
  context option) on home and download, and add `border: 2px solid ButtonText` for `buttonVariants` primary and
  `onBrand` under `@media (forced-colors: active)` if they look borderless.

### CA-7 (note): `border-line` is decorative
- Computed `line` vs surface: light `bg` 1.31:1, `bg-alt` 1.21:1, `card` 1.31:1; dark `bg` 1.55:1, `bg-alt` 1.46:1,
  `card` 1.35:1. Used on cards, the FAQ list, header, tables and trust-bar tiles.
- These borders only frame content; each component is identified by its text, so WCAG 1.4.11 does not apply.
  The trust-bar tiles (`index.astro`, links with `border-line`) are links whose label carries the meaning; hover
  switches to `line-strong`. Interactive borders that identify a control use `line-strong` (computed 4.52:1 on `bg`
  light, 3.84:1 on `brand-soft` light, 6.08:1 on `bg` dark, 4.62:1 on `brand-soft` dark), which meets 3:1.
- No change proposed. If the designer wants stronger card edges, `line-strong` is the existing token.

## Passing pairs (computed, light / dark)

Minimum required 4.5:1 unless noted. Lowest value in each row is shown.

| Pair (where used) | Light | Dark |
|---|---|---|
| `text` on bg, bg-alt, card, surface, brand-soft | 14.66 to 17.26 | 12.50 to 16.44 |
| `muted` on bg, bg-alt, card, surface, brand-soft (leads, captions, PageHead gradient) | 7.48 to 8.80 | 8.40 to 11.05 |
| `heading` on bg, bg-alt, card, surface, brand-soft (headings, nav hover, FAQ hover, badges) | 12.69 to 14.94 | 11.39 to 14.98 |
| `brand` on bg, bg-alt, card, brand-soft (kicker, secondary button, pills; icons need 3) | 10.42 to 12.27 | 7.94 to 10.45 |
| `link` on bg, bg-alt, card, surface, brand-soft | 7.56 to 8.90 | 8.46 to 11.13 |
| `brand-ink` on `brand` (primary button, step bubble, skip link) | 12.27 | 10.45 |
| `brand-ink` on `heading` (primary hover) | 14.94 | 14.98 |
| `band-brand-ink` on `band-brand` (final CTA band) | 13.09 | 13.44 |
| `ok` on bg, bg-alt, card (badge, check icon) | 6.45 to 6.98 | 9.50 to 10.94 |
| `warn` on bg, card (badge, info icon) | 7.13 | 10.04 to 11.56 |
| `footer-text` on `footer-bg` | 14.38 | 15.45 |
| `muted` as x/dash icon on bg (needs 3) | 8.80 | 11.05 |
| `line-strong` (control borders, needs 3) on bg, card, bg-alt, brand-soft | 3.84 to 4.52 | 4.62 to 6.08 |
| `accent` underline on current nav link, on bg / card (needs 3) | 7.49 | 8.25 to 9.49 |
| `::selection` (`#151b26` on `#f2b705`, hard-coded, `global.css:50`) | 9.49 | 9.49 |

Source-reading notes (no failure found):
- Skip link (`global.css`, `.skip-link`): moved off screen with `transform`, visible on `:focus`, `z-50` above the
  `z-40` header, tokens pass.
- Header: toggle and nav links use `min-h-tap` (3rem = 48px at the 125% root); current page has an underline as
  well as colour (not colour alone). Sticky header height is about 85px and `html` has `scroll-padding-top: 6rem`
  (120px), so focused links are not hidden behind it (reasoned, not tested).
- Marquee: pause checkbox is a real input, label 8.80:1 (light); the moving list has no focusable items, so no
  focus-ring clipping from its `overflow-hidden` wrapper.
- Focus transitions are disabled (`transition: none !important`), `main:focus` removes the outline only on the
  skip-link target.
- Motion: reveal, beam and marquee animations are inside `prefers-reduced-motion: no-preference`; marquee shows a
  static list under reduce.

## Not covered (unverified)
- Pages other than `index.astro`, and illustrations in `web/src/art/` (graphic-designer area).
- Rendering at 360px, 200% zoom and forced colours; real keyboard order; screen readers.
- Whether `tests/test_web_*` still pass on a fresh build was not run in this session (shell unavailable); this
  change adds only a notes file.
