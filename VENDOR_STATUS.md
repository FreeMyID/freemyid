# WO-334 (issue pending)

## Done
- Cron: `render.cron_lines` takes the same environment dict as systemd and launchd (`ENV_PASSTHROUGH` via `_job_env`) and puts a safely quoted `NAME=value` on both the daily line and the `@reboot` line. `install()` passes that env, so a custom `FREEMYID_HOME` is what the cron job uses.
- macOS: `launchd_plist` sets `RunAtLoad` true. The install message says, in plain words, that a check missed while the Mac was switched off runs at the next login. The job still runs with `--scheduled`, so a login run only checks sites that are due.
- Windows: `windows_task_xml` settings are unchanged. A test pins `StartWhenAvailable` true and `DisallowStartIfOnBatteries` false.
- Values with spaces, quotes, `%`, and `$` round-trip for cron, systemd, and launchd. Tests render Linux, macOS, and Windows on this machine (`tmp_path`, `pathlib`, no hard-coded `/tmp`).

## Finding
A custom `FREEMYID_HOME` does not reach a Windows task without a CLI change. `windows_task_xml` has no environment block (only `Command` and `Arguments` on the Exec action). `install()` writes that XML and does not pass `_job_env()`. `paths.home()` (`src/freemyid/paths.py`) reads `FREEMYID_HOME` from the process environment, and `cli.py` has no flag for another data folder. The scheduled task therefore sees only the Windows account's stored environment, not a value that existed only in the install command. `cli.py` is in-house, so it was not edited. Linux cron and macOS launchd do receive `FREEMYID_HOME` and `FREEMYID_PASSPHRASE_FILE`.

## Next
In-house review. Nothing left in this work order unless the owner wants the Windows home gap fixed in `cli.py`.

## Questions for the owner
Should a custom `FREEMYID_HOME` on Windows be a CLI flag (in-house), or is the account's stored environment enough? This work order did not change `cli.py`. Tracker: WO-334 (freemyid-pm#254).

## How to test
From this worktree (`.vendor-wt/wo-334`):

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_scheduler_catchup.py
```
9 passed in 0.16s

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/test_scheduler_render.py tests/test_scheduler_ci.py tests/test_scheduler_real.py
```
14 passed, 2 skipped in 0.22s (the 2 skips are Windows-only / real-scheduler tests; they were not edited)

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```
2488 passed, 206 skipped, 2 xfailed, 1 warning in 326.55s (0:05:26). 0 failed.

```
../../.venv/bin/ruff check src/freemyid/scheduler/render.py src/freemyid/scheduler/__init__.py tests/grok
```
All checks passed!

```
../../.venv/bin/mypy src/freemyid/scheduler/render.py src/freemyid/scheduler/__init__.py
```
Success: no issues found in 2 source files
