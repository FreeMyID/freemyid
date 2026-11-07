# web-qa handoff

## R7 re-check (site-v3 971b1ec..cd35f9c, rebuilt from HEAD)

PASS on all four items: WR-50, WR-51, WR-52, WR-54 verified (rows updated). With WR-50 fixed the R7 verdict becomes **PASS with P3s** (open P3: WR-53 hero label wrap, WR-55 safety art, and the WR-51 tab-out note).
- `tools/site_shots.py` at 320/360/390/414/768/1280 x light/dark: 120 combos, 0 hard problems, 0 targets between 24 and 44 px. Leo Hart's edit to the menu check (popover button first, `<details>` fallback, "menu did not open" guard) reviewed: correct, and it exercises the popover path here.
- Popover keyboard pass (320/360/414): focus the Menu button, Enter opens (links at 31..289 / 329 / 383, inside viewport), Tab goes How it works, Guides, Is it safe?, For families, FAQ, then the header Download, every stop with a visible ring; Escape closes and returns focus to the Menu button; click outside closes; Enter on the button toggles; button hidden at 1280. Fallback `<details>` panel (forced with inline style, no non-popover browser available) stays inside the viewport at 320/360/390.
- Budgets (KiB, check-site): home first view 21.6; /download/ JS 78.3 KiB (80,053 bytes = 80.1 kB decimal); CSS 8.6 on every page; dist `_assets` now only CSS, client, CopyHash, react (TimelineBeam gone).
- Copy: home says "29 step-by-step opt-out guides"; no stale text.

## R7 site-v3 (2026-11-07, Astro site in web/, branch site-v3)

Verdict: **FAIL** (one P1 blocks switch-over). P1: 1 (WR-50), P2: 0, P3: 5 (WR-51 to WR-55). Everything else passes; fix WR-50 and the verdict becomes PASS with P3s.

**WR-50 (P1):** the opened phone menu is clipped off the left edge at 390px and narrower, so on phones the only navigation is partly unreadable. `tools/site_shots.py` now detects it.

Method: `pnpm build` (43 pages), copied dist to scratchpad/srv/freemyid and served it with `python -m http.server`. `tools/site_shots.py --prefix freemyid/ --crops --zoom-check --reduced-motion` on home, safety, download, how-it-works, faq, families, guides, one guide, i-do-not-consent, 404 at 320/360/768/1280 x light/dark (80 combos), then looked at 360 crops of home, download, faq, safety (light and dark), 768 how-it-works, 1280 home, 404. Tab-through at 1280 and 360 on home and download with computed focus styles; header menu opened by keyboard and mouse at 320/360/390/414/540/768; text contrast computed for every visible text node on 8 pages x 2 themes x 360/1280 (zero below AA); banned-phrase and number grep on rendered text; source comments in templates; Copy button and console errors on /download/; external requests logged.

Results:
- Layout: no horizontal scroll at 320/360/768/1280, one h1 per page, no skipped heading levels, every img has alt/width/height, no interactive target under 24px (only the 30px Pause checkbox is under 44).
- Keyboard: skip link is the first stop and is visible; 58 stops on home at 1280 (54 at 360), every stop has a 3px yellow outline plus dark inner ring (works on both themes); order is logical; focus leaves the page at the end, no traps; the scrollable comparison region is focusable by design. Menu: Escape does not close it (WR-51).
- Contrast: all text meets AA in both themes (lowest body text about 7:1); the two-tone focus ring clears 3:1 on light and dark.
- Product truth (WR-38): home hero, final CTA and download page show v0.1.0 and the real installer link; no "opens soon / not published / coming soon" text anywhere in dist. Download page: 64 MB, sha256, SmartScreen steps present.
- Claims: no banned phrase ("guarantee", "100%", "erase", "forever", "fifteen minutes", "audited", "trusted by", stars or ratings); "never" appears only as "never asks for ..." (POSITIONING rule 4). Numbers: 29 guides (build-derived, WR-54 wording), six screens, once a day, 64 MB, 0.1.0 all match D8 or release.yaml. The WR-37 ODNI text and source comment are in. Every claim section has a source comment in the Astro templates (31 on home, 17 safety, 13 families, 11 download).
- Privacy: no third-party requests, CSP meta on every page, `content_check.py dist` OK (host-hash leak scan off in this worktree).
- Copy button works, announces "Copied" in an aria-live region, no console errors other than the intentional 404 test URL.

