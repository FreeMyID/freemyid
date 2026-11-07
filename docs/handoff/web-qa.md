# web-qa handoff: R7 verification of redesign v2 (2026-11-07)

Verdict: **PASS with P3s** for layout and accessibility; **FAIL-lite on claims**: 3 P2 copy fixes (WR-25, 26, 27) should land before the site is published. P1: 0, P2: 3, P3: 8.

Method: built to scratchpad/qa/site (not site/), served on :8765, `tools/site_shots.py --crops --zoom-check`
(10 pages x 360/768/1280/320 x light/dark = 80 combos), viewport-height crops at full resolution reviewed for
home, safety, download and the Spokeo guide at 360 in both themes, keyboard tab-through, banned-word grep, claim
audit against D8 and R5, gzip sizes. Screenshots: scratchpad/qa/shots (+ shots404, m/ montages).

Clean: no horizontal scroll at 320/360/640/768/1280 in either theme; one h1 per page; no skipped heading
levels; no image without alt/width/height; no tap target under 24px (none under 44px either, outside the
unstyled 404 test); dark mode contrast and polish good; focus ring visible on every one of 54 (1280) and 50 (360)
tab stops, logical order (skip link, logo, nav, header CTA, hero, ..., footer), `scroll-padding-top` 120px so the
sticky header does not cover focus; 404 renders fine under /freemyid/ (it uses absolute base-path URLs, so it only
looks right under that prefix: `site_shots.py --prefix freemyid/`).
Claims: all banned phrases absent (erase, guarantee, 100%, forever, audited, trusted by, ratings, counters);
broker count is build-derived (29 guides); comparison paid column uses only the six R5 rows, no prices, no
competitor names; made-up-data captions present on both screenshots.

Sizes (gzip): home HTML 7.2 KB, safety 4.4, download 4.3, faq 4.9, guide ~3.8, CSS 10.2 KB (all under 50 KB);
home total with images about 286 KB (budget 300).

Tools: `tools/site_shots.py` (new, reusable) and three new `tools/site_check.py` rules (banned phrases on visible
text, screenshot figure caption must contain "made-up data", no release-asset link or releases-page button while
`release.yaml` version is null). All pass on current content; negative-tested on a tampered copy. `build_site.py
--check` OK, ruff clean.

| ID | Page | Sev | Problem |
|---|---|---|---|
| WR-25 | home, safety | P2 | "Nothing leaves your computer" vs text that the app contacts sites; table cell same |
| WR-26 | home | P2 | "works on Windows 10 and 11 today" with no release |
| WR-27 | download + 5 templates | P2 | "Installs in a few minutes" untimed; no source comments on download/how-it-works/faq/consent/guides |
| WR-28 | safety, home | P3 | "don't have to trust us at all" absolute |
| WR-29 | safety, download, home | P3 | fingerprint promise and links to empty releases page |
| WR-30 | safety | P3 | app-password inside "never asks for" list |
| WR-31 | home 360 | P3 | comparison table no scroll cue, tall header cell |
| WR-32 | home 360 | P3 | oversized single-column "what it removes" cards |
| WR-33 | download 360 | P3 | callout nested in card, cramped |
| WR-34 | inner pages 360 | P3 | h1 flush to lead |
| WR-35 | home | P3 | 286 KB total, oversized hero image, unreadable report at 360 |
