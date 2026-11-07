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
   approve_and_send refuses unless real_submissions_enabled or FREEMYID_DEV_FIXTURES.
   CR-2 from qa applied to mail.py.
3. submitters/base.py (copy_fields/form_vars minimization), assisted.py, email.py,
   web_form.py (data-driven search+form, any error -> Assisted todo), engine/plugins.py.
4. engine/runner.py: Runner + run(); consent gate; DROP first for CA; tier stored for every
   broker (ca_drop too); blind brokers presumed FOUND; covered_by mirrors parent; IMAP links
   (confirmation_domains only, never clicked in dry run); escalation ladder; one notification.
5. browser.py: msedge first on win32 (channel_candidates), FREEMYID_BROWSER_EXECUTABLE,
   fixture_base routing (route.fetch -> local server), start().
6. engine/_dev/: registry.yaml (6 fake .example brokers), site/, inbox/, fixture_registry(),
   fixture_server(), fixture_inbox(); devrun.py (`python -m freemyid.engine._dev.devrun
   [--no-mailbox|--submit|--scheduled]`) drives the real CLI `freemyid run --dry-run`.
Also: handoff.mark_resolved (dashboard "I did it" -> SUBMITTED); postal_letter template no
longer embeds a Subject line.

## Tests
- Drafts: `.venv/bin/python -m pytest -q src/freemyid/engine/_test_drafts` -> 20 pass
  (test_tiers, test_runner, test_outbox_letters; conftest re-exports tests/conftest).
- tests/test_e2e_dryrun.py fails ONLY because tests/conftest.make_profile uses
  text_version="v1" (consent gate refuses -> profile skipped). Passes with "v1" accepted.
- Full suite: 167 pass, 2 fail (those two). ruff clean on engine/ and submitters/.

## Notes
- Playwright in .venv expects chromium 1248; ~/.cache has 1208 only. Fixture mode falls back
  to the newest cached headless shell automatically; else set FREEMYID_BROWSER_EXECUTABLE.
- Pending CRs: Config.browser_automation, Windows browser_channel default, conftest
  text_version, interfaces.py run() kwargs doc, pyproject package-data for _dev,
  beautifulsoup4 not needed by engine (can drop).

## Security wave 2 fixes (2026-11-06) - done: SEC-16, 21, 26, 18, 29, 28 (+ SEC-27 engine part)
- SEC-16 browser.py: `service_workers="block"` on every context; every launch gets
  `--host-resolver-rules` from `host_resolver_rules(NetPolicy.allowed)` (fixture mode: only
  localhost/127.0.0.1/::1). Verified: the rules also cover IP literals (unlisted 127.0.0.1 ->
  ERR_NAME_NOT_RESOLVED), so allowlisted IPs are EXCLUDEd explicitly. A `request` listener
  records off-list redirect hops (any frame) and main-frame navigations in
  `ctx.freemyid_escaped`; `goto` and `check_escaped(page)` raise BlockedByPolicy (never
  retried). web_form click/submit calls `bm.check_escaped`; the headed handoff window uses
  `bm.goto`. `url_allowed` uses `netpolicy.host_of`.
  OPEN GAP: Chromium resolves `localhost` itself, so a redirect to an off-list `localhost`
  is SENT before it is detected (probe: hit reached the server, BlockedByPolicy raised).
  It matters only for local services. The full fix is the in-process allowlisting proxy
  (SEC-16 option A), which isn't done. Needs care: Chromium bypasses proxies for loopback
  unless `--proxy-bypass-list=<-loopback>` is set, and route.fetch in fixture mode runs
  in the driver.
- SEC-21: `outbox.dev_fixture_base()` (runner re-exports it): http + loopback host only,
  never when `sys.frozen`; `_default_mailer` uses it.
- SEC-26: `BrowserManager.start()` closes on failure; `Runner.browser()` closes bm too.
- SEC-18 mail.py: anchors parsed with their text; cancel/unsubscribe/not-you/preferences/...
  are dropped by URL tail (path, query, fragment, not the host) or text; confirm/verify links
  are ranked first; runner clicks only `links[:1]`.
