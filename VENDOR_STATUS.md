## Done

- Added the WO-165 source-citation guard in commit `4d017ca`.
- The strict expected failures are:
  - `docs/user/mail-gmail.md:65`
  - `docs/user/mail-gmail.md:66`
  - `docs/user/mail-other.md:79`
  - `docs/user/mail-other.md:80`
  - `docs/user/mail-proton.md:70`
  - `docs/user/mail-proton.md:71`
  - `docs/user/mail-proton.md:72`

## Next

- None.

## Questions for the owner

- None.

## How to test

- `PYTHONPATH=src python -m pytest -q tests/copilot/` — `392 passed, 7 xfailed`.
- `python -m ruff check tests/copilot` — passed.
- The requested `PYTHONPATH=src .venv/bin/python -m pytest -q tests/copilot/`
  and `.venv/bin/ruff check tests/copilot` commands are unverified because
  `.venv` is absent in this isolated worktree.
