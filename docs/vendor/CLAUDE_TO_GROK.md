# Claude → Grok channel

In-house (Morgan Reyes, Claude project engineer) writes this file. Grok replies in `GROK_TO_CLAUDE.md`.
Protocol: `docs/vendor/AGENT_CHANNEL.md`. Contract: the "Grok vendor" section of `AGENTS.md`.

## CLAUDE-G-001

- Date: 2026-11-09
- From: Morgan Reyes (Claude project engineer)
- To: Grok vendor team
- Reply to: none
- Status: channel open; no work order yet (WIP 0/5)

- **Welcome.** You are the third team, beside in-house (Claude) and Codex (Nora Bennett's team). Read `AGENTS.md` (Grok section) and `docs/vendor/AGENT_CHANNEL.md` before anything else.
- **Your files:** reply to me in `docs/vendor/GROK_TO_CLAUDE.md` (GROK-NNN; create it with your first message). Keep `docs/vendor/GROK_BOARD.md`. To talk to Codex directly, write `docs/vendor/GROK_TO_CODEX.md` (GROK-X-NNN) and read `docs/vendor/CODEX_TO_GROK.md`. Vendor-to-vendor messages are for coordination only; anything about scope or work comes to me.
- **Please acknowledge CLAUDE-G-001 as GROK-001** and confirm: (1) the lane in AGENTS.md; (2) that the `freemyid` sandbox actually starts for you. On 2026-11-09 a `grok sessions list` here failed with "socket deny resolution failed: could not resolve runtime-socket deny path /run/podman/podman.sock: Permission denied" and refused to start. If that blocks you, report it exactly; don't loosen the sandbox (`~/.grok/` and `.grok/` are in-house only).
- **Where to run:** your open session is in `~/Documents/CODE` (the parent folder). For work orders, start Grok from the prepared worktree (`cd .vendor-wt/wo-3NN && grok`), so the write area is that worktree only.
- **Next:** first work orders (WO-301+) come after v0.3.1 is out and your sandbox check passes. Proposals welcome in GROK_TO_CLAUDE.md, for your lane only.
