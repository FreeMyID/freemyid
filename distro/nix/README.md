# Nix flake for Free My ID

This is a community recipe. It is not submitted upstream. The app version in this tree is 0.3.1.
The version is read from `pyproject.toml`. The package takes that version at flake.nix, line 23.
The flake has no checksum field. This page does not invent a hash.
This is a community recipe for Nix users. It is not part of any release, and the Windows installer
remains the way most people get the app. The Windows installer record in `site_src/data/release.yaml`
is version 0.3.1. That record does not list Nix, so this channel stays **coming**.

## How a maintainer would build and check it

Run every command from the repository root of a full checkout (the flake reads `../../pyproject.toml` and builds that tree). These commands
were not run here. They need Nix, and they need the network to fetch nixpkgs. That is
**release-day, in-house**. Not done here.

```
nix flake check ./distro/nix
nix build ./distro/nix
./result/bin/freemyid --help
```

`nix run ./distro/nix -- --help` starts the same program. `nix develop ./distro/nix` opens a shell
with pytest and ruff. If Nix says the flake is not tracked, run `git add distro/nix` first
(a flake only sees tracked files). Not done here.

## What is not tested

- The package sets `doCheck = false` (flake.nix, line 56). A Nix build does not run the test suite.
  The suite needs fixtures and a prepared site build. Run pytest in the checkout instead. Not run here.
- `pythonRelaxDeps = true` (flake.nix, line 51) lets nixpkgs copies older than the minimums in
  `pyproject.toml` build. Whether those older copies still work was not checked.
- Playwright browsers are not installed by this package. Browser steps need a browser supplied
  separately, for example `playwright-driver.browsers` from nixpkgs. Not tested here.
- There is no `flake.lock`. The first build would write one. Pinning it takes `nix flake lock ./distro/nix`,
  Nix, and the network. **release-day, in-house.** Not done here.
- The systems named in the flake were not built: `x86_64-linux`, `aarch64-linux`, `x86_64-darwin`,
  and `aarch64-darwin`.
- `pythonImportsCheck` for `freemyid` runs only on a real build. Not run here.

## Notes

- The build uses the local checkout, not a downloaded archive, so there is no placeholder hash to replace.
- The wheel bundles the public sample registry only, as in the PyPI build.
- If you try the app, use fake data only, for example Jane Q Testperson, Springfield IL.

## Try it locally

Status: **coming**. The check, build, and help commands are **unverified** (not run). They are the
same commands as above, and they were not run here:

```
nix flake check ./distro/nix
nix build ./distro/nix
./result/bin/freemyid --help
```
