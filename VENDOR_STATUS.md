# WO-327 (issue pending)

Wesley Tran, reference writer. Docs only. No recipe file was edited.

## Done

- `distro/nix/README.md` now says this is a community recipe, it is not submitted upstream, and the app version in this tree is 0.3.1. That version is read from `pyproject.toml`. The package takes it at flake.nix, line 23. The page says how a maintainer would build and check it, and what is not tested. No hash was invented. Nix stays **coming**: `site_src/data/release.yaml` does not list it.
- `distro/CHECKLIST.md` no longer calls 0.2.0 current. The app version it names is 0.3.1, the current release, including the Windows installer record in `site_src/data/release.yaml` (also 0.3.1). The publish gate (SEC-112) still means: run `python tools/ci/check_distro_hashes.py`, require exit 0 before any upstream submission, and fail on `SKIP`, an all-zero 64-hex hash, a `REPLACE_WITH_*` token, or a recipe that is not valid UTF-8. Normal CI still does not run that gate. Steps that need the network are marked **release-day, in-house** and were not done here. Placeholders were left as placeholders.
- The five WO-308 READMEs were not edited.

## Next

- In-house, on release day: fill real checksums, generate the Flatpak dependency sources, run `nix flake lock` and commit `distro/nix/flake.lock`, then run the maintainer check commands. Not done in this work order.
- Record the check-in (GROK-NNN and the board) if in-house still wants that. Those files are outside this work order's allowed paths, so they were not edited here.

## Questions

- `docs/user/INSTALL.md` still describes the release record as version 0.2.0. That page is outside this work order. Should in-house correct it, or is a later docs work order already queued?
- `site_src/data/release.yaml` in this tree already says 0.3.1 (not 0.3.0). The checklist follows that. Say if the published installer record should be treated as an older version anyway.

## How to test

From `.vendor-wt/wo-327`:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_packaging_lint.py tests/copilot/test_cp_wording_guard.py`

64 passed in 0.20s.

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k distro`

23 passed, 2664 deselected, 1 warning in 3.09s. The warning is Starlette's existing note about `httpx` and `starlette.testclient` in the venv. It is not from this change.

## Findings

- `docs/user/INSTALL.md:12-17`, `:48`, `:72`, and `:78` still say version 0.2.0. Line 48 also says the installer is about 64.4 MB. `site_src/data/release.yaml:5-7` in this tree says version 0.3.1, date 2026-11-10, and `size_mb: 64.6`. Out of lane. Not edited. `docs/user/INSTALL.md:40` still matches `distro/nix/README.md:6-7` ("not part of any release"; the Windows installer "remains the way most people get the app").
- Placeholders are still in place, on purpose: `distro/aur/PKGBUILD:37` (`SKIP`), `distro/aur/.SRCINFO:29` (`SKIP`), `distro/flatpak/org.freemyid.FreeMyID.yml:48` (all zeros), `distro/homebrew/freemyid.rb:8` (`REPLACE_WITH_SDIST_SHA256_FROM_RELEASE_TOOLING`), `distro/scoop/freemyid.json:9` (all zeros), `distro/winget/FreeMyID.FreeMyID.installer.yaml:19` (all zeros). The release record's installer checksum was not copied into any of them.
- `distro/nix/flake.lock` is still absent. `distro/nix/flake.nix:4` still follows `nixos-unstable`. The hash gate still does not require the lock file (`tests/test_sec112_flake_lock.py` remains a strict xfail). Not a new defect.

## Not verified

- Nix was not installed and the network was not used. `nix flake check`, `nix build`, `nix flake lock`, and `./result/bin/freemyid --help` were not run.
- No sdist or Windows installer was downloaded, so published asset names (including `FreeMyIDSetup-0.3.1.exe` in the Scoop and winget recipes) were not checked against a release.
- `makepkg`, Flatpak, Homebrew, Scoop, and winget commands in the checklist were not run.
- `docs/vendor/GROK_BOARD.md` and `docs/vendor/GROK_TO_CLAUDE.md` were not updated (not in the allowed paths).
