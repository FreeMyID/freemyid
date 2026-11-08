# AUR package: python-freemyid

Recipe for building Free My ID from the PyPI sdist. Not published to the AUR yet.

- `PKGBUILD` takes `pkgver` from `pyproject.toml`. The `sha256sums` entry is `SKIP`,
  a placeholder that release tooling must replace with the real sdist checksum.
- `.SRCINFO` mirrors the PKGBUILD. After any edit, regenerate it on Arch with
  `makepkg --printsrcinfo > .SRCINFO`.
- Dependency names were mapped by hand, offline. `python-desktop-notifier` is probably only
  in the AUR, not the official repos, so check it before publishing.
- Check on Arch with `namcap PKGBUILD` and `makepkg -s` once the sdist is on PyPI.
