# Codex–Claude project channel

Created at the user's request on 2026-11-07 for agents sharing this repository.
This is a file-based handoff, not a connection to either terminal. No automatic
notifications or background polling are installed.

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
