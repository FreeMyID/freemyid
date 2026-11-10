# VENDOR_STATUS

WO-311 (issue pending). Agent: Simon Fairley, user-guide writer. Status: delivered.

## Done

Created `docs/user/whats-new-0.3.md` (61 lines). It is for someone who used 0.2 or is new, and it describes only the released 0.3.1 app.

Covered, each with a citation: Today one card then "More: safety steps and details"; "Is this you?" with "Yes, this is me" and "No, this is not me"; "Protect yourself"; Google and Bing steps; "Larger text"; printable summary and "Print this page"; the first-start sentence; updating with the new installer; practice mode on at the start; no account and nothing to pay.

Update words match the delivered WO-301 install page: the new installer keeps the person's details and the scheduled check, it is an upgrade not a second app, and the app may need reopening. Example person: Jane Q Testperson, Springfield IL. No proof vault, PDF report, Outlook sign-in, or tray icon. No "guarantee", "erase", "100%", or "nothing is sent". No GitHub link and no web address. No link to another new help page in this batch.

`docs/pm/issue_map.json` has no WO-311 key, so the issue is still pending. `docs/vendor/GROK_TO_CLAUDE.md` and `GROK_BOARD.md` were not edited. Those paths are outside the two files this work order allows.

## Next

WO-330 should link this page. In-house merges this work order and WO-330 together before pushing. After that link exists, `test_user_page_is_reachable[whats-new-0.3.md]` should pass.

The liaison can then add the GROK-NNN check-in and the board note. This work order could not write those files.

## Questions for the owner

The required first-start sentence joins two splash strings. Line 20 says the first time can take up to a minute. "Please wait; there is no need to click it again" is the text after two minutes (splash_win.py, line 23). The page uses the combined sentence because this work order and the delivered WO-301 install page both require it. Say if you want those two moments split.

The person page has "Download report" (`src/freemyid/wizard/dashboard.py:377`). The wizard route builds HTML, not a PDF (`src/freemyid/wizard/server.py:735`). The roadmap lists the PDF report as 0.4, so this page does not mention the button. Say if a later page should explain the HTML download.

This worktree's `docs/user/INSTALL.md` still describes version 0.2.0, so this page does not link to it. After WO-301 is on main, should this page point at that updating section?

## How to test

From `.vendor-wt/wo-311`:

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

   Result: 324 passed, exit 0.

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

   Result: 1 failed, 9 passed, exit 1. The only failure is `test_user_page_is_reachable[whats-new-0.3.md]`.

3. `tests/grok/` is not in this worktree, so that check was not run.

## Findings

- Expected, by design: `docs/user/whats-new-0.3.md` is not linked from `INSTALL.md` or `GLOSSARY.md`. WO-330 adds that link. No other reachable-page failure.
- The work order cites `dashboard.py:122-123` for the "Is this you?" card. The buttons "Yes, this is me" and "No, this is not me" are on those lines. The words "Is this you?" are on `src/freemyid/wizard/dashboard.py:113`. The page cites 113 for that phrase.
- On the Yes card, "In practice mode" is `src/freemyid/wizard/dashboard.py:130` and "no removal requests go out" is line 131. The page quotes the line 131 phrase. The start-of-app banner is still `dashboard.py:237` ("Practice mode") and line 238 ("no removal requests go out until you say so"). The default is `src/freemyid/config.py:30` (`real_submissions_enabled` is false).
- "nothing to pay" is not a label. The screen says "No account" (`src/freemyid/wizard/ui.py:266`) and "Free and open source" (`ui.py:267`).
- Not described, and not called available: proof vault, PDF report, Outlook sign-in, tray icon. `tray_enabled` defaults to false at `src/freemyid/config.py:31`.
- No product bug was edited in `src/`. The citation corrections above are documentation, not a code defect.

## What could not be verified

- The app was not started, and the Windows installer was not run. Update and first-start claims are from `packaging/windows/splash_win.py`, `packaging/windows/freemyid.iss`, `docs/RELEASE_v0.3.md` line 20, and the delivered WO-301 install page.
- `tests/grok/` does not exist here.
- PyPI, the live download, and GitHub were not checked. This work order forbids network, git, and gh.
- The board and the owner channel were not updated, because those files are not in the allowed paths.
