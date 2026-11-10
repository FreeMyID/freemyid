# WO-307 status

Vendor: Linda Moreau. Worktree: `.vendor-wt/wo-307`. Docs only.

## Done

Extended `docs/user/HELPING.md` for a helper sitting with someone (example: Jane Q Testperson, Springfield IL):

- Sit together. Open the page first (**Open the page**), then **Yes, this is me** or **No, this is not me**, and what each does.
- The first answer stays. A second press says the question was already answered.
- Practice mode still searches. No removal requests go out until the person says so.
- How to update: the new installer keeps details and the scheduled check. The app may need to be opened again.
- The required wait sentence is used exactly: "The first time can take up to a minute. Please wait; there is no need to click it again."
- `src/freemyid` lines are cited in HTML comments. The starting box is cited in words (splash_win.py, line 20, and line 23), not as a `packaging/windows/splash_win.py:20` citation.

No files under `src/`, `web/`, or `docs/vendor/` were edited. No new test was added (existing doc, wording, and citation guards already cover this page).

## Next

Owner review of `docs/user/HELPING.md`. No further edits are planned in this work order.

## Questions for the owner

- Please confirm on a Windows PC that running the new installer over an old one keeps the saved details and the daily check, and that the app is closed and may need to be opened again. This session only read the installer script.
- `docs/USER_GUIDE.md:177` and `docs/HELPER_GUIDE.md:62` still say practice mode sends nothing. Those files are outside this work order. Should a later order fix them?
- The queued-WO note on `docs/vendor/GROK_BOARD.md` was not written. This order allows only `docs/user/HELPING.md` and `VENDOR_STATUS.md`.

## How to test

From this worktree:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot tests -k "doc or wording or helping"`

Exact result: **620 passed, 17 skipped, 2102 deselected, 1 xfailed**, 1 warning, about 6s.

The xfail is pre-existing and not from this order: `tests/copilot/test_cp_never_asks_parity.py::test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]` (strict; `docs/FRIDGE_CARD.md:17` missing "never charges you").

Skips: 14 because `web/dist/index.html` is not built; 3 because `tests/copilot/test_cp_never_asks_parity.py` looks for `docs/FAMILY_QUICK_START.md` and that path is not in the tree (the quick start file is at the repo root). Not introduced here.

## Findings

- `src/freemyid/wizard/dashboard.py:510-511`: the Settings card says practice mode "does not send any request" while the app still searches. The Today banner at `src/freemyid/wizard/dashboard.py:237-238` is the line the guide quotes ("no removal requests go out until you say so"). `src/` was not edited. `tests/codex/test_cx_app_practice_wording.py` does not flag "any request", so no new xfail was added.
- `docs/USER_GUIDE.md:177`: "While practice mode is on, nothing is actually sent." That fights the practice-mode rule. Not edited (outside this order).
- `docs/HELPER_GUIDE.md:62`: "it looks for listings but sends nothing." Same issue. Not edited.
- `src/freemyid/paths.py:10` docstring says `%APPDATA%\Free My ID`. The code at `src/freemyid/paths.py:14` uses `FreeMyID`, and the installer data folder does too. The guide does not name the folder.
- The spoken wait sentence is not one string in the starting box. splash_win.py, line 20, says the first time can take up to a minute. splash_win.py, line 23, says please wait; there is no need to click it again. The guide uses the required combined sentence and points at both lines in words.

## Could not verify

- Did not run the Windows installer, the splash window, or an upgrade over an existing install. Keeping details and the scheduled check is from the script: saved details live outside the program folder (`src/freemyid/paths.py:13-16`); `schedule remove` runs on uninstall, not when new program files are copied (`packaging/windows/freemyid.iss`, uninstall step). CloseApplications can close a running copy, so the app may need to be opened again.
- Did not open the Today screen in a browser. Button labels and flash text were read from `src/freemyid/wizard/dashboard.py` and `src/freemyid/wizard/server.py`.
- Did not build `web/dist`, so the 14 website skips above were not run.
- Did not run `freemyid run`, `send`, or `schedule install`.