Sizes (gzip, measured): home HTML 12.8 KB + CSS 8.5 KB + JS 0 = 21.3 KB first view; with lazy images at desktop (dashboard-1200 59 KB, report-900 84 KB raw webp) about 165 KB worst case, about 105 KB at 360 (700w and 600w). Budget 300 KB: pass. CSS 8.5 KB on every page (budget 20): pass. HTML: safety 5.9, faq 6.0, families 6.6, how-it-works 6.1, download 8.2, guide 4.8, 404 2.8. JS: zero on every page except /download/, where after the checksum panel opens it is 80,454 bytes gzip = 78.6 KiB / 80.5 KB (budget 80 KB: at the limit, WR-52). An unused 32 KB gzip TimelineBeam chunk is emitted but never loaded (WR-52).

| ID | Page | Sev | Problem | Owner |
|---|---|---|---|---|
| WR-50 | all (phone menu) | P1 | opened menu panel clipped off the left edge at 390px and below (left edge -86px at 320, -46 at 360) | web-builder |
| WR-51 | all (phone menu) | P3 | menu does not close on Escape, outside click or focus leaving | web-builder |
| WR-52 | /download/, build | P3 | JS budget at the 80 KB limit (78.6 KiB / 80.5 KB); unused TimelineBeam chunk still emitted | web-builder |
| WR-53 | home hero | P3 | button label wraps to "Download Free My / ID" at 360; ghost button inset misaligned at 1280 | web-designer |
| WR-54 | home, faq | P3 | "29 sites" counts credit bureaus, DROP and Google; say "29 guides" | web-builder |
| WR-55 | safety hero art (dark) | P3 | 5px text on the laptop card overlaps its edge | graphic-designer |

Tools: `tools/site_shots.py` gained `--reduced-motion` (scroll-driven reveals otherwise leave blank bands in full-page shots) and a header-menu clipping check that fails the run. Scratch scripts for keyboard, contrast and text dumps are in the session scratchpad (not committed). Shots: scratchpad/shots.

---

## Earlier: R12 re-verify after round 2 (jinja site, 2026-11-07)

Verdict: **PASS with P3s**. P1: 0, P2: 0, P3: 1 new (WR-36). WR-25 to WR-35 verified fixed in the built output (a rebuild to scratchpad is byte-identical to site/).

Method: built to scratchpad/qa2/site, `tools/site_shots.py --crops --zoom-check` (10 pages x 320/360/768/1280 x light/dark), full-resolution 360 crops of home, download, safety read in light and dark, keyboard tab-through at 1280 and 360, h-scroll at 320 and 640 on 7 pages, banned-word grep on visible text, gzip sizes. Shots: scratchpad/qa2/shots.

Verified: no h-scroll at 320/360/640/768/1280; one h1; no skipped levels; images have alt/width/height; no target under 24px (only the 404 test page at the root, unstyled by design, and logo 32px info). Focus ring on all 55 (1280) and 51 (360) tab stops, order logical. Comparison renders as stacked cards at 360 (every td has data-label); without :has() it falls back to the sideways-scrolling table (acceptable). "What it removes" is 2 columns; download "opens soon" callout is top of card, readable; safety copy matches WR-25/28/30; no releases links while release.version is null. srcset: dashboard 700/1200, report 600/900, aspect ratios match width/height attributes, no CLS risk. Banned phrases absent (only "permanent opt-out" in the OptOutPrescreen guide, a quote of the official form, fine).

Sizes (gzip): home HTML 7.3 KB, safety 4.4, download 4.2, how-it-works 3.9, faq 4.9, families 5.2, guide 3.7, CSS 11.0 KB. Home first-view transfer about 104 KB with 700w images (budget 300).

Tools: fixed `site_shots.py -h` crash (unescaped % in help text).

| ID | Page | Sev | Problem |
|---|---|---|---|
| WR-36 | faq, families, 404 templates | P3 | claims without source comments |
