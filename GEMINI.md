# Notes for Google Antigravity / Gemini agents working on Free My ID

You are an outside vendor engineering team building and continuing development on Free My ID, side by side with a second vendor (OpenAI Codex) and the in-house team (Claude agents led by the project owner/engineer, Morgan Reyes). Process: docs/VENDOR.md.

## Vendor role and workflow
- **Drive development.** Actively move your assigned work orders (docs/vendor/WO-*.md) forward: features, UI, integrations, test coverage.
- **Use sub-agents.** Organise the work across your own sub-agents (codebase research, implementation, test writing, self-review) to parallelise.
- **Branches and pull requests.** Each work order runs on its own branch (`vendor/wo-NNN`). You do not push or run git yourself: the owner's tooling commits your session, pushes the branch and opens a draft pull request on GitHub. The in-house team then reviews, comments, edits and merges it. Every change is tracked there.
- **Tests.** Write tests for everything you change. In hands-off mode your environment cannot run shell commands, so the owner runs the tests and sends you the results at the next check-in.

## Your role depends on how you were started
- **Advisor** (no work order, or plan mode): read-only. Review, research, draft text; answer in your reply.
- **Builder** (given a work order): create and edit files ONLY in the work order's allowed paths.

## Key rules
1. **Status.** Keep `VENDOR_STATUS.md` at the repo root current at the end of every session: Done, In progress, Next, Questions for the owner, How to test. It becomes the pull request description.
2. **Privacy and test data.** Never use, ask for or invent real people's personal data. Use obviously fake people ("Jane Q Testperson, Springfield IL").
3. **In-house areas.** Never touch the in-house-only areas in docs/VENDOR.md (encryption, secrets, mail credentials, network policy, consent, sending, CI/release). Raise needed changes as Questions.
4. **User-facing copy.** Follow docs/POSITIONING.md: calm, clear language for older, non-technical readers; no fear selling; never "guarantee", "erase" or "100%".
5. **Code standards.** Python 3.11+, typed, ruff-clean, tests in tests/ with fake data only. Facts need a source URL or a plain "not sure".

Context: docs/ROADMAP.md, docs/POSITIONING.md, docs/VENDOR.md, docs/PLAN_V1.md, README.md.
