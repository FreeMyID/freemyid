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

## SEC-55 per-draft approved pin (done)
- Removed global `app.state.approved_pin`. The approved fingerprint lives only on the draft (`Draft.tls_pin`, set by `/wizard/trust-certificate` from the server-side `pending_pin`; the browser never supplies it).
- Settings mailbox GET makes `draft_from_profile(p)` the app draft (replacing any other) and clears `pending_pin`. POST applies a draft pin only if the app draft's id equals that profile id; otherwise the profile's saved pin is kept. After a successful save, wizard finish, new draft or edit start, `pending_pin` is cleared and the draft dropped.
- Tests added to `tests/test_wizard_bridge_trust.py` (A vs B, direct POST to B, cleared after save, new draft drops pending, edit keeps saved pin). Existing trust test now reads `app.state.draft.tls_pin`.

## SEC-56 import clears pending_pin (done)
- `POST /wizard/import` now sets `app.state.pending_pin = None` right after `load_bundle` replaces the draft. All other `app.state.draft` assignments (init, get_draft new, edit start, settings GET, finish, cancel) already cleared it.
- Test: `tests/test_wizard_bridge_trust.py::test_import_drops_pending_pin_and_old_prompt_cannot_pin_imported_draft`.

## VM check of CI run 42384413361 (main@6aa4661), 2026-11-07
Installer artifact is FreeMyIDSetup-0.1.1 (pyproject still says 0.1.1, so this is not labelled 0.1.2). Clean snapshot, fake Pat Testperson, practice mode. Screenshots: brand/screenshots/vm-v0.1.2/.
- PASS: SmartScreen More info -> Run anyway (launching from Explorer; a scheduled-task launch skips SmartScreen). Installer, all 6 wizard screens, dashboard, window fits 1024x768 (~905x680, above taskbar), toast shows the Free My ID icon.
- PASS: Proton Bridge, no Bridge running: Test -> red box, no password sent (nothing listening), Next -> "Please press Test that it works and approve the security code first." Not saved; cmdkey list empty, "fakepassword" not in the data folder.
- PASS: Other, SSL and STARTTLS both off: Test and Next both show "Your password would be sent unprotected ..." and refuse.
- Findings: (1) LOW: Bridge unreachable message is "could not reach the mail app (ConnectionRefusedError); is it running?" - exception name leaks, not a calm Bridge-specific message. (2) LOW: the Ready to Install page still appears (ShouldSkipPage fix ineffective). (3) LOW: after the refused Bridge attempt, the "Other" form says "A password is saved. Leave empty to keep it." though nothing is stored (draft holds it in memory). (4) MEDIUM-ish: silent uninstall while the app is running leaves FreeMyID.exe + _internal behind (files locked); with the app closed it removes the install dir, shortcut and the "Free My ID Recheck" task cleanly. Silent uninstall keeps user data by design. GUI uninstall dialog not exercised.

## v0.2 "Every platform" + v0.1.3 fixes (Nina Alvarez)
- A schedulers: Linux systemd --user timer+service and macOS LaunchAgent install/remove/status are real (launchctl bootstrap/bootout gui/<uid>, status via `launchctl print`; systemctl --user daemon-reload/enable --now; cron fallback; install message hints `loginctl enable-linger $USER`). Job is `freemyid run --headless --scheduled` on Linux/macOS (Windows unchanged: `run --scheduled`). FREEMYID_HOME and FREEMYID_PASSPHRASE_FILE are copied into the unit/plist Environment. User level only. Tests: tests/test_scheduler_real.py (fake `_run`), test_scheduler_render.py.
  DEPENDENCY: `--headless` on `run` is being added to cli.py by another engineer; until it lands, a scheduled Linux/macOS job fails with a usage error. Same for `freemyid doctor --json` (Docker HEALTHCHECK).
