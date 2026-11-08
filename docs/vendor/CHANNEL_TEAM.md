# Interactive Codex vendor team

Started at the user's explicit request on 2026-11-07. This team belongs to the
interactive channel session. It does not replace Elena's independently running
Codex team or take any work allocated to her specialists.

## Active roster

Fictional working names and role instructions: [CHANNEL_PERSONAS.md](CHANNEL_PERSONAS.md).
Names label existing runtimes; no new agents were created for this roster.

| Name | Runtime | Job | Current state |
| --- | --- | --- | --- |
| Nora Bennett | Current PM task | Vendor project manager; sole shared status/team-doc writer | Coordinates Claude assignments and reviews |
| Owen Brooks | Prior lead task | Delivery lead for existing three children | Planning consolidated; workers available |
| Maya Chen | ui_review under Owen | UI and accessibility specialist | WO-103 planning complete; awaiting scope |
| Iris Patel | test_review under Owen | Tests and regression specialist | WO-106 planning complete; awaiting scope |
| Samir Vale | queue_coordinator under Owen | Scope, dependencies and path conflicts | Queue audit complete; assignments pending |
| Jules Mercer | Dedicated liaison task | Claude channel monitoring and receipt acknowledgments | Monitoring confirmed active for initial 30-minute window; Claude acknowledgment pending |

Availability is session-dependent. Names do not imply persistent background
services or identify the user's five unconfirmed Ready sessions.

## Dispatch rules

1. Nora owns this board, CODEX_PROPOSALS.md and shared VENDOR_STATUS.md.
   Jules alone appends outbound channel receipt acknowledgments during the
   documented liaison window; Nora resumes channel ownership afterward.
   Other workers send results through Owen to Nora.
2. Work from Claude-assigned work orders and their prepared worktrees. Each
   implementation assignment names exact files, permitted helpers and required
   checks. No two agents write the same path concurrently.
3. Independent read-only review may run alongside implementation. Do not create
   a competing implementation of a delivered work order while it is in review.
4. No git, network, dependency installs, real personal data or protected in-house
   changes. Follow AGENTS.md and docs/VENDOR.md. Only owner tooling creates
   worktrees, commits, pushes, opens PRs and integrates dependencies.
5. After a worker reports completion, root checks scope, considers review
   findings, runs necessary checks, updates status and posts one owner handoff.
6. Await prepared WO-103/106 and owner integration of WO-101 into WO-102. Do not
   take Elena's five proposal allocations or infer approval from a queued item.

## Current review results

- ui_review: no actionable correctness findings in WO-104; actual assistive-
  technology announcement remains unverified. Source review only, no rerun.
- test_review: no blocking findings; WO-105 independently reran, 4 passed. WO-102 independently confirmed 3 passed/1 dependency failure. Completed the narrow improvement: actual main-illustration role and aria-label asserted. Ruff passed; 3 source tests pass and strict dependency assertion still fails. No product edits.
- queue_coordinator: no new implementation worktree available. WO-102 requires owner integration; WO-103/106 require prepared work orders/worktrees. Identified and corrected stale proposal status text.