- SEC-29 letters: first+last unless MIDDLE_NAME is shown.
- SEC-28: handoff notifications use `GENERIC_HELP`; the run notification passes url=None.
  The click-to-open-app part is in notify.py (wizard-packager), sent as a CR.
- SEC-27 (orchestrator request): `needs_approval(profile, kind, store)`: the first AUTO email
  per profile waits for approval (no store -> approval).
- Removed the strict xfails for SEC-16/18/21/26 in tests/test_security_wave2.py.
- Drafts: src/freemyid/engine/_test_drafts/test_wave2_fixes.py (8 tests;
  run with `.venv/bin/python -m pytest -q src/freemyid/engine/_test_drafts`).
- Results: full suite 243 passed under -W error::PytestUnraisableExceptionWarning; ruff clean.

## D9 "Fill it in for me" (wave 3, 2026-11-06) - DONE, reported
- engine/filler.py: Control (JS scan of main-frame input/select/textarea; marks each with
  data-freemyid-field), classify() (label > aria-labelledby > aria-label > name > id >
  placeholder > title, then autocomplete / input type; negative list first), protected()
  (captcha ancestors/data-sitekey, password/file/hidden/checkbox/radio/buttons, invisible,
  off-screen, aria-hidden, tabindex=-1, disabled/readonly), choose_state_option (NC /
  North Carolina / "NC - North Carolina"), plan_values() = submitters.base.form_vars
  (same minimization as Automatic tier), fill_page() -> FillReport (keys+counts only).
  Never ticks anything; never overwrites a non-empty text box.
- engine/fill_for_me.py: `async fill_for_me(store, profile_id, broker_id, *, timeout_s=600,
  registry=None, browser=None, headed=True, cfg=None, state_laws=None, on_ready=None,
  close_delay_s=4.0) -> FillResult` and `fill_for_me_sync(...)` (runs in a worker thread if a
  loop is already running). Consent gate, covered_by -> parent, web_form + opt_out_url only,
  id-upload w/o permission -> fallback. Headed context via BrowserManager (netpolicy, bm.goto
  check_challenge=False, check_escaped every poll). Banner (yellow/black 26px, role=alert,
  textContent only, re-shown after a reload while a form is on the page). Success = the
  expect_text / wait_for steps after the last click/submit step of Broker.form (what web_form
  checks), and only after a navigation/POST if the text was already on the page. Success ->
  2 screenshots (filled form, confirmation) as SCREENSHOT evidence, SENT web_form Request,
  FOUND->SUBMITTED via mark_submitted (+AWAITING_VERIFICATION if needs_email_verification),
  next_check_at, Event actor=USER detail via=fill_for_me, closes ASSISTED_OPT_OUT/CAPTCHA
  todos. Fallback (timeout, window_closed, unverified, nothing_filled, blocked,
  browser_unavailable, error:<T>) -> existing/new ASSISTED_OPT_OUT todo id in result.
  Practice mode: fills; banner adds "Practice mode is on, but this is the real website:
  pressing Submit really sends your removal request."
- Fixtures: engine/_dev/site/devfill.example/{labels,aria,fullname,empty,done}.html
  (brokers built in tests, dev registry untouched).
- Drafts: engine/_test_drafts/test_fill_for_me.py (+conftest). 54 pass.
- Full: `pytest -q tests src/freemyid/engine/_test_drafts` 305 passed; ruff clean.
- CRs: wizard button; optional `freemyid fill`; Broker.success_text/success_url and
  safe_checkboxes (registry); see final report.

## Wave 4 (2026-11-06): mypy cleanup + D9 registry fields + D10 listing finder - DONE, reported
1. mypy (src clean, `.venv/bin/mypy src` -> no issues): browser.url_allowed treats a None
   host as blocked (only behaviour change); handoff add_cookies cast; plugins var rename;
   web_form `sel = st.selector or ""` guard; fill_for_me navs/task annotations.
