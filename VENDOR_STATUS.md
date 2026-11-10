# WO-350

Tracker: WO-350 (freemyid-pm#270).

## Done
- New pure helper `src/freemyid/scheduler/pathcheck.py`. `check_path(argv, os_name)` checks the program and its arguments for `linux`, `macos`, or `windows`. It does not read this machine's OS, the file system, or a process.
- `problems` is a list of `{code, index}`. An empty list means safe to schedule. Codes only: `unknown_os`, `empty_command`, `empty_program`, `not_text`, `nul`, `newline`, `control`, `invalid_char`, `cron_backslash_percent`. A problem does not contain the path.
- `quoted` is the command text when that OS has one. Windows: one CreateProcess command line (CommandLineToArgvW rules), so a trailing backslash inside quotes is doubled and does not eat the closing quote. Linux: systemd `ExecStart` words (`%` doubled; quotes and backslashes escaped). `cron_quoted` is the crontab command (shell quoting, then `\%`, because cron rewrites `%` before the shell and quotes do not stop it). Both Linux strings are set only when `problems` is empty, because install may use either scheduler. macOS: `quoted` is None. launchd stores an argument array, so no shell line exists. An empty problem list still means safe.
- The table covers each OS with a space, an apostrophe, non-ASCII (`café`), a trailing backslash, a percent sign, `$`, and an embedded quote. Every path is Jane Q Testperson of Springfield IL.
- On Linux, an odd run of backslashes immediately before `%` is `cron_backslash_percent` and is not quoted. Crontab cannot hand that sequence to the shell as one field. The same bytes round-trip on Windows and macOS.
- Not wired into schedule install. `scheduler/__init__.py` and `scheduler/render.py` were not edited. No contract change.

## Next
In-house review. A later work order can call this helper from install.

## Questions for the owner
- Keep the Linux refusal for an odd run of backslashes before `%`, instead of a `$(printf ...)` field, when this is wired in?
- Windows `quoted` is one command line. `windows_task_xml` stores the program and the arguments separately. Should the wiring work order keep this single line, or also return those two fields?
- macOS returns no quoted string. Should `quoted` stay None, or be the XML-escaped `ProgramArguments` text?

Tracker: WO-350 (freemyid-pm#270).

## How to test
From this worktree (`.vendor-wt/wo-350`):

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_scheduler_pathcheck.py
```
29 passed in 0.19s

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "pathcheck"
```
29 passed, 2699 deselected, 1 warning in 2.37s

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```
2517 passed, 206 skipped, 5 xfailed, 1 warning in 312.94s (0:05:12). Exit 0. The 5 xfailed are pre-existing. No existing test failed because of this change.

Skips are not passes. `web/dist` is missing: `pytest -m web_dist` reported 184 skipped (built website not found), including 3 browser-marked tests. Those 3 did not run. 2 more skips are Windows-only (`tests/test_scheduler_ci.py:24` and `:41`; the second is also `real_scheduler`). That leaves 20 other skips, not from this change (this file's 29 tests all passed). Browser tests that do not need `web/dist` did run: `pytest -m "browser and not web_dist"` reported 38 passed in 33.06s. Chromium launched. They sit inside the 2517, not in the skip count.

```
../../.venv/bin/ruff check tests/grok src/freemyid/scheduler/pathcheck.py
```
All checks passed!

```
../../.venv/bin/mypy src/freemyid/scheduler/pathcheck.py
```
Success: no issues found in 1 source file
