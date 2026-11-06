# automation-engineer handoff

Scope = PLAN_V1 D1-D4 (end-to-end loop). Per-broker parsers DROPPED. Next wave (not started,
wait for orchestrator): D9 visible-Edge "Fill it in for me" + D10 listing finder.

## Status: wave complete (steps 1-6), reported to orchestrator
1. engine/tiers.py: tier_for / automatic_eligible (needs real fill/click steps, verified,
   no captcha/human step, permissions ok, Config.browser_automation) / has_email_route /
   can_scan / submit_target (covered_by -> parent).
2. engine/outbox.py: compose, compose_links (Gmail/Outlook/Yahoo/mailto), queue_email,
   send_request, approve_and_send, effective_law (template: ccpa/state_privacy ONLY when the
   current-address state's law has last_verified, deletion right, in effect; else generic).
   Letters stored as LETTER evidence; dry_run -> DRAFT never sent; legal demand always queued;
   approve_and_send refuses unless real_submissions_enabled or VANISH_DEV_FIXTURES.
   CR-2 from qa applied to mail.py.
3. submitters/base.py (copy_fields/form_vars minimization), assisted.py, email.py,
   web_form.py (data-driven search+form, any error -> Assisted todo), engine/plugins.py.
4. engine/runner.py: Runner + run(); consent gate; DROP first for CA; tier stored for every
   broker (ca_drop too); blind brokers presumed FOUND; covered_by mirrors parent; IMAP links
   (confirmation_domains only, never clicked in dry run); escalation ladder; one notification.
5. browser.py: msedge first on win32 (channel_candidates), VANISH_BROWSER_EXECUTABLE,
   fixture_base routing (route.fetch -> local server), start().
6. engine/_dev/: registry.yaml (6 fake .example brokers), site/, inbox/, fixture_registry(),
   fixture_server(), fixture_inbox(); devrun.py (`python -m vanish.engine._dev.devrun
   [--no-mailbox|--submit|--scheduled]`) drives the real CLI `vanish run --dry-run`.
Also: handoff.mark_resolved (dashboard "I did it" -> SUBMITTED); postal_letter template no
longer embeds a Subject line.

## Tests
- Drafts: `.venv/bin/python -m pytest -q src/vanish/engine/_test_drafts` -> 20 pass
  (test_tiers, test_runner, test_outbox_letters; conftest re-exports tests/conftest).
- tests/test_e2e_dryrun.py fails ONLY because tests/conftest.make_profile uses
  text_version="v1" (consent gate refuses -> profile skipped). Passes with "v1" accepted.
- Full suite: 167 pass, 2 fail (those two). ruff clean on engine/ and submitters/.

## Notes
- Playwright in .venv expects chromium 1248; ~/.cache has 1208 only. Fixture mode falls back
  to the newest cached headless shell automatically; else set VANISH_BROWSER_EXECUTABLE.
- Pending CRs: Config.browser_automation, Windows browser_channel default, conftest
  text_version, interfaces.py run() kwargs doc, pyproject package-data for _dev,
  beautifulsoup4 not needed by engine (can drop).
