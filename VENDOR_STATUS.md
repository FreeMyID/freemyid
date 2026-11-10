# WO-337 status

Tracker: WO-337 (freemyid-pm#257).

## Done

When an automatic web form cannot finish, the person's to-do now says why, then the same steps as before. `WebFormSubmitter.submit` reports `challenge`, `human_step`, `no_confirmed_listing`, `timeout` (exception type name `TimeoutError`, so Playwright and asyncio both match without a browser), `blocked_by_policy`, `unexpected_page`, or `error`. `_fallback` passes that reason to `assisted.todo_for` instead of collapsing everything except a challenge into "error".

Each reason has one calm line. `challenge` and `error` keep the sentences they already had. No line says "error" or "failed". The outcome code is still `fallback_assisted:<reason>[:<detail>]`. Existing reason spellings are unchanged; the three new codes are additions. Exception detail is still the type name. Challenge detail is still the kind.

## Next

In-house review. This session did not edit `docs/vendor/GROK_BOARD.md` or `docs/vendor/GROK_TO_CLAUDE.md` (not in the allowed paths).

## Questions for the owner

The new to-do sentences are not in `docs/i18n/STRINGS.md` (Codex lane; citation line bounds still hold). Please add them on the next string inventory.

The run still stores the machine code on `needs_human_reason` (`src/freemyid/engine/runner.py:698`), and the wizard shows that note. The calm sentence is only on the to-do body, which is what this WO asked for. Say if the note should use the same sentence; that would touch the wizard.

## How to test

From `.vendor-wt/wo-337`:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_web_form_fallback.py` — 13 passed in 0.18s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/test_assisted_no_mailbox.py tests -k "web_form or assisted or fallback"` — 38 passed, 2662 deselected, 1 warning in 19.70s.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2492 passed, 206 skipped, 2 xfailed, 1 warning in 299.19s (0:04:59). No failures. The two xfail are pre-existing and not from this change: `tests/test_sec112_flake_lock.py:23` (`test_gate_fails_on_flake_without_lock`) and `tests/copilot/test_cp_never_asks_parity.py:87` (`test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]`).
- `../../.venv/bin/ruff check src/freemyid/submitters/web_form.py src/freemyid/submitters/assisted.py tests/grok` — All checks passed.
- `../../.venv/bin/mypy src/freemyid/submitters/web_form.py src/freemyid/submitters/assisted.py` — Success: no issues found in 2 source files.

Fake person only (Jane Q Testperson, Springfield IL). No browser, no network, no subprocess.
