# WO-314 VENDOR_STATUS

Agent: Margaret Lund (plain-language editor)
Worktree: `.vendor-wt/wo-314`
Files changed: `docs/user/practice-mode.md`, `VENDOR_STATUS.md`

## Done

Wrote `docs/user/practice-mode.md`. It answers "Is it doing anything yet?" in the app's words.

Confirmed these labels are still in `src/freemyid/wizard/dashboard.py`, and quoted them with a same-line citation:

- "Practice mode:" at line 237
- "Practice mode is on" at line 510
- "Start sending real requests" at line 515
- "Start sending real requests?" at line 481
- "Yes, start sending real requests" at line 493
- "No, stay in practice mode" at line 494
- "Go back to practice mode" starts at line 519 (the words "practice mode" finish on line 520)

The page says practice mode looks for listings and shows them, and that a search still visits the sites. It says no removal request goes out on its own until the person turns real requests on. It quotes the first-email rule and "Requests already sent cannot be taken back." It has a "When to turn on real requests" part: after looking at the results, with someone you trust if they like.

Example person only: Jane Q Testperson, Springfield IL.

Links only to pages already in this worktree: `docs/user/troubleshooting.md` and `docs/user/GLOSSARY.md`. No other new help page is linked. `FAMILY_QUICK_START.md` was not edited.

## Next

WO-330 is the page that should link `docs/user/practice-mode.md`. In-house merges this WO and WO-330 together before pushing. Until then, the one reachable-test failure below is expected.

Board check-in (`docs/vendor/GROK_TO_CLAUDE.md`, `GROK_BOARD.md`) is outside this work order's allowed paths, so it was not done here.

## Questions

"Fill it in for me" can send one real request while practice mode is still on (`src/freemyid/wizard/dashboard.py:347-350`). The page says so, instead of claiming every removal request waits for the Settings switch. Say if that exception should come off this page.

## How to test

Command:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

Result: 344 passed, 0 failed, 0 skipped (1.34s).

Command:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

Result: 1 failed, 9 passed, 0 skipped (0.33s).

The one failure is `test_user_page_is_reachable[practice-mode.md]`: `docs/user/practice-mode.md` is not linked from `INSTALL.md` or `GLOSSARY.md` (one hop). That is the failure the work order expects. WO-330 adds the link. No other test in that file failed.

`tests/grok/` is not in this worktree, so `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok` was not run.

## Findings

- Work order line for the first-email sentence says `dashboard.py:487-488`. The sentence starts on line 486 (`The first`) and continues on line 487. Line 488 is the next sentence ("Some sites need steps by hand..."). The page cites line 486.
- "Go back to practice mode" is split across `dashboard.py:519` and `:520`. The citation test still sees the full label in the joined Python string. Not a product bug.
- "Fill it in for me" is a real request if the person presses Submit on the site, even while practice mode is on. The app already warns on `dashboard.py:347-350`. The help page repeats that warning. Not a new bug.
- `docs/user/troubleshooting.md` cites `src/freemyid/wizard/server.py:64` for "Please let a practice check finish first, then look at the results." That sentence is on `server.py:69` now. The citation test only checks that the line exists and that the quoted words are somewhere in the file, so the old citation still passes. Out of scope to edit. This page cites line 69.