2. D9 wired to the new Broker fields: success = expect_text/wait_for OR `success_text` OR
   `success_url_pattern` (fill_for_me.url_matches: re.search on path+query, capped 2048
   chars, fragment ignored). URL success needs the page to have moved; text/selector
   success already on the page needs a move too (unchanged guard). `safe_checkboxes`:
   filler.tick_safe_checkboxes - main frame only, real visible enabled unticked
   `input[type=checkbox]`, not in a CAPTCHA/aria-hidden ancestor, max 10 selectors x 5
   elements, bad selectors skipped; FillReport.ticked (logged as a count).
   Fixture devfill.example/consent.html. Drafts: _test_drafts/test_fill_for_me_fields.py (16).
3. D10 engine/listing_finder.py: `find_listing(store, profile_id, broker_id, *,
   timeout_s=600, registry=None, browser=None, headed=True, cfg=None, on_ready=None,
   close_delay_s=3.0) -> FindResult` + `find_listing_sync(...)`. search_url_pattern ->
   results URL; else Broker.url + filler.fill_page(search_values: first/last/full name,
   city, state only). Banner + green 'This is me' + 'I can't find me' via a context init
   script (DOM APIs + textContent only, re-added every 800 ms, main frames only). Binding
   name random per window; init script moves it into a closure and deletes it from window;
   only `event.isTrusted` clicks report; URL comes from Playwright's source frame (must be
   a main frame). check_listing_url: https, no creds, host on broker.domains, not the
   search page, re.search(listing_url_pattern, path[:2048]) when set, else not "/".
   Accepted -> record_listing: CONFIRMED Listing (score 100, reasons user_confirmed +
   listing_finder, shown_fields = listing_url/full/first/last name/city/state), screenshot
   evidence, after_scan -> FOUND, next_check_at=None, Event actor USER
   `listing_confirmed`, REVIEW_MATCH todos closed. Fallback (timeout, window_closed,
   user_cant_find, blocked [off-allowlist navigation], browser_unavailable, error:<T>) ->
   existing REVIEW_MATCH todo id, else Assisted card (fill_for_me._fallback_todo).
   Fixtures: _dev/site/devfind.example/{search,results,hostile}.html + p/{2 profiles}.
   Drafts: _test_drafts/test_listing_finder.py (32). Drafts folder recreated (qa had moved
   it): __init__.py + conftest.py (same re-export as before) are new copies.
- Results: `pytest -q tests src/freemyid/engine/_test_drafts` 368 passed, 3 xfailed; drafts
  48 pass x3; ruff clean; mypy clean.

## Registry split (2026-11-06) - IN PROGRESS
Public repo ships brokers/registry.sample.yaml only; full brokers/registry.yaml becomes private.
Checkpoint: sample, registry.py, spec, build.yml, LICENSE-DATA, .gitignore, tests/test_registry_split.py done.
Next: full suite with brokers/registry.yaml moved to brokers/registry.yaml.ASIDE (restore if you see that name!).

