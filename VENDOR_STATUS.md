# WO-341 status

Tracker: WO-341 (freemyid-pm#261).

## Done

`classify_reply` in `src/freemyid/engine/mail.py` turns one already-accepted broker reply into a code: `confirmed`, `denied`, `needs_id`, `needs_more_time`, or `unknown`. It takes text (`str` or `bytes`) and returns only that code. It does not log, and the result has no names, addresses, or message text.

`mail.py` was copied from the delivered WO-331 worktree because rebase is not available. `ReplyScan` is unchanged. `classify_reply` reuses `asks_for_id` and `claims_extension` and does not change them. "please verify your identity" is needs ID even though it is not a document request. "we need 45 more days" is needs more time even though that wording is not an extension claim. A clear removal that is also hedged, taken back, or paired with another category is `unknown`, never `confirmed`. Empty input, input over `MAX_MESSAGE_BYTES`, and non-text input are `unknown` and are not parsed.

No contract change. The runner does not call this yet (`runner.py` is out of scope).

## Next

In-house review. This session did not edit `docs/vendor/GROK_BOARD.md` or `docs/vendor/GROK_TO_CLAUDE.md` (not in the allowed paths).

## Questions for the owner

A reply that states a removal and also asks for ID, asks for more time, denies the record, or takes the removal back is `unknown`. Say if one clear "we have removed your listing" should win over a later caveat.

## How to test

From this worktree, with the parent venv. Counts are from the final tree. Fake person only (Jane Q Testperson, Springfield IL). No browser was launched for the new tests. No network, no subprocess, no `freemyid run`, `send`, or `schedule install`.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_mail_classify_reply.py
```

130 passed in 0.96s. No failures, skips, or xfails.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "mail"
```

495 passed, 3 skipped, 2331 deselected, 1 warning in 24.72s. The 3 skips are `tests/conftest.py:180` (built website not found at `web/dist/index.html`), not browser tests, and are not passes.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```

2618 passed, 206 skipped, 5 xfailed, 1 warning in 324.71s (0:05:24). Exit 0. No failures. Skips are not passes, including any browser skips in that 206. The five xfails are pre-existing markers, not from this change:

- `tests/test_sec112_flake_lock.py:23` `test_gate_fails_on_flake_without_lock`
- `tests/copilot/test_cp_never_asks_parity.py:87` `test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]`
- `tests/codex/test_cx_monitor_previous_hardening.py:81` `test_cli_drops_huge_previous_generated_at_instead_of_copying_it`
- `tests/codex/test_cx_proof_note_a11y.py:150` `test_call_note_safety_hint_uses_at_least_20px_text[light]`
- `tests/codex/test_cx_proof_note_a11y.py:150` `test_call_note_safety_hint_uses_at_least_20px_text[dark]`

```
../../.venv/bin/ruff check tests/grok src/freemyid/engine/mail.py
```

All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/mail.py
```

Success: no issues found in 1 source file.

Direct collection of the WO-331 file failed. `pytest` loaded `../wo-331/tests/conftest.py`, which raises `pytest.UsageError` at line 34 when `PYTHONPATH` points at this worktree. The file was not modified. The same test, copied to a temp directory outside this worktree (stub `freemyid_env` only, `PYTHONPATH` this worktree's `src`), passed 11 in 0.12s. In-tree mail tests above still passed.
