# qa-security handoff
Done (earlier): scaffold review (docs/SECURITY_REVIEW.md), conftest, fixtures, test_models,
test_state, test_crypto, test_storage, test_redaction, test_netpolicy, test_consent.
Done (v1 wave 1, 2026-11-06):
- Fixed test_log_file_redacted: CLI tests call logging_setup.setup(), which leaked a StreamHandler
  bound to CliRunner's (closed) stderr into later tests and made setup() a no-op. conftest's
  autouse `freemyid_env` now removes/closes any root handlers a test adds and restores the level.
- Dropped the SEC-04b xfail marker (Store now registers profile PII).
- tests/ ruff clean (dict literals, import order, UTC, InvalidTag instead of blind Exception).
- New tests: Tier, BrokerStatus.tier, new TodoKinds, Todo.copy_fields (models, encrypted store
  round-trip with no plaintext on disk, never logged). SEC-15 strict xfail (copy_fields in repr).
- tests/test_e2e_dryrun.py: scaffold, skips until freemyid.engine.runner.run and a dev module
  exposing fixture_registry() + fixture_server() exist (looks in freemyid.engine._dev, freemyid._dev,
  freemyid.engine.devrun). Asserts D1 tiers, data-minimized copy_fields, nothing sent.
Open CRs: interfaces.py UP037 (orchestrator), engine/mail.py S110 (automation-engineer),
models.py SEC-15 repr=False (orchestrator).
Next: adopt src/freemyid/wizard/_test_drafts and tests/fixtures/test_wizard_server.py (misplaced
test file in fixtures/) once wizard-packager's wave settles; un-skip e2e when runner lands and
align _load_dev() names; tools/registry_health.py; review engine/wizard/scheduler for this wave.
Wave 2 (2026-11-06):
- Step 1 DONE: git mv engine/_test_drafts/test_{outbox_letters,runner,tiers}.py and
  wizard/_test_drafts/test_{scheduler_render,wizard_dashboard,wizard_desktop,wizard_screens,
  wizard_server}.py into tests/; deleted the drafts' conftest/__init__ and both draft dirs.
  tests/fixtures/test_wizard_server.py no longer exists. e2e dry-run now runs (not skipped).
  pytest 220 passed, ruff clean.
- Step 2 tests DONE: tests/test_security_wave2.py (14 pass, 7 strict xfail = SEC-16,18,19,20,
  21,22,24). Redirect bypass (SEC-16) confirmed live with the cached chromium headless shell.
- Step 2 doc DONE: SECURITY_REVIEW.md wave-2 section (SEC-16..29). Verdict BLOCK on SEC-16.
- Orchestrator FYI handled: Windows CI 'Event loop is closed' = SEC-26 (Playwright driver leak on
  failed launch), reproduced + fix verified on Linux; xfail test cleans up after itself.
Next wave: remove xfail markers as SEC fixes land; tools/registry_health.py still TODO.
Wave D9 (2026-11-06):
- A DONE: tests/test_wizard_browser_e2e.py. Real Playwright Chromium (headless) against
  start_background() with FREEMYID_NO_BACKGROUND=1: all 6 screens (Pat Testperson, Raleigh NC) to
  the dashboard, then a Settings permissions save. Asserts each POST → 303 → expected next step,
  real Origin header, no 403/5xx, Referrer-Policy != no-referrer, nothing leaves 127.0.0.1. A
  second test checks that foreign, null and other-port Origins and a bad CSRF still get 403. Skips
  if Chromium can't launch. Negative check (scratch, not committed): forcing no-referrer via an
  ASGI header rewrite gives Origin: null → 403 and the walk stops on step 1, so the test catches
  the 54ff105 bug, including with the context route in place.
- B DONE: engine/_test_drafts/test_fill_for_me.py → tests/test_fill_for_me.py (byte-identical,
  54 pass; no conftest changes needed). Verified it before git rm of engine/_test_drafts.
- C DONE: SECURITY_REVIEW.md D9 section SEC-30..38; tests/test_security_d9.py (3 pass, 4 strict
  xfail = SEC-30,31,32,33). Verdict BLOCK (narrow) on SEC-31 (robot checkbox via broad
  safe_checkboxes selector).
- Full suite: 320 passed, 4 xfailed; ruff clean.
Next: remove xfail markers as SEC-30..33 land; tools/registry_health.py still TODO.
Post-v0.1.0 wave (2026-11-07):
- SEC status table in SECURITY_REVIEW.md: SEC-01..45 = 41 Fixed, 4 Accepted (38, 41, 44, 45), 0 Open.
  Rulings recorded (SEC-38 accepted + one-time confirm 8637941; SEC-41 accepted by peer ruling +
  regenerated 450bb34; SEC-44/45 INFO). SEC-40/42/43 confirmed with tests.
- tools/registry_health.py DONE (offline default; --online HEAD via NetPolicy, polite; --selectors;
  --report md/json; exit 1 on ERROR). tests/test_registry_health.py (33, no network). Real
  registries: 0 errors, 447 warnings (mostly no last_verified). CR: weekly CI workflow (below).
- Adopted drafts: test_first_email_approval.py (7), test_reply_matcher.py (13),
  test_escalation_timers.py (6); tracked engine/_test_drafts removed (a6c6869). An untracked
  test_search_guard.py appeared there afterwards (automation-engineer WIP): adopt next time.
- New: SEC-46 (fixed 85e1f74 by O), SEC-47 MED open (approve card hides held AUTO emails it also
  sends), SEC-48 LOW open (approve sends on the event loop), SEC-49 LOW open (/safety/ report
  copy omits the label). tests/test_security_wave3.py: 3 strict xfails (47, 48, 49) + guards.
- Use FREEMYID_TEST_NO_FULL_REGISTRY=1 to run as a public checkout (never rename registry.yaml).
- CR (orchestrator, .github/workflows): weekly job `python tools/registry_health.py --report
  registry-health.md` (offline; add --online only if the runner's egress is acceptable), upload
  the report as an artifact.
Next: remove xfail markers as SEC-47/48/49 land; adopt test_search_guard.py.