## Post-v0.1.0 wave (2026-11-07) - IN PROGRESS
Drafts: src/freemyid/engine/_test_drafts/ (conftest re-exports tests/conftest; qa to adopt).
1. DONE SEC-27 engine: outbox.email_sent_before (only a real SENT *email* opens the gate; a
   web-form SENT no longer does), held_by_first_approval, first_email_pending (for the
   dashboard card), HOLD_ACTION Event marker per held request, release_held (approve_and_send
   in AUTO mode sends every held AUTO email; legal demands / dry / approve_each untouched;
   one failure doesn't stop the rest; RELEASE_ACTION event with counts). queue_email also
   sends an existing held AUTO request once the gate is open (was stuck forever before).
   Drafts: test_first_email_approval.py (7).
2a. DONE reply matcher (mail.py): pure scan_replies(raws, broker, since) -> ReplyScan(links,
   id_requested, messages, duplicates, stale). Dedupe by Message-ID (else bytes); mail dated
   before last_submitted_at - 1h is stale (old confirmation never clicked for a new
   submission); newest message's links first (broker answering twice); any reply asking for
   an ID document (asks_for_id: gov/state-issued, photo ID, driver's licence, passport, SSN,
   last 4 digits, notarized, utility bill, proof of identity/address) contributes NO links.
   Both mailers have async scan_replies(); wait_for_confirmation returns [] on an ID request.
   Runner._verify: ID request -> ID_UPLOAD todo (resume_token id_requested:<broker>), state
   NEEDS_HUMAN reason id_requested, nothing clicked/sent (dry run: event only); open ID todo
   pauses new submissions to that site (_id_hold); handoff.mark_resolved on that todo ->
   SUBMITTED (clocks restart). Event mail_replies_skipped(duplicates, stale).
   Drafts: test_reply_matcher.py (13).
   (qa adopted test_first_email_approval.py + test_reply_matcher.py into tests/.)
2b. DONE escalation timers (runner._escalate): a rung whose letter FAILED keeps the level and
   retries one window later (escalation_failed event) instead of skipping to the next rung;
   an unapproved queued request or an open manual_email:<broker>:* to-do blocks the next
   rung (escalation_waiting, why=awaiting_approval|awaiting_manual_letter); _ladder_view
   anchors the wait on the latest real SENT time (a follow-up approved 40 days late no longer
   lets the legal demand come 5 days after it). outbox.released_by_approval(store, profile,
   req) for the SEC-47 approve card. Drafts: test_escalation_timers.py (6).
2c. DONE search guard (submitters/web_form.search_listings): HTTP >= 400 on the search page,
   or a page with neither results nor the configured no_results_text, raises UnexpectedPage
   (runner: scan_failed -> treated as blind) instead of recording a false NOT_FOUND.
   Fixtures _dev/site/devauto.example/name/jane-testperson/{nc,oh}.html. Drafts:
   test_search_guard.py (3).
3. DONE VM finding 7 (submitters/assisted.py): without a mailbox, registry steps' "your/the
   removal email (address)" renders as "an email address you can check", plus a note (own
   address is fine; leave empty if optional). With a mailbox nothing changes. Registry prose
   untouched. Drafts: test_assisted_no_mailbox.py (2).
