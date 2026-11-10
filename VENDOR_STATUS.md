# WO-308

Vendor: Wesley Tran (Grok). Worktree: `.vendor-wt/wo-308`. Docs only. Recipe files were not edited.

## Done

- Rewrote `distro/aur/README.md`, `distro/flatpak/README.md`, `distro/homebrew/README.md`, `distro/scoop/README.md`, and `distro/winget/README.md`.
- Each one says it is a community recipe, it is not submitted upstream, hashes in the recipe are placeholders until the release hashes are filled in, do not invent hashes, and do not replace a placeholder with a real hash.
- Each one says the app version in this tree is 0.3.1 (`src/freemyid/__init__.py`) and the published Windows installer record is version 0.3.0, about 64.5 MB, dated 2026-11-09 (`site_src/data/release.yaml`). None of them call 0.2.0 current.
- Each one says how a maintainer would verify it: read-only checks first, then channel commands that were not run, and only after release tooling fills the real hashes.
- No recipe file was changed (`PKGBUILD`, `.SRCINFO`, yml, rb, json, yaml). No hash was invented or written over a placeholder.

## Next

- Owner review of the five READMEs.
- Leave the placeholder hashes in place until release tooling fills them for a real published file.
- Optional follow-up, outside this work order: `distro/CHECKLIST.md`, `distro/nix/README.md`, and `docs/vendor/GROK_BOARD.md` (see findings).

## Questions for the owner

- `distro/CHECKLIST.md` still says `release.yaml` records version 0.2.0, and it cites README line numbers this edit moved. Should a later work order correct that file?
- `distro/nix/README.md` was not in the allowed paths, so it does not yet carry the same 0.3.1 / 0.3.0 sentences. Should it?
- Scoop and winget still name a `v0.3.1` installer, while `site_src/data/release.yaml` records the Windows installer as 0.3.0. Leave that for release tooling?
- `docs/vendor/GROK_BOARD.md` still lists WO-308 as queued. This session did not edit it, because `docs/vendor/` is outside the allowed paths. Should the owner mark the board?

## How to test

From this worktree:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_packaging_lint.py tests -k distro
```

Result: **23 passed, 2653 deselected, 1 warning in 3.57s**. Exit code 0.

Those 23 are:

- `tests/copilot/test_cp_wording_guard.py`: 12 (banned words and "available" on the six `distro/*/README.md` files, including nix, which was not edited).
- `tests/test_distro_hash_gate.py`: 11.

The 26 tests in `tests/copilot/test_cp_packaging_lint.py` were deselected. Their node ids do not contain `distro`. The work order also says that file must still pass, so it was run on its own:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_packaging_lint.py
```

Result: **26 passed in 0.19s**. Exit code 0.

The warning on the combined run is the existing Starlette/`httpx` deprecation from `fastapi.testclient` while collecting `tests/`. It is not from these READMEs.

## Findings

- `distro/CHECKLIST.md:3` still says `site_src/data/release.yaml` records version 0.2.0. The file actually says version `0.3.0`, date `2026-11-09`, `size_mb: 64.5` (`site_src/data/release.yaml:5-7`). Not edited (not an allowed path). Not a `src/` bug, so no `xfail` was added.
- `distro/CHECKLIST.md:36`, `:45`, `:53`, `:69`, and `:78` still point at the old README command line ranges (`aur` 18-25, `flatpak` 31-35, `homebrew` 29-34, `scoop` 19-23, `winget` 19-24). Those commands moved. Not edited.
- Placeholders are still in the recipes, on purpose: `distro/aur/PKGBUILD:37` and `distro/aur/.SRCINFO:29` (`SKIP`); `distro/flatpak/org.freemyid.FreeMyID.yml:48` (all zeros); `distro/homebrew/freemyid.rb:8` (`REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING`); `distro/scoop/freemyid.json:9` (all zeros); `distro/winget/FreeMyID.FreeMyID.installer.yaml:19` (all zeros). Packaging lint expects version 0.3.1 because `pyproject.toml:6` is `0.3.1` and is not a pre-release. That matches `src/freemyid/__init__.py:2`.
- `distro/scoop/freemyid.json:8` and `distro/winget/FreeMyID.FreeMyID.installer.yaml:18` name `FreeMyIDSetup-0.3.1.exe` on tag `v0.3.1`. The published installer record is 0.3.0. The 0.3.0 checksum in `release.yaml` was not copied into any README or recipe.
- `distro/nix/README.md` was not updated. It already says the recipe is community-style, status coming, and that it has no placeholder hashes because it builds from the checkout. It does not state tree version 0.3.1 or the 0.3.0 installer size and date.
- `docs/vendor/GROK_BOARD.md:14` still says WO-308 is queued.

## What this session could not verify

- No network. No `git`, `gh`, `pip`, `curl`, or `wget`. No AUR, Flatpak, Homebrew, Scoop, or winget install. The maintainer commands in the READMEs were not run.
- Did not check whether `freemyid-0.3.1.tar.gz` is on PyPI, or whether `FreeMyIDSetup-0.3.1.exe` exists on GitHub.
- Did not hash a published installer, and did not confirm the Scoop uninstall path or that `python-desktop-notifier` is only in the AUR.
- Did not build Nix. `distro/nix/` was out of scope.
