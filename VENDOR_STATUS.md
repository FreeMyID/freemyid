# WO-332

## Done

A transient outbox send is retried. A permanent one still marks the request FAILED.

- `is_transient_mail_error` treats `TimeoutError`, `socket.timeout` (an alias of `TimeoutError` on Python 3.10+), `ConnectionError`, `smtplib.SMTPServerDisconnected`, and `smtplib.SMTPResponseException` with an integer 4xx code as transient. `SMTPAuthenticationError` is permanent even with a 4xx code. 5xx and every other error are permanent.
- On a transient error, `send_request` leaves the current status, logs `email_failed` with `transient: true`, the attempt number, and the exception type name, and still raises `OutboxError`. The third transient failure for that request, or any permanent error, marks FAILED as before.
- Attempts come from `store.events` (`email_failed` rows with `transient` true for that request id). No new `Request` field or status.
- `release_held` skips a request whose last transient failure is newer than its backoff (15 minutes after the first, 1 hour after the second) and counts it as `deferred`. The key is omitted when nothing was deferred, so a normal release event stays `{sent, failed}`.
- `SmtpImapMailer` wraps SMTP errors in `MailError` (`from None` still keeps `__context__`). The classifier follows that chain, so a real timeout or 4xx is still retried. The event stores the inner type name only, never the message.
- Dry-run requests are still never sent. The first-email approval rule is unchanged.

## Next

Nothing on this work order. In-house review.

## Questions for the owner

- `queue_email` (the path the runner reuses) still calls `send_request` immediately and does not apply the 15-minute / 1-hour backoff. Only `release_held` does. Should the next scheduled run wait too?
- `SMTPRecipientsRefused` is not an `SMTPResponseException`, so a 4xx recipient refusal stays permanent. Say if that should be transient.
- `deferred` is left out of the release event when it is zero, so `tests/test_first_email_approval.py` (the `{sent, failed}` check) stays unchanged. Say if you want `deferred: 0` on every release; that needs an in-house test update.
- Tracker: WO-332 (freemyid-pm#252).

## How to test

From `.vendor-wt/wo-332`. Fake person only (Jane Q Testperson, Springfield IL). No network.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_outbox_retry.py
```

43 passed.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/test_first_email_approval.py tests/test_outbox_letters.py
```

11 passed.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "outbox or mail or email"
```

421 passed, 3 skipped, 2306 deselected.

```
../../.venv/bin/ruff check src/freemyid/engine/outbox.py tests/grok
```

All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/outbox.py
```

Success: no issues found in 1 source file.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```

2522 passed, 206 skipped, 2 xfailed. The warning is the existing Starlette/httpx deprecation from FastAPI's test client.

Pre-existing xfail, not caused here and not edited:

- `tests/test_sec112_flake_lock.py:23` SEC-112 residual: the publish gate does not require `distro/nix/flake.lock`.
- `tests/copilot/test_cp_never_asks_parity.py:87` `docs/FRIDGE_CARD.md:17` missing "never charges you".

No contract change.
