# WO-248 (issue pending) — First-run browser checks

## Done
- Added `tests/codex/test_cx_firstrun_browser.py` after searching existing `tests/`
  for direct first-run browser guards; none were found.
- Acceptance checklist:
  - [x] Each Windows browser installation path is detected with all filesystem checks faked.
  - [x] A search-path browser takes priority; later search-path candidates are checked;
    no available browser returns `None`.
  - [x] An existing browser avoids both the question and installation.
  - [x] Blank, negative, whitespace and other answers without a leading `y` decline.
  - [x] `y`, `Y` and ` yes ` each invoke the fake runner once with `check=True`.
  - [x] Installation command uses the current Python executable and selects Chromium only.
  - [x] The question explains download size and avoids the explicit banned claims.
- Detection and installation are faked throughout. An autouse guard rejects any real
  subprocess launch. Synthetic executable paths use `tmp_path` and `pathlib`.
- Only the new test and this status file were written. Product code remains unchanged.
- No defect or strict xfail was needed; no real personal data, network or installation used.

## Next
- Ready for Owen Brooks's independent read-only review, followed by in-house review.
- Native Windows CI can run the same portable tests; this host run is not a native Windows run.

## Questions for the owner
- Tracker issue number is pending in-house sync.

## How to test
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_firstrun_browser.py`
  — **20 passed in 0.17s**, zero skipped or xfailed.
- `../../.venv/bin/ruff check tests/codex` — **all checks passed**.
