# Packaging

## Windows installer (the main target)
Built by `.github/workflows/build.yml` on `windows-latest`:
1. `pip install .[package]` then `pytest`
2. `pyinstaller packaging/windows/vanish.spec --noconfirm` gives `dist/Vanish/`
   (`Vanish.exe` windowed, `vanish-cli.exe` console)
3. `iscc /DAppVersion=<ver> packaging\windows\vanish.iss` gives `dist/VanishSetup-<ver>.exe`

Per-user install (no admin), Start Menu + Desktop shortcut. The uninstaller removes the daily
scheduled task and asks before deleting saved data. The build is unsigned for family testing
(Windows SmartScreen shows "More info -> Run anyway"; see FAMILY_QUICK_START.md).

Family installer: `iscc /DAppVersion=<ver> /DFamilyBundle=C:\path\Mom.vanish-profile ...`
puts the passphrase-protected `.vanish-profile` (made with `vanish profile export`) next to
`Vanish.exe`; the wizard offers to import it. The person still reviews and consents.

## Developers / Linux / macOS
```
pipx install .                 # CLI + web wizard: vanish setup
pipx install ".[package]"      # adds pywebview for `python -m vanish.wizard.desktop`
```
There is no Playwright browser download: Vanish uses the system Edge or Chrome. Only when
neither exists (`vanish.wizard.firstrun.ensure_browser`) does it ask before downloading Chromium.
