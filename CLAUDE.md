# Vanish — orchestrator notes

Main session = orchestrator: owns architecture, contracts (`src/vanish/{models,state,interfaces,registry,netpolicy,crypto,secrets,logging_setup,config,paths,cli}.py`, `storage/`, `schema/`, `pyproject.toml`), integration, PROGRESS.md and sign-off.
Agents and ownership: `.claude/agents/*.md` (broker-researcher, automation-engineer, wizard-packager, qa-security). Shared rules: `.claude/agents/_shared-rules.md`.
`zzz_legacy/` = the user's earlier Claude-driven prototype. Reference only.
Dev: `.venv/bin/python`, `.venv/bin/pytest -q`, `.venv/bin/vanish`. Regenerate schemas after model changes: `.venv/bin/python tools/gen_schema.py`.
Ask the user before: system-wide installs (scheduler jobs, browsers), the first real submission, any real email, any git push.
