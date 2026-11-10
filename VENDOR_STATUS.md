# WO-333 — one calm notification summary, sturdier monthly marker

## Done
- `ThrottledNotifier` in `src/freemyid/notify.py`. The first notice in a run is delivered as sent. Later notices are counted while that run is still open, and any notice within 10 minutes of the first one that went out is counted too (every wrapper in the process shares that window). `flush()` sends one closing summary and closes the run. Four held notices become the title `Free My ID: 4 things need you` and the body `4 things need you. Open Free My ID to see them.` One held notice uses `1 thing needs you`. The summary is the count only: no site names, no links, no personal details. A second `flush()` sends nothing.
- `handoff.get_notifier` returns that wrapper around `notify.get_notifier()`. Existing `.notify(...)` call sites do not need to change. `notify.get_notifier()` itself stays unwrapped so the monthly toast is not rewritten as a "things need you" summary.
- `maybe_monthly_progress` catches a missing or unwritable home folder (including `paths.home()` raising `OSError`), logs the exception type only, and returns False. Nothing is sent. The marker is written by a temp file in the same folder, then `os.replace`. If replace fails, the old marker is left as it was and no toast goes out.
- `tests/test_notify_monthly.py` was not edited. No contract file was changed.

## Next
- In-house needs a small `runner.py` change, which this work order does not allow. Until `flush()` is called, notices after the first are counted and then dropped when the process exits. They are not shown.
- Call it on the same object the run already holds, after `_finish`, including when there is nothing left open (an interactive run can notify per to-do and then have `n == 0`). `Runner.run` (`src/freemyid/engine/runner.py`, `_finish` is called just before the return, around line 379):

```python
self._finish(profiles)
notifier = self.notifier
flush = getattr(notifier, "flush", None)
if callable(flush):
    try:
        flush()
    except Exception as exc:  # a toast must not fail the run
        log.info("notification summary failed: %s", type(exc).__name__)
return self.report
```

- Do not call `_notifier()` just to flush. That builds a desktop notifier when the run never notified. `self.notifier` is already set when `get_notifier()` was used.
- Scheduled runs are unchanged until that call exists. `_handoff` passes `NullNotifier()` when the run is not interactive (`runner.py` lines 347-351), so per-to-do pops are already silenced. The one end-of-run notice from `_finish` (line 985) is the first notice on the throttled notifier and still goes out. `flush()` then has nothing held.
- On an interactive run, handoff uses the throttled notifier. The first to-do notice still goes out. `_finish`'s "Free My ID needs 5 minutes of your help" is counted with the later to-do notices if any notice already went out, and the closing text becomes the summary above once `flush()` is wired.

## Questions for the owner
- The summary counts only notices that were held back, not the one already shown. Say if the number should include that first notice.
- Singular copy is "Free My ID: 1 thing needs you". Say if you want different words.
- The work order's burst is described as a scheduled run. In this tree a scheduled run does not notify per to-do; it uses `NullNotifier` and one `_finish` notice. The wrapper still coalesces interactive runs (and any other caller of `handoff.get_notifier`). No `runner.py` edit was made. Say if scheduled handoff should use the real notifier too.
- Tracker: WO-333 (freemyid-pm#253). `docs/vendor/GROK_TO_CLAUDE.md` and `GROK_BOARD.md` were not edited from this worktree.

## How to test
From this worktree. No failures. The Starlette warning is the existing FastAPI test client deprecation, not this change.

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_notify_throttle.py` — 15 passed in 0.19s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/test_notify_monthly.py` — 3 passed in 0.16s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "notify or handoff"` — 20 passed, 2682 deselected, 1 warning in 4.05s.
- `../../.venv/bin/ruff check src/freemyid/notify.py src/freemyid/engine/handoff.py tests/grok` — All checks passed.
- `../../.venv/bin/mypy src/freemyid/notify.py src/freemyid/engine/handoff.py` — Success: no issues found in 2 source files.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2494 passed, 206 skipped, 2 xfailed, 1 warning in 325.78s. No failures. The 2 xfailed are pre-existing strict xfails, not this change.

## Findings
- No contract change. `Notifier` only requires `notify`; `flush` is an extra method on the wrapper.
- Pre-existing long line, not introduced here: `src/freemyid/notify.py:26` is 103 characters (icon path). Ruff did not flag it.
- No test outside the allowed paths was edited. Nothing failed.
