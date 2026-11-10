# VENDOR_STATUS — WO-319 (issue pending)

Plain-language editor. Docs only. `docs/pm/issue_map.json` has no WO-319 number.

## Done

- Added `docs/user/printable-checklist.md`: "Your first week with Free My ID" (7 items) and "Once a month" (5 items). Each item is one line, with `[ ]`, and each list has a blank Date line.
- Added a "Who to call for help" box with blank lines. No names and no phone numbers.
- Last line quotes the welcome-screen trust panel, not the guessed sentence (see Findings).
- Did not link this page from `INSTALL.md` or `GLOSSARY.md`. WO-330 is the page that should link it.

## Next

- In-house merges this with WO-330, which links the page, before push.
- No code change. `src/`, `web/`, and `docs/vendor/` were not edited.

## Questions

- The guessed last line is not in the app. The page quotes the trust panel at `src/freemyid/wizard/ui.py:266` instead. Is that the line you want kept?
- The update sentence joins two Windows splash strings (line 20 and line 23). Say if the printed line should be those two strings separately.
- Cards on screen are titled "Is this {name}?" (`src/freemyid/engine/runner.py:1000`), not the words "Is this you?". The checklist still uses "Is this you?" because that phrase is in `dashboard.py:113`. Say if the printed line should name the person instead.

## How to test

From `.vendor-wt/wo-319`:

```text
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py
```

Result: 286 passed.

```text
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py
```

Result: 1 failed, 9 passed. The only failure is `test_user_page_is_reachable[printable-checklist.md]`.

`tests/grok/` is not in this worktree, so that check was not run.

## Findings

- `draft.py:67-69` is right for the six step titles. Line 66 is only `STEP_TITLES = {`. Cited `src/freemyid/wizard/draft.py:67`.
- `dashboard.py:237` is right. The banner is "Practice mode:" plus "Free My ID is looking for your listings, but no removal requests go out until you say so."
- `dashboard.py:501` is wrong for "Run automatically". Line 501 is the Settings heading. The words "Run automatically" are on line 502. The button "Turn on" is on line 506. Cited line 502.
- `ui.py:43` is right for "Today" and "Protect yourself".
- `views.py:301` is right for "Print this page".
- `ui.py:266-267` does not contain "Free My ID never asks for your Social Security number or bank or card details." The trust panel (lines 266-268) reads: "No account. No cloud. Never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime." Nearby, not the same sentence: `dashboard.py:529` ("It will never ask for a Social Security number or bank or card details.") and `views.py:273` ("Free My ID never pays for you and never asks for your Social Security number.").
- "Yes, this is me" and "No, this is not me" are `dashboard.py:122-123`. "Is this you?" is a comment at `dashboard.py:113` (also `server.py:360` and `runner.py:991`). The card title a person sees is built at `runner.py:996` and `runner.py:1000`.
- "Look at them" is `dashboard.py:255`. "Approve and send" is `dashboard.py:473`. The outbox lead at `dashboard.py:254` was not copied.
- "What we did for you" is `dashboard.py:376`. It is not inside quotes on the print line, because that line cites `views.py:301`, and every quote on a citation line must be in that one file.
- The update sentence is not one string. `packaging/windows/splash_win.py` line 20 has "The first time can take up to a minute." and "Please wait." Line 23 has "Please wait; there is no need to click it again." Cited in words, not as `src/freemyid/...py:NNN`, because that file is outside `src/freemyid/`.
- Not a product defect, and no `src/` edit. Not checked on paper, and the app was not started.
