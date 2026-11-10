# WO-331 (issue pending)

## Done

Hardened the pure reply matcher in `src/freemyid/engine/mail.py`. `ReplyScan` fields and their order are unchanged. No contract file, runner, or other test was edited.

- `sender_domain` uses the parsed From address (`Address.domain`, or `email.utils.getaddresses` when that header has no parsed address). It does not use the first `@` in the header. `"privacy@broker.example" <x@attacker.example>` is `attacker.example`, so `check_sender` drops the message and its links are never used.
- `_EXTENSION` no longer matches a bare "extension". A time word has to sit in the same sentence, and "phone extension" / "browser extension" do not count. "we are taking a 45-day extension" and "we need additional time" match. "call us at ext. 204", "phone extension 12", and "install our browser extension" do not.
- `claims_extension` uses the same `MAX_MESSAGE_BYTES` cap as `asks_for_id`. A larger message is not a claim and is not parsed.
- `scan_replies` parses each raw message once per call. A second call parses again. Mail over the cap is parsed from the first 64KiB only, for the header checks.

Tests: `tests/grok/test_gk_mail_reply_matcher.py`. An autouse fixture makes `socket.socket.connect` and `socket.create_connection` raise. No logs were added. Fake people and example domains only.

## Next

In-house review. `docs/pm/issue_map.json` has no WO-331 number yet, so this stays "WO-331 (issue pending)". `docs/vendor/GROK_TO_CLAUDE.md` and `GROK_BOARD.md` were not edited; this task allows only `mail.py`, the new test, and this file.

## Questions for the owner

None. Tracker: WO-331 (freemyid-pm#251).

## How to test

From this worktree, with the parent venv. Counts below are from the final tree.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_mail_reply_matcher.py
```

11 passed in 0.23s. No failures, skips, or xfails.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_reply_matcher_fuzz.py tests/test_mail_sec50_53.py tests -k "mail or reply"
```

394 passed, 3 skipped, 2301 deselected, 1 warning, in 26.20s. The summary listed no failures and no xfails.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```

2490 passed, 206 skipped, 2 xfailed, 1 warning, in 330.45s (exit 0). No failures. The two xfails are existing expected markers in other test files; this change does not touch them.

```
../../.venv/bin/ruff check src/freemyid/engine/mail.py tests/grok
```

All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/mail.py
```

Success: no issues found in 1 source file.
