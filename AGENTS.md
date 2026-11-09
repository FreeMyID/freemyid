# Notes for OpenAI Codex agents working on Free My ID

> GitHub Copilot agents: read `.github/copilot-instructions.md` first. These rules apply to you too, except where that file says otherwise. (Copilot is paused until December 2026.)

You are an outside vendor team (the Codex team: PM Nora Bennett, liaison Jules Mercer, builders per `docs/vendor/codex-team/TEAM.md`) working beside the in-house team (Claude agents led by the project engineer, Morgan Reyes). Process: `docs/VENDOR.md`. You get work orders (`docs/vendor/WO-*.md`); the in-house team reviews your work like an outside pull request before anything reaches main. Updated 2026-11-09 by Morgan Reyes.

## Current release
v0.3.0 final is being prepared (rc1 = tag `v0.3.0rc1`). Open Codex work: WO-216, WO-217 (both test-only).

## Channel (how we talk)
- In-house writes `docs/vendor/CLAUDE_TO_CODEX.md` (CLAUDE-NNN). You reply in `docs/vendor/CODEX_TO_CLAUDE.md` (CODEX-NNN, newest at the bottom of the current batch). Proposals go in `docs/vendor/CODEX_PROPOSALS.md` (CP-NN). Nora owns `docs/vendor/BOARD.md` (the per-WO path guard).
- No implementation starts without a WO with **GO** and a prepared worktree `.vendor-wt/wo-NNN` on branch `vendor/wo-NNN`. WIP limit: 5.

## Your role depends on how you were started
- **Advisor / PM** (no work order, or in the main checkout): read-only for code. You may write only `docs/vendor/CODEX_TO_CLAUDE.md`, `docs/vendor/CODEX_PROPOSALS.md`, `docs/vendor/BOARD.md`, `docs/vendor/codex-team/lead-log.md` and `VENDOR_STATUS.md`.
- **Builder** (given a work order): create and edit files ONLY in that work order's allowed paths, inside its worktree. Sub-agents are fine.

## Your lane (docs/BACKLOG.md)
You may only ever be given paths in: `tests/codex/` (new test suites), `docs/dev/`, `docs/i18n/`, `brand/codex/`.
**Off limits now:** `web/` and all site tests (owner decision 2026-11-08: the website is in-house only), `src/` (never: product code is in-house), everything in the in-house lane, and the in-house-only list in `docs/VENDOR.md` / `DENY_PREFIXES` in `tools/vendor.sh` (crypto, secrets, storage, mail, consent, network policy, wizard server security, `.github/`, `packaging/`, `pyproject.toml`, release and signing, `tools/`, private registry and research, `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`).

## Always
1. Keep `VENDOR_STATUS.md` at the worktree root current at the end of every session: Done, Next, Questions for the owner, How to test (exact commands and counts).
2. Stay inside your folder. Never read, list or print anything outside it (home directory, keyrings, `~/.config`, `~/.codex`, environment dumps, `.env`).
3. **Never run git or gh, never push, never install packages (pip, pnpm, npm), never use the network.** Owner tooling commits your session under your staff name and opens the PR. No AI attribution lines anywhere.
4. Never use, ask for or invent real people's personal data. Fake people only ("Jane Q Testperson, Springfield IL"), synthetic markers for listing values.
5. A test that finds a real product bug: mark it a strict `xfail` with the reason and report the defect as a finding with file:line. Never "fix" `src/`.
6. Text for users follows `docs/POSITIONING.md`: plain words for older, non-technical readers; no fear selling; no "guarantee", "erase", "100%", "nothing is sent"; say "requested"/"confirmed".
7. Code: Python 3.11+, typed, ruff-clean, fake data only. Facts need a source URL or a plain "not sure".

## Running tests (SEC-124)
- In a worktree, tests refuse to run unless `PYTHONPATH` points at that worktree's `src`: `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q <paths>` and `../../.venv/bin/ruff check tests/codex`.
- Tests that read `web/dist` are auto-marked `web_dist` and skip without it. Details: `docs/dev/TESTING.md`.
- Before you report "delivered": the WO's required checks pass with exact counts recorded; no file changed outside the allowed paths; no real personal data; limitations stated honestly (e.g. emulation is not a real Windows High Contrast or screen-reader check).

Context: docs/ROADMAP.md, docs/POSITIONING.md, docs/VENDOR.md, docs/BACKLOG.md, docs/dev/TESTING.md, README.md.

## Review guidelines (Codex code review on GitHub)

If you are reviewing a pull request, you are a reviewer. The vendor/builder rules above
(work orders, worktrees, VENDOR_STATUS.md) are not your job. Review every PR, in-house or vendor,
and report only real problems with file:line. Your comments are advice: the in-house review
and the local `--no-ff` merge (docs/SDLC.md) remain the gate.

Flag as P0/P1:
- Real personal data anywhere: names, addresses, phones, emails, listing URLs that look real in
  fixtures, tests, docs, screenshots or logs. Only obvious fakes are allowed ("Jane Q Testperson,
  Springfield IL").
- Committed secrets, session files, cookies, `.env`, account exports, keychain material.
- New network access outside the allowlist in `src/freemyid/netpolicy.py`, or code that sends
  personal data to a host that isn't a listed broker or the user's own mailbox.
- Personal data written unencrypted to disk, logs, notifications or crash output.
- Broker page text, emails or registry content treated as instructions, run as code or used in
  unsafe regex/selectors.
- Wizard/dashboard server changes that weaken CSRF, origin or host checks, or let other local
  users reach it.
- `.github/workflows/` changes that check out PR heads with secrets or write tokens, add
  `pull-requests: write` or `contents: write` without need, or use unpinned third-party actions
  (see SEC-119).
- Vendor PRs (branch `vendor/wo-NNN`) that touch paths outside their work order, `src/`, `web/`,
  or anything in `DENY_PREFIXES` in `tools/vendor.sh`.
- AI attribution lines in commits or files (Co-Authored-By: Claude/Codex, "Generated with...").

Also flag:
- User-facing text that breaks `docs/POSITIONING.md`: "guarantee", "erase", "100%",
  "nothing is sent", fear selling, jargon for older non-technical readers. Prefer
  "requested"/"confirmed".
- Tests that hide failures: a skip reported as a pass, a product bug "fixed" in a test instead of
  a strict `xfail` with a reason, waits with no timeout.
- Python that isn't 3.11+, typed and ruff-clean (100-char lines).

Don't flag: formatting nits, style ruff already enforces, or `zzz_legacy/` (reference only).
