# WO-340 status

Tracker: WO-340 (freemyid-pm#260).

## Done

Proved every `*_doc` in `src/freemyid/cli_json.py` (status, profiles, todos, outbox, registry, registry-source, schedule, reports, run, secrets, error, exposure, plus the nested trend fragment and skipped rows) omits personal details. The new test builds those documents from one fake person, Jane Q Testperson of Springfield IL, with markers for the street (`MARKER-STREET-1`), mailbox (`jane.testperson@example.com`), password (`MARKER-PASSWORD`), copy-fields, letter body and date of birth (`1980-04-01`), then walks the JSON at every depth.

No marker appears. Each top-level document is one object whose `schema` is `<name>/1`. `emit` writes one JSON object. Display labels such as "Mom" still show. State of residence is the two-letter code only (`IL`); the street does not. `has_mailbox` is true without the mailbox address.

No leak to fix. `src/freemyid/cli_json.py` is unchanged. No field was renamed or removed, and the schema version was not bumped. This does not need an in-house contract change.

The new file has an autouse fixture that makes `socket.socket.connect` and `socket.create_connection` raise. No network, subprocess, or real `freemyid run` / `send` / `schedule install`.

## Next

In-house review. This session was told not to edit `docs/vendor/GROK_*.md`, so `GROK_BOARD.md` and `GROK_TO_CLAUDE.md` were left untouched.

## Questions for the owner

`exposure_doc` copies `check_url` and listing `url` on purpose (`src/freemyid/cli_json.py` around the entries list; docs/CLI.md says the text output shows those links). The engine fills a search URL from the person's name, city, state and ZIP, and an email-only lookup URL can contain the email. Blanking those fields would make the link wrong, and removing them is a contract change, so they were left as they are. The serializer does not copy the street, mailbox address, password, copy-fields, letter body or date of birth into that URL. Say if you want a different rule.

`trend_doc` has no schema of its own. It sits inside `exposure/1`. Adding a schema key would change the trend object `tests/test_cli_old_addresses.py` matches exactly.

## How to test

From this worktree:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_cli_json_no_pii.py` — 3 passed
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_cli_json_contract.py tests/test_cli_json_headless.py tests/test_cli_json_serialization_edges.py` — 74 passed
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2482 passed, 206 skipped, 2 xfailed, 0 failed (1 warning)
- `../../.venv/bin/ruff check src/freemyid/cli_json.py tests/grok` — all checks passed
- `../../.venv/bin/mypy src/freemyid/cli_json.py` — no issues in 1 source file
