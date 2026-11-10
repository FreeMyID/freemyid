# WO-348

Tracker: WO-348 (freemyid-pm#268).

## Done

The email submitter no longer raises when a send does not go out. `SubmitOutcome.message` is `not sent: <reason>` and a to-do says what to do. No new result field.

Reasons, each from a fake mailer (the approval case uses a mailer that would raise `ConnectionError` if `send` were called):

- `mailer not set up` — password missing, auth failure, or no mailer when a send is due
- `refused address` — `SMTPRecipientsRefused`, including the real mailer's `smtp failed: SMTPRecipientsRefused`
- `connection error` — `ConnectionError`, `TimeoutError`, `OSError`
- `first-email approval missing` — AUTO mode, no earlier sent email

The approval-gate reason is not the connection-error reason. The recipient address is not copied into the message or the to-do. A sent email, an approve-each queue, a dry-run draft, and the no-mailbox letter are unchanged (`email_sent`, `email_queued`, `email_draft`, `manual_email`).

## Next

In-house review. Nothing here merges. `docs/vendor/GROK_TO_CLAUDE.md` and `GROK_BOARD.md` were left untouched.

## Questions for the owner

- A failed resubmit used to raise `OutboxError`, which `runner.py:874` turns into `escalation_failed` so the ladder does not climb (`runner.py:858-867` treats any other resubmit result as success). The submitter now returns instead of raising, so that rung can still advance. Follow-up and legal demand still go through `runner._letter` and still raise. No existing test covers a failed resubmit through the submitter. Honoring `not sent` there is a runner change, out of scope for this WO.
- On a first email the queued request is still returned, so the runner still counts it as waiting for approval (`runner.py:688-694`), and an `APPROVE_EMAIL` to-do is added as well. Say if that second card is one too many.
- `engine/outbox.py:396-401` still stores only the exception type and still raises. Direct `queue_email` / `approve_and_send` callers do not get this reason. Not edited.

## How to test

From `.vendor-wt/wo-348`. Browser skips are not counted as passes. This run had no browser skips. The skips below are pre-existing (web/dist not built, Windows-only, registry not in this checkout, and similar). The 5 xfails were already in the suite. Exit code 0.

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_email_submitter_reasons.py` — 11 passed
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "email"` — 63 passed, 3 skipped, 2644 deselected
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2499 passed, 206 skipped, 5 xfailed
- `../../.venv/bin/ruff check tests/grok src/freemyid/submitters/email.py` — All checks passed
- `../../.venv/bin/mypy src/freemyid/submitters/email.py` — Success: no issues found in 1 source file
