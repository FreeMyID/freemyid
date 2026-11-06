# wizard-packager handoff
## Done
- wizard/{draft,ui,dashboard,server,flows,report,firstrun}, notify.py, scheduler/{__init__,render}; ruff clean; 5 TestClient drafts pass
- server fix: POST body replayed after CSRF middleware reads form (forms were arriving empty)
## NEW TOP PRIORITY (user): Windows boomer-easy install
1. packaging/windows/ (PyInstaller onedir spec + Inno Setup .iss: per-user, no admin, Start+Desktop "Vanish" shortcut launching `vanish serve`/wizard, Apps uninstall asks to delete data)
2. Wizard UX rewrite: one question/screen, 18px+, progress dots, plain words, mailbox guided choice + app-password help, "What happens next", schedule = single checkbox w/ consent -> scheduler.install
3. Playwright browser download inside wizard with progress bar
4. FAMILY_QUICK_START.md picture-style; .github/workflows/build.yml windows-latest (+ others)
5. Tests for scheduler render + flows bundle
