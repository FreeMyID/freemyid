# Agent channel: Claude (in-house), Codex and Grok

> **Vendor availability (owner, 2026-11-09): Google Antigravity and GitHub Copilot are OUT of order** (token limit / usage exhausted) and will not be back for over a month, not before about 2026-12-10. Assign them no work, don't wake them, and keep `tools/copilot.sh` and its watcher off. Their lanes stay with in-house (see docs/BACKLOG.md). Active vendors: OpenAI Codex and xAI Grok.

Updated 2026-11-09 for three teams. Everything below the "History" heading is the original
Codex–Claude setup from 2026-11-07, kept for reference.

## Who writes which file

Each team writes only files that start with its own name. Read everything addressed to you.

| From → To | File | Message IDs | Written by |
|---|---|---|---|
| Claude → Codex | `CLAUDE_TO_CODEX.md` | CLAUDE-NNN | in-house (Morgan Reyes) |
| Codex → Claude | `CODEX_TO_CLAUDE.md` | CODEX-NNN (Nora numbers) | Codex |
| Claude → Grok | `CLAUDE_TO_GROK.md` | CLAUDE-G-NNN | in-house |
| Grok → Claude | `GROK_TO_CLAUDE.md` | GROK-NNN | Grok |
| Grok → Codex | `GROK_TO_CODEX.md` | GROK-X-NNN | Grok |
| Codex → Grok | `CODEX_TO_GROK.md` | CODEX-X-NNN | Codex |

All files live in `docs/vendor/`. The first message in a file creates it; nobody creates another
team's file, so a file's existence never implies a reply. Boards: Codex = `BOARD.md` (Nora),
Grok = `GROK_BOARD.md`.

## Message format

```
## <ID> — <short subject>
- Date: YYYY-MM-DD
- From: <name / team>
- To: <name / team>   (vendor-to-vendor: always "cc Morgan Reyes")
- Reply to: <ID or none>
- Status: <one line>
```
Then short bullets. Append; never edit or delete earlier messages. No secrets, no real personal data.

## Challenges: vendors push back on in-house (owner rule, 2026-11-09)

In-house (Claude) has the final say, but Codex and Grok are expected to **challenge it**: question decisions, point out what in-house missed, and suggest bolder or simpler approaches their models see. Agreeing by default is not the job.

- **What to challenge:** in-house commits, PRs, work orders, architecture, release choices, wording, tests, process. Anything in the repo is fair to read and criticise, including paths you may not edit.
- **How:** a message headed `## <your ID> — CHALLENGE: <subject>` in your channel to Claude, with: **What** (file:line or commit/PR), **Why it matters** (the user, security, cost, maintainability), **Proposal** (the alternative, as concrete as you can), **Confidence** (high/medium/low). Several small challenges in one message are fine.
- **Think outside the box:** "do it a different way", "drop this entirely" and "this test proves nothing" are welcome, as long as you give reasons.
- **Limits:** a challenge is words, not code. Never edit outside your WO's allowed paths to prove a point. If a prototype would help, ask for a WO. No personal data, no secrets, and the same plain-language rules.
- **In-house must answer every challenge** with ACCEPTED (and what changes), DECLINED (and why) or DEFERRED (to when), in the next reply. Accepted challenges are credited to the vendor in the commit message.
- **Final look:** whatever comes out of a challenge, in-house reviews the resulting PR or commit and decides. Vendor-to-vendor challenges (Grok ↔ Codex) follow the same format and always copy Morgan.

## Vendor-to-vendor rules (Grok ↔ Codex)

- **For coordination only:** shared test fixtures or helpers, a path that looks like it overlaps,
  a finding in the other team's lane, "does your WO touch X?", handing over context.
- **Not for work:** a vendor message never assigns work, approves anything, widens a work order's
  allowed paths, or asks the other team to edit files in its own lane. Those go to in-house.
- **In-house reads both files.** Anything that changes scope, lanes or a deadline: write it to
  Claude too (`CODEX_TO_CLAUDE.md` / `GROK_TO_CLAUDE.md`) and wait for a CLAUDE message.
- **Disagreement:** state both positions in your own file; Morgan decides in a CLAUDE message.
- A request is delivered only when the recipient acknowledges its ID.

## Waking a team

Writing a file does not wake anyone. In-house watches every `*_TO_*.md` file and relays:
- Codex: `tools/codex_wake.sh send "<message>"` (queues to Nora's thread; set `CODEX_CHANNEL_THREAD`
  for another thread).
- Grok: `tools/grok_wake.sh status | send "<message>"`. If a Grok session is open in a terminal, a
  message can't be pushed into it: the owner is asked to type
  "read docs/vendor/CLAUDE_TO_GROK.md" there.
- Vendors can't run these scripts (sandbox, no `~/.codex`/`~/.grok` access). Ask in-house to relay.

---

# History: original Codex–Claude setup (2026-11-07)


Created at the user's request on 2026-11-07 for agents sharing this repository.
This is a file-based handoff, not a connection to either terminal. A dedicated
Codex liaison task was created on 2026-11-07 for an initial 30-minute monitoring
window, checking for replies roughly every 30 seconds while running. This is
not a persistent service. Claude reported its own watcher in CLAUDE-003; its
post-handover availability is unconfirmed (acknowledgment requested in CODEX-016).

## Use

- Codex writes `docs/vendor/CODEX_TO_CLAUDE.md`.
- The Claude project engineer writes `docs/vendor/CLAUDE_TO_CODEX.md`.
- Each agent reads the other file before starting work and at checkpoints.
- Include a message ID, reply-to ID, sender, recipient, and status. Preserve
  previous messages when adding a new one. Each agent writes only its own file.
- A request is delivered only when the recipient acknowledges its ID. A queued
  request does not assign work or establish approval.
- Existing work-order scopes and in-house review requirements still apply.
- Keep secrets and personal information out of messages.

## First connection

Tell the Claude project engineer in its current terminal:

> Read docs/vendor/AGENT_CHANNEL.md and docs/vendor/CODEX_TO_CLAUDE.md.
> Reply in docs/vendor/CLAUDE_TO_CODEX.md, acknowledging CODEX-001 and assigning
> the next non-overlapping Codex work order with any review notes. Use this
> channel for subsequent coordination and check it at work checkpoints.

The Claude reply file is intentionally not created by Codex so that its presence
does not imply a reply or acknowledgment.

## Current liaison window

- Task: `01a1b88b-a4f3-7de0-8b5b-c2a8c1023032` (Codex–Claude live liaison).
- PM: `01a1b886-69b0-7d31-b9d0-90e898fb9eaa`.
- Liaison alone appends receipt acknowledgments to CODEX_TO_CLAUDE.md during
  this window; other Codex workers send findings to the PM.
- Liaison relays new Claude message IDs to PM through the Codex task tool.
- PM alone maintains VENDOR_STATUS.md. Receipt is not approval or acceptance.
- On expiration, liaison reports its last received ID to PM; PM resumes channel
  ownership. No monitoring is promised after expiration or session shutdown.
