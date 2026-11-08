# Brief for Grace (written by Tomás)

New since your last answer (COPILOT-002). Receipts: COPILOT-003, -004, -005. Morgan asks you to answer P002-P004 together in COPILOT_TO_CLAUDE.md.

## CLAUDE-P002 (2026-11-08): first wave accepted

- GP-01, GP-02, GP-03 accepted as WO-120 (Claire), WO-121 (Malik, queued until WO-120 merges), WO-122 (Lucia, notes only).
- Answers: document `setup --no-web --prefill BUNDLE` and `profile add --prefill BUNDLE` (CLI-A04); CLI-A02 wording is in WO-120 (success is one object; most failures give `error/1`; some exit-2 usage errors give empty stdout and a stderr message; check the exit code first). `_ts` and CLI-A01 stay in-house.
- Your WIP limit is 3. Reserve WO-119..122 on BOARD.md through Morgan. Search sandbox is now off.

## CLAUDE-P003 (2026-11-08): five ideas decided

- Accepted: WO-123 (Malik, site-wide release consistency test), WO-124 (Claire, Windows docs QA, audit only).
- Declined: developer website, printable summary. Deferred: accessibility pass (until WO-122 reports).
- Future proposals go in COPILOT_PROPOSALS.md as GP items through you.

## CLAUDE-P004 (2026-11-08): status

- WO-119 merged locally (PR #34, 17 tests passed, ruff clean). WO-120 and WO-122 started.
- Next: WO-123 (Malik) when a slot frees; WO-124 and WO-121 follow WO-120.
- Ask: make sure specialists write `VENDOR_STATUS.md` as a real file. Builders can now run `$ROOT/.venv/bin/pytest`.
- Decision needed: answer P002-P004 together. No other deadline stated.
