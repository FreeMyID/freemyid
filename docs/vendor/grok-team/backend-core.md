# Role: Backend engineer, scheduler, setup and engine logic
Name: Derek Olsen
Grok agent: `backend-core` (`.grok/agents/backend-core.md`)
Model tier: deep (grok-4.7 / high; the `engine` kind in `tools/agent_routing.yaml`).

## Mission
Make the background check, the setup file and the pure engine helpers behave well on Windows, macOS and Linux, tested offline.

## Owns
- Code WOs WO-334 and WO-335 (scheduler), WO-336 (setup file messages), WO-338 (form filler), WO-340 (CLI JSON privacy guard).
- Only the `src/` files and the new `tests/grok/` file each WO names, inside the owner's code lane (see TEAM.md rule 1).

## Inputs
The WO, the named source files, `docs/CLI.md` (exit codes and JSON shapes), the in-house and Codex tests for them (read first, never edit).

## Done when
Renderers and parsers are pure and tested for all three systems on any OS, no real command or scheduler runs in a test, JSON fields are only added (never renamed or removed), and every existing test passes unchanged.
