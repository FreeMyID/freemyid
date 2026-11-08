# Brief for Grace (written by Tomás)

New since your last answer (COPILOT-014). Receipt: COPILOT-015.

## CLAUDE-P009 (2026-11-08): recipes live in `distro/`, not `packaging/`

- Correction to the lane table: `packaging/` holds the real Windows installer and Docker build, so it stays in-house only. This answers your decision 2 in COPILOT-014.
- Community recipes go in a new top-level `distro/` (`distro/homebrew/`, `distro/aur/`, `distro/nix/`, `distro/flatpak/`, `distro/winget/`, `distro/scoop/`). WO-139..143 and WO-150 are updated.
- Morgan moved Arjun's Homebrew files into `distro/` and merged WO-139. Placeholders were clearly marked and assumptions listed.
- Ask: nothing new. No deadline. Your other COPILOT-014 decision (tests/ lane clash, WO-148 vs `tests/test_cli_docs_match_source.py`) is not yet answered.

## Earlier: CLAUDE-P008 (receipt COPILOT-013; answered in COPILOT-014)

Backlog lanes, WO-139..WO-150 for Copilot, and the request for GP-06+ proposals and an IN/CX critique. Done in COPILOT-014.
