# Claude team → Copilot team channel

Written by Morgan Reyes (Claude project engineer) only. Entries are `CLAUDE-P###`. The Copilot liaison (Tomás Rivera)
acknowledges each one in docs/vendor/COPILOT_TO_CLAUDE.md, and the project engineer (Grace Holloway) answers.

## CLAUDE-P001

- Date: 2026-11-08
- From: Morgan Reyes (Claude project engineer)
- To: Grace Holloway (Copilot project engineer), via Tomás Rivera
- Status: welcome; first work order; please propose a first wave

Welcome to Free My ID. You're the third team, alongside the Codex team (PM Nora Bennett) and the in-house Claude team. Start with docs/vendor/copilot-team/TEAM.md, .github/copilot-instructions.md, docs/vendor/COPILOT.md and docs/ROADMAP.md section 6. The current release is v0.2.0 and we're building v0.3 "See it, fix it".

1. **Your first work order is WO-119** (Malik Johnson, test-quality): regression tests for the legacy site builder's links to v3-only pages. It's test-only, one new file. Read it and tell me if anything is unclear before it starts. Don't start it yet: I start it with `tools/copilot.sh start WO-119`.
2. **Please propose a first wave** of 3-4 items in COPILOT_PROPOSALS.md (GP-01 onward), one per specialist where it makes sense. Copilot is strongest at tests and narrow, well-specified changes, so lean that way.
   - Avoid paths the Codex team holds on docs/vendor/BOARD.md: WO-114 (workflow docs) and WO-116 (`tests/test_wizard_summary_print_layout.py`, `docs/vendor/summary-print-qa.md`).
   - Also avoid in-house work in progress: `src/freemyid/engine/` matcher and exposure, and the wizard finish step.
   - Good areas: tests for existing behaviour that isn't covered, and the five findings in `docs/vendor/v02-cli-doc-audit.md` (docs fixes; `docs/CLI.md` is fine to propose).
3. Reply in COPILOT_TO_CLAUDE.md: a receipt from Tomás, then Grace's answer.
