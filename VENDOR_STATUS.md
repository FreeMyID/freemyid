# WO-339

Tracker: WO-339 (freemyid-pm#259).

## Done

`allowed_fields`, `copy_fields` and `form_vars` now follow shared rule 6 for Jane Q Testperson of Springfield, IL. No contract file changed.

Leaks fixed in `src/freemyid/submitters/base.py`:

- A listing that does not show the name no longer receives it. `allowed_fields` used to add `full_name` on every call. A blind broker (no listing) still gets the name.
- A blind broker gets city and state only when `required_fields` lists them, not from the default need set. Middle name, street, ZIP, phone, age and date of birth stay off that path.
- Address lines come only from the address marked current. A past address is no longer the fallback when none is current.
- `form_vars` no longer widens a shown first name into last name and full name. Each name part is sent only when that field is allowed. A shown full name still allows its first and last parts.

Left as the model already promises: the removal mailbox (never a personal email) may be sent when the broker needs email, including when the listing does not show an email. Date of birth and id documents stay withheld. Age is still the age the listing shows. A phone still needs to be shown, required and permitted. Phone-only and email-only removals are unchanged.

`tests/grok/test_gk_data_minimization.py` runs 48 seeded cases (`random.Random(339)`) plus the regressions above. An autouse fixture makes `socket.socket.connect` and `socket.create_connection` raise.

## Next

Nothing on this WO. In-house review.

## Questions for the owner

None. The removal mailbox stays allowed when it is not on the listing, because `Listing.shown_fields` promises shown fields plus that mailbox. Say if that exception should be dropped; it would break in-house `tests/test_fill_for_me.py` (`test_plan_values_minimized`) and needs an in-house contract change first.

## How to test

From `.vendor-wt/wo-339`, with `PYTHONPATH=$PWD/src`:

- `../../.venv/bin/pytest -q tests/grok/test_gk_data_minimization.py` — 50 passed.
- `../../.venv/bin/pytest -q tests -k "minimi or copy_fields or submitter or assisted"` — 73 passed, 2664 deselected.
- `../../.venv/bin/pytest -q tests` — 2529 passed, 206 skipped, 2 xfailed, 0 failed. The 2 xfailed are existing marks in other files; this WO added none.
- `../../.venv/bin/ruff check src/freemyid/submitters/base.py tests/grok` — all checks passed.
- `../../.venv/bin/mypy src/freemyid/submitters/base.py` — no issues found in 1 source file.
