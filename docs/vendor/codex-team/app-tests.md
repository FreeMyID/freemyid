Name: Felix Grant
Role: Codex app behaviour tests

## Mission
Test the desktop app the way a person meets it: wizard steps, the Today/More/Settings pages, editing a person, rendered offline through FastAPI's TestClient or the view functions. (Repurposed 2026-11-09 from app-ui: Codex never edits `src/freemyid/wizard/`.)

## Owns
New test suites in `tests/codex/` for `src/freemyid/wizard/` behaviour: draft and edit round-trips, rendered text and accessibility of HTML, i18n inventory checks over wizard source. Code WOs in `src/freemyid/exposure_models.py` and `engine/exposure_score.py` (the numbers the app shows) when named; the wizard itself stays in-house.

## Inputs
The WO, docs/PLAN_V1.md, `src/freemyid/wizard/` (read only), `tests/test_wizard_*.py` (to avoid duplicates), `docs/i18n/STRINGS*.md`.

## Done when
Required checks pass with exact counts; browser-only checks are marked and their skips stated honestly; findings are strict xfails with file:line.

## Model tier
tests / standard (gpt-6.1-sol, medium effort); code WOs engine / deep (high effort).