4. DONE SEC-48 (coordinator request, wizard/server.py was clean): /outbox/{rid}/approve runs
   approve_and_send via starlette run_in_threadpool (store is RLock + check_same_thread=False).
   SEC-47: server._disclose_releases splices a note into the first-email card ("Approving it
   also sends the N other emails waiting for <label> (to: <sites>)...") and changes its
   confirm to "Send this email and N others now?", using outbox.released_by_approval.
   Both strict xfails removed in tests/test_security_wave3.py (coordinator-authorized).
   dashboard.py NOT edited (peer session had uncommitted changes) -> CR-W1 below.
5. DONE fixture audit: engine/_dev (registry, site, inbox), tests/fixtures/registry_min.yaml,
   drafts: only *.example / .invalid / loopback hosts, fake "Jane (Q) Testperson", no real
   streets or non-555 phones. tests/*.py use example.org/example.com (RFC 2606 reserved, qa).

## Open CRs (this wave)
- CR-W1 wizard-packager, dashboard.outbox_page: render the SEC-47 note inside the card
  (call engine.outbox.released_by_approval(store, profile, r) when building items) and
  delete server._disclose_releases. Same text as now.
- CR-M1 orchestrator, models.Request: optional `held_reason: str | None = None`
  ("first_email") so the hold is a field, not inferred (today: AUTO + queued + email + not
  legal demand, plus the email_held_first_approval Event as audit).
- CR-M2 orchestrator, interfaces.Mailer: add `async scan_replies(profile, broker, since,
  timeout_s=0) -> engine.mail.ReplyScan` (both mailers implement it; runner falls back to
  wait_for_confirmation if missing).
- CR-R1 broker-researcher: registry steps could say "your email" instead of "removal email";
  the Assisted card now rewrites it when no mailbox exists, so this is cosmetic only.

## 2026-11-07 TLS pinning for Proton Bridge (PROGRESS ticket)
- models.MailboxConfig.tls_cert_sha256 (orchestrator-approved single field): lowercase hex
  SHA-256 of the DER leaf cert; colons/spaces/uppercase normalised; else ValidationError.
  Schemas unchanged (gen_schema covers Registry/StateLaws only).
- engine/mail_tls.py: client_context(host, pin) (no pin -> ssl.create_default_context(),
  unchanged; pin + non-loopback -> TlsPinError; loopback = exactly 127.0.0.1, ::1,
  localhost), check_peer(sock, pin) (hmac.compare_digest on sha256 of the DER peer cert),
  fetch_loopback_fingerprint / trust_on_first_use(mb) -> TrustResult(fingerprint, display,
  plain-language message). TOFU never sends credentials.
- engine/mail.py: SMTP (STARTTLS + SSL) and IMAP (STARTTLS + SSL) check the pin right after
  the handshake, before login; mismatch -> MailError("... refused: ...").
- tests/test_mail_tls_pin.py (17): fake self-signed IMAP/SMTP server on 127.0.0.1.
- Open CR-W2 wizard-packager: on the proton_bridge mailbox screen, call
  trust_on_first_use(mb), show .message with Yes/No, store .fingerprint in
  mb.tls_cert_sha256 on Yes; on MailError containing "certificate changed" offer re-trust.
  SECURITY: wizard/draft.py ~L394 ctx_for() "Test connection" sets CERT_NONE +
  check_hostname=False for loopback WITHOUT a pin and then logs in with the Bridge password.
  Replace with mail_tls.client_context(host, pin) + check_peer(sock, pin) before login
  (no pin -> verified context fails for Bridge, which is correct; run TOFU first).
- Open CR-C1 orchestrator (optional): `freemyid mailbox trust <profile>` CLI wrapper.

## 2026-11-07 SEC-50 / SEC-51 / SEC-53 (engine side) - DONE
- b631dfe SEC-53: `SmtpImapMailer._imap` refuses plaintext IMAP (imap_ssl and imap_starttls
  both false) on EVERY host, loopback included, before any socket opens:
  MailError("mail connection is not encrypted; refusing to sign in"). Independent of the
  f1167f5 model validator (bypassable via model_copy). qa's strict xfail
  `test_qa_sec53_plain_imap_without_pin_is_refused` now XPASSes -> qa-security should drop
  the xfail marker (their file; not touched).
- c92a9f9 SEC-50: mail_tls.LOOPBACK_PEER_IPS = {127.0.0.1, ::1}; `check_loopback_peer(sock)`
  (exact match on getpeername()[0], fails closed on any error/shape). Called by
  `check_peer` whenever a pin is set (so mail.py SMTP+IMAP and wizard draft.py inherit it)
  and by `fetch_loopback_fingerprint` before reading the cert. LOOPBACK_HOSTS (name-level,
  incl. `localhost`) unchanged. Bridge preset already stores 127.0.0.1 (wizard/draft.py
  PRESETS, wizard-owned; no change needed).
- 678db34 SEC-51: `fetch_loopback_fingerprint(..., netpolicy=None)` and
  `trust_on_first_use(mb, timeout_s=10.0, *, netpolicy=None)` call `is_allowed(host)` for
  both hosts before connecting -> TlsPinError("mail host not on allowlist"). None falls back
  to `NetPolicy(None, allow_loopback=True)` (still loopback-only via is_loopback).
- CR-W3 wizard-packager: pass the wizard's NetPolicy: `trust_on_first_use(mb,
  netpolicy=<policy>.with_loopback())` in wizard/server.py offer_trust and wizard/flows.py
  _trust_local. Backward compatible; optional.
- Still open: SEC-52 (TOFU with a plaintext config uses STARTTLS; now unreachable through a
  validated MailboxConfig, cheap to add the same refusal in trust_on_first_use if wanted).
- Tests: tests/test_mail_sec50_53.py (new, fakes only, no network).
