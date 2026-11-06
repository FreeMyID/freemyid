# wizard-packager handoff
## Done (v1 wave, ruff clean, 22 TestClient drafts pass: src/vanish/wizard/_test_drafts)
1. Wizard = 6 screens (consent, name, address, about, mailbox, finish) per D6. Provider presets
   gmail/yahoo/icloud/proton_bridge/other + "Skip, I'll do these by hand"; Outlook -> says skip.
   Finish: "run automatically" checkbox (default on) -> scheduler.install (skipped under pytest or
   VANISH_NO_BACKGROUND), first run in a thread (dry unless config.real_submissions_enabled), then "/".
2. Dashboard D7: status sentence, to-do cards (ASSISTED_OPT_OUT, SEND_EMAIL_MANUALLY, generic),
   Settings page (schedule, practice/real toggle, per-person mailbox + permissions).
## Todo
3 desktop.py (+ CHANGE REQUEST for `vanish app`) 4 Windows scheduler 5 packaging/windows
6 .github/workflows/build.yml 7 FAMILY_QUICK_START.md
3. DONE wizard/desktop.py (+ server.start_background, /_focus, /quit); tests test_wizard_desktop.py
4. DONE Windows scheduler: hidden per-user task, windowed Vanish.exe/pythonw, idempotent /F, no
   console flash (CREATE_NO_WINDOW); tests test_scheduler_render.py
5. DONE packaging/windows/{vanish.spec,vanish.iss,launcher_gui.py,launcher_cli.py}, packaging/README.md.
   Spec test-built on Linux (scratchpad venv): data paths + vanish-cli OK. Family bundle: iss
   /DFamilyBundle=..., wizard/flows.find_family_bundle, import page uses it.
6. DONE .github/workflows/build.yml
7. DONE FAMILY_QUICK_START.md (text screenshots; real screenshots TBD)
