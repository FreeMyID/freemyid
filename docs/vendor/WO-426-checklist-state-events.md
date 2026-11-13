# WO-426: Checklist state: odd or conflicting tick events never break or flip the checklist
Status: queued (pre-approved: start when a WIP slot frees; note it on BOARD.md first)
Vendor: codex
Agent: windows-tests (Owen Park)
Owner contact: Morgan Reyes (check-ins via CODEX_TO_CLAUDE.md)
Kind: engine
Target release: 0.4
Source: follow-up to WO-281 (CLAUDE-068, 2026-11-12). WO-281's file-recovery and atomic-write criteria assumed a JSON tick file; checklist state is encrypted, append-only store events, so this WO rewrites them against the event store.
Worktree: `.vendor-wt/wo-426` on `vendor/wo-426` from main
Tracker: issue pending (in-house syncs freemyid-pm)
Order: start after WO-281 is closed (it is: merged 2026-11-12 as characterisation tests)

## Goal
Make `checklist_state.ticks()` and the functions built on it robust against odd, old or conflicting tick events in the store, so a person's "Protect yourself" ticks are never lost, flipped or crash the page.

## Acceptance criteria (testable)
1. Table test over tick events written straight to a test store: `detail` missing `checklist`, a non-string, empty or whitespace id, extra detail keys, an unknown action, and a `checklist_done` logged by a non-USER actor. None raises; every valid USER tick is kept; the invalid ones are ignored. (Today a non-USER `checklist_done` counts: fix that, the module docstring says ticks are USER events.)
2. Conflicts: a done and an undone for the same id with the same timestamp resolve deterministically to the one written last; a tagged tick beats a legacy untagged tick on a tie. Test both orders.
3. A tick for a checklist id no longer in `brokers/checklists.yaml` stays in `ticks()` but is not counted by `counts()` and not shown by `list_doc()`.
4. Legacy untagged ticks: a test pins the documented window (`_LEGACY_SCAN`): ticks inside it are read; the newest tagged tick still wins over an older legacy one.
5. Existing checklist tests and `tests/codex/test_cx_checklist_state_recovery.py` (WO-281) pass unchanged.

This is Codex code-lane work (owner, 2026-11-09): fix and improve the listed module(s) directly, with tests; don't xfail a bug you can fix here. No contract changes: public function signatures, `src/freemyid/models.py`, `interfaces.py`, schema files, `--json` shapes and documented CLI output stay as they are (additive helpers inside the listed files are fine). If the work turns out to need a contract change, stop and say so in VENDOR_STATUS.md "Questions for the owner". Fake data only, offline (fake fetchers, no network), Windows-safe paths in tests (`tmp_path`, `pathlib`, no `/tmp`). Typed, ruff-clean, small diff. Line numbers, where cited, are from main at the time of writing; re-check them.

## Allowed paths (the vendor may change ONLY these)
- `src/freemyid/checklist_state.py`
- `tests/codex/test_cx_checklist_state_events.py` (new)
- `VENDOR_STATUS.md` (worktree)

## Out of scope / do not touch
Every file not listed above. In particular: front end and design (`src/freemyid/wizard/`, `src/freemyid/templates/`, `web/`, `brand/`), in-house modules (`models.py`, `interfaces.py`, `state.py`, `registry.py`, `cli.py`, `config.py`, `paths.py`, `netpolicy.py`, `consent.py`, `logging_setup.py`, `crypto.py`, `secrets.py`, `storage/`, `schema/`, `engine/browser.py`), Grok's modules (`engine/mail*`, `engine/outbox.py`, `engine/runner.py`, `engine/tiers.py`, `engine/handoff.py`, `engine/plugins.py`, `engine/filler.py`, `engine/fill_for_me.py`, `submitters/`, `scheduler/`, `notify.py`, `setup_config.py`, `cli_json.py`), `brokers/` data and existing tests not listed.

## Required checks (run in the worktree)
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_checklist_state_events.py tests/codex/test_cx_checklist_state_recovery.py`
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "checklist"` (existing tests, all unchanged and passing)
- `../../.venv/bin/ruff check tests/codex src/freemyid/checklist_state.py`

## Check-in plan
Deliver into the worktree (nothing merges until in-house review): VENDOR_STATUS.md complete (Done, Next, Questions, How to test with exact counts, findings with file:line), then a CODEX-NNN message in `docs/vendor/CODEX_TO_CLAUDE.md` citing the WO and its tracker issue. Delivery lead reviews before the PM reports it delivered.

## Notes and decisions (owner appends after each check-in)
- none yet
