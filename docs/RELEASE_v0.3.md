# Release v0.3.0 checklist

Owner: Dana Ortiz (devops). Status 2026-11-09: **v0.3.0rc1 released, v0.3.0 NOT tagged.** A minor release needs the owner's OK (docs/AUTONOMY.md, Tier 3). Agents cannot push tags; the OWNER runs every tag command below.

## rc1 status (verified 2026-11-09)
- Tag `v0.3.0rc1` = f14203a (cut by the owner on 2026-11-08).
- GitHub release v0.3.0rc1: `isPrerelease: true`. Assets: FreeMyIDSetup-0.3.0rc1.exe, FreeMyIDSetup.exe, SHA256SUMS.txt, freemyid.cdx.json (CycloneDX SBOM). SHA256SUMS.txt matches the asset digests GitHub reports (exe 2c1cb51f…1638f, both names identical).
- `gh release view --json tagName` = **v0.2.0**: the website's `releases/latest` link still serves the stable installer.
- PyPI: 0.3.0rc1 wheel + sdist published, not yanked; project `info.version` is still 0.2.0, so `pip install freemyid` ignores the rc and `--pre` gets it.
- GHCR (public, anonymous pull works): `ghcr.io/freemyid/freemyid:v0.3.0rc1` exists (sha256:7a287ef7…a794b). `:latest` = `:v0.2.0` (sha256:eb3d2579…dd590); the rc did not move latest.
- Nothing broken found.

## What changes from rc1 to final
- Version `0.3.0rc1` → `0.3.0` in: `pyproject.toml`, `src/freemyid/__init__.py`, `packaging/windows/freemyid.iss` (`#define AppVersion` and the `iscc` comment line).
- Distro recipes keep the last stable version during a pre-release (`tests/copilot/test_cp_packaging_lint.py` reads it from `site_src/data/release.yaml`). At final they must name `0.3.0`, or the lint fails once pyproject says `0.3.0`: `distro/aur/PKGBUILD`, `distro/aur/.SRCINFO`, `distro/flatpak/org.freemyid.FreeMyID.yml` (+ README), `distro/homebrew/freemyid.rb`, `distro/scoop/freemyid.json` (+ README), `distro/winget/*.yaml` (+ README). Their hashes stay placeholders until release-day tooling (`distro/CHECKLIST.md`, gate `tools/ci/check_distro_hashes.py`); no channel is published.
- `distro/CHECKLIST.md` line 3 describes `site_src/data/release.yaml`; it becomes true for 0.3.0 only after `site-release-info` runs, so it is left alone in the bump.
- Inno Setup **AppId is unchanged** from v0.2.0 (`{90CB7231-F487-4012-93B4-C1CE0AC4DF82}`; `git diff v0.2.0 -- packaging/windows/freemyid.iss` touches only the version, the new `[Messages]` first-start wait text and the `[Run]` label). An install over 0.2.0 is therefore an upgrade, not a second app.
- Prepared bump: branch `release/v0.3.0` (worktree `.vendor-wt/rel-030`), one commit "Release v0.3.0: version bump" on top of local main b3b5013. Not merged, not pushed. `pytest -k "version or packaging or distro"`: 62 passed, 6 skipped.
- Release notes: `docs/marketing/release-notes-v0.3.0.md` (Jordan). For final, delete the rc title line and the "test version" paragraph, and the commit comments.

## Checklist: rc1 to v0.3.0
Each push and tag needs the owner's OK. Do the steps in order; stop on any red.

1. **Owner: Windows VM check of the rc1 installer** (Windows 10 and/or 11, normal non-admin user):
   - Download `FreeMyIDSetup-0.3.0rc1.exe` + `SHA256SUMS.txt` from the pre-release page; `Get-FileHash -Algorithm SHA256 .\FreeMyIDSetup-0.3.0rc1.exe` equals the SHA256SUMS line.
   - **Upgrade over 0.2.0:** on a snapshot with v0.2.0 installed and set up (fake data: Jane Q Testperson, Springfield IL), run the rc1 installer. Expect no second "Free My ID" entry in Settings > Apps, the profile and reports still there, and the scheduled task still present (`schtasks /Query /TN "Free My ID" /V /FO LIST`).
   - **Fresh install:** on a clean snapshot. SmartScreen "unknown publisher" is expected (unsigned). The finish page shows the "up to 15 seconds the first time" text.
   - **Splash:** on first start a splash window appears while the app unpacks and closes by itself when the wizard opens on 127.0.0.1. No double start if you wait.
   - Walk all 6 wizard screens with fake data only; no real email sent. Run the task once: `schtasks /Run /TN "Free My ID"`.
   - **Uninstall while running:** leave the app window open (and/or start the task), then uninstall from Settings > Apps. Expect the app closed by the uninstaller, `%LOCALAPPDATA%\Programs\FreeMyID` gone including `FreeMyID.exe` and `_internal`, the scheduled task removed, and the "delete saved information?" question honoured (No keeps `%APPDATA%\FreeMyID`, Yes removes it).
   - Record the result in PROGRESS.md (screenshots in `brand/screenshots/vm-v0.3.0/`). Any failure blocks 0.3.0 (fix → rc2).
2. **Other rc1 checks (any machine):**
   ```
   pipx install --pip-args=--pre freemyid==0.3.0rc1 && freemyid --version
   gh release view v0.3.0rc1 --json isPrerelease,assets
   gh release view --json tagName          # must still say v0.2.0
   docker pull ghcr.io/freemyid/freemyid:v0.3.0rc1
   ```
