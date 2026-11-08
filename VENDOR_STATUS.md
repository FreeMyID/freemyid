# WO-168

## Done
- Added a source-level parity guard using `web/src/pages/safety/index.astro` as the master list.
- Checks each named, existing hand-written copy for Social Security number, bank or card details, and the no-charge promise.
- Rejects bare `passwords` in a never-asks sentence unless it is an app-password or email-password context.
- Reports and skips the missing `docs/FAMILY_QUICK_START.md`.

## Next
- Update the fridge card's never-asks sentence to include “never charges you”, then remove its strict xfail.

## Questions for the owner
- The work order names `docs/FAMILY_QUICK_START.md`, but the repository currently has `FAMILY_QUICK_START.md` at the root. Should the named path be restored, or should the work order move the guard to the root file?

## How to test
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/copilot/` — unverified:
  `.venv/bin/python` is not present in this worktree.
- `.venv/bin/ruff check tests/copilot` — unverified: `.venv/bin/ruff` is not present
  in this worktree.
- `PYTHONPATH=src python3 -m pytest -q tests/copilot/test_cp_never_asks_parity.py`
  — passed: 14 passed, 2 skipped, 1 xfailed.
- `python3 -m ruff check tests/copilot` — passed.
- `git diff --check` — passed.
