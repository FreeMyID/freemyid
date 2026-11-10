# WO-343 (freemyid-pm#263)

## Done
- Added `request_deadline` in `src/freemyid/engine/runner.py`. It says when one sent removal request is overdue. A standard state-law request is due 45 calendar days after the send date. A stated shorter deadline (a verified response window under 45 days) is due in 15. Days the broker claimed as an extension are added. No sent date is never overdue. The count is calendar dates, so a leap day or a DST change does not move the due day.
- `_escalate` uses that helper for the legal-demand wait, the complaint hand-off, and whether a follow-up is only a reminder. A verified window longer than 45 days (Iowa is 90) still has to finish. No new state or schema field.
- Tracker: WO-343 (freemyid-pm#263).

## Next
In-house review. Nothing in this work order is left open. WO-355 can call `request_deadline` from `handoff.py`. This session did not edit `GROK_BOARD.md` or `GROK_TO_CLAUDE.md`; those files were not in the allowed paths.

## Questions for the owner
A verified response window under 45 days is counted as 15 calendar days, not the raw number. No state in the deletion matrix is in that range today (the windows on file are 45 or 90). A longer verified window still waits out its own date. Say if a 30-day statute should keep 30 instead. Tracker: WO-343 (freemyid-pm#263).

## How to test
From this worktree (`.vendor-wt/wo-343`):

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_runner_escalation_due.py
```
25 passed in 0.25s

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "runner"
```
48 passed, 2676 deselected, 1 warning in 13.17s. The warning is the existing StarletteDeprecationWarning from FastAPI's test client. No failure.

```
../../.venv/bin/ruff check tests/grok src/freemyid/engine/runner.py
```
All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/runner.py tests/grok/test_gk_runner_escalation_due.py
```
Success: no issues found in 2 source files.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```
2513 passed, 206 skipped, 5 xfailed, 1 warning in 324.99s (0:05:24). 0 failed. The 5 xfailed marks were already in the suite; this work order adds none. The 206 skips include browser tests and tests that need `web/dist` or a real scheduler. Those skips are not passes. The same StarletteDeprecationWarning as above.

## Findings
None in the allowed paths. Browser tests were not executed in this sandbox.
