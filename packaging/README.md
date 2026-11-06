# Packaging

## Windows installer (the main target)
Built by `.github/workflows/build.yml` on `windows-latest`:
1. `pip install .[package]` then `pytest`
2. `pyinstaller packaging/windows/freemyid.spec --noconfirm` gives `dist/FreeMyID/`
   (`FreeMyID.exe` windowed, `freemyid-cli.exe` console)
3. `iscc /DAppVersion=<ver> packaging\windows\freemyid.iss` gives `dist/FreeMyIDSetup-<ver>.exe`

Per-user install (no admin), Start Menu + Desktop shortcut. The uninstaller removes the daily
scheduled task and asks before deleting saved data. The build is unsigned for family testing
(Windows SmartScreen shows "More info -> Run anyway"; see FAMILY_QUICK_START.md).

Family installer: `iscc /DAppVersion=<ver> /DFamilyBundle=C:\path\Mom.freemyid-profile ...`
puts the passphrase-protected `.freemyid-profile` (made with `freemyid profile export`) next to
`FreeMyID.exe`; the wizard offers to import it. The person still reviews and consents.

## Developers / Linux / macOS
```
pipx install .                 # CLI + web wizard: freemyid setup
pipx install ".[package]"      # adds pywebview for `python -m freemyid.wizard.desktop`
```
There is no Playwright browser download: Free My ID uses the system Edge or Chrome. Only when
neither exists (`freemyid.wizard.firstrun.ensure_browser`) does it ask before downloading Chromium.
