# Scoop manifest for Free My ID

This is a community recipe. It is not submitted upstream. There is no Scoop bucket for it.

`freemyid.json` points at a Windows installer, runs it silently for the current user, then deletes the downloaded file. The uninstall script looks for an Inno Setup `unins*.exe` under `%LOCALAPPDATA%\Programs\FreeMyID`. That path was not checked against a real install. Not sure it matches.

The app version in this tree is 0.3.1 (`src/freemyid/__init__.py`). The manifest `version` is `0.3.1`, and the download URL names `FreeMyIDSetup-0.3.1.exe` on the `v0.3.1` release. The published Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09 (`site_src/data/release.yaml`). That record is the Windows installer only. It does not list Scoop. 0.2.0 is not the current version. Not sure the `0.3.1` installer filename exists. This note did not look up release assets.

Hashes in the recipe are placeholders until the release hashes are filled in. `hash` is all zeros. The manifest notes call that a placeholder. Do not invent hashes. Do not replace a placeholder with a real hash. In-house release tooling fills the real installer checksum later. This note did not. Do not copy the 0.3.0 installer checksum into this 0.3.1 manifest.

## How a maintainer would verify it

Read the file. Do not edit the hash.

1. Open `src/freemyid/__init__.py` and confirm `__version__` is `0.3.1`.
2. Open `freemyid.json` and confirm `version` is `0.3.1`.
3. Open `site_src/data/release.yaml` and confirm the Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09. The manifest URL is a different version. Leave the URL until release tooling updates it.
4. Confirm `hash` is still all zeros. Leave it.

After release tooling has set `version`, the URL, and `hash` to one published installer, and not before, check on Windows 10 or 11 with Scoop, on a test machine or virtual machine. These commands were not run here:

```
scoop install .\distro\scoop\freemyid.json
scoop list
scoop uninstall freemyid
```

`scoop list` should show `freemyid` after install. When the published file and the filled-in `hash` are both present, hash that file on the machine and confirm it matches the manifest. If `hash` is still all zeros, stop. Do not paste a computed hash over the placeholder.

If a step fails, write down the exact message and report it to the in-house team.

Status: **coming**.
