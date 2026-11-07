# WO-006 — Hannah Cole (test-quality)

## Done

- Added 48 deterministic renderer regression cases in
  `tests/test_wizard_summary_regressions.py`: all listing states, separate counts
  and wording, internal-ID exclusions, empty/singular/plural results, ordering,
  date selection, repeatability, personal-information limits, hostile text, and
  print/table HTML semantics.
- Added coverage matrix and reproducible fake-data manual print-preview steps in
  `docs/vendor/WO-006-test-notes.md`. Manual preview has not been performed; no
  PDF support claim.
- New tests: **48 passed, 0 failed, 0 expected failures**. Existing internal-ID
  summary regression: **1 passed**. Changed Python file is typed and Ruff-clean.
- Product code, existing tests, and shared fixtures are unchanged.

## Next

- Owner reruns the existing v0.3 HTTP summary test outside this sandbox and
  performs the documented manual browser print-preview check.
- In-house review of the three allowed files.

## Questions for the owner

- The existing `test_summary_is_printable_and_pii_light` stalls in this sandbox;
  a separate 15-second bounded run exited 124 without a result. Please confirm its
  result in the normal test environment. This is an incomplete verification,
  not a confirmed product bug. No product defects or strict xfails were added.
- Internal-ID tests cover status-derived counts and rows. Request and person-step
  totals are supplied to the renderer; their upstream calculation is outside
  these direct renderer tests.

## How to test

```sh
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_wizard_summary_regressions.py tests/test_wizard_v03.py::test_summary_is_printable_and_pii_light tests/test_wizard_protect_tips.py::test_summary_page_skips_internal_ids
/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_wizard_summary_regressions.py
```

See `docs/vendor/WO-006-test-notes.md` for individual test commands, the coverage
matrix, sandbox limitation, and manual preview instructions using only fake data.
