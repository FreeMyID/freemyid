# WO-249 (issue pending) — Editing a person keeps every answer

## Done

- Added only `tests/codex/test_cx_draft_edit_roundtrip.py` and this status file. Product code is unchanged.
- Checked existing `tests/`, `tests/copilot/`, `tests/codex/` and `tests/grok/` references before writing. Existing wizard password-hint tests and bundle/import guards do not exercise `draft_from_profile` edit round trips.
- Acceptance checklist:
  - [x] Twelve synthetic profiles cover each consent basis, DOB versus age only, both email modes, all permission flags off/on/one-at-a-time, every removal scope, schedule values, mailbox present/absent, middle name/suffix, nicknames, two prior names, three addresses with exactly one current, phones/emails/relatives.
  - [x] Parameterized 798 independent dumped-field comparisons. Each affected input leaf has a strict `xfail(strict=True, raises=AssertionError)` with the responsible source location; unexpected exceptions still fail. There are 102 expected failures across six defect categories, not 102 distinct defects.
  - [x] Aggregate comparison preserves every other dumped field and the complete leaf/key structure, so extra/missing list entries and unlisted field losses fail. Only top-level `id`, `created_at` and `updated_at` are omitted from that dump: ID has its own assertion; `save_draft` owns persisted creation/update times. Nested consent timestamp and authorization reference are checked.
  - [x] `keep_consent=True` retains the exact original consent object and rebuilt consent data, including old text version, timestamp, and authorization reference; `False` leaves it unset and requires new acknowledgment.
  - [x] `_has_saved_password` is stubbed before conversion; separate true/false cases verify a bool, blank draft password, no mailbox password/keyring-service field, and copied mailbox/TLS settings. No real mailbox, keyring, browser or network operation is invoked.
- Date-based minor calculation is fixed to synthetic test time (2026-11-09), so DOB cases do not age out of the guardian branch.

## Findings — in-house product fixes required

Each finding is outside this WO's code-edit lane and remains an independent strict field assertion. Repeated profile cases test different input combinations; an individual fixed field becomes XPASS and fails until its marker is removed.

1. `src/freemyid/wizard/draft.py:610-611`: previous names omit `suffix`. Synthetic `Sr.` and `III` become `None` after edit/rebuild (24 expected failures).
2. `src/freemyid/wizard/draft.py:612-613`: addresses omit `from_year`. Synthetic current year `2020` and prior years `2018`/`2015` become `None` (36 expected failures).
3. `src/freemyid/wizard/draft.py:612-613`: addresses omit `to_year`. Synthetic prior years `2019`/`2017` become `None` (24 expected failures; the current address's original `None` remains a passing assertion).
4. `src/freemyid/wizard/draft.py:542-543`: rebuilding the schedule omits `respect_broker_intervals`. An explicit `False` becomes default `True` (6 expected failures).
5. `src/freemyid/wizard/draft.py:527`: rebuilding `Profile` omits `removal_scope`. Explicit `phone` or `email` becomes `full` (8 expected failures). These profiles retain names/addresses so each assertion isolates scope loss rather than a validation exception.
6. `src/freemyid/wizard/draft.py:539-541`: rebuilding permissions omits `allow_email_disclosure`. Explicit `True` becomes default `False` (4 expected failures).

## Next

- Ready for Owen Brooks's independent test-quality and scope review before Nora reports delivery.
- In-house fixes each lost input in its app lane, then removes the corresponding strict xfail cases once they XPASS.
- Native Windows CI can run the same test; this session did not execute Windows.

## Questions for the owner

- Please track and fix the six field-loss findings above in-house. No source-file scope expansion is requested.
- Tracker issue number is pending in the local issue map; no number invented.

## How to test

Run from `.vendor-wt/wo-249`:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_draft_edit_roundtrip.py` — **734 passed, 102 xfailed, 0 skipped**, exit 0 (1.02 seconds).
- `../../.venv/bin/ruff check tests/codex` — **All checks passed**, exit 0.

No product, browser, real-keyring, real-mailbox or native-Windows verification is claimed. The tests use fake names and reserved contact hosts, no host-specific paths, no symlinks, and no file-mode assumptions.
