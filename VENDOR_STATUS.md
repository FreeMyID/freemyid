# WO-002 status

## Done

- Exposure scans reuse `Runner._review_todo` after merging saved listings, following
  scan's possible-without-confirmed rule. The shared helper deduplicates open reviews.
- Added fake-page tests for immediate reviews, cached and refreshed re-scans, confirmed
  matches, check-by-hand sites, practice mode, consent refusal, and earlier review answers.
- Documented `checklists/1` and `checklist/1` fields in docs/CLI.md and the new review
  behavior in docs/EXPOSURE.md.
- Ruff passed for both changed Python files. All 7 new tests passed.
- Combined exposure test run: 16 passed, 3 failed because this sandbox forbids opening
  the loopback socket needed by the existing fixture-server tests. Those failures occur
  before the exposure scan runs. Two further review-answer tests were added and passed
  after that combined run.

## Next

- Owner runs the full exposure tests in an environment permitting the local fixture server.
- In-house review and acceptance.

## Questions for the owner

- None. Full test acceptance awaits the local fixture-server run outside this sandbox.

## How to test

```sh
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_exposure.py tests/test_exposure_todos.py
/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check src/freemyid/engine/exposure.py tests/test_exposure_todos.py
```
