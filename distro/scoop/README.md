# Scoop manifest for Free My ID

Status: **coming**. There is no Scoop bucket yet. `site_src/data/release.yaml` lists the Windows installer
only, not Scoop.

`freemyid.json` downloads the release installer and runs it silently (per-user install), then removes the
downloaded file. The uninstaller looks for the Inno Setup `unins*.exe` under `%LOCALAPPDATA%\Programs\FreeMyID`.

- `hash` is all zeros: a **placeholder**. Release tooling replaces it.
- The installer filename (`FreeMyIDSetup-0.3.0.exe`) was copied from the manifest, not checked against the
  published release assets: not sure it matches.
- The install path used by the uninstaller is not confirmed against the real installer: not sure.

## Try it locally

Run on Windows 10/11 with Scoop, on a test machine or virtual machine. All commands are **unverified**
(not run when this was written).

1. Put the real SHA-256 of the downloaded installer in `hash`
   (`Get-FileHash .\FreeMyIDSetup-0.3.0.exe -Algorithm SHA256`).
2. Install from the file: `scoop install .\distro\scoop\freemyid.json`
3. Check it: `scoop list` should show `freemyid`.
4. Remove it: `scoop uninstall freemyid`

If a step fails, write down the exact message and report it to the in-house team.
