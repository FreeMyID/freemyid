# WO-338

Tracker: WO-338 (freemyid-pm#258).

## Done

`classify` and `choose_state_option` in `src/freemyid/engine/filler.py` handle more opt-out form variants. `plan_values` is unchanged. `fill_page` and the browser code are unchanged. No contract change.

Labels now include "Given name", "Surname", "Last / family name", "ZIP / Postal code", "E-mail address", "Street address line 1", "Town/City", and "Province or state", plus one-word forms (`emailaddress`, `postalcode`, `address1`, `street1`, `streetaddress`, `addr1`, `zip4`). "Postal address" maps to street, not ZIP. "Cardholder name" is not a full name.

Password, payment, and ID-number controls stay unfilled whatever the label says (`cc-*` autocomplete, and a name, id, or placeholder that says card, SSN, passport, or driver's license). A negative or honeypot word on any descriptor blocks a friendly label.

State options: "CA - California", "California (CA)", "Calif.", lower-case and dotted codes (`ca`, `D.C.`, `N.C.`), a leading "Select...", and territories (PR, DC, and GU, VI, AS, MP). If the option value and the text name two different states, that option is skipped. Arkansas is not Kansas, West Virginia is not Virginia, and Washington is not D.C.

Before this change, a value of `SC` with text "North Carolina" was returned for NC, and a value of `CA` with text "Colorado" was returned for CO. Both now return none.

Tests: `tests/grok/test_gk_filler_classify.py` (fake controls only, Jane Q Testperson of Springfield IL). An autouse fixture makes `socket.socket.connect` and `socket.create_connection` raise.

## Next

In-house review. `docs/vendor/GROK_BOARD.md` and `docs/vendor/GROK_TO_CLAUDE.md` were not edited; those paths are outside this WO's allowed writes.

## Questions for the owner

None on the behavior. Should in-house mark WO-338 delivered on GROK_BOARD.md?

## How to test

From `.vendor-wt/wo-338`:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_filler_classify.py` — 115 passed
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "filler or fill_for_me"` — 186 passed, 2616 deselected, 1 warning
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2594 passed, 206 skipped, 2 xfailed, 1 warning (exit 0)
- `../../.venv/bin/ruff check src/freemyid/engine/filler.py tests/grok` — all checks passed
- `../../.venv/bin/mypy src/freemyid/engine/filler.py` — no issues in 1 source file

The 2 xfailed tests are existing marks, not this change. No in-house or Codex test failed.
