# Flatpak: org.freemyid.FreeMyID (draft)

Draft recipe for the command-line tool and the local dashboard. Not published, not built, not on Flathub.

- Runtime `org.freedesktop.Platform` 24.08. Version `0.2.0` follows `pyproject.toml`.
- Permissions are minimal: network, and the desktop secret service for the keyring. No home folder access.
  Data goes to `$XDG_DATA_HOME/freemyid` through the `freemyid-flatpak` launcher (sets `FREEMYID_HOME`).
- Running the app with no arguments opens the dashboard.

## Not done yet

- **Playwright browser bundling.** The `playwright` package is listed, but the Chromium download is not
  bundled. Browser-based (Automatic) removals will not work in the Flatpak until a browser is packaged
  (a Flatpak extension or a pinned download built as its own module).
- **Pinned dependencies.** The `python3-freemyid-deps` module has no sources. Generate them with
  `flatpak-pip-generator` once the release is on PyPI; every file needs a url and sha256.
- **Source checksum.** The sdist `sha256` is a placeholder.
- **Desktop file, icon and AppStream metainfo** are missing (needed for Flathub).
- **Opening the browser from the dashboard** inside the sandbox is untested.

## Not verified (written offline)

Nothing here was built. Check with `flatpak-builder --user --install build org.freemyid.FreeMyID.yml`,
then `flatpak run org.freemyid.FreeMyID doctor --offline`. Also confirm the keyring works through the sandbox.

## Try it locally

Status: **coming**. `site_src/data/release.yaml` lists the Windows installer only. The commands are **unverified**
(not run). They will not work until the dependency sources and the source `sha256` placeholder are filled in:

```
cd distro/flatpak
flatpak-builder --user --install --force-clean build org.freemyid.FreeMyID.yml
flatpak run org.freemyid.FreeMyID doctor --offline
flatpak uninstall --user org.freemyid.FreeMyID
```
