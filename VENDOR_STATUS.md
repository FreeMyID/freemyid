# WO-349 — a missing notifier stays quiet

## Done
- `notify.py` was copied from the delivered WO-333 worktree (`.vendor-wt/wo-333/src/freemyid/notify.py`) because rebase is not available. Nothing else was copied. `handoff.py` was not changed. The WO-333 throttle and the monthly marker rules are unchanged: the first notice in a run goes out as sent, later notices in that run or within 10 minutes become one count-only summary, and `maybe_monthly_progress` still survives a missing or unwritable home folder.
- On top of that copy, an OS notice is a quiet no-op when the platform tool is missing, and one non-zero exit or runner error disables further OS notices for the rest of the process. Linux looks up `notify-send`, macOS `osascript`, Windows `powershell`. There is no retry loop. Title and body that contain a link or an email are not passed to the tool. The optional `url` argument is not passed either. Output from the tool is captured, so a failure does not print a traceback.
- `desktop-notifier` is no longer called. Its Linux backend logged a warning with a traceback when no notifier was there. The shell path does not.
- No contract file was changed. `Notifier.notify` still returns nothing. The bool result is internal (`_deliver_os_notice`).

## Next
- In-house review of this worktree. Nothing here should merge until that review.
- If this shell path is kept, in-house can drop the unused `desktop-notifier` dependency from `pyproject.toml`. This work order cannot edit that file.
- WO-333's `flush()` still needs the small `runner.py` call described in that work order's status. This branch's `handoff.get_notifier` does not wrap `ThrottledNotifier`.

## Questions for the owner
- A missing executable is checked again on the next notice. It does not latch. A non-zero exit or a runner error does latch for the process. Say if a missing tool should latch too.
- Linux without `notify-send` stays quiet even when a D-Bus notification daemon is up, because `desktop-notifier` is no longer called. Say if that trade is wrong.
- macOS permission and Windows toasts-off were not run on those systems. If `osascript` exits 0 and shows nothing, each later notice tries once. It does not loop. Say if a denied permission that exits 0 should latch.
- A direct `notify()` still sends the caller's title and body when they have no link and no email. That is the WO-333 rule: the first notice goes out as sent, and held notices become the count summary. Say if a direct notice must also be refused when it contains a name or a city.
- Tracker: WO-349 (freemyid-pm#269). `docs/vendor/GROK_TO_CLAUDE.md` and `GROK_BOARD.md` were not edited from this worktree.

## How to test
From this worktree. No failures in the commands below. The Starlette warning is the existing FastAPI test client deprecation, not this change. The 206 skipped tests are not passes. Browser tests skipped in this sandbox are in that count. This change added no skips. The 5 xfailed are pre-existing strict xfails (this change added none). The suite exited 0.

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_notify_missing_backend.py` — 19 passed in 0.14s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "notify"` — 22 passed, 2696 deselected, 1 warning in 2.35s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2507 passed, 206 skipped, 5 xfailed, 1 warning in 338.71s (0:05:38).
- `../../.venv/bin/ruff check tests/grok src/freemyid/notify.py` — All checks passed.
- `../../.venv/bin/mypy src/freemyid/notify.py` — Success: no issues found in 1 source file.

Read-only check of the delivered WO-333 throttle file, with `--noconftest` and this worktree's fixtures (`PYTHONPATH=$PWD/src:$PWD`, `-p tests.conftest`). That file was not modified. 14 passed, 1 failed. The failure is not from this change: `../wo-333/tests/grok/test_gk_notify_throttle.py:188` expects `handoff.get_notifier()` to return `ThrottledNotifier`, and this branch's `src/freemyid/engine/handoff.py:41` returns `notify.get_notifier()` unwrapped. `handoff.py` was not copied, as this work order required. The other 14 tests, including the throttle text and the monthly marker, passed.
