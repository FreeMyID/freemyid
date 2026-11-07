# web-qa handoff: R12 re-verify after round 2 (2026-11-07)

Verdict: **PASS with P3s**. P1: 0, P2: 0, P3: 1 new (WR-36). WR-25 to WR-35 verified fixed in the built output (a rebuild to scratchpad is byte-identical to site/).

Method: built to scratchpad/qa2/site, `tools/site_shots.py --crops --zoom-check` (10 pages x 320/360/768/1280 x light/dark), full-resolution 360 crops of home, download, safety read in light and dark, keyboard tab-through at 1280 and 360, h-scroll at 320 and 640 on 7 pages, banned-word grep on visible text, gzip sizes. Shots: scratchpad/qa2/shots.

Verified: no h-scroll at 320/360/640/768/1280; one h1; no skipped levels; images have alt/width/height; no target under 24px (only the 404 test page at the root, unstyled by design, and logo 32px info). Focus ring on all 55 (1280) and 51 (360) tab stops, order logical. Comparison renders as stacked cards at 360 (every td has data-label); without :has() it falls back to the sideways-scrolling table (acceptable). "What it removes" is 2 columns; download "opens soon" callout is top of card, readable; safety copy matches WR-25/28/30; no releases links while release.version is null. srcset: dashboard 700/1200, report 600/900, aspect ratios match width/height attributes, no CLS risk. Banned phrases absent (only "permanent opt-out" in the OptOutPrescreen guide, a quote of the official form, fine).

Sizes (gzip): home HTML 7.3 KB, safety 4.4, download 4.2, how-it-works 3.9, faq 4.9, families 5.2, guide 3.7, CSS 11.0 KB. Home first-view transfer about 104 KB with 700w images (budget 300).

Tools: fixed `site_shots.py -h` crash (unescaped % in help text).

| ID | Page | Sev | Problem |
|---|---|---|---|
| WR-36 | faq, families, 404 templates | P3 | claims without source comments |