3. **Merge queue done, CI green on main** (incl. `commit-email-check`, `windows-installer`, docker): `gh run list --branch main --limit 8`. Full suite on the exact SHA to be pushed.
4. **Dependabot #24 (cosign-installer v4):** merge just before the bump (see below), so the tag run is the first signing with cosign v3. Hold #67, #68, #70, #71, #72 until after the tag.
5. **Bump** (devops prepared it; orchestrator merges and pushes with the owner's OK):
   ```
   git merge --no-ff release/v0.3.0       # or cherry-pick the "Release v0.3.0: version bump" commit
   .venv/bin/pytest -q
   git push origin main
   gh run list --branch main --limit 6    # wait for build, docker, pages green
   ```
   If main moved after the branch was made, re-check `git grep -n 0.3.0rc1 -- pyproject.toml src packaging distro` is empty and `git grep -n 0.2.0 -- distro` only hits `distro/CHECKLIST.md`.
6. **Owner tags** the green bump commit:
   ```
   git fetch origin && git log -1 --format='%h %s' origin/main   # must be the bump (or its merge)
   git tag -a v0.3.0 "$(git rev-parse origin/main)" -m "Free My ID v0.3.0"
   git push origin v0.3.0
   ```
7. **Watch:** `gh run list --limit 8`, then `gh run watch <id>` for build, pypi, docker. Approve the `pypi` environment if asked. Re-run only failed jobs: `gh run rerun <id> --failed`.
8. **Verify (devops):**
   - GitHub release v0.3.0: NOT a pre-release and is `latest` (`gh release view --json tagName` = v0.3.0); assets FreeMyIDSetup.exe, FreeMyIDSetup-0.3.0.exe, SHA256SUMS.txt, freemyid.cdx.json; `sha256sum -c SHA256SUMS.txt` passes.
   - `site-release-info` committed "Site: v0.3.0 release info"; pages.yml redeployed; `curl -s https://freemyid.org/download/ | grep -c 0.3.0` > 0 and the shown SHA-256 equals SHA256SUMS.txt; `curl -sIL https://freemyid.org/get/windows | grep -i -E '^(HTTP|location)'` ends 200 on FreeMyIDSetup.exe of v0.3.0.
   - PyPI: JSON API `info.version` = 0.3.0; clean `pipx install freemyid && freemyid --version` says 0.3.0.
   - GHCR: `docker pull ghcr.io/freemyid/freemyid:v0.3.0`; `:latest` has the same digest; signature (cosign v3, new bundle format if #24 merged):
     `cosign verify ghcr.io/freemyid/freemyid:v0.3.0 --certificate-identity-regexp '^https://github.com/FreeMyID/freemyid/.github/workflows/docker.yml@refs/tags/v0.3.0$' --certificate-oidc-issuer https://token.actions.githubusercontent.com`
     and `cosign verify-attestation --type spdxjson` with the same flags.
9. **Owner: VM check of the final `FreeMyIDSetup-0.3.0.exe`**, upgrading over the rc1 install (settings, data and scheduled task survive; still one entry in Settings > Apps).
10. Record in PROGRESS.md and `docs/handoff/devops-engineer.md`; publish the release notes; announce.

## Dependabot at this release
- **#24 sigstore/cosign-installer 3.9.1 → 4.1.3: safe.** One-line SHA change in docker.yml. v4 installs cosign v3.1.4 by default (we set no `cosign-release`). The only documented breaking change is that `cosign sign-blob` needs `--bundle`; we use only `cosign sign --yes` and `cosign attest --yes --type spdxjson --predicate`, both unchanged. Cosign v3 writes the new Sigstore bundle format, so verify with cosign ≥ 2.6 (v3 recommended). The PR's docker build-smoke passed, but `publish` (signing) only runs on tags, so the v0.3.0 tag run is the real test; if signing fails there, revert #24 and re-run the docker job. Its only red check is `commit-email-check` (Dependabot author, expected).
- #67 python 3.12-slim → 3.15-slim (Docker base): **hold**, the app targets 3.12; a new interpreter at release time is a needless risk. Revisit after 0.3.0 with a full test run, or ignore majors.
- #68 hatchling 1.27 → 1.33 (`tools/ci/build-requirements.txt`): **hold / rework**, its `dist` job fails (`--require-hashes`: a new unpinned dependency) and it changes the reproducible wheel build.
- #69 claude-code-action 1.0.268 → 1.0.269: **merge after the tag** (patch, not on the release path; needs `@dependabot rebase` first).
- #70 actions/download-artifact v4 → v8: **hold**, used by the release job; four majors.
- #71 docker/build-push-action v6 → v7: **hold**, the image publish path.
- #72 pnpm/action-setup v4 → v6: **hold**, the site build path.
- #67–#72 all show red `test` jobs: they branched from caf2262, where `tests/test_web_home_hero_layout.py` needs `web/dist` (fixed on main, c218cd9 green). `@dependabot rebase` before judging their CI.

## Rollback
- PyPI: yank 0.3.0 on the project page and publish 0.3.1 (versions can never be re-uploaded).
- GHCR: retag `:latest` to the v0.2.0 digest (sha256:eb3d2579…dd590) or delete the v0.3.0 version in package settings (owner OK).
- GitHub release: `gh release edit v0.2.0 --latest` brings the download button back to 0.2.0; `gh release delete v0.3.0 --cleanup-tag` only with the owner's OK (Tier 3).
- Site: revert the automatic "Site: v0.3.0 release info" commit and dispatch pages.yml.
- Code: `git revert` on main plus a patch release; never rewrite history.
