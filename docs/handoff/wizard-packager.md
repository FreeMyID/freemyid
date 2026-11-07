# wizard-packager handoff
## Done (v1 wave, ruff clean, 22 TestClient drafts pass: src/freemyid/wizard/_test_drafts)
1. Wizard = 6 screens (consent, name, address, about, mailbox, finish) per D6. Provider presets
   gmail/yahoo/icloud/proton_bridge/other + "Skip, I'll do these by hand"; Outlook -> says skip.
   Finish: "run automatically" checkbox (default on) -> scheduler.install (skipped under pytest or
   FREEMYID_NO_BACKGROUND), first run in a thread (dry unless config.real_submissions_enabled), then "/".
2. Dashboard D7: status sentence, to-do cards (ASSISTED_OPT_OUT, SEND_EMAIL_MANUALLY, generic),
   Settings page (schedule, practice/real toggle, per-person mailbox + permissions).
## Todo
3 desktop.py (+ CHANGE REQUEST for `freemyid app`) 4 Windows scheduler 5 packaging/windows
6 .github/workflows/build.yml 7 FAMILY_QUICK_START.md
3. DONE wizard/desktop.py (+ server.start_background, /_focus, /quit); tests test_wizard_desktop.py
4. DONE Windows scheduler: hidden per-user task, windowed FreeMyID.exe/pythonw, idempotent /F, no
   console flash (CREATE_NO_WINDOW); tests test_scheduler_render.py
5. DONE packaging/windows/{freemyid.spec,freemyid.iss,launcher_gui.py,launcher_cli.py}, packaging/README.md.
   Spec test-built on Linux (scratchpad venv): data paths + freemyid-cli OK. Family bundle: iss
   /DFamilyBundle=..., wizard/flows.find_family_bundle, import page uses it.
6. DONE .github/workflows/build.yml
7. DONE FAMILY_QUICK_START.md (text screenshots; real screenshots TBD)
## Wave 2 fixes
- SEC-20 .iss DONE (no FREEMYID_HOME; DelTree only if freemyid.db/.freemyid-home present, after wipe --yes)
- SEC-27 DONE (GET /settings/submissions/confirm page, confirm=yes POST, needs a completed practice scan/dry request). First-email-per-profile approval needs engine change: CR below.
- SEC-17 DONE (To/Subject/escaped letter on outbox cards). SEC-24 DONE (list2cmdline, Hidden=false). SEC-25 DONE (0600 + os.replace). SEC-19 DONE (https only). SEC-23 DONE (EXCLUSIVEADDRUSE on win32).
- CI install test step added to windows-installer job in build.yml (unverified until it runs on GitHub).

## Wave 3 (Windows VM walkthrough fixes) DONE, pytest+ruff green
- Window fits screen: desktop.window_geometry (<=90% of primary screen, centered; webview.screens, Win32 fallback).
- Friendly 403 pages: ui.error_page (3 cases: bad origin, bad CSRF, no session), status unchanged. app.js data-back.
- Installer: DisableDirPage/ReadyPage, SetupIconFile, icon on shortcuts + both exes (spec ICON). tools/make_icon.py -> packaging/windows/freemyid.ico.
- Consent copy: mailbox sentence fixed in draft.py; draft.CONSENT_VERSION now imports consent.CURRENT_TEXT_VERSION. CR pending: bump consent.py to 2026-11-b and keep 2026-11-a in ACCEPTED_TEXT_VERSIONS.
- D9 Fill it in for me: POST /todo/{id}/fill (thread, one at a time), GET /fill (waiting page, meta refresh), outcomes submitted/fallback+submit_seen/else. Tests tests/test_wizard_polish.py.

## Update 2026-11-06 (positioning change requests 1-8 applied)
- Items 1-8 from wizard-packager-positioning.md applied: status_sentence, consent text and authorization form (people-search wording, scope sentence, same legal meaning), STEP_TITLES, report.py (sentence-form counts, "Site", no removed count), "Not running yet" banners now `.note` (style.css already had it; no CSS change), server.py / flows.py / firstrun.py strings. Tests and FAMILY_QUICK_START.md updated to the new sentence. Item 10 (declaration step) deferred.
- Still says "broker" in user-visible text: firstrun is fixed, but cli.py help text (not mine) and the consent hint "also called data brokers" on the welcome screen (intentional, explains the term).
- site/ fact-check done: see orchestrator report (birthday, ID photo, "never leaves your computer", report contents, browser download exception fixed).

## Wave 4 (post v0.1.0)
- SEC-38 DONE: practice mode, first "Fill it in for me" press -> server-rendered GET /todo/{id}/fill/confirm ("This sends a real request to the site."), POST confirm=yes writes <home>/.fill-confirmed; one-time. Tests in tests/test_wizard_polish.py (file is qa-owned? existing; I added one test + ack in _fill_env).
- VM walkthrough of v0.1.0 DONE (brand/screenshots/vm-v0.1.0/01..17, fake Pat Testperson, practice mode, no mailbox, no submissions/email). Findings:
  1. Installer still showed a "Ready to Install ... Click Install" page despite DisableReadyPage=yes (MEDIUM). Fixed in .iss with ShouldSkipPage(wpReady); UNVERIFIED until next CI build (cannot compile Inno here). Until then site copy "Click Install" is correct.
  2. Window fits (905x~680 inside 1024x768), friendly validation errors OK, scheduled task "Free My ID Recheck" created, practice banner shown.
  3. Consent screen: Next button is ~4 page-downs below the fold (LOW, UX; possible fix: shorter consent card or sticky button).
  4. Step 6 never says practice mode is on; dashboard banner is the first mention (LOW).
  5. Toast uses Python icon (LOW; desktop-notifier default icon, needs icon path).
  6. Assisted card step 3 says "Type your removal email address" with no mailbox set and no email in Copy list (LOW, content/engine owner).
  7. Released v0.1.0 lacks the SEC-38 confirm page (ships in next build).

