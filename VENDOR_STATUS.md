# WO-309

## Done

- Added `tests/grok/test_gk_doc_labels_exist.py`. It reads `USER_GUIDE.md` when that file exists, plus `docs/USER_GUIDE.md`, `FAMILY_QUICK_START.md`, and `docs/user/*.md`. A label counts when the docs quote it in bold or quotes and call it a button or a link.
- Those labels must appear as their own phrase in UI source under `src/freemyid/wizard/` (`.py`, `.js`, `.html`, `.css`, `.svg` only; read-only).
- Website-only allowlist: `FAMILY_QUICK_START.md:20` **Download Free My ID** (freemyid.org download button).
- Fake fixtures use `tmp_path` and `pathlib`: a real hit (`Continue`), a clean line (bold text and the word "links", plus a fenced block and an HTML comment that must not count), and a missing quoted button that is reported.
- Live gaps are strict xfails. `src/` and the user docs were not edited.
- Added `tests/grok/__init__.py`. This does not duplicate `tests/copilot/test_cp_source_citations.py` (that guard checks quoted text on a source-citation line).

## Next

- Owner decides whether the three findings stay xfails, get allowlisted, or are fixed in docs later. This work order does not change `src/` or the guides.
- The allowlist and the known mismatches match the file and the label, not the line number. Moving a sentence does not turn a known gap into a new failure. Deleting the label removes the xfail. A new missing label still fails.

## Questions for the owner

- `docs/USER_GUIDE.md:36` calls `"confirm your request"` the links that people-search sites send. That phrase is not a wizard control. Should it stay an xfail, or move to the website-only allowlist?
- `FAMILY_QUICK_START.md:24` **Run anyway** is the Windows SmartScreen button, also drawn on the download page. Should OS chrome be allowlisted the same way as website buttons?
- `FAMILY_QUICK_START.md:65` joins three compose buttons into one quoted label and says "Yahoo", while the app says "Yahoo Mail". Confirm the doc should list **Open in Gmail**, **Open in Outlook**, and **Open in Yahoo Mail** separately (not changed here).
- Bold labels the guides say to click, but do not call a button or a link (`**I couldn't**`, `**I sent it**`, setup **Next** / **Finish**), are out of this guard. Say if those should be included.

## How to test

From this worktree:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_doc_labels_exist.py`

`../../.venv/bin/ruff check tests/grok`

Pytest: 14 passed, 3 xfailed (0 failed). Ruff: all checks passed.

Live labels checked: 11. 7 match the wizard (`I finished it`, `I did it`, `Open the page`, `Yes, this is me`, `No, this is not me`, `Open the site`, `Copy`). 1 allowlisted. 3 xfailed, listed below. Root `USER_GUIDE.md` is not in this tree, so it was not scanned; the path helper includes it when the file exists (covered by a `tmp_path` fixture).

## Findings

1. `docs/USER_GUIDE.md:36` quotes `"confirm your request"` links. That phrase is not in `src/freemyid/wizard/`. These are links people-search sites send, not a Free My ID button. Strict xfail. Docs and `src/` left as they are.
2. `FAMILY_QUICK_START.md:24` quotes the **Run anyway** button. That string is not in `src/freemyid/wizard/`. It is the Windows SmartScreen button. Strict xfail. Not a wizard defect. Docs and `src/` left as they are.
3. `FAMILY_QUICK_START.md:65` quotes one button, **Open in Gmail / Outlook / Yahoo**. That string is not in the wizard. `src/freemyid/wizard/dashboard.py:171` builds a separate button per provider from `dashboard.py:30-34`: Open in Gmail, Open in Outlook, and Open in Yahoo Mail. Strict xfail. Docs and `src/` left as they are.
