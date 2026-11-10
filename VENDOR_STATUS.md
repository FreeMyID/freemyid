# VENDOR_STATUS.md — WO-312 (issue pending)

Vendor: grok. Agent: Linda Moreau. Page: `docs/user/what-to-do-when.md`.

`docs/pm/issue_map.json` has no WO-312 number yet.

## Done

Wrote a calm help page for 11 everyday moments that are not errors.
Each situation uses the reader's heading, the app's exact words, what they mean, one thing to do, and when to stop and ask someone you trust.
Real errors point at `docs/user/troubleshooting.md` only. That file was not edited.
Screen quotes cite the line that holds the words. Work-order line numbers that were guesses were checked against the source.
The only example person is Jane Q Testperson, Springfield IL.
No "guarantee", "erase", "100%", or "nothing is sent". The app sentence "Nothing is sent until you do" is not copied.
The page says the person presses **Approve and send** when they want that request to go out.
Listings are described as requested or confirmed. The page does not say a site has removed a listing.

## Next

WO-330 is what links this page. In-house merges WO-312 and WO-330 together before pushing.
Until that link exists, `test_user_page_is_reachable[what-to-do-when.md]` fails by design.
`docs/vendor/GROK_BOARD.md` and `docs/vendor/GROK_TO_CLAUDE.md` were not updated. They are outside this work order's allowed paths.

## Questions

None that block this page.
The issue number is still pending.

## How to test

Run from this worktree.

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

Result: **370 passed**, exit 0.

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

Result: **1 failed, 9 passed**, exit 1.
The only failure is `test_user_page_is_reachable[what-to-do-when.md]`.
Message: `docs/user/what-to-do-when.md` is not linked from INSTALL.md or GLOSSARY.md (one hop).

3. `tests/grok/` is not in this worktree, so that check was not run.

## Findings

Not changed. `src/` is out of scope.

- `src/freemyid/wizard/dashboard.py:253` says "press Approve". The button at `src/freemyid/wizard/dashboard.py:473` is "Approve and send". The page names both.
- `src/freemyid/wizard/dashboard.py:254` still shows "Nothing is sent until you do." This page does not copy that sentence.
- `src/freemyid/wizard/dashboard.py:242-243` shows the raw `consent_ok` reason. Examples: `src/freemyid/consent.py:64` ("consent has no attesting name") and `src/freemyid/consent.py:84` ("authorized agent needs the signed authorization attached"). Those words are technical for this reader.
- Settings "Right now" shows `scheduler.status()` from `src/freemyid/scheduler/__init__.py:183-203`, such as "not installed" or "systemd timer: ...", via `src/freemyid/wizard/dashboard.py:504`. The page tells the reader to ask if those words do not make sense.

One app sentence quoted in full is 25 words ("If a site wants a photo ID..."). It is the screen text, so it was not shortened.

## What I could not verify

- No live window. `freemyid run`, `send`, and `schedule install` were not run. Quotes were checked against source text, including strings Python joins across lines.
- "A note near the top" for practice mode is the banner order in `home_page`, not a screenshot.
- Not run on Windows. No new tests were added. The checks above only read files.
- `tests/grok/` does not exist here.
- Board and channel files were not edited, as noted under Next.
