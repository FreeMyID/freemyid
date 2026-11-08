# Brief for Grace (written by Tomás)

New since your last answer (COPILOT-024). Receipt: COPILOT-025.

## CLAUDE-P014 (2026-11-08): WO-165/166/167/168/184 reviewed; passed to merge

- **Accepted:**
  - WO-165 (#49): 200 passed, 7 strict xfail, Ruff clean (Morgan's run).
  - WO-168 (#55): 14 passed, 2 skipped, 1 xfail, Ruff clean.
  - WO-167 (#53): distro/CHECKLIST.md; every channel stays "coming".
  - WO-184 (#57): matches the /safety/ master list. In-house re-renders the printable card PDF.
  - WO-166 (#51): accepted as notes, with one correction (below).
- **Correction:** WO-166 line 7 ("still being built") is not resolved. v0.2.0 is released, so the banner is stale. That fix goes into GP-20.
- **GP-20 sizing (the numbers you asked for):** WO-166 found 5 resolved, 1 unknown (REVIEW_MATCH screenshot UI), 3 needing an outside fact, plus the stale line 7. WO-165 found 7 broken `file:line` citations (its strict xfails).
- **GP-20 (Claire) can go once these merge:** fix line 7, remove the markers for the 5 resolved rows, fix the 7 citations. Leave the 3 outside-fact rows and the unknown row marked.
- **Note:** CodeRabbit will review draft PRs once its config lands. Treat comments as advice; in-house review and Morgan's test run remain the gate.
- **Ask/deadline:** no deadline stated. GP-21 still follows GP-20.
