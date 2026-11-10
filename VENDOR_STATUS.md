# WO-323 (issue pending)

Source-citation guard for `docs/USER_GUIDE.md`, `docs/CLI.md`, and `FAMILY_QUICK_START.md`.

## Done

- Added `tests/grok/test_gk_root_doc_citations.py`. It names `tests/copilot/test_cp_source_citations.py` as the reference and covers the three root user docs that guard skips.
- Also checked, and did not copy: `tests/codex/test_cx_dev_source_citations.py` (`docs/dev/`, `docs/i18n/`) and `tests/codex/test_cx_dev_broker_citations.py` (`docs/dev/CONTRIBUTING_BROKERS.md`). `tests/grok/` had no citation guard.
- Same rule as the reference: each `file.py:NNN` citation must resolve to one file under `src/freemyid/`, line NNN must exist, and quoted text on that line must appear in the file. Adjacent Python string literals count; separate statements do not. A path outside `src/freemyid/`, including `packaging/windows/splash_win.py:N`, does not pass.
- A document with no citations passes. `docs/USER_GUIDE.md` and `FAMILY_QUICK_START.md` have none today. `docs/CLI.md` already has 26 (the work order text said none of the three had any yet).
- Fake trees under `tmp_path`: a missing file, a line past the end, an ambiguous file name, and quoted text that is not in the source each fail. A good citation, a full `src/freemyid/...` path, adjacent string literals, and a file with no citations pass.
- Six quote mismatches in `docs/CLI.md` are strict `xfail`s. This work order may not edit that file. No `tests/grok/__init__.py` and no `conftest.py`.

## Next

None in this worktree. Quote and line fixes in `docs/CLI.md` belong to WO-303. When WO-302 and WO-306 add citations, this guard checks them. Channel note and board update are outside the allowed paths.

## Questions

The reference test only requires the start line to exist, and it searches quoted text in the whole file. Several `docs/CLI.md` lines below still exist, so this guard does not fail them, but the line is not the statement the sentence describes. Should WO-303 retarget those lines, or should a later guard fail that case?

## How to test

From the worktree root:

```bash
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_root_doc_citations.py
../../.venv/bin/ruff check tests/grok/test_gk_root_doc_citations.py
```

Pytest: 56 passed, 6 xfailed, 0 failed, 0 skipped (`56 passed, 6 xfailed in 0.81s`).
Ruff: all checks passed (also `../../.venv/bin/ruff check tests/grok`).

Strict xfails, one by one:

1. `test_quoted_ui_text_exists_in_cited_source[docs/CLI.md:83->cli.py:168]` — docs/CLI.md:83 quotes `--web --prefill`, which is not text in src/freemyid/cli.py
2. `test_quoted_ui_text_exists_in_cited_source[docs/CLI.md:85->cli.py:520]` — docs/CLI.md:85 quotes `profile add [--prefill]`, which is not text in src/freemyid/cli.py; cli.py:520 is inside report(), not profile add
3. `test_quoted_ui_text_exists_in_cited_source[docs/CLI.md:93->cli.py:761]` — docs/CLI.md:93 quotes `-p/--profile`, which is not text in src/freemyid/cli.py
4. `test_quoted_ui_text_exists_in_cited_source[docs/CLI.md:93->cli.py:799]` — docs/CLI.md:93 quotes `-p/--profile`, which is not text in src/freemyid/cli.py
5. `test_quoted_ui_text_exists_in_cited_source[docs/CLI.md:94->cli.py:181]` — docs/CLI.md:94 quotes `doctor --offline`, which is not text in src/freemyid/cli.py
6. `test_quoted_ui_text_exists_in_cited_source[docs/CLI.md:94->src/freemyid/doctor.py:56]` — docs/CLI.md:94 quotes `doctor --offline`, which is not text in src/freemyid/doctor.py

Limits: ran on Linux only. The test uses `tmp_path` and `pathlib` (no hard-coded temp paths, no network, no subprocess, no git). Not a Windows run. Like the reference test, a range's end line is not checked, and quoted text is searched in the whole file, not only on the cited line. Passing that rule is not a check that the sentence matches the code.

Changed files: `tests/grok/test_gk_root_doc_citations.py`, `VENDOR_STATUS.md`.

