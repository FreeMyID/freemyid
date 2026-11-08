# How we build: one process for all three teams

In-house Claude agents, the Codex team (PM Nora Bennett) and the Copilot team (PM Grace Holloway) all follow this.
Tracking lives in the private repo `FreeMyID/freemyid-pm` and the private Project "Free My ID delivery".
The code repo `FreeMyID/freemyid` is public, so no tracking detail goes there that shouldn't be public.

## The lifecycle

1. **Issue (PM-#).** Every piece of work has one issue. Labels: team, kind, lane, priority.
2. **WO file and branch.** Work orders are files in `docs/vendor/WO-NNN.md`. Branch `vendor/wo-NNN` for vendors, `inhouse/<topic>` for in-house.
3. **Commits** under staff names (`.claude/agents/_shared-rules.md` rule 14), noreply email only, no AI attribution.
4. **Pull request** on `FreeMyID/freemyid`, referencing PM-#. Morgan opens PRs for vendor work. CI must pass and qa-security reviews. No security details in public text before a fix ships.
5. **Merge locally** with `--no-ff` by Morgan. Never the web button and never `gh pr merge` (SEC-93c, email leak).
6. **Push** of the exact SHA the full suite ran on.
7. **Close.** `tools/pm_sync.py` closes the issue with the merge SHA.
8. **Release.** The issue sits in a release milestone (v0.3, v0.4). The release is tagged by the orchestrator after the owner's go.

## Status and who moves it

| Status | Meaning | Moved by |
|---|---|---|
| Backlog | Idea or planned, no WO yet | PM of the lane |
| Ready | Meets Definition of Ready | Morgan |
| In progress | A builder has started | The builder's team (via status file) |
| In review | PR open, CI/qa-security running | Morgan |
| Done | Merged locally and pushed | pm_sync (from the merge commit) |
| Blocked | Waiting on a decision or owner task | Whoever finds the block |

## Definition of Ready
- Goal in plain words, testable acceptance criteria, and allowed paths all in one lane.
- No overlap with another open WO (BOARD.md check).
- Release target set.

## Definition of Done
- Acceptance criteria met; tests and ruff pass; CI green.
- qa-security reviewed (no open MED+).
- Merged locally with `--no-ff`, exact tested SHA pushed.
- Docs or handoff updated; issue closed with the SHA.

## How vendors report
Vendor builders can't run `gh`. They update their status file (`VENDOR_STATUS.md` and the channel docs). Morgan then runs
`tools/pm_sync.py` (dry-run first). The files stay the source of truth; the issues mirror them.

`tools/pm_sync.py --dry-run` is the default and makes no network calls. `--apply` writes to GitHub and refuses to run
unless `FREEMYID_PM_APPLY=1` is set. The mapping file `docs/pm/issue_map.json` keeps it from creating duplicates.
Staged setup files are in `docs/pm/` (labels, milestones, issue templates).

## Later option
A GitHub Actions job in `freemyid-pm` could run the sync on a schedule from a read-only checkout. Not needed yet.
