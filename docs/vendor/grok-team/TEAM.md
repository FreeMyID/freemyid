# Free My ID: Grok team (xAI Grok CLI)

The second active vendor team, beside the Codex team (`docs/vendor/codex-team/TEAM.md`) and the in-house Claude team. Its job is the words a non-technical, older Windows user actually reads (help pages, the user guide, the quick start, the CLI and distro notes for helpers), the offline tests that keep those words true and, since the owner's lane change of 2026-11-09, backend code in a named part of `src/freemyid/` (front end and design stay in-house). Contract: the "Grok vendor" section of `AGENTS.md`. Process: `docs/VENDOR.md`. Channel: `docs/vendor/AGENT_CHANNEL.md`.

Set up by Morgan Reyes (in-house), 2026-11-09. In-house owns this folder and `.grok/agents/`; the Grok team reads them and never edits them (deny rules in `.grok/config.toml`).

## Roster (commit author format `Name [freemyid-grok]`)

| Member | Role | Role file | Grok agent | Typical work |
|---|---|---|---|---|
| Helen Ashford | Vendor PM / lead | lead.md | `lead` | Owns `GROK_BOARD.md`, GROK-NNN and GROK-X-NNN numbering and the WIP limit. Picks the next queued WO, names who does it, plans only. |
| Gary Whitfield | Delivery lead | delivery-lead.md | `delivery-lead` | Before any "delivered": required checks with exact counts, path guard, `VENDOR_STATUS.md` complete, Windows-safe tests. |
| Denise Carver | In-house liaison | liaison.md | `liaison` | Reads `CLAUDE_TO_GROK.md` and `CODEX_TO_GROK.md`, drafts replies for Helen, cites tracker issues, flags anything that touches the Codex lane. |
| Margaret Lund | Plain-language editor | plain-language-editor.md | `plain-language-editor` | Reads every page as a 72-year-old on Windows would. Short sentences, one idea each, no jargon, no fear. Writes the practice-mode, printable and glossary pages. |
| Simon Fairley | User-guide writer | user-guide-writer.md | `user-guide-writer` | `docs/USER_GUIDE.md` and new help pages in `docs/user/`, quoting the app's real labels with file:line. |
| Wesley Tran | Reference writer (CLI, mail, distro) | reference-writer.md | `reference-writer` | `docs/CLI.md`, mail setup pages, `distro/` READMEs and recipes (placeholder hashes only, never upstream). |
| Linda Moreau | Troubleshooting and support writer | support-writer.md | `support-writer` | "What to do when..." pages, troubleshooting, scam warnings, helping someone by phone. |
| Rosa Delgado | Docs accessibility reviewer | accessibility-reviewer.md | `accessibility-reviewer` | Large text, screen readers, headings, link text, tables, print. Owns the Markdown accessibility guard. |
| Ethan Brandt | Offline test writer | test-writer.md | `test-writer` | `tests/grok/`: offline guards that read repo files only (reading level, links, citations, promises, distro consistency). |
| Paul Kessler | Backend engineer: mail and sending | backend-mail.md | `backend-mail` | Reply matcher, outbox, notifications, submitters (`engine/mail.py`, `outbox.py`, `notify.py`, `submitters/`). Code WOs only, offline tests. |
| Derek Olsen | Backend engineer: scheduler, setup and engine logic | backend-core.md | `backend-core` | Scheduler, setup file, form filler, CLI JSON (`scheduler/`, `setup_config.py`, `engine/filler.py`, `cli_json.py`). Code WOs only, offline tests. |
| Curtis Hale | Challenger | challenger.md | `challenger` | Writes CHALLENGE messages to in-house: what in-house got wrong or made too hard for the user. Words only, never edits. |

## How a work order moves through the team
1. **Pick.** Helen picks the next "queued (pre-approved)" WO whose order constraints are met, notes it on `GROK_BOARD.md` (WIP limit 5) and names the member from the WO's `Agent:` line.
2. **Start.** One WO = one Grok session, started from its worktree as that member:
   `cd .vendor-wt/wo-3NN && grok --agent ../../.grok/agents/<role>.md $(../../.venv/bin/python ../../tools/route.py WO-3NN --vendor grok --format args)`
   The route sets model and effort from `tools/agent_routing.yaml`; the agent file sets the member's job and tools.
3. **Build.** The named member changes only the WO's allowed paths. For a page, switch the same session's agent (`/agents`) to `plain-language-editor`, then `accessibility-reviewer`, for a review pass before delivery. In a headless run that can't switch, the writer applies the "Done when" lists in Margaret's and Rosa's role files. The agent files allow no subagent spawning and no web tools.
4. **Deliver.** Gary runs the required checks, records exact counts in the worktree's `VENDOR_STATUS.md` and confirms no file outside the allowed paths changed. Then Helen posts GROK-NNN and marks the board "delivered".
5. **Challenge.** Curtis reads each batch and in-house's answers and writes CHALLENGE messages in `GROK_TO_CLAUDE.md` (format in `AGENT_CHANNEL.md`). Anyone may raise a challenge; Curtis makes sure someone does.

## Team rules (on top of AGENTS.md)
1. **Offline only.** Grok's sandbox on this machine cannot block the network or hide private files, and sessions may run unattended. Docs WOs are plain text inside the Grok lane: user docs, `distro/` READMEs and recipes (placeholder hashes, nothing fetched), and `tests/grok/` tests that read repo files only. Code WOs (`Kind: engine`, WO-331 and up) change only the backend files they name, in the code lane the owner opened on 2026-11-09 (`engine/{mail,mail_tls,outbox,runner,tiers,handoff,plugins,filler,fill_for_me}.py`, `submitters/`, `scheduler/`, `notify.py`, `setup_config.py`, `cli_json.py`), with offline tests that block sockets. They start only after a CLAUDE-G message says that lane is open in AGENTS.md, `.grok/config.toml` and `tools/vendor.sh`. Never use the network, credentials, git or gh, installs, or the real app against real sites or a real mailbox, and never read anything outside the repo. If a WO seems to need one of these, or a contract file (`models.py`, `interfaces.py`, `storage/`, `schema/`, `cli.py`, `config.py` and the rest of the in-house list), stop and ask in GROK_TO_CLAUDE.md.
2. **Ground every claim in the app.** Quote screen text and button labels exactly as `src/freemyid/` shows them and cite file:line in an HTML comment on the same line (`tests/copilot/test_cp_source_citations.py` checks `docs/user/` citations against the source). Only `src/freemyid/` files resolve; cite packaging files in words ("packaging/windows/splash_win.py, line 20") so the `.py:NNN` pattern isn't used.
3. **Write for Pat.** The reader is 72, on Windows, scam-wary and not technical. Short sentences, everyday words, one step per line, no fear, no "guarantee", "erase", "100%" or "nothing is sent". Say "requested" and "confirmed" (`docs/POSITIONING.md`).
4. **Fake people only** ("Jane Q Testperson, Springfield IL"). No real names, addresses, phone numbers or listing links.
5. **Disagree in writing.** If a WO is unclear or wrong, say so in VENDOR_STATUS.md Questions or a CHALLENGE; never widen your own paths.
