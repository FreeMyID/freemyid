# Outside vendors: Google Antigravity and OpenAI Codex

Owner-approved 2026-11-07. Two vendor teams work side by side with the in-house Claude agents: Google Antigravity (CLI `agy`, rules in GEMINI.md) and OpenAI Codex (CLI `codex`, rules in AGENTS.md). Each works like an outside contractor team: the Free My ID owner/engineer (Morgan Reyes) sets the scope, checks in, and accepts or rejects the work. Rule 15 in .claude/agents/_shared-rules.md.

## Lifecycle of a work order
1. **Scope.** The owner writes `docs/vendor/WO-NNN.md` from the template below and commits it.
2. **Start.** `tools/vendor.sh start WO-NNN` creates branch `vendor/wo-NNN` in a fresh worktree of `main` (gitignored private files never exist there) and runs the vendor in builder mode with the work order. After each vendor session the script commits the vendor's changes on that branch.
3. **Check-ins.** `tools/vendor.sh checkin WO-NNN "message"` sends the owner's notes (answers, corrections, next steps) and the vendor continues. `tools/vendor.sh status WO-NNN` shows VENDOR_STATUS.md, the diff summary and any files changed outside the allowed paths.
4. **Pull request.** `tools/vendor.sh pr WO-NNN` (owner tooling, owner's credentials) refuses out-of-scope changes, pushes `vendor/wo-NNN` and opens or updates a draft PR with VENDOR_STATUS.md as its description. Review comments, in-house edits and the merge all happen on that PR, so every change is tracked. Vendors never push.
5. **Acceptance.** When the vendor reports done: the owning in-house agent reviews the diff line by line as an outside pull request; qa-security reviews anything near security, privacy, network or PII; the full gate passes (pytest, ruff, mypy, site checks). Accepted work is squashed onto main by the reviewer under their staff name, with "vendor-assisted (WO-NNN)" in the message. Rejected work gets a check-in with the reasons, or the work order is closed.
6. **Close.** `tools/vendor.sh close WO-NNN` removes the worktree. The branch stays for the record until merged or deleted.

## In-house only (never in a work order)
`src/freemyid/{crypto,secrets,secret_backends,netpolicy,config,models,state}.py`, `src/freemyid/engine/mail*.py`, `storage/`, consent and practice-mode logic, anything that sends email or submits forms for real, `.github/workflows/`, release and signing, `tools/social/`, the private registry and research files.

## Good vendor work
Website pages and components (web/), app UI screens and copy (src/freemyid/wizard/ templates and views, not security logic), translations, docs, tests for existing behaviour, developer tooling, accessibility fixes.

## Work order template (docs/vendor/WO-NNN.md)
```
# WO-NNN: <title>
Status: open | in progress | review | accepted | closed
Vendor: agy | codex
Agent: <codex team role file, e.g. web-builder> (codex only)
Owner contact: Morgan Reyes (check-ins via tools/vendor.sh)
## Goal
## Acceptance criteria (testable)
## Allowed paths (the vendor may change ONLY these)
## Out of scope / do not touch
## Check-in plan (e.g. after the first session, then when done)
## Notes and decisions (owner appends after each check-in)
```

## Vendor differences
- **Antigravity (`agy`)**: file tools only; it cannot run commands in hands-off mode, so the owner runs the tests at each check-in.
- **Codex (`codex exec -s workspace-write`)**: Codex reads code through small shell commands, so it may run read-only commands and the tests inside its worktree. Its sandbox blocks writes outside the worktree and all network; AGENTS.md and the prompt forbid reading outside the worktree.
- Pick per work order with the `Vendor:` line (or `VENDOR=codex tools/vendor.sh ...`). Give each vendor different paths so their branches never conflict.

## Autonomous mode (owner decision 2026-11-07)
The vendor teams know the roadmap, so they choose their own work. `tools/vendor.sh auto [N]` runs the Codex lead (Elena Vasquez) with write access to `docs/vendor/` only. She picks up to N pieces of work for the current release, writes the work orders herself and names a specialist for each. The script then runs each specialist and opens a pull request for each. No owner approval is needed before work starts: control sits at the pull request, where the in-house team reviews, edits, merges or rejects.
Hard limits that hold in every mode, enforced by the script:
- The in-house-only list (`DENY_PREFIXES` in tools/vendor.sh: security, secrets, storage, mail, consent, network policy, server security, CI, packaging, release, tools/social, private data, and the vendor rules themselves) can never be changed by a vendor. A work order that lists such a path is skipped, and a branch that touches one gets no pull request.
- Changes outside the work order's own allowed paths block its pull request.
- Vendors never push or hold credentials; nothing reaches main without in-house review.
