# Flatpak: org.freemyid.FreeMyID

This is a community recipe. It is not submitted upstream. It is not on Flathub. It has not been built.

The app version in this tree is 0.3.1 (`src/freemyid/__init__.py`). The manifest names the PyPI file `freemyid-0.3.1.tar.gz`. The published Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09 (`site_src/data/release.yaml`). That record is the Windows installer only. It does not list Flatpak. 0.2.0 is not the current version.

Hashes in the recipe are placeholders until the release hashes are filled in. The source `sha256` is all zeros, and the line says it is a placeholder. The dependency module `python3-freemyid-deps` has an empty source list, so those checksums are not filled in either. Do not invent hashes. Do not replace a placeholder with a real hash. In-house release tooling fills them later. This note did not.

## What else is in the manifest

- Runtime `org.freedesktop.Platform` 24.08. The command is `freemyid-flatpak`. With no arguments it opens the dashboard.
- Permissions asked for: network, and the desktop secret service for the keyring. No home-folder access. The launcher sets `FREEMYID_HOME` to `$XDG_DATA_HOME/freemyid`.
- Playwright is named as a dependency. Chromium is not bundled. Browser-based steps will not work in this Flatpak until a browser is packaged. Not done.
- A desktop file, icon, and AppStream metainfo are missing. Opening a browser from the dashboard inside the sandbox is untested.

## How a maintainer would verify it

Read the files. Do not edit the hash.

1. Open `src/freemyid/__init__.py` and confirm `__version__` is `0.3.1`.
2. Open `org.freemyid.FreeMyID.yml` and confirm the source URL names `freemyid-0.3.1.tar.gz`.
3. Open `site_src/data/release.yaml` and confirm the Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09.
4. Confirm the source `sha256` is still all zeros, and that `python3-freemyid-deps` still has `sources: []`. Leave both.

After release tooling has filled the real source checksum and the pinned dependency sources, and not before, a maintainer can try a local build. These commands were not run here:

```
cd distro/flatpak
flatpak-builder --user --install --force-clean build org.freemyid.FreeMyID.yml
flatpak run org.freemyid.FreeMyID doctor --offline
flatpak uninstall --user org.freemyid.FreeMyID
```

Also check that the keyring works through the sandbox. Do not type a hash in by hand. Generating the dependency list needs network access; that is release tooling, not a hand-written checksum.

Status: **coming**.
