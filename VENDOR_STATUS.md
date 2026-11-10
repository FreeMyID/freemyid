# VENDOR_STATUS — WO-317 (issue pending)

Agent: Rosa Delgado (accessibility reviewer). Worktree: `.vendor-wt/wo-317`.
`docs/pm/issue_map.json` has no entry for WO-317, so the issue number is pending.

## Done

Added `docs/user/larger-text.md` only. No edits under `src/`, `web/`, or `docs/vendor/`.

The page tells people with poor eyesight to use the app buttons first, then Windows and browser controls. Headings go in order. There is no table. Steps do not depend on colour alone. The only example person is Jane Q Testperson, Springfield IL. The only link is to `docs/user/INSTALL.md`, which is already on main.

Lines checked before they were written up:

- "Larger text" is the default label at `src/freemyid/wizard/ui.py:61`. Cited on that line.
- "Normal text" is set in app.js, line 131. Cited in words, not as `app.js:131`.
- "Dark" is the default label at `src/freemyid/wizard/ui.py:58`. Cited on that line.
- "Light" is set in app.js, line 111. Cited in words, not as `app.js:111`.
- The buttons are in the header after the menu (`src/freemyid/wizard/ui.py:71-73`). On a wide window they sit beside the menu (style.css, lines 202-204). On a narrow window the menu wraps below them (style.css, lines 37-41). The page says both.
- Theme: app.js, line 101 says the choice is kept in a cookie. app.js, line 118 writes `fmi_theme`. theme.js, lines 5-6 read it.
- Text size was checked before calling it the same. It is a cookie too. app.js, line 124 says it is remembered like the theme. app.js, line 137 writes `fmi_text`. theme.js, lines 8-9 read it. It does not start from the computer's dark or light setting. Missing cookie, or a cookie that is not `large`, leaves the usual size.
- Both cookies use `max-age=31536000`, which is 365 days. theme.js, line 2 says the choice lives in a cookie on this computer.
- "Print this page" on the summary is `src/freemyid/wizard/views.py:301` (the guess was right). The heading "What Free My ID did for" is `views.py:303`. The way in from Today is "More: safety steps and details" (`dashboard.py:275`), then "Everything" (`dashboard.py:288`), then "People" (`dashboard.py:310`), then the button that starts "What we did for" (`dashboard.py:315`).

## Next

WO-330 should link `docs/user/larger-text.md` from the help topics. This page stays unlinked on purpose until that merge.

In-house can note delivery on `docs/vendor/GROK_BOARD.md` and in `docs/vendor/GROK_TO_CLAUDE.md`. Those files are outside this work order's allowed paths, so they were not edited here.

If in-house wants the two buttons on setup screens, that is a `src/` change and was not done.

## Questions

- Should the setup screens show "Larger text" and "Dark" / "Light" even though they hide the menu? The code ties both buttons to `nav` (`ui.py:58` and `ui.py:59`). Setup uses `nav=False` (`ui.py:413`).
- Not sure the Windows 11 Settings search still uses the exact words "Make text bigger". Windows 10 uses that label. This environment has no Windows session and the work order forbids network, so the live Settings label was not opened. The page uses those words, as the work order asked, and gives no menu path.
- What issue number should replace "issue pending" once `docs/pm/issue_map.json` lists WO-317?

## How to test

Run from `.vendor-wt/wo-317`.

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

   Result: **288 passed** in 1.16s. Exit 0.

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

   Result: **1 failed, 9 passed** in 0.23s. Exit 1.

   The only failure is `test_user_page_is_reachable[larger-text.md]`: `docs/user/larger-text.md` is not linked from `INSTALL.md` or `GLOSSARY.md` (one hop). That is the expected failure. WO-330 adds the link. Any other failure would have been fixed. There were no others.

3. `tests/grok/` is not in this worktree. That check was not run.

## Findings

1. **Setup and other menu-less screens hide both buttons.** `layout` builds the theme button only when `nav` is true (`src/freemyid/wizard/ui.py:56-58`) and the text button only inside `if nav` (`ui.py:59-61`). Call sites that pass `nav=False`: error page `ui.py:85`, wizard steps `ui.py:413`, authorization form `ui.py:432`, closing page `src/freemyid/wizard/server.py:646`, family-import form `server.py:848`. A person who needs larger text during first setup will not see the buttons. The new page sends them to Ctrl and + instead. Not changed, because `src/` is out of scope. This looks deliberate (one flag), not a stray omission. Still a gap for the people this page is for.

2. **"Beside the menu" is the wide layout only.** Default CSS puts the menu on its own row under the buttons (style.css, lines 37-41). At `min-width: 52rem` the buttons move beside the menu (style.css, lines 202-204). The usual window asks for 1100px wide (`src/freemyid/wizard/desktop.py:95-96`), which is wide at a normal root font and still wide with the app's larger text (`html` at 125%, style.css line 5, so 52rem is about 1040px). Strong browser zoom can make the same window count as narrow. The page says so. Not treated as a defect.

3. **A second "Print this page" is on the authorization form** (`src/freemyid/wizard/ui.py:431`), and that form also uses `nav=False` (`ui.py:432`), so it has print but not the text or theme buttons. The user page documents the summary button only (`views.py:301`), which is what WO-317 asked for.

4. **Buttons are marked `hidden` until app.js runs** (`ui.py:56` and `ui.py:60`; shown at app.js, lines 113 and 133). theme.js can still apply a saved cookie before paint. If app.js did not run, the buttons would stay hidden. Not treated as a defect in this local app.

## What was not verified

- The app was not started. The buttons were not clicked. Ctrl and + and Ctrl and 0 were not pressed in the Edge WebView2 window. app.js, line 124 says browser zoom still works on top of the text button. `desktop.py` uses pywebview, which the file says uses Edge WebView2 on Windows. That shortcut was not exercised here.
- Windows 10 and Windows 11 Settings were not opened. The "Make text bigger" wording is the work order's stable name, not a check of a live Settings window.
- No screen reader, high contrast, print preview, or zoomed screenshot. No screenshots were made (offline, and the page forbids them).
- `tests/grok/` does not exist here, so that pytest command was not run.
