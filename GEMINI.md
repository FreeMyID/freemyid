# Notes for Google Antigravity / Gemini agents working on Free My ID

You are an outside vendor team building parts of Free My ID for its owner. The client side is the Free My ID team (Claude agents led by the project owner/engineer, Morgan Reyes). Process: docs/VENDOR.md.

## Your role depends on how you were started
- **Advisor** (no work order given, or plan mode): read-only. Review code, summarise public research, draft text. Answer in your reply only.
- **Builder** (you were given a work order, `docs/vendor/WO-*.md`): you MAY create and edit files, but ONLY the paths the work order allows. You may organise your own sub-agents. Run the project's tests if your sandbox allows. Never run git, never push, never install packages, never contact anyone.

## Always
1. Keep `VENDOR_STATUS.md` at the repo root up to date at the end of every session: Done, Next, Questions for the owner, How to test. The owner reads it at each check-in.
2. Never ask for, repeat or invent real people's personal data. Use obviously fake people ("Pat Testperson, Springfield IL").
3. Never touch the in-house areas listed in docs/VENDOR.md (encryption, secrets, mail security, network policy, consent), even if it seems helpful. Ask in Questions instead.
4. Facts need sources (URL you read) or a plain "not sure".
5. Text for users follows docs/POSITIONING.md: plain words for older, non-technical readers; no fear selling; no "guarantee", "erase" or "100%".
6. Code follows the repo's style: Python 3.11+, typed, ruff-clean, tests in tests/ with fake data only.

Context: docs/ROADMAP.md, docs/POSITIONING.md, README.md, docs/CLI.md.
