# WO-347 status

Tracker: WO-347 (freemyid-pm#267).

## Done

When fill-for-me does not see a success signal, the result and a new Assisted to-do now say why.

- `timeout`: the wait ended with no success signal, and the address did not move to an error page. A landing on `/done` stays this reason, as the existing tests already require.
- `window_closed`: the person closed the window.
- `error_page`: the success pattern was never seen, and the address changed to an error page (a path segment such as `error`, `404`, or `500`, a name like `error.html` or `server-error`, or a query key `error`, `errors`, `error_code`, or `errcode`). The query value is ignored.

Each of those three codes is different on `FillResult.reason`. `FillResult` already lives in `src/freemyid/engine/fill_for_me.py` and already had `reason`, so this is not a contract change.

Each new fallback card reuses `_fallback_todo`. The card body starts with a plain next step, then the existing Assisted steps (open the opt-out page, numbered steps, "Never pay."). An Assisted card that is already there is reused unchanged: same id, first reason wins. A reason that starts with `error` (such as `error:TimeoutError`) still uses the generic Assisted "error" sentence and does not get the extra next-step line. `listing_finder` still calls `_fallback_todo` with no reason.

The success path is unchanged. A success signal is checked before the error-page check, so a real confirmation still wins if the address looks like an error page. The golden test locks status `submitted`, reason `success_text`, a sent web-form request, the two proof captions, and no fallback to-do.

Events and the log hold codes and counts only (`fill_for_me_fallback` detail is `reason` and `submit_seen`; the log line is `code`, `filled`, and `submit_seen`). No page address, next-step sentence, or personal data.

Browser fakes only. `engine/browser.py` was not edited. No existing test failed because of this change.

## Next

In-house review. Nothing here is merged.

## Questions for the owner

Error pages are detected from the page address only. The snapshot has no HTTP status, and `engine/browser.py` is out of scope. Should a status of 400 or higher on an address that did not change also count as `error_page`? That would need in-house browser work.

A success phrase or success address still counts as success even when the new address looks like an error page. Say if an error address should override a success signal.

## How to test

From this worktree. Browser tests for fill-for-me ran (Chromium was available). The skips below are pre-existing and are not counted as passes. The five xfails are pre-existing. The suite exited 0.

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_fill_for_me_reasons.py` — 21 passed in 3.22s
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "fill_for_me"` — 92 passed, 2628 deselected, 1 warning in 81.02s. No skips in this filter.
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests` — 2509 passed, 206 skipped, 5 xfailed, 1 warning in 315.05s (exit 0)
- `../../.venv/bin/ruff check tests/grok src/freemyid/engine/fill_for_me.py` — All checks passed
- `../../.venv/bin/mypy src/freemyid/engine/fill_for_me.py` — Success: no issues found in 1 source file

The one warning on both pytest runs is the pre-existing `StarletteDeprecationWarning` from `fastapi/testclient.py`. Of the 206 skips, a marker probe accounted for 186: 172 missing `web/dist` at `tests/conftest.py:180`, 12 in `tests/test_web_og_images.py` (lines 91, 124, 142) for the same missing build, and 2 Windows-only in `tests/test_scheduler_ci.py` (lines 24 and 41). The other 20 skips were not listed one by one; they are the usual non-browser skips (registry, wheel, and similar), not a Playwright skip on this change.
