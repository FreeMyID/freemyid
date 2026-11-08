# Distro release-day checklist

`site_src/data/release.yaml` records version 0.2.0 and its Windows installer,
but does not list any of these distribution channels. Therefore every channel
in this checklist remains **coming**. Do not describe a channel as available
until that data explicitly supports it.

Run the release-tooling items only after confirming the published asset names
and checksums. Commands in the source files were **unverified** when this
checklist was written; this work order did not run them.

## AUR

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/aur/PKGBUILD:5,35` | Set `pkgver` and its PyPI sdist source URL to the released version. | In-house release tooling | coming |
| `distro/aur/PKGBUILD:37` | Replace `SKIP` with the published sdist SHA-256. | In-house release tooling | coming |
| `distro/aur/.SRCINFO:3,28` | Regenerate the version and source from the updated `PKGBUILD` with `makepkg --printsrcinfo`. | Maintainer | coming |
| `distro/aur/.SRCINFO:29` | Regenerate the real sdist SHA-256 from the updated `PKGBUILD`; do not retain `SKIP`. | Maintainer | coming |
| `distro/aur/README.md:18-25` | `makepkg`, `namcap`, install, help, and removal commands are **unverified**; run on Arch after the sdist is on PyPI. | Maintainer | coming |

## Flatpak

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/flatpak/org.freemyid.FreeMyID.yml:16,47` | Update the documented version and the Free My ID sdist URL to the released version. | In-house release tooling | coming |
| `distro/flatpak/org.freemyid.FreeMyID.yml:28` | Replace empty `sources: []` with pinned PyPI dependency URLs and SHA-256 values from `flatpak-pip-generator`. **This needs network access.** | In-house release tooling | coming |
| `distro/flatpak/org.freemyid.FreeMyID.yml:48` | Replace the all-zero sdist SHA-256 with the published sdist checksum. | In-house release tooling | coming |
| `distro/flatpak/README.md:31-35` | Flatpak build, run, and uninstall commands are **unverified**; run after the dependency sources and checksum are filled. | Maintainer | coming |

## Homebrew

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/homebrew/freemyid.rb:7` | Replace the PyPI sdist URL and embedded version with the released sdist URL. | In-house release tooling | coming |
| `distro/homebrew/freemyid.rb:8` | Replace `REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING` with the published sdist SHA-256. | In-house release tooling | coming |
| `distro/homebrew/freemyid.rb:14-17` | Add generated `resource` URL and SHA-256 blocks for every transitive dependency. | In-house release tooling | coming |
| `distro/homebrew/README.md:29-34` | Homebrew install, test, help, and uninstall commands are **unverified**; run after the checksum and resources are present. | Maintainer | coming |

## Nix

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/nix/flake.nix:17,23,27` | No placeholder: retain the dynamic version from `pyproject.toml` and local checkout source; no hash, URL, or version replacement is needed. | Maintainer | coming |
| `distro/nix/README.md:42-45` | Nix check, build, and help commands are **unverified**; run them in a checkout with Nix installed. | Maintainer | coming |

## Scoop

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/scoop/freemyid.json:2,8,30` | Set the manifest version and release-installer URL to the published version; retain the `$version` autoupdate template. | In-house release tooling | coming |
| `distro/scoop/freemyid.json:9` | Replace the all-zero `hash` with the published installer SHA-256. | In-house release tooling | coming |
| `distro/scoop/README.md:19-23` | Scoop hash, install, list, and uninstall commands are **unverified**; run on a Windows 10/11 test machine or VM. | Maintainer | coming |

## winget

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/winget/FreeMyID.FreeMyID.yaml:4`; `distro/winget/FreeMyID.FreeMyID.locale.en-US.yaml:3`; `distro/winget/FreeMyID.FreeMyID.installer.yaml:5` | Set all three `PackageVersion` values to the released version. | In-house release tooling | coming |
| `distro/winget/FreeMyID.FreeMyID.installer.yaml:18` | Replace the installer URL and embedded version with the published installer asset URL. | In-house release tooling | coming |
| `distro/winget/FreeMyID.FreeMyID.installer.yaml:19` | Replace the all-zero `InstallerSha256` with the SHA-256 in the release `SHA256SUMS.txt`. | In-house release tooling | coming |
| `distro/winget/README.md:19-24` | winget hash, validation, settings, install, and uninstall commands are **unverified**; run on a Windows 10/11 test machine or VM. | Maintainer | coming |
