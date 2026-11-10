# VENDOR_STATUS.md — WO-320

Agent: Linda Moreau (support writer). Worktree: `.vendor-wt/wo-320`.

## Done

Wrote `docs/user/helping-by-phone.md` only, plus this status file.
The page is for a grown child or friend talking Jane Q Testperson, Springfield IL, through Free My ID by phone.
It links to `docs/user/HELPING.md` for sitting together and does not repeat that guide.
Safety rules come first: do not ask her to read out a password, a code, or a Social Security number, and do not ask for a bank or card number.
The setup promise is quoted from `src/freemyid/wizard/ui.py:266-268`.
Screen labels are the ones she sees: "Today", "Protect yourself", "Emails", "Settings", and "More: safety steps and details".
Three call scripts cover the first look at Today, the "Is this you?" card ("Yes, this is me" / "No, this is not me"), and the first email ("Look at them", then "Approve and send" when she wants that request to go out).
If she is upset or unsure, the helper stops. Waiting does not lose the work. Practice mode text is quoted from the Today banner.
No remote-control software, screen sharing, or extra download is recommended.

## Next

WO-330 is the page that should link this one. This WO does not add that link.
In-house merges this WO with WO-330 before pushing.
Channel files (`docs/vendor/GROK_TO_CLAUDE.md`, `docs/vendor/GROK_BOARD.md`) were not edited. They are outside the allowed paths for this order.

## Questions

None that block the page.
One copy question is in Findings: the Today card says "press Approve", and no button uses that exact label.

## How to test

Command:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

Result: **364 passed** in 2.04s. Exit 0.

Command:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

Result: **1 failed, 9 passed** in 0.27s. Exit 1.
The only failure is `test_user_page_is_reachable[helping-by-phone.md]` (`tests/copilot/test_cp_user_docs_reachable.py:64`).
Nothing links the new page yet. That is the expected WO-330 gap.

`tests/grok/` is not in this worktree, so `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok` was not run.

## Findings

Line guesses checked against the current source. Wrong guesses are cited at the line that contains the words.

- `src/freemyid/wizard/ui.py:43` has "Today", "Protect yourself", and "Emails". `src/freemyid/wizard/ui.py:44` has "Settings". The guess `ui.py:43-44` was right.
- `src/freemyid/wizard/dashboard.py:275` has "More: safety steps and details". The guess was right.
- `src/freemyid/wizard/dashboard.py:122` is "Yes, this is me". `src/freemyid/wizard/dashboard.py:123` is "No, this is not me". The guess was right.
- `src/freemyid/wizard/dashboard.py:473` is "Approve and send". The guess was right.
- "Look at them" is `src/freemyid/wizard/dashboard.py:255`, not line 253. Line 253 is "waiting for your OK" and "Look at each one, then press Approve."
- `src/freemyid/wizard/dashboard.py:254` says "Nothing is sent until you do." This page does not copy that sentence. The helper is told she presses "Approve and send" when she wants that request to go out.
- "Practice mode:" is `src/freemyid/wizard/dashboard.py:237`. "no removal requests go out until you say so." is `src/freemyid/wizard/dashboard.py:238`. The guess of line 237 is the banner start, not the removal-request words. The review card repeats "no removal requests go out." at `src/freemyid/wizard/dashboard.py:131`.
- The setup promise starts at `src/freemyid/wizard/ui.py:266` ("Never asks for your"), the Social Security words are on `src/freemyid/wizard/ui.py:267`, and "Uninstall anytime." is on `src/freemyid/wizard/ui.py:268`. The guess `266-267` covered the start, not the last line.
- The words "Is this you?" are the card name in the docstring at `src/freemyid/wizard/dashboard.py:113`. The title she sees is built at `src/freemyid/engine/runner.py:1000` ("Is this {name}?") or `src/freemyid/engine/runner.py:996` (phone number or email address). The page says that, so the helper does not hunt for the words "Is this you?".
- Copy mismatch, not edited (wizard UI is out of scope): `src/freemyid/wizard/dashboard.py:253` tells her to "press Approve", but the buttons are "Look at them" (`src/freemyid/wizard/dashboard.py:255`) and "Approve and send" (`src/freemyid/wizard/dashboard.py:473`). No control is labeled "Approve".
- `src/freemyid/wizard/dashboard.py:475` ("Cancel it") marks the queued email cancelled at `src/freemyid/wizard/server.py:612`. The phone guide says to wait and not press it, because waiting keeps the email.
- Consent-screen overclaim, not edited: `src/freemyid/wizard/ui.py:264-265` says sites are asked "in the written form they have to answer." `docs/POSITIONING.md:51` says not to write that without the qualifier that only some states require an answer. The phone page does not quote that sentence.

## What was not verified

The app was not opened. Labels were checked by reading source, not by a live window.
No Windows run. These files are Markdown, and the copilot tests only read files.
`tests/grok/` is absent, so that suite was not run.
Git status was not checked (git is out of bounds for this order).
