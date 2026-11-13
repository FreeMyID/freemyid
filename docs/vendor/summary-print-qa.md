# Printable summary layout QA — WO-116

Status: delivered. The original pre-fix run found four narrow-screen failures; Morgan reports all 48 cases pass after in-house SUM-320 fix 76410e6. No expected-failure markers were added.

## Owner update after the initial run

CLAUDE-021 reports that Nina fixed SUM-320 in-house (76410e6) and that Iris's unchanged WO-116 test passes all 48 cases against the fix, with no xfails. This is the owner's report; Nora did not rerun the test. The results below preserve the original pre-fix measurements and verification limits.

## Browser, media and paper model

- Browser: installed Playwright Chromium, headless, JavaScript disabled. Tests fulfill the rendered fake summary from memory and its existing static assets from disk; other destinations are blocked. No application server, store, mailbox or broker submission is used.
- Screen: 320 × 900 and 640 × 900 CSS pixels, each in light and dark modes. These are viewport checks, not actual desktop/browser-chrome zoom operations.
- Print: Chromium `print` media at content boxes modeled for A4 portrait (680 × 1009 CSS pixels) and US Letter portrait (703 × 943 CSS pixels), each in light and dark contexts. Dimensions approximate each sheet less the product's 1.5cm margins at 96 CSS pixels per inch.
- The paper cases are **modeled content areas**, not paper selections in a print dialog. No printer, physical page boundaries, browser print-preview UI or PDF export feature was verified. Browser print-media checks do not establish app PDF support.

## Fake fixtures

- Empty: no statuses or requests.
- Single: one requested site.
- Many: 48 fake sites, consisting of 12 requested, 12 confirmed, 12 removed and 12 not found. This produces 36 table rows plus its header; not-found results contribute to a separate count.
- All cases use the long label “Pat Testperson — a deliberately long fake profile label for a sample summary”. Site names identify fake sites and include a deliberately long, spaced description. Dates are fixed at 2026-11-07.
- Existing fake-profile/status helpers are reused without editing their module. No real personal data or credentials are used.

## Results

The 48 cases comprise three fake-data scenarios × eight screen/print/theme configurations × two checks (content/media behavior and horizontal geometry).

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Requested versus confirmed/removed versus checked/not-found | PASS in all 24 content/media cases | Rendered counts and exact table outcomes remain distinct. Not-found results stay out of the request-history table. |
| Long fake label and site names at 640px | PASS | Heading, summary and document widths fit. No observed sideways scrolling. |
| Empty summary at 320px | PASS in both themes | Explanatory empty text appears; no unnecessary table; heading/document fit. |
| Single/many-site summary at 320px before SUM-320 | FAIL in both themes | Original run: document width was 322px against a 320px viewport. Summary client width was 286px but scroll width was 305px. Morgan reports the cases pass after fix 76410e6. |
| Print-content geometry, A4/US Letter models | PASS for empty/single/many, both contexts | Summary and heading fit modeled content width, including the long fake text. This does not prove final printer pagination. |
| Print-only presentation | PASS | Header and print/back controls hidden; body text black. Controls remain visible on screen. |
| Row-break policy | PASS as a computed-style check | Every table row has `break-inside: avoid` in print media. Many-site content is taller than either modeled sheet content height, exercising a report that needs pagination. |
| Actual page breaks, repeated column headings and heading/orphan placement | UNVERIFIED | Print-media DOM geometry does not expose native paginated preview. These require the owner/reviewer follow-up below. |
| Print button invokes print preview; physical printer output | UNVERIFIED | JavaScript is disabled in the layout tests. No print-dialog interaction or printer verification was performed. |

## Resolved defect: narrow-screen table overflow (SUM-320)

- Reproduction: `test_summary_content_fits_without_horizontal_clipping` for `screen-narrow-light-single`, `screen-narrow-light-many`, `screen-narrow-dark-single`, and `screen-narrow-dark-many`.
- Observed in actual Chromium: `document.documentElement.scrollWidth` = 322 while viewport width = 320; `.summary.clientWidth` = 286 while `.summary.scrollWidth` = 305.
- Impact: request-history summaries with a table cause sideways scrolling on a narrow screen, even with spaced fake names rather than an unbroken hostile token.
- Owning product files for in-house review: `src/freemyid/wizard/views.py`, `summary_page` table markup; `src/freemyid/wizard/static/style.css`, general table rules and `.summary table td:last-child` date no-wrap rule. The precise product fix is not determined by these tests.
- Iris changed no product files and added no xfails. Morgan reports the in-house fix landed as 76410e6 and the unchanged four assertions now pass.

## Commands and outcomes

From `.vendor-wt/wo-116`:

```sh
PYTHONPATH=src ../../.venv/bin/pytest -q tests/test_wizard_summary_print_layout.py
../../.venv/bin/ruff check src tests
```

- Pre-fix approved browser execution: **44 passed, 4 failed, 1 warning in 3.86s**. Failures were precisely the four narrow-screen table cases above. Morgan reports the post-fix 48-case run passes; Nora did not rerun. Existing Starlette/httpx deprecation warning remains for the initial run.
- Ruff: **All checks passed**.
- Initial sandbox execution skipped 48 cases because Chromium could not launch. Those skips are not a browser-verification pass; the exact test command was rerun with approved execution outside the sandbox.
- No build or borrowed dependency links are needed for this renderer/static-asset task.

## Manual print-preview follow-up — not performed

1. In an owner-provided disposable fake-data app session, open the printable summary for empty, single-site and many-site cases matching the matrix above. Use only fake profiles and leave real submissions disabled.
2. Open the browser's Print command. Select portrait A4, 100% scale, then US Letter; retain the app's 1.5cm page margins. Record browser/version, printer destination and any overrides rather than assuming they match the automated model.
3. Confirm navigation and print/back controls disappear; counts remain readable and distinct; long labels/site names and date columns remain visible.
4. For the many-site case, inspect each actual page boundary for split rows, stranded headings, clipped last rows, repeated column headings and excessive blank pages. Record failures with screenshots using the owner's approved artifact location.
5. Cancel printing. This verifies only the actual preview/browser/settings inspected; it does not establish PDF support or outcomes for other printers.