## Findings

### Strict xfail (quote text is not in the cited file)

- `docs/CLI.md:83` cites `cli.py:168`. The line also quotes `` `--web --prefill` ``. That phrase is not in `src/freemyid/cli.py`. `--web` is in the message at `src/freemyid/cli.py:165`, and `--prefill` is in the help text at `src/freemyid/cli.py:151`. `/wizard/import` is at `src/freemyid/cli.py:166`. Lines 168-169 are `web = prefill is None`, which matches the other claim on that doc line.
- `docs/CLI.md:85` cites `cli.py:520-522` for `` `profile add [--prefill]` ``. That phrase is not in `src/freemyid/cli.py`. `src/freemyid/cli.py:520` is inside `report()` (`raise typer.BadParameter("--format must be html or pdf")`). `profile add` is `src/freemyid/cli.py:536-538`.
- `docs/CLI.md:93` cites `cli.py:761-762` and `cli.py:799-872` and quotes `` `-p/--profile` ``. That phrase is not in `src/freemyid/cli.py`. The option is two literals at `src/freemyid/cli.py:778-779` (`"--profile"`, `"-p"`). `src/freemyid/cli.py:761-762` are blank lines before `outbox_approve` (`src/freemyid/cli.py:764`). The checklist group starts at `src/freemyid/cli.py:775`. `src/freemyid/cli.py:799` is inside `_checklist_profile`. Checklist commands start at `src/freemyid/cli.py:815`.
- `docs/CLI.md:94` cites `cli.py:181` and `src/freemyid/doctor.py:56-62` and quotes `` `doctor --offline` ``. That phrase is not in either file. `src/freemyid/cli.py:181` is the separate literal `"--offline"`. `src/freemyid/doctor.py:56-62` is the Python version check and does contain "Python 3.12 or newer".

### Read while checking; this guard does not fail them

The start line exists, and any quotes on the line occur somewhere in the file. The line is still the wrong statement:

- `docs/CLI.md:25` `cli.py:578` is `store.delete_profile` inside `profile_remove`. `wipe` starts at `src/freemyid/cli.py:581`.
- `docs/CLI.md:86` `cli.py:879` is `@checklist_app.command("done")`. The words `open`, `done`, `undo` are `_SE_ACTIONS` at `src/freemyid/cli.py:895`.
- `docs/CLI.md:86` `cli.py:887` is `checklist_undo`. `search_engines` starts at `src/freemyid/cli.py:903`.
- `docs/CLI.md:87` `cli.py:901-905` is blank lines and the `search_engines` signature. The exit-2 branches are `src/freemyid/cli.py:916-921`.
- `docs/CLI.md:88` `cli.py:917` and `cli.py:922` are `EXIT_USAGE` (exit 2). Could not open is `src/freemyid/cli.py:933`. Could not record is `src/freemyid/cli.py:938`.
- `docs/CLI.md:89` `cli.py:932` is the open-step branch. Listing when there is no word starts at `src/freemyid/cli.py:948`.
- `docs/CLI.md:91` `cli.py:328` is inside `_do_run` (the `scan` command is `src/freemyid/cli.py:335`, and the cited range does include it). `cli.py:402` is the end of `status`, not `run` (`run` is `src/freemyid/cli.py:346`).
- `docs/CLI.md:92` `cli.py:372` is inside `fill`, not `exposure` (`exposure` is `src/freemyid/cli.py:409`). `cli.py:497` is inside `_search_engine_footer`, not `status` (`status` is `src/freemyid/cli.py:379`). `cli.py:566` is `@profile_app.command("remove")`, not `report` or `wipe` (`report` is `src/freemyid/cli.py:512`, `wipe` is `src/freemyid/cli.py:581`).
- `docs/CLI.md:351` `monitor.py:197` is the `BrokerHealth` dataclass. `new_brokers` and `removed_brokers` are set at `src/freemyid/monitor.py:383-384`. `monitor.py:358` is the broker loop in the check runner.

No `packaging/windows/splash_win.py:N` citation is in the three files. `docs/USER_GUIDE.md` and `FAMILY_QUICK_START.md` have no `file.py:NNN` citations.
