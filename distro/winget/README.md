# winget manifest for Free My ID

Status: **coming**. Nothing is submitted to the winget community repository. `site_src/data/release.yaml`
lists the Windows installer only, not winget.

Three files describe the package: `FreeMyID.FreeMyID.yaml` (version), `FreeMyID.FreeMyID.locale.en-US.yaml`
(names and text) and `FreeMyID.FreeMyID.installer.yaml` (download link and checksum).

- The installer is a per-user Inno Setup `.exe` with silent switches (see the installer file).
- `InstallerSha256` is all zeros: a **placeholder**. Release tooling fills it in from the release's `SHA256SUMS.txt`.
- The installer filename in the manifest (`FreeMyIDSetup-0.3.1.exe`) was copied from the manifest, not checked
  against the published release assets: not sure it matches.

## Try it locally

Run on Windows 10/11 with the `winget` tool, in a folder that holds the three manifest files. Use a test
machine or virtual machine. All commands below are **unverified** (not run when this was written).

1. Replace the zero hash in the installer file with the real SHA-256 of the file you downloaded
   (`Get-FileHash .\FreeMyIDSetup-0.3.1.exe -Algorithm SHA256`). Do not commit that change by hand.
2. Check the files: `winget validate --manifest .`
3. Allow local manifests once (needs an administrator window): `winget settings --enable LocalManifestFiles`
4. Install from the folder: `winget install --manifest .`
5. Remove it: `winget uninstall FreeMyID.FreeMyID`

If a step fails, write down the exact message and report it to the in-house team.
