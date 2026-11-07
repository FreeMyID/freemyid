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

## 2026-11-07 Scheduled social poster (tools/social/) - DONE, NOT INSTALLED
- 58eb3f5 / 08ca135: tools/social/poster.py (httpx; stdlib otherwise). One queued item per run
  from docs/marketing/seo/bluesky-queue.md -> bsky.social createSession + createRecord with
  link facets (UTF-8 byte offsets). Strict parser (`## Q-NNN`, `status:`, optional `note:` lines,
  ```text fence); malformed blocks skipped with a warning. >300 graphemes skipped (stdlib grapheme
  approximation: ZWJ/flags/skin tones/combining marks/VS). Success -> atomic status rewrite
  (re-parses fresh file, refuses if the block changed) + outreach-log row. Allowlist
  {bsky.social} checked before every request; verify=True, no redirects, trust_env=False, 20 s.
  Secrets scrubbed by a logger filter + PosterError messages (scrub before truncation).
  Exit 0 ok/skip, 1 HTTP (item stays queued), 2 posted but not recorded, 3 unreadable queue.
  Backend protocol; MastodonBackend stub (not in BACKENDS).
- c6eb11d: freemyid-poster.service (oneshot, hardened: NoNewPrivileges, PrivateTmp,
  ProtectSystem=strict, ProtectHome=read-only + ReadWritePaths=docs/marketing/seo,
  RestrictAddressFamilies, etc.), freemyid-poster.timer (10:00 + 16:00, Persistent,
  RandomizedDelaySec=300), README with install/pause commands. systemd-analyze verify clean;
  a transient `systemd-run --user` dry-run with the same sandbox worked and reached the keyring.
- tests/test_social_poster.py (44). Handle = `user` field of keyring entry `bluesky`.
- Open: bluesky_token not yet in keyring (runs will skip until it is). Lead installs the timer.

## Checkpoint 2026-11-07 (orchestrator, session end)
- SEC-57/58/59 fix: NOT done. The agent stopped on a usage limit with nothing on disk; tree was clean at bbf96b1.
- Next (in order, one commit each, no push until the lead says):
  1. SEC-57: fcntl.flock lockfile in docs/marketing/seo/; atomic `status: posting <iso>` before createSession; revert to queued only on definite pre-createRecord failure; `posting` never auto-retried; strict at:// URI regex; escape URI with `_cell` in outreach-log.
  2. SEC-58: skip items whose text has Unicode Cf chars (except ZWJ in emoji); keep /über paths working.
  3. SEC-59 (lead's decision): tools/social/install.sh. Read-only copy at ~/.local/share/freemyid-poster/poster.py (0444, dir 0555) + own pinned venv (httpx, keyring); COPY unit/timer to ~/.config/systemd/user (0444); ExecStartPre `sha256sum -c` against a hash pinned in the installed unit; `--update` recomputes and prints the hash (lead-only step); never enables the timer; refuses root; test only on a temp HOME. README: install/update/pause/uninstall, drop ln -sf steps.
- Don't edit tests/test_social_poster.py (qa-owned; strict xfails flip when fixed). Own tests go in tests/test_social_poster_state.py.
- Timer install waits on qa PASS after these land.

## v0.2 secrets backends (Theo Park, 2026-11-07)
Files: `src/freemyid/secret_backends.py` (new), `crypto.py` (`_get_or_create_key` -> backend;
old keyring code now `_keyring_get_or_create_key`, unchanged; `delete_key` clears every backend),
`secrets.py` (mailbox passwords via `select()`), `config.py` (`secrets_backend`, default None =
auto). Tests: `tests/test_secret_backends.py` (29). CLI wiring for `migrate` NOT done (cli.py
is in another session's hands); see "CLI wiring" below.

### Design
- Store format unchanged (`V1` AES-GCM blobs, same 32-byte data key). Only the key's home moves.
- keyring: same service/entry (`freemyid`/`db-key-v1`) as 0.1. Windows installs see no change.
- passphrase: `FREEMYID_HOME/datakey.wrapped.json` = {v, kdf=scrypt, n=2^17, r=8, p=1, salt(16),
  nonce, AES-GCM(KEK, data key, AAD "freemyid:datakey-wrap:v1")}. Mailbox passwords in
  `FREEMYID_HOME/secrets.enc` (JSON map encrypted with the data key, AAD "freemyid:secrets:v1").
  Both written 0600 via temp file + replace/link.
- systemd-creds: same wrap file; passphrase from `$CREDENTIALS_DIRECTORY/freemyid-passphrase`.
  So an admin can create the key interactively and run the timer with `LoadCredential=`.
- Selection: config wins. Auto: wrap file exists -> passphrase (systemd-creds if the credential
  is present); keychain usable -> keyring; no keychain and no DB yet -> passphrase with a plain
  notice; no keychain but a DB exists -> fail closed (never mint a key that orphans data).
- `migrate(to)` -> `MigrateResult(from_backend, to_backend, secrets_moved, changed)`: loads the
  key from the current backend, writes and re-reads it in the target (compare_digest), switches
  config, copies mailbox passwords (ids from the store's profiles + secrets.enc), verifies, and
  only then deletes the old copy. On failure config is restored and the source is untouched.
  passphrase <-> systemd-creds is a config-only change (shared wrap).

### CLI wiring (for whoever owns cli.py)
```python
secrets_app = typer.Typer(help="Where Free My ID keeps its encryption key and passwords.")
app.add_typer(secrets_app, name="secrets")

@secrets_app.command("migrate")
def secrets_migrate(to: Annotated[str, typer.Option("--to", help="passphrase|keyring|systemd-creds")]):
    from . import crypto, secret_backends
    try:
        r = secret_backends.migrate(to)
    except (ValueError, crypto.KeyUnavailable) as e:
        con.print(f"[red]{e}[/]"); raise typer.Exit(2)
    con.print(f"Now using {r.to_backend} (was {r.from_backend}); "
              f"{r.secrets_moved} saved password(s) moved." if r.changed else "Nothing to change.")
```
Optional `freemyid secrets status` = `secret_backends.select().name`. `doctor` can call
`KeyringBackend().usable()` for the keychain check.

### Threat model (for qa-security)
Assets: data key (decrypts every profile/evidence blob), mailbox app passwords, passphrase.
In scope / mitigations:
- Offline theft of FREEMYID_HOME (backup, stolen disk): wrap needs scrypt(passphrase) at
  2^17/8/1 (~128 MiB, ~0.2 s per guess). Strength is bounded by the passphrase; min 8 chars
  enforced at creation only. Weak passphrases are the main residual risk.
- Passphrase leakage: never read from a plain env var (`FREEMYID_PASSPHRASE` is refused with a
  message that does not echo it); passphrase file must be a regular file owned by the user with
  no group/other bits (0600/0400), checked on the opened fd with O_NOFOLLOW (no symlink, no
  TOCTOU swap); max 4 KiB; never logged; prompts via getpass with confirmation on creation.
- systemd credential: world-readable refused; group-readable allowed (systemd may set it).
- Wrong passphrase / tampered wrap: AES-GCM tag fails -> KeyUnavailable, file untouched, no new
  key minted. Wrong passphrase and tampering are indistinguishable (tag check is constant time
  in OpenSSL; secret comparisons use hmac.compare_digest).
- KDF downgrade/DoS via edited wrap file: n must be a power of two in [2^14, 2^20], r in [8,16],
  p in [1,4], salt >= 16 bytes, else "corrupt".
- Silent plaintext fallback: impossible; there is no plaintext backend. Rejected keyring
  backends (fail/null/PlaintextKeyring) still count as unusable. Explicit `keyring` never falls
  back.
- Data split between two keys: auto never creates a passphrase key when a DB already exists
  without a wrap; Store's key_check still refuses a mismatched key.
- Migration loss: target verified before source deletion; config rolled back on failure.
Out of scope / residual:
- Malware running as the user (can read the file, keylog the prompt, or read process memory;
  the unwrapped key is cached in-process for the run, as Cipher already holds it).
- Windows: POSIX mode checks are skipped for the passphrase file (NTFS ACLs not inspected);
  Windows users stay on Credential Manager by default.
- Root/admin on the box, swap/hibernation containing the key, cold-boot.
- `FREEMYID_TEST_KEY` path is unchanged (pytest or FREEMYID_ALLOW_TEST_KEY=1 only).
Suggested qa checks: race two first-run processes (os.link exclusivity), fuzz the wrap JSON,
confirm no passphrase/key bytes in logs at DEBUG, and wipe on a headless box (delete_key now
swallows any KeyringError).

## CLI v0.2 (Theo Park, 2026-11-07)

Done (all in `cli.py` plus new modules; reference `docs/CLI.md`):
- `--json` on status, report, profile list, todo list, outbox list, registry show/source,
  schedule status, secrets status, doctor, and scan/run (`run/1`). Shapes live in
  `src/freemyid/cli_json.py` (`"schema": "<name>/1"`, add-only). With --json, human messages
  go to stderr (`cli._ui()`), stdout is one JSON object.
- Exit codes `cli_json.EXIT_*`: 0 ok, 1 error, 2 usage, 3 needs-human, 4 not-configured.
- `run --headless` / `scan --headless`: interactive=False, never prompts; fails closed:
  no DB / no profiles / KeyUnavailable / practice mode without --dry-run -> 4; nobody with
  valid consent -> 3. After a headless run: needs_human>0 -> 3, else errors>0 -> 1, else 0.
  Interactive `run` still exits 0. `--headless --scheduled` keeps the practice-mode dry run.
  KeyUnavailable now exits 4 with a message on every store-opening command (was a traceback).
- `freemyid doctor` (`src/freemyid/doctor.py`): python, home, secrets (secret_backends.select()
  + KeyringBackend().usable()), store (never creates the DB), browser (FREEMYID_BROWSER_EXECUTABLE,
  system Chrome/Edge, Playwright cache incl. PLAYWRIGHT_BROWSERS_PATH), scheduler, mailbox
  (TCP + TLS hello via NetPolicy, no login; loopback = TCP only; `--offline`), registry age
  (warn > 120 days). Exit 1 if any fail.
- `freemyid setup --from FILE [--yes] [--check] [--update]` (`src/freemyid/setup_config.py`):
  pydantic `SetupConfig` v1 -> wizard Draft via `draft.apply_step` (same validators) ->
  `save_draft`. Passwords only via `password_env`/`password_file`; inline `password` rejected.
  Errors list field paths, never values. Schema `schema/setup-config.schema.json` generated by
  `tools/gen_schema.py` (edited, orchestrator-owned); example `docs/examples/setup-config.example.yaml`.
- `freemyid secrets status [--json]` and `secrets migrate --to ...` (ValueError/KeyUnavailable -> exit 2).
- Tests: `tests/test_cli_json_headless.py`, `tests/test_cli_doctor.py`, `tests/test_cli_setup_from.py`.

Notes / open:
- setup_config imports `wizard.flows._Form` (private) and `draft.apply_step`; wizard-packager
  has uncommitted edits in draft.py/flows.py right now: re-run tests/test_cli_setup_from.py
  after they land.
- No config keys are read beyond existing ones (`browser_automation`, `browser_channel`,
  `registry_url`, `real_submissions_enabled`; `secrets_backend` via secret_backends).
- schedule/1 `installed` is parsed from `scheduler.status()` text; if scheduler grows a
  structured status, switch `cli_json.schedule_doc` and `doctor.check_scheduler` to it.
- Exit 3 after every headless run that leaves Assisted/NEEDS_HUMAN items may be noisy for
  cron users; docs suggest `SuccessExitStatus=3`. Orchestrator call if you want it opt-in.
