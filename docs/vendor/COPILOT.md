# Copilot vendor team (GitHub Copilot coding agent)

Third outside vendor, next to the Codex team (docs/vendor/codex-team/) and the in-house Claude team. Set up
2026-11-08 at the owner's request. Same principle as docs/VENDOR.md: a vendor works only from a work order,
only in its allowed paths, and nothing reaches `main` without in-house review.

## How it differs from Codex
| | Codex team | Copilot team |
|---|---|---|
| Where it runs | Local sandbox in `.vendor-wt/wo-NNN` | GitHub Actions sandbox (environment from `.github/workflows/copilot-setup-steps.yml`) |
| Hand-off | `docs/vendor/WO-NNN.md` + channel files | The same WO file, copied into a GitHub issue labelled `vendor:copilot` |
| Talking to it | CLAUDE_TO_CODEX.md / CODEX_TO_CLAUDE.md | Issue and PR comments (`@copilot ...` on the PR to request changes) |
| Git | Never; owner tooling commits | Commits and pushes its own `copilot/*` branch, opens a draft PR. Never `main`. |
| Path guard | Sandbox + `tools/vendor.sh` scope check | Instructions + `tools/copilot.sh scope` before merge (soft guard; the review is the wall) |
| Rules | AGENTS.md, codex-team/ | `.github/copilot-instructions.md`, `.github/agents/*.agent.md`, `.github/instructions/` |

## Roles (custom agents in .github/agents/)
`web-builder`, `web-designer`, `app-ui`, `app-features`, `test-quality`: the same specialist split as the Codex
team, so a work order's `Agent:` line works for either vendor. No Copilot lead: the owner writes Copilot work
orders, and Copilot does not plan its own work (no autonomous mode).

## Lifecycle
1. **Scope.** The owner writes `docs/vendor/WO-NNN.md` with `Vendor: copilot` and an `Agent:` line, reserves its
   paths on docs/vendor/BOARD.md (tell Nora in the channel so the Codex board stays the single collision guard)
   and commits it.
2. **Issue.** `tools/copilot.sh issue WO-NNN` opens the issue. The owner assigns it to Copilot and picks the
   named custom agent in the assignee dialog.
3. **Work.** Copilot opens a draft PR. Check-ins are PR comments starting with `@copilot`.
4. **Review.** `tools/copilot.sh scope PR` must be clean. The owning in-house agent reviews the diff line by line;
   qa-security reviews anything near security, privacy, network or PII. CI must be green.
5. **Merge.** `tools/copilot.sh merge PR` squashes onto local `main` as `Copilot team [freemyid-copilot]` with the
   noreply email (the squash drops Copilot's co-author trailer: no AI attribution in history). Run the full
   suite on that exact SHA, push it (`git push origin <sha>:main`), then close the PR with a comment naming the
   commit. Never the web merge button or `gh pr merge` (SEC-93c).
6. **Close.** Mark the WO `Status: closed` and update BOARD.md.

## Good Copilot work
Copilot is strongest at tests, repetitive code and well-specified, narrow changes. Give it test-only and small
UI or page work with exact acceptance criteria. Keep security-adjacent and cross-cutting work in-house.

## Owner prerequisites
- A Copilot plan that includes the coding agent, enabled for the FreeMyID org and this repository.
- `main` protected: no direct pushes, PRs only.
- The `copilot-setup-steps.yml` workflow lives on the default branch (Copilot only reads it from there).
- Billing: the coding agent uses Actions minutes (free on this public repo) and Copilot AI credits.
