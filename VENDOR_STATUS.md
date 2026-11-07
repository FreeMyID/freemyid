# Vendor Status: WO-001

## Done
- **"Good to know" tips on Protect yourself**:
  - Updated `src/freemyid/wizard/views.py` (`_checklist_item`) to render `tips` under an `<h3>Good to know</h3>` heading with an unordered list (`<ul><li>...</li></ul>`), placed immediately after `<h3>Steps</h3><ol>...</ol>` and before the undo instructions, matching the website implementation in `web/src/pages/protect/[id]/index.astro`.
  - If a checklist has no tips, the heading and list are omitted.
  - Internal research `notes` continue to never be rendered on any page.
- **Durable checklist ticks via checklist_state**:
  - Updated `src/freemyid/wizard/protect.py` to delegate `load_checklists()`, `progress()`, `set_done()`, and `counts()` directly to `src/freemyid.checklist_state`.
  - App ticks now write events tagged with `TAG = "_checklist"`.
  - Legacy untagged ticks written by v1 (`broker_id is None`) continue to read as done through `checklist_state`'s bounded scan.
- **Reserved internal id handling on per-site pages**:
  - Updated `src/freemyid/wizard/views.py` (`broker_page`) to raise `HTTPException(status_code=404, detail="Not found")` when `bid.startswith("_")`, ensuring requests for `_checklist` and `_consent` return 404 rather than rendering a broker page.
  - Updated `views.summary_page` to filter out any status records with `s.broker_id.startswith("_")`.
  - Updated `tests/test_wizard_v03.py` to assert that `/profile/{p.id}/site/_checklist` and `/profile/{p.id}/site/_consent` return 404.
- **Tests written**:
  - Created `tests/test_wizard_protect_tips.py` covering:
    - Tips displayed under "Good to know" with proper placement and omission when empty.
    - Research `notes` never appear in rendered HTML.
    - App ticking and unticking agree with `checklist_state` and write `_checklist` tagged events.
    - Old untagged tick events read as done in `checklist_state` and in the dashboard UI.
    - Site pages for `_checklist` and `_consent` return 404 and never display as brokers.
    - Summary page ignores internal reserved IDs.

## Next
- Owner check-in to run tests and linters.
- In-house review by Nina Alvarez (wizard-packager) for acceptance.

## Questions for the owner
- None. Requirements are clear and all acceptance criteria are covered.

## How to test
- Run pytest:
  ```bash
  .venv/bin/pytest -v tests/test_wizard_v03.py tests/test_checklist_state.py tests/test_wizard_protect_tips.py
  ```
- Run ruff check on changed files:
  ```bash
  .venv/bin/ruff check src/freemyid/wizard/protect.py src/freemyid/wizard/views.py tests/test_wizard_v03.py tests/test_wizard_protect_tips.py
  ```
