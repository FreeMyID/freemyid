# AUR package: python-freemyid

This is a community recipe. It is not submitted upstream. It is not on the Arch User Repository.

The app version in this tree is 0.3.1 (`src/freemyid/__init__.py`). `PKGBUILD` and `.SRCINFO` both say `pkgver` 0.3.1. The Windows installer record is version 0.3.1, dated 2026-11-10 (`site_src/data/release.yaml`). That record is the Windows installer only. It does not list this package.

Hashes in the recipe are placeholders until the release hashes are filled in. `sha256sums` is `SKIP` in `PKGBUILD` and in `.SRCINFO`. Do not invent hashes. Do not replace a placeholder with a real hash. In-house release tooling fills the real source checksum later. This note did not.

## What else is in the recipe

- The source URL names the PyPI file `freemyid-0.3.1.tar.gz`. That is the tree version. Not sure that file is on PyPI yet. This note did not look it up.
- The package name is `python-freemyid`.
- Dependency names were mapped by hand, offline. `python-desktop-notifier` may be only in the AUR, not the official repos. Not sure. Check that before anyone publishes.
- `.SRCINFO` is already in this folder. It still has `sha256sums = SKIP`.

## How a maintainer would verify it

Read the files. Do not edit the hash.

1. Open `src/freemyid/__init__.py` and confirm `__version__` is `0.3.1`.
2. Open `PKGBUILD` and `.SRCINFO` and confirm `pkgver` is `0.3.1`.
3. Open `site_src/data/release.yaml` and confirm the Windows installer record is version 0.3.1, dated 2026-11-10.
4. Confirm `sha256sums` is still `SKIP`. Leave it.

After release tooling has replaced `SKIP` with the checksum published for that same source file, and not before, check on Arch. These commands were not run here:

```
cd distro/aur
makepkg --printsrcinfo
namcap PKGBUILD
makepkg -si
freemyid --help
sudo pacman -R python-freemyid
```

Compare the printed source info with `.SRCINFO`. Regenerate `.SRCINFO` only after the real checksum is already in `PKGBUILD`. Do not type a hash in by hand.

Status: **coming**.
