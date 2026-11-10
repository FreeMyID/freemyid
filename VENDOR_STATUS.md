# WO-328

## Done

Added `tests/grok/test_gk_distro_readme_matches_recipe.py`. It names `tests/copilot/test_cp_packaging_lint.py` (that guard checks version and hash fields inside each recipe) and compares each `distro/<channel>/README.md` with its recipe for aur, flatpak, homebrew, nix, scoop, and winget.

For each channel the guard checks four things: a placeholder hash (all zeros, `REPLACE_WITH...`, or `SKIP`) is described as "placeholder" or "not filled in" in the same paragraph as the hash; a version the README names is one the recipe states (the package version, or another version written in the recipe, such as the Flatpak runtime); the README says the recipe is not submitted upstream; package names or IDs in the README match the recipe (`python-freemyid`, `org.freemyid.FreeMyID`, formula `freemyid`, scoop `freemyid`, nix `freemyid`, `FreeMyID.FreeMyID`).

Fake trees under `tmp_path` prove a README that hides a placeholder, puts the word "placeholder" away from the hash, names a wrong version, or names a wrong id (`otherformula`, `Other.App`) fails, and a matching pair passes. "not filled in" counts. A real 64-hex hash does not need the placeholder word.

No files under `distro/` were edited. `tests/grok/__init__.py` and `conftest.py` were not created.

AUR, Flatpak, Homebrew, Scoop, and winget match on this base tree, so they are not xfailed. AUR and Homebrew READMEs do not name `0.3.1`; this guard only compares a version the README actually names. WO-308 owns adding that number.

## Next

In-house review. WO-327 owns `distro/nix/README.md`. After that README says the recipe is not submitted upstream, drop the strict xfail on `test_distro_readme_matches_its_recipe[nix]` or the run will report XPASS. WO-308 owns the other five READMEs; this guard should keep passing if those edits stay truthful.

## Questions

None.

## How to test

From `.vendor-wt/wo-328`:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_distro_readme_matches_recipe.py
```

15 passed, 1 xfailed.

XFAIL `test_distro_readme_matches_its_recipe[nix]`: distro/nix/README.md:5 does not say the recipe is not submitted upstream; it says the flake is not part of any release. WO-327 owns this README.

```
../../.venv/bin/ruff check tests/grok/test_gk_distro_readme_matches_recipe.py
```

All checks passed.

## Findings

- `distro/nix/README.md:5`: the README says the flake is a community-style recipe and "not part of any release". It does not say the recipe is not submitted upstream (not published, not in nixpkgs, or the same). Strict xfail on `test_distro_readme_matches_its_recipe[nix]`. WO-327 owns this README. Not edited here.
- `distro/aur/PKGBUILD:37`: `sha256sums=('SKIP')` for the PyPI release tarball on line 35 (`source=.../${_name}-${pkgver}.tar.gz`), not a VCS checkout. `distro/aur/.SRCINFO:29` repeats `sha256sums = SKIP`. `SKIP` tells makepkg not to check that tarball. The README already calls this a placeholder (`distro/aur/README.md:5-6` and `:27`), so this guard does not xfail AUR. In-house: replace `SKIP` with the real sdist SHA-256 before any publish. `tools/ci/check_distro_hashes.py` already flags `SKIP` on release day.
