# WO-304 status

## Done

Updated `docs/user/GLOSSARY.md` with short plain-language entries for practice mode, the "Is this you?" review, the listing score, requested, confirmed, relisted, the Assisted step, and the phone-call note. Practice mode still searches, and no removal requests go out until you say so. The listing score is only about the sites we could check. Each new entry cites the app source with file and line in an HTML comment. The example person is Jane Q Testperson, Springfield IL. No product code was changed.

## Next

Owner review of the glossary wording, then merge when it looks right.

## Questions for the owner

- The screen does not say "relisted". It says "reappeared" or "It came back. We are asking again" (`src/freemyid/wizard/ui.py:29`, `src/freemyid/wizard/views.py:34`). The glossary uses "relisted" for that state. Is that the word you want helpers to use?
- The Today line counts both "site confirmed" and "not listed now" as confirmed (`src/freemyid/wizard/dashboard.py:27`). The glossary says so. Should a later change split those two counts?
- "Fill it in for me" can make a real request if the person presses Submit on the site, even while practice mode is on (`src/freemyid/wizard/dashboard.py:347-350`). The Assisted entry says that. Should practice mode say it too?

## How to test

From this worktree:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot tests -k "doc or wording or glossary"`

Result: 656 passed, 17 skipped, 2102 deselected, 1 xfailed, 1 warning in 6.16s.

The one xfail was already in the tree. It is `tests/copilot/test_cp_never_asks_parity.py::test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]` because `docs/FRIDGE_CARD.md:17` is missing "never charges you". That file is outside this work order, so it was not changed.