- B PyPI: pyproject has classifiers, urls, SPDX license, sdist include list; wheel carries only registry.sample.yaml + state_laws.yaml + LICENSE-DATA.md + schema (force-include per file, no full registry). tests/test_wheel_contents.py builds the wheel and asserts it (skips if `build` is missing; `build` added to dev extras). Built 0.1.2 wheel locally; `pipx install` from the wheel in a temp HOME works, `freemyid --help` OK, registry source = sample (31 brokers). Note: system pipx at ~/.local/bin is broken (missing module), I used a scratch venv pipx.
- C Docker: packaging/docker/{Dockerfile,compose.example.yaml,example-config.yaml}, root .dockerignore (excludes brokers/registry.yaml, zzz_legacy, docs, site, tests). python:3.12-slim-bookworm + `playwright install --with-deps chromium` to /opt/ms-playwright, uid 10001, HOME and FREEMYID_HOME=/data. Built with podman; verified non-root, `touch /x` fails (read-only), Chromium launches and renders under --read-only --tmpfs /tmp, only the sample registry is present. Not verified: HEALTHCHECK/`run --headless` (need CLI flags), hadolint (not installed), docker (daemon works but I used podman), GHCR publish. example-config.yaml keys are illustrative until the `setup --from` schema lands.
- D v0.1.3: uninstaller runs taskkill /F /T /IM FreeMyID.exe (+1.5 s) at usUninstall before the wipe prompt and file removal (CI/VM needed: compile with iscc, silent uninstall while the app runs). Ready page: dead DisableReadyPage line removed, comment records it stays on purpose (there was no ShouldSkipPage code left). Bridge unreachable copy: draft.unreachable_message (Bridge-specific vs generic), used by test connection, offer_trust and CLI; sign-in/outgoing errors no longer show exception names. Password hint: Draft.saved_password is true only when the secret store really holds a password; typed-but-unsaved shows "ready but not saved yet". Tests: tests/test_wizard_v013.py.

## v0.3 app redesign (Nina Alvarez) DONE
- Shared look: `wizard/static/tokens.css` is a byte copy of `web/src/styles/tokens.css` (test `test_tokens_css_matches_site_copy` fails if they drift: re-copy). `style.css` rewritten on the `--fmi-*` tokens, same class names. Icons are CSS masks (`static/icons/*.svg`, brand/v3 style), art in `static/img/` (copies of brand/v3/sections). No inline styles/scripts (CSP unchanged). Illustrations follow the OS scheme only, not the manual toggle.
- Dark mode: tokens' `light-dark()` + `<html data-theme>`. Header toggle (JS) stores `fmi_theme` in a cookie (shared across ports; localStorage is per-port and the port is random). `static/theme.js` applies it before paint.
- Today (`/`): practice/consent banners (kept), one hero card (outbox approval first, else the first todo reusing `todo_card`, else a calm card), then `N requests sent, N confirmed, N need you` (real sent only, practice excluded). Remaining todos under "Also waiting", then Protect and exposure cards. `dashboard.home_page` has new kwargs `sent`, `exposure`, `protect`.
- Broker detail `/profile/{pid}/site/{bid}` (views.broker_page): what the site shows, requests, replies, next check, receipts, short timeline. Linked from the Sites table.
- Protect yourself `/protect?p=`: `checklists.load()` via `wizard/protect.py`. Ticks are append-only encrypted audit Events (actor USER, action `checklist_done`/`checklist_undone`, detail `{"checklist": id}`), newest per id wins, so no new table and no db.py change. Partial entries show a calm note; `notes` (editor text) is never shown, `status_note` is. "Open the web page" is a POST that opens the checklist's own URL server-side.
- Exposure card: real `engine.exposure.latest_exposure` (score, found count, by-hand count); ImportError -> "Coming soon"; any error -> calm line.
- "What we did for you" `/profile/{pid}/summary`: plain words, name label only, print CSS (@media print), Print button. PDF later (weasyprint is optional in report.py).
- Nav is now Today / Protect yourself / Emails / Settings; "Add a person" moved to the Today "More" card.
- Tests: `tests/test_wizard_v03.py`. Screenshots (fake data): `brand/screenshots/app-v0.3/` (683x512 = 1024x768 at 150%, dark, 200% zoom, full pages).
- Not done / ideas: real screen-reader pass (needs NVDA on the VM), keyboard walk of the wizard pages on Windows, PDF of the summary, unrestyled wizard screens only inherit the new CSS (not individually reviewed).

