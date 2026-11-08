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

## Where the teams talk

Tracker: private repo FreeMyID/freemyid-pm (issues) plus the private org Project "Free My ID delivery" (once gh has the `project` scope). Each WO, open SEC finding and owner task has one issue; `docs/pm/issue_map.json` maps keys to issue numbers.

- The channel files (`docs/vendor/CLAUDE_TO_*.md`, `*_TO_CLAUDE.md`) stay the working channel, because vendor builders can't run gh. Morgan mirrors each message that concerns a WO as a comment on that WO's issue ("CODEX-061: ..." or "CLAUDE-P013: ..."), so the issue holds the full history.
- No GitHub Teams: all three teams work under one GitHub account, so team grouping is the `team:*` label and the Project's Team field.
- Open SEC findings are listed in `docs/pm/tracked.json` (Marcus keeps it current). Issues show ID, severity, owner and status only.
- Run `tools/pm_sync.py --dry-run` to see the plan, and `FREEMYID_PM_APPLY=1 tools/pm_sync.py --apply --repo FreeMyID/freemyid-pm` to sync. It's idempotent: re-running changes only what moved.

## Codex with GitHub and Canva (owner, 2026-11-08)

Codex now has a GitHub plugin (signed in as the owner's account, GrayManSam) and a Canva plugin.

- **GitHub, allowed:** create and comment on issues in the private FreeMyID/freemyid-pm, and set their Project fields. A new idea is an issue titled `Proposal: ...` with labels `team:codex` and Status Backlog. Once Morgan accepts it, he writes `docs/vendor/WO-NNN.md` and renames the issue `WO-NNN: ...`; pm_sync adopts it (no duplicate), adds the planned lane/kind/priority labels and milestone, and posts the work-order mirror as a comment (the proposal text is kept). A closed issue is reopened if the WO is still open. Codex may also open a PR from its own `vendor/wo-NNN` branch on FreeMyID/freemyid when a WO says so.
- **GitHub, never:** pushing to `main`, merging or approving PRs, commits made in the GitHub web editor or through the API (they can expose the owner's email, SEC-93c), releases, tags, settings, secrets, Actions, Pages, or anything on a public issue/PR that names a SEC finding's details. Morgan merges locally with `--no-ff`.
- **Canva (design lane, `brand/codex/`):** Codex designs social posts, Open Graph images, website illustrations and app art in Canva from a design WO. Each WO names the requester (Jordan in brand-marketing for social, the seo-growth lead for search images, Leo for the website) and the reviewer (the in-house graphic-designer).
  - Follow docs/BRAND.md (colours, type, tone) and docs/POSITIONING.md (claim rules). Copy on an image comes from the WO, word for word.
  - Export to `brand/codex/<WO>/` as PNG (and SVG or PDF where Canva allows), at the sizes the WO lists, plus light/dark pairs for site art. Record each file in `brand/codex/MANIFEST.md`: file, WO, the Canva design link, any Canva stock elements used, and alt text.
  - One writer for the manifest: when design WOs run at the same time, each designer puts its rows in `brand/codex/<WO>/ROWS.md` and the Codex lead alone merges them into `brand/codex/MANIFEST.md`, so a stale copy can't overwrite another designer's rows.
  - Closing a design WO: a design-only WO has no `Merge WO-NNN` commit, so pm_sync can't mark it done by itself. When the graphic-designer approves, Morgan commits the files and sets the WO's line to `Status: done (<delivery commit>)`; the next sync closes the issue. The same applies when a design WO is delivered in-house.
  - The logo, wordmark and app icons stay in-house SVG; no Canva stock in them (Canva's license does not allow stock in trademarks). Use no photos of real, identifiable people unless they are licensed stock and the WO allows it. Show no real personal data on screens or mock-ups: use Jane Q Testperson, Springfield IL.
  - The graphic-designer reviews, then copies approved files into `brand/`, `web/` or the app (a copy, not a move: the export and its MANIFEST row stay in `brand/codex/`, which in-house does not write). Codex never edits those folders, except its own subtrees `brand/codex/` and `web/src/pages/developers/` (docs/BACKLOG.md lane table).
