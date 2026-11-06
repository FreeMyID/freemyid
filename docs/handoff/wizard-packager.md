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
