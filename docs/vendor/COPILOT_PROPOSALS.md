# Copilot team proposals

Written by Grace Holloway (Copilot project engineer). Items are `GP-##`. Proposals are not work orders: Morgan Reyes
accepts or declines them in docs/vendor/CLAUDE_TO_COPILOT.md and writes the work order. Check docs/vendor/BOARD.md for
path collisions before proposing; never propose an in-house-only path (.github/copilot-instructions.md).

First wave, 2026-11-08 (reply to CLAUDE-P001). Collisions checked by eye against BOARD.md (state at CODEX checkpoint
CODEX-037); none of these paths are listed there. I did not run a repo search, so evidence lines cite the audit.

## GP-01: CLI docs fixes (CLI-A03, CLI-A05)
- Agent: app-features (Claire Dubois)
- Evidence: `docs/vendor/v02-cli-doc-audit.md` rows CLI-A03 (CLI.md command table omits `checklist list/show/done/undo`) and CLI-A05 (README and USER_GUIDE do not link to CLI.md). Both are labelled P3 and narrow in the audit.
- Proposed allowed paths: `docs/CLI.md`, `README.md`, `docs/USER_GUIDE.md`.
- Deliverable: add four checklist rows to the CLI.md table with the existing schema names (`checklists/1`, `checklist/1`) and a short "full reference" link in README and the USER_GUIDE helper section. Keep the user guide short and keep released versus planned wording. Optional, if Morgan agrees: CLI-A04 terminal prefill spelling.
- Collisions: WO-002 once held CLI.md and is merged; the board shows no active hold. Morgan to confirm no in-house edit of README or CLI.md is open.
- Not included: CLI-A01 (developer page, held by WO-111 and in-house), CLI-A02 and CLI-A04 wording (need Morgan's decision).

## GP-02: Docs spellings match the CLI (test only)
- Agent: test-quality (Malik Johnson)
- Evidence: CLI-A01 and CLI-A03 are both cases of docs naming a command that does not match the registered CLI. Nothing tests that. Existing tests cover JSON output, not docs.
- Proposed allowed paths: `tests/test_cli_docs_match_source.py` (new).
- Deliverable: using the Typer app in `src/freemyid/cli.py` (read only), check that every command and subcommand appears in the `docs/CLI.md` command table, and that each `freemyid <words>` example in `docs/CLI.md`, `README.md` and `docs/USER_GUIDE.md` resolves to a real command. Hidden commands such as `run --scheduled` are exempt. No network, no new dependencies, fake data only.
- Dependency: lands after GP-01. If it must go first, the checklist case ships as a strict xfail with a reason.
- Collisions: new file; no overlap on the board.

## GP-03: Website contrast and keyboard-focus audit (notes only)
- Agent: web-designer (Lucia Ferraro)
- Evidence: not verified. This is a proposal to find evidence, not a claim of a defect. The older Codex CP-09 families audit is unstarted per the board, so this one avoids `web/src/pages/families/`.
- Proposed allowed paths: `docs/vendor/web-contrast-audit.md` (new).
- Deliverable: read-only review of design tokens and shared components in `web/` for text and background contrast and visible keyboard focus, with file and line evidence, a proposed fix list and any measured ratios labelled as computed or unverified. No edits to `web/`; Morgan decides what becomes a work order.
- Collisions: new file in `docs/vendor/`; the work order must name it explicitly as allowed.
