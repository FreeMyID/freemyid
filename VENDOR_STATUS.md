# WO-005 — Felix Grant [freemyid-codex]

## Done
- Updated only exposure_card and its typing import in views.py, plus the new focused test file and this status file.
- Kept the interface and latest_exposure(store, profile) integration. No discovery, matching, scoring, storage, workflow, security, CSS, or JavaScript changes.
- Distinguished missing engine, no saved result, unavailable result, and completed checks with zero found listings.
- Kept the numeric score and checked date. Added limits for site coverage and overall safety; corrected count wording. All explanation lines now appear, escaped (previously only the first four appeared).
- Added fake-result tests for states, missing profile, engine arguments, zero/one/multiple found and manual counts, score/date/limits, six hostile explanation lines, and failure-message privacy.
- Added an offline browser layout test for all states in light/dark at effective viewports 683x512 (1024x768 at 150%) and 512x384 (200% zoom). It checks horizontal overflow and text block bounds; vertical scrolling is allowed.

## Rendered text examples
All states retain the heading “Where you are listed”. These are HTML-output text examples, not browser screenshots.

- Missing engine: “Coming soon. This version does not include the listing check.”
- No saved result: “No picture yet. There is no saved result to show. Results will appear here after a check.”
- Unavailable result: “Your saved result is not available right now. This does not tell us whether any sites list you.”
- Completed zero result: “No listings found on the sites checked. 0 sites need a manual check.” Followed by “These results cover only the sites checked, not every website.”, the checked date, the unchanged score, and “This score describes this check, not your overall safety.”
- Singular example: “Listings found on 1 site. 1 site needs a manual check.”

## Next
- Owner/in-house review and browser verification on the supported desktop environment.
- Resolve the old v0.3 assertion described below in an owner-authorized path.

## Questions for the owner
- tests/test_wizard_v03.py::test_exposure_card_with_and_without_engine asserts the exact ungrammatical string “1 site list you, 1 to look at by hand”. Correct wording conflicts with that assertion; this file is outside WO-005's allowed paths. Please update the assertion to the singular example above.
- No uncertainty found in the latest_exposure contract: it returns ExposureResult or None; lookup exceptions retain a generic page message. A missing profile still skips the lookup.

## How to test
- `PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_wizard_exposure_card.py -rs` — 13 passed, 1 skipped. Chromium launch failed with TargetClosedError, so visual layout, zoom, and theme verification remain pending. CSS review confirms existing wrapping block layout and theme tokens; this is not a substitute for visual verification.
- `/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check src/freemyid/wizard/views.py tests/test_wizard_exposure_card.py` — passed.
- `PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_wizard_v03.py::test_exposure_card_with_and_without_engine` — 1 failed at line 199, solely on the old wording assertion described above; the score assertion passes.
- Full existing v0.3 run stalled without producing a result and was interrupted. A rerun with `FREEMYID_TEST_TIMEOUT=5` also stalled without output and was interrupted. Full regression remains unverified; no unrelated test or app changes were made to work around this environment issue.
