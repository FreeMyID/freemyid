# web-builder checkpoint

Round 1, rows R2 + R3 (builder #1, owns partials + pages.yaml). Status: **R2 and R3 done**, waiting on lead (R6).
Preview: `.venv/bin/python tools/build_site.py --out <scratchpad>/builder/site` -> OK.

## Commits
- cd95901 `partials/cta-download.html` (D5): vars `cta_variant` (main|header), `cta_class`.
- be1f48c `/safety/` replaces `/privacy/` (D2). Anchors #local #never-asks #open-source #uninstall (+ #updates #verify #limits #this-website). pages.yaml keeps a TEMPORARY `privacy` entry (template redirect.html, noindex) until the lead adds the site.yaml redirect.
- 6d4d6cd header per D1 (one `nav.site-nav` > `ul.site-nav__list` + `details.menu` > `ul.menu__list`), contract Header row updated.
- 9d945a2 faq.yaml: 8 home entries per teardown section 11; new `scam`, `where-data`; free answer drops the paid hint.
- 7d7e75c home in D10 order (real screenshots, R5 paid column, $0 card). 08fd87c footer four columns + legal row.
- 7b33a0a..9bb8b8c Download buttons on faq/families/i-do-not-consent/guide/guides/how-it-works through the partial.

## Open (in the final report as CHANGE REQUESTs)
- lead: site.yaml redirects `privacy.html: safety` + a `privacy/index.html` stub, then drop the temporary pages.yaml `privacy` entry.
- designer: header CTA not visible at 360px (no Download/Coming soon in the small-screen header or menu).
- marketing: source "past addresses" / "email addresses" cards; family-member limit item for the $0 card; helper time + printable sheet claims.

## Round 2 (R9): WR-25..28, 30, 35 + .section -> .band. Status: done, waiting on lead.
Preview: `--out scratchpad/builder2/site` -> OK. Shots: scratchpad/builder2/shots (home/safety/download/how-it-works, 360+1280).
- 0cbb72e WR-25, 9ece257 WR-26, 141a488 8f6f4ad 482fe57 4325ffd c785df4 WR-27, a7e9b02 WR-28, c4982ad WR-30, 98da0c4 WR-35,
  d5583d9 band migration (download, how-it-works; safety already used bands), 5d812cd comparison `data-label` (WR-31 request), 65369d9 board.
- Dropped as unsourced: install time (download), "A few minutes" (guide email item), "A step-by-step guide is planned" (faq facebook).
- Open: WR-29 (lead), full-size report link text differs from the orchestrator's "Tap to see it full size" (a11y).
