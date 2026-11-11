# winget manifest for Free My ID

This is a community recipe. It is not submitted upstream. It is not in the winget community repository.

Three files describe the package:

- `FreeMyID.FreeMyID.yaml` (version)
- `FreeMyID.FreeMyID.locale.en-US.yaml` (names and text)
- `FreeMyID.FreeMyID.installer.yaml` (download link and checksum)

The installer entry is a per-user Inno Setup `.exe` with silent switches. See the installer file. That was not tried on a machine.

The app version in this tree is 0.3.1 (`src/freemyid/__init__.py`). All three files set `PackageVersion` to `0.3.1`. The installer URL names `FreeMyIDSetup-0.3.1.exe` on the `v0.3.1` release. The Windows installer record is version 0.3.1, dated 2026-11-10 (`site_src/data/release.yaml`). That record is the Windows installer only. It does not list winget. Not sure the `0.3.1` installer filename exists. This note did not look up release assets.

Hashes in the recipe are placeholders until the release hashes are filled in. `InstallerSha256` is all zeros, and the line says it is a placeholder. Do not invent hashes. Do not replace a placeholder with a real hash. In-house release tooling fills it later from that release's `SHA256SUMS.txt`. This note did not.

## How a maintainer would verify it

Read the files. Do not edit the hash.

1. Open `src/freemyid/__init__.py` and confirm `__version__` is `0.3.1`.
2. Open the three manifests and confirm each `PackageVersion` is `0.3.1`. `ManifestVersion: 1.10.0` is the winget schema version, not the app version.
3. Open `site_src/data/release.yaml` and confirm the Windows installer record is version 0.3.1, dated 2026-11-10.
4. Confirm `InstallerSha256` is still all zeros. Leave it.

After release tooling has set the version, the URL, and `InstallerSha256` to one published installer, and not before, check on Windows 10 or 11 with winget, on a test machine or virtual machine. These commands were not run here:

```
winget validate --manifest .
winget settings --enable LocalManifestFiles
winget install --manifest .
winget uninstall FreeMyID.FreeMyID
```

Run them in the folder that holds the three manifest files. Enabling local manifests needs an administrator window, once. When the published file and the filled-in checksum are both present, hash that file on the machine and confirm it matches `InstallerSha256`. If the field is still all zeros, stop. Do not paste a computed hash over the placeholder. Do not commit a hand-edited checksum.

If a step fails, write down the exact message and report it to the in-house team.

Status: **coming**.
