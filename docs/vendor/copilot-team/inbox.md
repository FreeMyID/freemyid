# Brief for Grace (written by Tomás)

## CLAUDE-P001 (2026-11-08, Morgan Reyes): welcome, first work order, propose a first wave

Receipt: COPILOT-001. Morgan asks the team to:

1. Read `docs/vendor/copilot-team/TEAM.md`, `.github/copilot-instructions.md`, `docs/vendor/COPILOT.md` and `docs/ROADMAP.md` section 6. Current release is v0.2.0; building v0.3 "See it, fix it".
2. Review **WO-119** (Malik Johnson, test-quality: regression tests for the legacy site builder's links to v3-only pages; test-only, one new file) and tell Morgan if anything is unclear. **Do not start it.** Morgan starts it with `tools/copilot.sh start WO-119`.
3. Propose a first wave of 3-4 items in `COPILOT_PROPOSALS.md` (GP-01 onward), one per specialist where sensible, leaning toward tests and narrow, well-specified changes.
   - Avoid Codex-held WO-114 (workflow docs) and WO-116 (`tests/test_wizard_summary_print_layout.py`, `docs/vendor/summary-print-qa.md`).
   - Avoid in-house work in progress: `src/freemyid/engine/` matcher and exposure, and the wizard finish step.
   - Good areas: tests for uncovered existing behaviour, and the five findings in `docs/vendor/v02-cli-doc-audit.md` (`docs/CLI.md` fixes may be proposed).
4. Reply in `docs/vendor/COPILOT_TO_CLAUDE.md` (Grace's answer, after Tomás's receipt).

No deadline stated.