## SEC-93a + v0.1.3 backlog audit (Nina Alvarez)
- SEC-93a: `views.exposure_card` now starts with "Results for <label>" (escaped) in every state except "Coming soon". Today shows one card per person (`server.py` joins a card per profile instead of only profiles[0]). WO-106 behaviour (5 explanations cap, hidden 0 manual line) untouched. Tests: `tests/test_wizard_exposure_card_followups.py` (escaped label, two people). Protect counts on Today still use profiles[0].
- v0.1.3 backlog, all already on main in bb2cf2a: uninstall closes the app (`CloseApplications=yes` plus `taskkill /F /T /IM FreeMyID.exe` at usUninstall; no AppMutex), calm Bridge-unreachable copy (`draft.unreachable_message`), honest "password saved" hint (`Draft.saved_password`). Ready page stays on purpose (b7fb97e, bb2cf2a).
- Needs a Windows VM check: silent uninstall while the app runs leaves no files; Bridge-off message wording on screen.

## v0.3 a11y pass (Nina Alvarez) DONE
- Tokens/dark mode were already in (2b3d2c9). This pass: Protect checklist sub-headings were h3 under h1 (skipped level), now `h2.sub`; checkbox rows get a 44px tap area.
- Tests: `tests/test_wizard_a11y.py` (landmarks, one h1, no skipped levels, labels point at real ids, no dup ids, no positive tabindex, alt on img, chips carry words, no px font sizes or motion, AA contrast of every token pair used, both themes) and `tests/test_wizard_a11y_browser.py` (real Chromium at 640px = 200% zoom and 320px, light and dark: no sideways scroll, 44px targets on Today/Sites/broker/Protect/Settings/Emails; keyboard order, skip link, 3px focus ring; manual dark toggle persists). Set `FREEMYID_A11Y_SHOTS=<dir>` to save screenshots.
- Not done: wizard pages are covered by HTML checks only (not the browser test); no real screen-reader pass (needs NVDA on the VM).

## SEC-98 wizard field errors (Nina Alvarez) DONE
- `ui.errors_html` gives each alert an id (`err-N`); `ui.mark_invalid` adds `aria-invalid="true"` and `aria-describedby` (existing ids kept) to the rejected input, matched from the server message via `ui.error_fields`. Used by `step_page` (consent, name, address, about, mailbox) and the Settings mailbox page. Alerts stay visible; no copy or layout change; no JS. Radios and the Outlook/choose-one errors are not field-linked (group-level).
- New fields must be added to `_FIELD_HINTS` in `ui.py` if their error wording is new. Tests: `tests/test_wizard_field_errors_sec98.py`.
- WO-112 browser test: drop the `@pytest.mark.xfail(strict=True, ...)` line above `test_wizard_validation_error_is_associated_with_its_field` once merged (strict xfail would otherwise fail on XPASS).

## 2026-11-08 v0.3 wave (Nina)
- CR-W1 done: dashboard.outbox_releases builds the SEC-47 note; server inline block removed (no `_disclose_releases` existed by then).
- Installer: [Messages] FinishedLabel warns first start takes up to 15 s (unverified on Windows; CI build only). A real splash would need launcher work.
- Finish step: dated "what happens next" timeline (ui._screen_body "finish").
- Tests: tests/test_wizard_v013.py (+2). Next: a11y zoom/AA audit on dashboard pages; native splash.

## 2026-11-08 SUM-320 (Nina Alvarez) DONE
- Summary page overflowed at 320px (long Site names + nowrap Date column + padding). Fix in style.css only: `.summary` text wraps (`overflow-wrap: anywhere`), and at <=40rem the Date cell may wrap, table font .9rem, tighter padding. 640px and print rules unchanged.
- Test: tests/test_wizard_summary_320.py (320/640px, light/dark, 1 and 36 sites; fails 4/8 on the old CSS). Codex WO-116 browser test (48 cases) also passes against this CSS when copied into tests/.
- v0.1.3 backlog: nothing remaining (see audit above); only the Windows VM checks stay open.
