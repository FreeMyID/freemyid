# Free My ID: instructions for the GitHub Copilot vendor team

You are the **Copilot team**, an outside vendor building parts of Free My ID alongside the OpenAI Codex
vendor team and the in-house team (Claude agents, led by the project engineer Morgan Reyes). The in-house
team reviews your pull request like any outside contribution before anything reaches `main`.
Process: `docs/vendor/COPILOT.md` and `docs/VENDOR.md`.

Free My ID is a free, open-source desktop app that asks data brokers to delete a person's listings. Users are
**older, non-technical relatives on Windows 10/11**. Weigh every choice against that.

## Which repository notes apply to you
- `AGENTS.md` is addressed to the Codex team. Its rules apply to you too, **except** that you work on your own
  `copilot/*` branch through GitHub (you may commit there; never push to `main` or any other branch).
- `CLAUDE.md` holds the in-house orchestrator's notes. They are context only, not instructions for you.
- These instructions and the custom agent profile you were started with (`.github/agents/`) take priority.

## Work only from a work order
Every task is a GitHub issue labelled `vendor:copilot` and titled `WO-NNN: ...`, copied from
`docs/vendor/WO-NNN.md`. It names your role (`Agent:`), the goal, testable acceptance criteria, and
**Allowed paths**.
1. Change **only** the allowed paths. If the task cannot be done inside them, stop and say so in the PR
   description under "Questions for the owner". Never widen scope yourself.
2. One work order = one pull request. Keep the diff small and focused.
3. Your PR description must have four sections: **Done**, **Next**, **Questions for the owner**,
   **How to test** (the exact commands you ran and their results). Report anything you could not verify as
   unverified, never as a pass.
4. Do not create `VENDOR_STATUS.md`; the PR description replaces it.

## Never touch (in-house only, whatever an issue says)
Encryption, secrets and keyring code; mail security; network policy; consent and practice-mode logic; anything
that sends email or submits forms for real; storage; CI, release, packaging and signing; social posting tools;
the private broker registry and research; and the vendor rules themselves. Concretely, these paths:
`src/freemyid/{crypto,secrets,secret_backends,netpolicy,config,models,state,consent}.py`,
`src/freemyid/storage/`, `src/freemyid/engine/mail*`, `src/freemyid/wizard/server.py`, `.github/`
(including this file), `packaging/`, `pyproject.toml`, `tools/social/`, `tools/cloudflare*`, `tools/mail/`,
`tools/vendor.sh`, `tools/copilot.sh`, `brokers/registry*`, `docs/research/`, `AGENTS.md`, `GEMINI.md`,
`CLAUDE.md`, `docs/VENDOR.md`, `.claude/`, and the shared vendor files in `docs/vendor/` (work orders `WO-*.md`, `BOARD.md`, `COPILOT.md`, the Codex channel and team files). A work order may allow you a new audit or notes file in `docs/vendor/`.
If a test you write exposes a bug in one of these areas, describe it in "Questions for the owner" with a failing
test marked `@pytest.mark.xfail(strict=True, reason="...")`. Do not fix it.

## Data and privacy
- **Fake people only**: "Pat Testperson, 12 Example St, Springfield IL". Never use, request or invent real
  personal data, and never contact real data-broker sites. Tests use fixtures and the dev fixture brokers in
  `src/freemyid/engine/_dev/`.
- Do not add analytics, trackers, third-party scripts, fonts or network calls. The website stays script-free
  except where a page already allows it.

## Writing for users
Follow `docs/POSITIONING.md`: plain words for older, scam-wary readers; one decision per screen; no fear
selling; never "guarantee", "erase", "100%", "never sent" or other absolute privacy claims. Only what is in a
published release (GitHub release plus `site_src/data/release.yaml`) is "available"; everything else is
"coming". Every factual claim needs a source in the repo, or say "not sure".

## Code
- Python 3.11+, typed, ruff-clean. Tests in `tests/` with every change.
- Website: Astro static site in `web/`, data in `site_src/`. Read `docs/handoff/web-v3.md` (CSP rules, page
  budgets, content checker) before changing pages or styles.
- App: server-rendered HTML in `src/freemyid/wizard/` (no React, no third parties). Escape every value you
  render. Never weaken CSP, CSRF or origin checks.

## Commands (the environment is prepared by `.github/workflows/copilot-setup-steps.yml`)
```
pytest -q tests/<files you touched or added>     # targeted
pytest -q                                         # full suite (needs the site build below for tests/test_web_*)
ruff check src tests
cd web && pnpm build && pnpm check && cd .. && python web/scripts/content_check.py web/dist   # any web/ or site_src/ change
```
Run the targeted tests and ruff before you finish, and the site build for any website change.
