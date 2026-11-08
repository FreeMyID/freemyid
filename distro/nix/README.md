# Nix flake for Free My ID

Builds `freemyid` with `buildPythonApplication` from the local source tree. The version is read from
`pyproject.toml`, so there is nothing to bump here.

This is a community-style recipe for Nix users. It is not part of any release, and the Windows installer
remains the way most people get the app.

## Use

Run from the repository root (the flake reads `../../pyproject.toml` and the source tree, so keep it
inside a full checkout):

```
nix build ./distro/nix        # result/bin/freemyid
nix run ./distro/nix -- --help
nix develop ./distro/nix      # shell with pytest and ruff
```

If Nix says the flake is not tracked, run `git add distro/nix` first (flakes only see tracked files).

## Notes

- `doCheck = false`: the test suite needs fixtures and a site build. Run `pytest -q` in a checkout instead.
- `pythonRelaxDeps = true` lets nixpkgs versions older than the minimums in `pyproject.toml` build.
- The wheel bundles the public sample registry only, as in the PyPI build.
- Playwright browsers are not installed by this package. Browser-based steps need a browser supplied
  separately (for example `playwright-driver.browsers` from nixpkgs); not tested here.
- `flake.lock` is not committed. The first `nix build` creates one; pin it if you want repeatable builds.

## Not verified

Written without network access or Nix installed, so it was never built. Please run
`nix flake check ./distro/nix` and `nix build ./distro/nix` and report any missing or renamed nixpkgs
attributes.
