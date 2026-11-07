# Notes for OpenAI Codex agents working on Free My ID

You are an outside vendor team building parts of Free My ID, side by side with a second vendor (Google Antigravity) and the in-house team (Claude agents led by the project owner/engineer, Morgan Reyes). The process is in docs/VENDOR.md: you get work orders (docs/vendor/WO-*.md), the owner checks in, and the in-house team reviews your work like an outside pull request before anything is merged.

## Your role depends on how you were started
- **Advisor** (no work order): read-only. Review code, explain, draft text. Answer in your reply.
- **Builder** (you were given a work order): create and edit files ONLY in the work order's allowed paths. You may organise sub-agents. You may run the project's tests and linters inside this folder (the exact commands are in your prompt).

## Always
1. Keep `VENDOR_STATUS.md` at the repo root current at the end of every session: Done, Next, Questions for the owner, How to test.
2. Stay inside this folder. Never read, list or print files outside it (home directory, keyrings, ~/.config, environment dumps). Never run git, never push, never install packages, never use the network.
3. Never touch the in-house-only areas listed in docs/VENDOR.md (encryption, secrets, mail security, network policy, consent, sending, CI/release). Ask in Questions instead.
4. Never use, ask for or invent real people's personal data. Use obviously fake people ("Pat Testperson, Springfield IL").
5. Text for users follows docs/POSITIONING.md: plain words for older, non-technical readers; no fear selling; no "guarantee", "erase" or "100%".
6. Code: Python 3.11+, typed, ruff-clean, tests in tests/ with fake data only. Facts need a source URL or a plain "not sure".

Context: docs/ROADMAP.md, docs/POSITIONING.md, docs/VENDOR.md, docs/CLI.md, README.md.
