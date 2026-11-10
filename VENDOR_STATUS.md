# WO-344 (freemyid-pm#264)

## Done
- Added `connection_failure_reason` in `src/freemyid/engine/mail_tls.py`. A mail connection or login exception maps to one fixed code: `cert_expired`, `cert_untrusted`, `hostname_mismatch`, `timeout`, `refused`, `auth_failed`, `starttls_not_offered`, or `unknown`.
- The code is only that word. Host names, user names, passwords, and server banners are not copied. Certificate checks are unchanged: with no pin, the context is still `ssl.create_default_context()` (`CERT_REQUIRED` and hostname checks on). Existing pin behavior is untouched.
- Tracker: WO-344 (freemyid-pm#264).

## Next
In-house review. The setup screen and the CLI can call `connection_failure_reason` when they word a failure. Those files are outside this work order. No contract change is required for the helper.

## Questions for the owner
A certificate that is not yet valid, self-signed, or missing an issuer is `cert_untrusted`. Only OpenSSL's "certificate has expired" is `cert_expired`. A hostname, email, or IP mismatch is `hostname_mismatch`. Say if expired and untrusted should be one code, or if not-yet-valid should be its own code. Tracker: WO-344 (freemyid-pm#264).

## How to test
From this worktree (`.vendor-wt/wo-344`):

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_mail_tls_reasons.py
```
34 passed in 0.17s

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "mail_tls"
```
91 passed, 2642 deselected, 1 warning in 3.59s. The warning is the existing StarletteDeprecationWarning from FastAPI's test client. No failure.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```
2522 passed, 206 skipped, 5 xfailed, 1 warning in 330.50s (0:05:30). 0 failed. The 5 xfailed marks were already in the suite; this work order adds none. The 206 skips include browser tests and tests that need `web/dist` or a real scheduler. Those skips are not passes. The same StarletteDeprecationWarning as above.

```
../../.venv/bin/ruff check tests/grok src/freemyid/engine/mail_tls.py
```
All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/mail_tls.py
```
Success: no issues found in 1 source file.

## Findings
None. No existing test failed, so there is no file:line to report. Browser tests skipped in this sandbox are not passes.
