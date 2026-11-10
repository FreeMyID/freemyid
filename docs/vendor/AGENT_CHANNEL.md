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

## Away-week operating rules (in-house offline until about 2026-11-14)

Goal: nobody waits on in-house. These rules override anything earlier that would make you stop.

**Scope (exact; enforced by `.grok/config.toml` for Grok and by `tools/vendor.sh` scope checks before any merge):**
- You change only the paths listed under "Allowed paths" in your WO, inside your own worktree `.vendor-wt/wo-NNN`. Nothing else, ever.
- Codex lane and Grok lane are in AGENTS.md "Your lane". A file in the other team's lane is off limits even if a WO lists it by mistake: stop that WO and report it.
- In-house only, never editable: `src/freemyid/wizard/`, templates, `web/`, `site*/`, `brand/` (except `brand/codex/`), security core (crypto, secrets, secret_backends, netpolicy, consent, logging_setup, storage/, engine/browser.py), contracts (models, interfaces, state, registry, config, paths, cli.py, `__init__.py`, schema/), `.github/`, `packaging/`, `tools/`, `pyproject.toml`, `.claude/ .codex/ .grok/`, AGENTS.md, CLAUDE.md, docs/VENDOR.md, WO files, team rosters, CLAUDE_TO_* files, EPICS.md.
- Never: git, gh, push, installs, network access, reading outside the repo (no `~/.config`, keyrings, `.env`, home directory), real personal data, secrets. Grok's sandbox can't technically block network or home reads on this machine: the rule still applies, and breaking it ends the engagement.

**No blockers:**
1. **WIP 5 counts only WOs you are actively building.** Delivered-and-waiting-for-review WOs don't count. Deliver, then pull the next queued WO.
2. **Blocked WO** (Status `blocked: ...`): skip it and take the next queued one. Don't try to unblock it yourself.
3. **"Start after WO-NNN"** means after WO-NNN is *delivered*, not merged. Start your worktree from main, then copy in WO-NNN's delivered changes for the shared file (read-only from `.vendor-wt/wo-NNN/`; reading your own team's sibling worktree is allowed for this) and say so in VENDOR_STATUS.md. In-house merges them in order.
4. **Needs a contract change mid-WO:** don't change the contract. Do everything possible behind the existing interfaces, write exactly what's missing under "Questions for the owner", deliver what you have as partial, and move on.
5. **Unclear spec:** choose the most conservative reading (least data sent, least behaviour change, most user-friendly), write the choice in VENDOR_STATUS.md, and keep going. Don't wait for an answer.
6. **Tests that can't run in your sandbox** (browser/Chromium, sockets): record them as "skipped in sandbox, needs in-house rerun", never as passing. That doesn't block delivery.
7. **A failing existing test unrelated to your change:** note it with the exact output and continue. Don't edit tests outside your WO to make them pass.
8. **Queue empty or all blocked:** send CHALLENGE messages (critique in-house code, docs, roadmap), propose new WOs in your proposals file, or improve tests/docs inside your own lane. No new code outside a WO.

**Delivery checklist (each WO):** required checks pass with exact counts; `git diff`-equivalent reviewed by your delivery lead; only allowed paths touched; VENDOR_STATUS.md has Done / Next / Questions / How to test; one channel message with the WO and its tracker issue number; board updated.

## Challenges: vendors push back on in-house (owner rule, 2026-11-09)

In-house (Claude) has the final say, but Codex and Grok are expected to **challenge it**: question decisions, point out what in-house missed, and suggest bolder or simpler approaches their models see. Agreeing by default is not the job.

- **What to challenge:** in-house commits, PRs, work orders, architecture, release choices, wording, tests, process. Anything in the repo is fair to read and criticise, including paths you may not edit.
- **How:** a message headed `## <your ID> — CHALLENGE: <subject>` in your channel to Claude, with: **What** (file:line or commit/PR), **Why it matters** (the user, security, cost, maintainability), **Proposal** (the alternative, as concrete as you can), **Confidence** (high/medium/low). Several small challenges in one message are fine.
- **Think outside the box:** "do it a different way", "drop this entirely" and "this test proves nothing" are welcome, as long as you give reasons.
- **Limits:** a challenge is words, not code. Never edit outside your WO's allowed paths to prove a point. If a prototype would help, ask for a WO. No personal data, no secrets, and the same plain-language rules.
- **In-house must answer every challenge** with ACCEPTED (and what changes), DECLINED (and why) or DEFERRED (to when), in the next reply. Accepted challenges are credited to the vendor in the commit message.
- **Final look:** whatever comes out of a challenge, in-house reviews the resulting PR or commit and decides. Vendor-to-vendor challenges (Grok ↔ Codex) follow the same format and always copy Morgan.

## GitHub tracking: one place for every work order (owner rule, 2026-11-09)

All three teams (Claude in-house, Codex, Grok) work from the same tracker: the private repo `FreeMyID/freemyid-pm` (one issue per WO, SEC finding and owner task) and the org Project "Free My ID delivery" (https://github.com/orgs/FreeMyID/projects/1; fields Status, Team, Lane, Kind, Priority, Agent, WO, Release). The WO files stay the source of truth; the issues mirror them through `tools/pm_sync.py`.

- **In-house** runs `FREEMYID_PM_APPLY=1 .venv/bin/python tools/pm_sync.py --apply --repo FreeMyID/freemyid-pm --project 1` after every change to a WO file or board, every GO, every delivery and every merge. Dry run first (`tools/pm_sync.py --dry-run`).
- **Codex and Grok** have no network or gh, so they never write to GitHub. They **cite the tracker issue** for each WO in every channel message, in VENDOR_STATUS.md and on their board: look it up in `docs/pm/issue_map.json` (key `WO-NNN`), e.g. "WO-301 (freemyid-pm#212)". A new WO gets its issue number at the next sync; until then write "issue pending".
- **PRs and merge commits** name the WO and its issue: "WO-301 (freemyid-pm#212)". A PR on the public repo never links the private issue as a URL in the description body; use the key and number only.
- **Challenges** (above) that in-house ACCEPTS become a WO or an in-house task, and so get their own tracker issue.
- Status flow and fields: docs/SDLC.md.

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
