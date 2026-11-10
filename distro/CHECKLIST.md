# Distro release-day checklist

The app version in this tree is 0.3.1 (`pyproject.toml`). `site_src/data/release.yaml`
records 0.3.1 for the Windows installer and does not list these channels.
Therefore every channel in this checklist remains **coming**. Do not describe
a channel as available until that data explicitly supports it.

Run the release-tooling items only after confirming the published asset names
and checksums. Commands were **unverified**; this work order did not run them.
Network steps are marked **release-day, in-house** and were not done here. No hash was filled in.

## Publish gate (SEC-112)

Release tooling **must** run `python tools/ci/check_distro_hashes.py` and see
exit 0 before any upstream submission (AUR push, Flathub, Homebrew, Scoop,
winget, Nix). It lists, and exits 1 on: `SKIP` in any checksum array
(`md5sums`, `sha1sums`, `sha224sums`, `sha256sums`, `sha384sums`, `sha512sums`,
`b2sums`, `cksums`, arch-specific variants too, on one line or spread over
several), any all-zero 64-hex hash, any `REPLACE_WITH_*` token, and any recipe
in `distro/` that is not valid UTF-8. Normal CI does not run it, because placeholders are
expected until release day. Tests: `tests/test_distro_hash_gate.py`.

Nix: `distro/nix/flake.nix` follows `nixos-unstable` and there is no
`flake.lock`. Generating one needs `nix flake lock` with Nix installed and
network access, which was not possible when this gate was added. That step is
**release-day, in-house**: run it on a machine with Nix and commit
`distro/nix/flake.lock`. Not done here.

## AUR

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/aur/PKGBUILD:5,35` | Set `pkgver` and its PyPI sdist source URL to the current release. In this tree both already say 0.3.1. | In-house release tooling | coming |
| `distro/aur/PKGBUILD:37` | Replace `SKIP` with the published sdist SHA-256. Needs the published file. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/aur/.SRCINFO:3,28` | Regenerate the version and source from the updated `PKGBUILD` with `makepkg --printsrcinfo`. In this tree both already say 0.3.1. | Maintainer | coming |
| `distro/aur/.SRCINFO:29` | Regenerate the real sdist SHA-256 from the updated `PKGBUILD`; do not retain `SKIP`. Needs the published file. **release-day, in-house.** Not done here. | Maintainer | coming |
| `distro/aur/README.md:18-25` | `makepkg`, `namcap`, install, help, and removal commands are **unverified**; run on Arch after the sdist is on PyPI. The install downloads that sdist. **release-day, in-house.** Not done here. | Maintainer | coming |

## Flatpak

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/flatpak/org.freemyid.FreeMyID.yml:16,47` | Update the documented version and the Free My ID sdist URL to the current release. In this tree both already say 0.3.1. | In-house release tooling | coming |
| `distro/flatpak/org.freemyid.FreeMyID.yml:28` | Replace empty `sources: []` with pinned PyPI dependency URLs and SHA-256 values from `flatpak-pip-generator`. This needs network access. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/flatpak/org.freemyid.FreeMyID.yml:48` | Replace the all-zero sdist SHA-256 with the published sdist checksum. Needs the published file. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/flatpak/README.md:31-35` | Flatpak build, run, and uninstall commands are **unverified**; run after the dependency sources and checksum are filled. The build downloads those sources. **release-day, in-house.** Not done here. | Maintainer | coming |

## Homebrew

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/homebrew/freemyid.rb:7` | Replace the PyPI sdist URL and embedded version with the current release. In this tree the URL already says 0.3.1. | In-house release tooling | coming |
| `distro/homebrew/freemyid.rb:8` | Replace `REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING` with the published sdist SHA-256. Needs the published file. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/homebrew/freemyid.rb:14-17` | Add generated `resource` URL and SHA-256 blocks for every transitive dependency. The formula says `brew update-python-resources` needs the network. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/homebrew/README.md:29-34` | Homebrew install, test, help, and uninstall commands are **unverified**; run after the checksum and resources are present. The install downloads those files. **release-day, in-house.** Not done here. | Maintainer | coming |

## Nix

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/nix/flake.nix:17,23,27` | No placeholder: retain the dynamic version from `pyproject.toml` (the current release, 0.3.1, taken at flake.nix, line 23) and the local checkout source; no hash, URL, or version replacement is needed. | Maintainer | coming |
| `distro/nix/README.md:16-19,51-54` | Nix check, build, and help commands are **unverified**; run them in a checkout with Nix installed. They need the network to fetch nixpkgs. **release-day, in-house.** Not done here. | Maintainer | coming |

## Scoop

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/scoop/freemyid.json:2,8,30` | Set the manifest version and release-installer URL to the current release; retain the `$version` autoupdate template. In this tree the version and the versioned URL already say 0.3.1. Confirming the asset name needs the published release. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/scoop/freemyid.json:9` | Replace the all-zero `hash` with the published installer SHA-256. Needs the published file. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/scoop/README.md:19-23` | Scoop hash, install, list, and uninstall commands are **unverified**; run on a Windows 10/11 test machine or VM. Hashing and install need the published installer. **release-day, in-house.** Not done here. | Maintainer | coming |

## winget

| File:line | Release-day item and replacement | Responsibility | State |
| --- | --- | --- | --- |
| `distro/winget/FreeMyID.FreeMyID.yaml:4`; `distro/winget/FreeMyID.FreeMyID.locale.en-US.yaml:3`; `distro/winget/FreeMyID.FreeMyID.installer.yaml:5` | Set all three `PackageVersion` values to the current release. In this tree all three already say 0.3.1. | In-house release tooling | coming |
| `distro/winget/FreeMyID.FreeMyID.installer.yaml:18` | Replace the installer URL and embedded version with the published installer asset URL. In this tree the URL already says 0.3.1. Confirming the asset name needs the published release. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/winget/FreeMyID.FreeMyID.installer.yaml:19` | Replace the all-zero `InstallerSha256` with the SHA-256 in the release `SHA256SUMS.txt`. Needs the published file. **release-day, in-house.** Not done here. | In-house release tooling | coming |
| `distro/winget/README.md:19-24` | winget hash, validation, settings, install, and uninstall commands are **unverified**; run on a Windows 10/11 test machine or VM. Hashing and install need the published installer. **release-day, in-house.** Not done here. | Maintainer | coming |
