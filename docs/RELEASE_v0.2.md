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

## State after rc1 (2026-11-07)
- `v0.2.0rc1` is out (tag cut by the owner on 107c9f0): GitHub pre-release with FreeMyIDSetup-0.2.0rc1.exe, FreeMyIDSetup.exe, SHA256SUMS.txt; `releases/latest` still v0.1.2; docker image pushed for the tag only.
- PyPI: a GitHub trusted publisher is now configured on the existing `freemyid` project (FreeMyID/freemyid, `pypi.yml`, env `pypi`). 0.2.0rc1 is published. Future tags publish by themselves; nothing more to set up.
- GHCR: the package is still PRIVATE. The org blocks public packages, so this is an owner action (below). `:latest` does not exist yet; the first final tag creates it.
- Agents cannot push tags (the auto-mode classifier blocks "Create Public Surface", even with full permissions). The OWNER runs every tag command below from a terminal.

## Owner action: GHCR public (do before or right after v0.2.0)
1. github.com/organizations/FreeMyID/settings/packages: allow members to create/publish **public** packages (org setting that is currently off).
2. github.com/orgs/FreeMyID/packages > `freemyid` > Package settings > link repository `FreeMyID/freemyid` if empty.
3. Danger Zone > Change package visibility > Public > type `freemyid`.
4. Check logged out: `docker pull ghcr.io/freemyid/freemyid:v0.2.0rc1`.
If you decide to keep it private, say so and the docs will stop pointing at ghcr.io.

## Checklist: rc1 to v0.2.0
Each push and tag needs the owner's OK. Do the steps in order; stop on any red.

1. Windows VM re-check of the rc1 installer (Windows 10 and/or 11, clean snapshot, a normal non-admin user):
   - Download `FreeMyIDSetup-0.2.0rc1.exe` from the pre-release page, run `sha256sum -c SHA256SUMS.txt` (or `Get-FileHash -Algorithm SHA256 .\FreeMyIDSetup-0.2.0rc1.exe` and compare to SHA256SUMS.txt).
   - SmartScreen shows "unknown publisher" (unsigned): expected. Install by clicking through; no admin prompt expected.
   - Wizard opens in the browser on 127.0.0.1; walk all 6 screens with fake data only (Jane Q Testperson, Springfield IL); no real email sent.
   - Scheduled task exists: `schtasks /Query /TN "Free My ID" /V /FO LIST` (name as set in the .iss); run it once with `schtasks /Run /TN "Free My ID"`.
   - Uninstall from Settings > Apps: files and task removed, user data kept/removed as the uninstaller says.
   - Record result in PROGRESS.md; any failure blocks 0.2.0.
2. Other rc1 checks (any machine):
   ```
   pipx install --pip-args=--pre freemyid==0.2.0rc1 && freemyid --version
   gh release view v0.2.0rc1 --json isPrerelease,assets
   gh release view --json tagName          # must still say v0.1.2
   ```
3. CI green on main (including `commit-email-check`): `gh run list --branch main --limit 8`.
4. Bump the version in the three places to `0.2.0` (devops commits, orchestrator pushes with the owner's OK):
   ```
   # pyproject.toml                       version = "0.2.0"
   # src/freemyid/__init__.py             __version__ = "0.2.0"
   # packaging/windows/freemyid.iss       #define AppVersion "0.2.0"  and the iscc comment line
   git commit -m "Release 0.2.0" -- pyproject.toml src/freemyid/__init__.py packaging/windows/freemyid.iss
   git push origin main
   gh run list --branch main --limit 6      # wait for build, docker, pages green
   ```
5. Owner tags (replace SHA with the green release-bump commit: `git rev-parse origin/main`):
   ```
   git fetch origin && git tag -a v0.2.0 "$(git rev-parse origin/main)" -m "Free My ID v0.2.0"
   git push origin v0.2.0
   ```
6. Watch: `gh run list --limit 8` then `gh run watch <id>` for build, pypi, docker. If pypi asks for environment approval, approve it in the Actions UI. Re-run only failed jobs: `gh run rerun <id> --failed`.
7. Verify (devops does this):
   - GitHub release v0.2.0 is NOT a pre-release and is `latest`; assets FreeMyIDSetup.exe, FreeMyIDSetup-0.2.0.exe, SHA256SUMS.txt; `sha256sum -c SHA256SUMS.txt` passes.
   - `site-release-info` committed "Site: v0.2.0 release info"; pages.yml redeployed; `curl -s https://freemyid.org/download/ | grep -c 0.2.0` and the shown SHA256 equals SHA256SUMS.txt; `curl -sIL https://freemyid.org/get/windows | grep -i -E '^(HTTP|location)'` ends 200 with the new exe.
   - PyPI: `pip index versions freemyid` lists 0.2.0 (non-pre-release); clean-machine `pipx install freemyid && freemyid --version`.
   - GHCR (only if public): `docker pull ghcr.io/freemyid/freemyid:v0.2.0`, `:latest` has the same digest; `cosign verify` keyless (identity = the docker.yml workflow of FreeMyID/freemyid, issuer https://token.actions.githubusercontent.com).
8. Windows VM re-check once more with the final `FreeMyIDSetup-0.2.0.exe`, including an upgrade install over the rc1 install (settings and scheduled task survive).
9. Record in PROGRESS.md and docs/handoff/devops-engineer.md; then announce (Discord, once the webhook exists).

Rollback: PyPI = yank the version in the project's page and publish a higher one; GHCR = delete the version in package settings; GitHub release = `gh release delete vX --cleanup-tag` (owner OK); site = revert the automatic site commit and dispatch pages.yml.
