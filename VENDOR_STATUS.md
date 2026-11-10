# WO-342

## Done

`src/freemyid/engine/outbox.py` was copied from the delivered WO-332 worktree because rebase is not available. WO-332 retry and backoff are unchanged.

A message the mailer has already accepted is not sent again.

- After `mailer.send` returns, an `email_handed` event is stored (`request_id`, `has_message_id` only) before the EMAIL_SENT blob and the SENT row. No new Request field. No new store method.
- The next `drain`, `queue_email`, or `send_request` sees that event or the EMAIL_SENT evidence, writes the SENT row once, and does not call the mailer again.
- A message that never reached the mailer has no marker, so the next pass still sends it. Approval rules are unchanged. `drain` and `release_held` still wait 15 minutes after the first transient failure and one hour after the second. `deferred` is still omitted from the release event when it is zero.
- A direct `send_request` still tries immediately, as WO-332 left it. The third transient failure, and any permanent error, still marks FAILED.
- Logs are counts and codes only (`outbox code=... count=...`, `outbox drain sent=... recorded=... failed=... deferred=...`).

Tracker: WO-342 (freemyid-pm#262).

## Next

Nothing on this work order. In-house review.

## Questions for the owner

- needs in-house contract change first: a crash after the mailer accepts the message and before `store.log` of `email_handed` commits looks the same as a send that never happened. The current store cannot close that gap. What it can do is delivered: once `email_handed` or EMAIL_SENT evidence is stored, the next pass does not send again. A new request status, or a mailer that remembers the request id, would be required to close the earlier gap.
- `drain` records a handed-off letter even when the first-email gate still looks closed. `release_held` still returns immediately until some request is already SENT, so the first crashed approval is finished by `drain`, `queue_email`, or a second approve, not by `release_held` alone. Say if `release_held` should finish that record too.
- Tracker: WO-342 (freemyid-pm#262).

## How to test

From `.vendor-wt/wo-342`. Fake person only (Jane Q Testperson, Springfield IL). No network.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_outbox_idempotent.py
```

5 passed.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "outbox"
```

19 passed, 2685 deselected. The warning is the existing Starlette/httpx deprecation from FastAPI's test client.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```

2493 passed, 206 skipped, 5 xfailed. Exit 0. Same Starlette warning.

The 206 skips are not passes. None are browser skips: 185 are `web/dist` not built (172 "built website not found", 13 "web/dist not built"), 13 are `install.sh` with no root-owned Python >= 3.12, 3 are a missing `docs/FAMILY_QUICK_START.md` copy, 3 are the full registry not present, and 2 are Windows-only. 41 browser-marked tests were collected and none were skipped, so they sit inside the 2493 passed because Chromium launched. That is not a headed-browser or screen-reader check.

Pre-existing xfail, not caused here and not edited:

- `tests/test_sec112_flake_lock.py:23` SEC-112 residual: the publish gate does not require `distro/nix/flake.lock`.
- `tests/copilot/test_cp_never_asks_parity.py:87` `docs/FRIDGE_CARD.md:17` missing "never charges you".
- `tests/codex/test_cx_monitor_previous_hardening.py:81` SEC-125: malformed `generated_at` is copied; `src/freemyid/monitor.py:379`.
- `tests/codex/test_cx_proof_note_a11y.py:150` call-note hint is 18px, not 20px; `src/freemyid/wizard/static/style.css:98` (light and dark).

```
../../.venv/bin/ruff check tests/grok src/freemyid/engine/outbox.py
```

All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/outbox.py
```

Success: no issues found in 1 source file.

WO-332 retry file, read-only, not modified. The direct command fails at `../wo-332/tests/conftest.py:34` because that conftest refuses another worktree's `src`. Same file, fixtures from this worktree:

```
PYTHONPATH="$PWD/src:$PWD" ../../.venv/bin/pytest -q --noconftest -p tests.conftest --rootdir=. --confcutdir=. ../wo-332/tests/grok/test_gk_outbox_retry.py
```

43 passed.

No contract change.
