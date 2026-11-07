# Free My ID — orchestrator notes

**Current scope: `docs/PLAN_V1.md`** (one-click Windows installer → 6-screen wizard → scheduled background runs; three tiers per broker: Email / Assisted / Automatic browser). Every agent reads it before starting work.

Main session = orchestrator / project lead: owns architecture, contracts (`src/freemyid/{models,state,interfaces,registry,netpolicy,crypto,secrets,logging_setup,config,paths,cli}.py`, `storage/`, `schema/`, `pyproject.toml`), integration, PROGRESS.md and sign-off.
Agents and ownership: `.claude/agents/*.md` (broker-researcher, automation-engineer, wizard-packager, web-developer, brand-marketing, graphic-designer, qa-security, devops-engineer: CI/CD, releases, freemyid.org infra). Website requests between marketing/art/web: `docs/WEBSITE_REQUESTS.md`. Shared rules: `.claude/agents/_shared-rules.md`. Handoffs: `docs/handoff/<agent>.md`.
`zzz_legacy/` = the user's earlier Claude-driven prototype. Reference only.
Target user: non-technical older relatives on Windows 10/11. Weigh every UX/packaging choice against that.
Dev: `.venv/bin/python`, `.venv/bin/pytest -q`, `.venv/bin/ruff check src tests`, `.venv/bin/freemyid`. Regenerate schemas after model changes: `.venv/bin/python tools/gen_schema.py`.
Windows exe is built only on GitHub Actions `windows-latest` (can't cross-build from Linux).
No AI attribution ever (no Co-Authored-By/Claude lines). Agents commit under their staff names: `.claude/agents/_shared-rules.md` rule 14. Author format `Name [freemyid]`; orchestrator = Morgan Reyes [freemyid].
Ask the user before: system-wide installs (scheduler jobs, browsers), the first real submission, any real email, any git push.
