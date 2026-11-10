# WO-313 vendor status

Agent: Simon Fairley (user-guide writer). Worktree: `.vendor-wt/wo-313`.

## Done

- Added `docs/user/is-this-you.md` only, plus this status file.
- The page explains why the "Is this you?" card appears (same name, and maybe the city, the age, a relative's name, a phone number, or an email address, is not enough).
- It quotes the three buttons and what the card says each one does, including practice mode.
- It tells the reader how to compare name, age, city, and relatives on the site's own page, and not to pay or sign up there.
- Not sure: wait and ask someone you trust. The open card stays until Yes or No (checked in code; see Findings).
- After No: no removal request goes out for that listing, and Free My ID will not ask about it again.
- The first answer stays. A second press does not flip it.
- Yes is described as confirmed (the listing is you) and requested (a removal on the next check). The page does not say the site has taken the listing down.
- Example person: Jane Q Testperson, Springfield IL. One link, to `docs/user/HELPING.md`, which already exists.

## Next

None in this work order. WO-330 is what links this page from the help topics. This WO does not add that link, on purpose.

## Questions

- `docs/USER_GUIDE.md:180` still says a mistaken press can be sorted out before the next check. The wizard does not do that (`src/freemyid/wizard/server.py:539-547`). WO-302 owns the guide. Should in-house correct that line when this page lands?
- `docs/USER_GUIDE.md:177` says practice mode sends nothing at all. The card says no removal requests go out (`src/freemyid/wizard/dashboard.py:130-131`). Same owner question.

## How to test

Ran in `.vendor-wt/wo-313` on 2026-11-09.

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

   **314 passed.**

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

   **1 failed, 9 passed.**

   The one failure is `test_user_page_is_reachable[is-this-you.md]`: `docs/user/is-this-you.md` is not linked from `INSTALL.md` or `GLOSSARY.md` (one hop). Expected. WO-330 adds that link. In-house merges this WO and WO-330 together before pushing.

3. `tests/grok/` is not in this worktree, so that check was not run.

## Findings

- Card stays until answered: no defect. An open review to-do is listed while `done_at` is empty (`src/freemyid/storage/db.py:344-350`). Yes and No set that (`src/freemyid/wizard/server.py:543`). Opening the page does not (`src/freemyid/wizard/server.py:488-499`). A later scan keeps the open to-do (`src/freemyid/engine/handoff.py:58-64`). There is no timer that drops the card. The help page says the card stays until Yes or No.
- Not a card bug, and not written into the help page: `freemyid todo done` can close any open to-do without recording Yes or No (`src/freemyid/cli.py:741-747`). The listing finder also closes a review to-do when the person picks a listing in that other flow (`src/freemyid/engine/listing_finder.py:341-343`).
- Docs mismatch, not edited: `docs/USER_GUIDE.md:180` implies a wrong press can still be changed before the next check. `src/freemyid/wizard/server.py:539-547` keeps the first personal answer, and a second press shows "That question was already answered. Nothing was changed." Covered by `tests/test_wizard_review_match.py:87`. Out of scope here (WO-302).

## Could not verify

- Did not start the wizard, and did not open a people-search page. This WO is text only and offline.
- Did not run `tests/grok` because that directory is not in the worktree.
