# WO-336

## Done

`freemyid setup --from` validation problems still start with the field path (`person.name.first: `), then a plain sentence.

- Missing: `is missing; add it`.
- Unknown key: `is not a setting Free My ID knows`. A close known key from `difflib` adds `did you mean ...?` (cutoff 0.65; a second guess only if it is within 0.08 of the best). Weak hits, such as `removal_scope` versus `email_mode`, get no guess.
- Wrong type: `should be a number`, `should be yes or no`, or `should be text`. A number that is the right kind but not an allowed choice stays specific (`version: should be 1`, `email_mode: should be approve_each or auto`).
- The model's own checks are the same words as the `ValueError`s in `setup_config.py`: `never put the password in the file; use password_env or password_file` and `give exactly one of password_env or password_file`. The `Value error, ` wrapper is not shown.
- Ranges, list length, a 2-letter state, and the certificate fingerprint are plain as well. The typed value is not repeated for a password, name, address, phone, email, or similar field.
- YAML messages are unchanged (`cannot read`, `is not valid YAML`, `should be a YAML mapping`, `is too large`).

No existing test asserted Pydantic's exact text (`Field required`, `Extra inputs are not permitted`, and the rest). Searched `tests/`. Codex and in-house setup tests were left as they are and passed. No contract change.

## Next

In-house review of `vendor/wo-336`. This task did not edit `docs/vendor/GROK_BOARD.md` or `docs/vendor/GROK_TO_CLAUDE.md`.

## Questions for the owner

None. Tracker: WO-336 (freemyid-pm#256).

## How to test

From this worktree:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_setup_config_messages.py` — 14 passed in 0.21s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_setup_from_yaml.py` — 13 passed in 0.36s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "setup"` — 87 passed, 1 skipped, 2613 deselected, 1 warning in 3.90s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_setup_from_yaml.py tests -k setup` — 87 passed, 1 skipped, 2613 deselected, 1 warning in 3.55s. The skip is `tests/conftest.py:180` (built website missing: `web/dist/index.html`).
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2493 passed, 206 skipped, 2 xfailed, 1 warning in 332.49s. No failures. The 2 xfailed were already marked in the tree; this change did not touch them.
- `../../.venv/bin/ruff check src/freemyid/setup_config.py tests/grok` — all checks passed.
- `../../.venv/bin/mypy src/freemyid/setup_config.py` — success, no issues found in 1 source file. One note, not an error: `src/freemyid/wizard/flows.py:97` (`annotation-unchecked`). That file was not edited.
