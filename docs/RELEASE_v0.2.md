# Release v0.2 ("Every platform") checklist

Owner: Dana Ortiz (devops). Status 2026-11-07: dry runs passed, NOT tagged. A minor release needs the owner's OK (docs/AUTONOMY.md, Tier 3).

## Passed (local dry run, clean worktree of origin/main 095aed6, version 0.1.2)
- `python -m build`: wheel + sdist built; `twine check --strict` PASSED on both.
- Wheel contents: sample registry only (`freemyid/_data/brokers/registry.sample.yaml`), `state_laws.yaml`, `state_law_deletion_matrix.yaml`, `checklists.yaml`, `LICENSE-DATA.md`, the three JSON schemas, Jinja templates, wizard static files. No `brokers/registry.yaml` (the only `registry.yaml` is the fake-data dev fixture `engine/_dev/registry.yaml`). Entry point `freemyid = freemyid.cli:app`.
- sdist: same data files, no private files.
- Clean venv install of the wheel: `freemyid --help` and `doctor --json` (valid JSON, 5 ok / 3 warn / 0 fail on Linux).
- Docker (podman build of `packaging/docker/Dockerfile`): builds; `--help` OK; `doctor --json` is valid JSON (exit 1 in a bare container because there is no keyring: "secrets" fails; the CI smoke step tolerates the exit code and only checks the JSON); runs as uid 10001 (non-root); works with `--read-only --tmpfs /tmp`; reports version 0.1.2; image is about 2.1 GB (Chromium). Podman ignores HEALTHCHECK in OCI format; docker honours it.

## Workflow review (on a v* tag)
- `pypi.yml`: gated on repo variable `PYPI_PUBLISH=true` (confirmed set) and environment `pypi` (confirmed exists). Build job runs `twine check --strict` and fails if `v<pyproject version>` != tag, so a mismatch never publishes. Publish uses OIDC Trusted Publishing, no token. Pre-release: tag `v0.2.0rc1` matches pyproject `0.2.0rc1` (PEP 440 form), and PyPI treats it as a pre-release (`pip install freemyid` ignores it; `--pre` gets it). Do not use `v0.2.0-rc.1`: the guard compares strings and would fail.
- PyPI name `freemyid` already holds `0.2.0.dev1` (owner's claim). PyPI never lets a version be re-uploaded: if a publish is wrong, yank it and bump (rc2).
- Fixed in this change (`.github/workflows/build.yml`, `docker.yml`), because an rc tag would otherwise have done damage:
  - build.yml `release`: non-final tags create a GitHub **pre-release** with `--latest=false`, so the website's `releases/latest/download/FreeMyIDSetup.exe` link (and `/get/windows` redirect) keeps serving the stable installer.
  - build.yml `site-release-info`: skipped for rc/alpha/beta tags (`update_release_info.py` rejects non-`X.Y.Z` anyway, and the website must not advertise an rc).
  - docker.yml `publish`: an rc tag pushes only `ghcr.io/freemyid/freemyid:v0.2.0rc1`; `latest` moves only on a final `vX.Y.Z`.
- Untested until it runs on GitHub: the new tag logic, cosign keyless signing, syft SBOM attestation, GHCR push. The rc is the rehearsal.
- The rc also runs the Windows job (test matrix, installer install test) and creates a pre-release with FreeMyIDSetup-0.2.0rc1.exe. Inno Setup takes AppVersion as free text, so `0.2.0rc1` is fine.

## GHCR: make the package public (one-time, after the first push, i.e. after the rc)
1. github.com/orgs/FreeMyID/packages > open the `freemyid` container package.
2. Right sidebar: "Package settings".
3. If "Connect repository" shows nothing linked: choose repository `FreeMyID/freemyid`.
4. Danger Zone > "Change package visibility" > Public > type `freemyid` to confirm.
5. Check without logging in: `docker pull ghcr.io/freemyid/freemyid:v0.2.0rc1`.
(If the org restricts public packages: org Settings > Packages > allow public. Free for public packages.)

## NOT tested (needs real hardware or owner)
- macOS launchd scheduler on real hardware (CI only covers the runner, not a user session).
- Windows 10/11 VM re-check of the installer and scheduled task.
- Real keyring behaviour on macOS/GNOME; Docker with a persistent `/data` volume over several runs.
- GitHub-side behaviour of cosign/SBOM/provenance steps (first run).

## Cutting the release (needs the owner's explicit OK for each push and tag)
Prep (one commit on main, via PR if main is protected). Version in all three places, then green CI on main:
```
# edit: pyproject.toml  version = "0.2.0rc1"
#       src/freemyid/__init__.py  __version__ = "0.2.0rc1"
#       packaging/windows/freemyid.iss  AppVersion default "0.2.0rc1"
git commit -m "Release 0.2.0rc1" -- pyproject.toml src/freemyid/__init__.py packaging/windows/freemyid.iss
git push origin main            # owner OK; wait for build, docker, pages green
```
Release candidate:
```
git tag -a v0.2.0rc1 -m "Free My ID 0.2.0rc1"
git push origin v0.2.0rc1       # owner OK
gh run list --limit 6           # build, pypi, docker
```
Verify: `pipx install --pip-args=--pre freemyid==0.2.0rc1 && freemyid --version`; `docker pull ghcr.io/freemyid/freemyid:v0.2.0rc1` (after making it public), `cosign verify` keyless; GitHub release is marked Pre-release and `latest` still points at the old stable; website unchanged. Then do the GHCR clicks above.

Final (only after the rc checks pass and the owner OKs; bump the same three files to `0.2.0`):
```
git commit -m "Release 0.2.0" -- pyproject.toml src/freemyid/__init__.py packaging/windows/freemyid.iss
git push origin main            # owner OK; wait for green
git tag -a v0.2.0 -m "Free My ID 0.2.0"
git push origin v0.2.0          # owner OK
```
Verify: PyPI page shows 0.2.0 and `pipx install freemyid` works on a clean machine; GHCR `:latest` and `:v0.2.0` share a digest; GitHub release v0.2.0 has FreeMyIDSetup.exe, FreeMyIDSetup-0.2.0.exe, SHA256SUMS.txt, and `sha256sum -c` passes; `site-release-info` committed "Site: v0.2.0 release info" and Pages redeployed (check freemyid.org/download shows 0.2.0 and the same SHA256).

Rollback: PyPI = yank the version in the project's page and publish a higher one; GHCR = delete the version in package settings; GitHub release = `gh release delete vX --cleanup-tag` (owner OK); site = revert the automatic site commit and dispatch pages.yml.
