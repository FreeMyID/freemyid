# WO-166 status

## Done

- Audited the line-7 build banner and all eight literal `TODO verify` markers
  in `docs/USER_GUIDE.md`.
- Added `docs/vendor/user-guide-todo-audit.md` with local file-and-line
  evidence and one required status per claim.
- Did not change `docs/USER_GUIDE.md` or fetch external facts.

## Next

- Owner can resolve the three outside-fact entries against the relevant
  provider or government sources, and decide how to implement or document the
  possible-match controls.

## Questions for the owner

- None. The audit identifies 1 still-unknown claim and 3 claims needing an
  outside fact.

## How to test

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/copilot/` — unverified:
  `.venv/bin/python` is not available in this worktree.
- `git diff --check` — passed before staging the documentation files.
- `git diff --cached --check` — passed after staging the two documentation
  files.
