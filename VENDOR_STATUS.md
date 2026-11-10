# WO-345

Tracker: WO-345 (freemyid-pm#265).

## Done

`tier_reason` in `src/freemyid/engine/tiers.py` explains `tier_for` for the same broker, profile, config and registry. `tier_for` return values are unchanged. No contract change.

The five codes, and what they pair with:

- `email_ok` is the email tier: the site takes email and a removal mailbox is set.
- `form_not_verified` is assisted: the form steps are not verified, and that is the first automatic check that failed.
- `permissions_block` is assisted: the profile does not allow an ID or a phone number the site requires, and that is the first automatic check that failed.
- `automation_off` is assisted: browser automation is off, and that is the first automatic check that failed.
- `no_email_route` is assisted for every other reason.

Automatic returns `None`. None of the five codes is true for that tier, and borrowing `email_ok` or `no_email_route` would disagree with `tier_for`. A phone-only or email-only removal never runs a form, so it is only `email_ok` or `no_email_route`.

A covered site uses the parent's tier and the parent's code. The result is a code or `None`, never an address, a mailbox or a URL.

## Next

Nothing on this work order. In-house review. The to-do card can read the code later. The wizard was not changed.

## Questions for the owner

- Automatic has no code in the list, so `tier_reason` returns `None`. Say if you want a sixth code instead, and what to call it. That can stay in `tiers.py`.
- `no_email_route` also covers a captcha, a human step, an account-required site, a health-check-only form, and an email route with no mailbox. Those do not have their own codes.
- When a permission and the automation switch both block a verified form, the code is `permissions_block`, because that check comes first.
- When the email tier wins, the code is `email_ok` even if the form is unverified or a permission would also have blocked automatic.
- Tracker: WO-345 (freemyid-pm#265).

## How to test

From `.vendor-wt/wo-345`. Fake person only (Jane Q Testperson, Springfield IL). No network.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_tier_reason.py
```

36 passed.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "tiers"
```

11 passed, 2724 deselected. The warning is the existing Starlette/httpx deprecation from FastAPI's test client.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```

2524 passed, 206 skipped, 5 xfailed. Same warning. Exit 0.

The 206 skips are pre-existing environment skips (built website missing, Windows-only tests, real scheduler only on CI). They are not passes. Browser-marked tests were run separately (`pytest -q tests -m browser`): 38 passed, 3 skipped. Those 3 skips are `tests/conftest.py:180` (web/dist is not built), not a Playwright launch failure. Chromium did launch. The 3 skips are not passes.

Pre-existing xfails, not caused here and not edited (5 xfailed):

- `tests/test_sec112_flake_lock.py:23` SEC-112 residual: the publish gate does not require `distro/nix/flake.lock`.
- `tests/copilot/test_cp_never_asks_parity.py:87` `docs/FRIDGE_CARD.md:17` missing "never charges you".
- `tests/codex/test_cx_proof_note_a11y.py:150` call-note hint is 18px, two schemes (light and dark).
- `tests/codex/test_cx_monitor_previous_hardening.py:81` SEC-125: a huge `generated_at` is copied (`monitor.py:379`).

```
../../.venv/bin/ruff check tests/grok src/freemyid/engine/tiers.py
```

All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/tiers.py
```

Success: no issues found in 1 source file.

No contract change.