## Wave 5 (v0.1.0 walkthrough follow-ups) DONE
- F3 consent: full legal text now in `<details>` "Read the full wording" (same text, same version); `form.card > .actions` is sticky at the bottom so Next/Back are always visible (all steps).
- F4 finish step: "Practice mode is on. Free My ID will look for listings but will not send anything to any site until you turn that on in Settings." (only when real submissions are off and not editing).
- F5 toast icon: notify.py passes wizard/static/freemyid.png (bundled via the existing static datas entry in the spec; falls back to packaging/windows/freemyid.ico in a checkout). Unverified on real Windows toast.
- F9 dashboard: nothing sent/confirmed yet -> "Free My ID has made a list of sites to work through. Start with the first one below when you have a few minutes." (or "... Nothing needs you yet." with no todos). Old sentence unchanged once anything is submitted/done. Test added.
- Step 4 accuracy finding: NOT never-sent. submitters/base.py: birth YEAR itself is never sent, but if the broker's listing shows age the letter/form gets `profile.estimated_age()` (derived from it); phone is sent only if the listing shows it / required and allowed (allow_phone_disclosure gates phone scripts and search URLs); personal emails and relatives are never sent (only the removal mailbox). Copy changed to: used to find the right listings; a site is only sent what its own listing already shows, never birth year/relatives/personal email, plus the removal address. NOTE: "never a birth year" is literal; an approximate age can appear if the listing shows one. If marketing prefers, reword site copy accordingly.
- Install steps as they are now (for LAUNCH_CHECKLIST / site, v0.1.0 build): 1 download FreeMyID-Setup.exe; 2 SmartScreen "Windows protected your PC": click "More info", then "Run anyway"; 3 installer wizard: a "Ready to Install" page still appears, click Install (ShouldSkipPage(wpReady) fix is in .iss but unverified until the next CI build; after it ships this page disappears); 4 installer finishes and opens Free My ID; 5 the in-app wizard (6 screens: welcome/consent, name, address, about, email, finish). Exe is unsigned, hence SmartScreen.

## CR-W2: Test connection pins the local mail certificate (done)
- Removed the `CERT_NONE` / `check_hostname=False` loopback special case in `wizard/draft.py`. `check_mailbox()` (and the `test_mailbox_connection` wrapper) use `mail_tls.client_context(host, pin)` then `check_peer(sock, pin)` before any login, for both IMAP and SMTP. A local host with no pin is never sent credentials (status `needs_trust`); a mismatch gives `cert_changed`.
- Proton Bridge screen: Test button -> `/wizard/test-connection` returns `status: "trust"` with the readable `AB:12:..` code (from `trust_on_first_use`, no password involved) and big Yes / No buttons. Yes -> `/wizard/trust-certificate` stores the pending fingerprint server-side (`app.state.approved_pin`, never taken from the client) and the test re-runs. On save the pin goes to `MailboxConfig.tls_cert_sha256` via `Draft.tls_pin`. Changed certificate: plain-language explanation and an offer to trust the new code.
- CLI `setup_cli`: `_trust_local` shows the same message and asks yes/no for proton_bridge.
- Saving a Bridge mailbox without a pin is allowed (existing `test_provider_presets` saves one); `_apply_mailbox(require_trust=True)` makes it an error. Suggest qa-security switch it on and update that test.
- Draft tests: `src/freemyid/wizard/_test_drafts/test_wizard_bridge_trust.py` (reuses the fake bridge from `tests/test_mail_tls_pin.py`).

## SEC-53 form + require_trust default (done)
- "Other" provider: new "Incoming uses STARTTLS" checkbox (ui.py; CLI asks too). With SSL and STARTTLS both off, `_apply_mailbox` and `check_mailbox` refuse with `draft.UNENCRYPTED_MSG` ("Your password would be sent unprotected. Turn on SSL or STARTTLS for incoming mail. If you are not sure, leave SSL ticked."). `build_profile` turns a MailboxConfig validator error into `SaveError`, never a traceback.
- `_apply_mailbox(require_trust=True)` is now the default. Callers: draft.apply step "mailbox"/"mailbox_login" (want True), server `/wizard/test-connection` (explicit False: that is where trust is established). Consequence: a Proton Bridge save with no approved pin is refused, so `tests/test_wizard_screens.py::test_provider_presets[proton_bridge-127.0.0.1]` now gets 400. qa-security to update that test to approve a pin first (d.tls_pin / app.state.approved_pin). I did not edit it.
- CR-W3 done: `trust_on_first_use` callers (server.offer_trust, flows._trust_local) pass `netpolicy=NetPolicy(None, allow_loopback=True)`.
- Bridge trust tests adopted into `tests/test_wizard_bridge_trust.py` (no sys.path hack) plus both-off tests.
