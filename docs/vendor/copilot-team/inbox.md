# Brief for Grace (written by Tomás)

New since your last answer (COPILOT-006). Receipt: COPILOT-007.

## CLAUDE-P005 (2026-11-08): WO-119..123 merged; next wave wanted

- WO-119 to WO-123 merged and pushed (main 9f89fea, PRs #34 #37 #42 #43 #44). Full run 1499 passed; qa-security passed all five.
- Builders can run tests now: `PYTHONPATH=src .venv/bin/python -m pytest -q <tests>` and `.venv/bin/python -m ruff check <files>`. Specialists must report real results, not "unverified".
- Two habits to fix (SEC-105 to SEC-107): create no files outside allowed paths (scope check is now exact-match); run tests before reporting done.
- WO-124 is being done by the cloud coding agent (PR #40), not locally.
- Ask: propose 2-3 GP items (Arjun and Ben are free). Candidates: CA-1 (onBrand hover on home final CTA, `web/src/components/ui/button-variants.ts`, Lucia or Ben) and CA-4 (CopyHash focus loss, if it holds up). Check BOARD.md first.
- Deadline: none stated.
