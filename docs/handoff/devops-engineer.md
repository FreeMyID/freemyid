# Handoff: devops-engineer (Dana Ortiz)

## v0.2 CI / release work (2026-11-07)

Files: `.github/workflows/{build,docker,pypi,domain-health,registry-health}.yml`, `.github/dependabot.yml`, `tools/cloudflare_redirects.py`. All actions SHA-pinned (comment shows major). Not yet run on GitHub (not pushed): first run needs watching.

- build.yml: job `test` is a matrix (ubuntu, macos, windows; py3.12; ruff + pytest; Playwright Chromium; `FREEMYID_REQUIRE_BROWSER=1` everywhere). Old check name `lint-test-linux` is gone; if branch protection requires it, update the required checks to `test (ubuntu-latest)` etc. Windows installer job no longer repeats pytest (the matrix covers it) and waits for `test`. New `dist` (sdist+wheel, twine check) and `pipx-smoke` (ubuntu, macos: pipx install wheel, `freemyid --help`, `doctor --json` must emit valid JSON). Release now needs test, dist, windows-installer.
- docker.yml: skips cleanly while `packaging/docker/Dockerfile` is absent. Build + smoke on PRs/main; on v* tags push `ghcr.io/freemyid/freemyid:{latest,vX.Y.Z}`, cosign keyless sign, SBOM (syft spdx) attached as signed attestation, provenance mode=max. Smoke also requires the image to run as non-root. Dockerfile needs `freemyid` on PATH. After first push, make the GHCR package public (Package settings) and link it to the repo.
- pypi.yml: gated by repo variable `PYPI_PUBLISH=true`; skips cleanly otherwise. Checks tag equals pyproject version.
- dependabot: github-actions (grouped), pip, npm `/web` (grouped minor/patch). Docker ecosystem to add once the Dockerfile exists.

### OWNER one-time PyPI setup (click steps)
1. Sign in (or create an account with 2FA) at https://pypi.org.
2. Go to https://pypi.org/manage/account/publishing/ ("Publishing" in the account menu).
3. Under "Add a new pending publisher" choose the GitHub tab and fill in exactly: PyPI project name `freemyid`; Owner `FreeMyID`; Repository name `freemyid`; Workflow name `pypi.yml`; Environment name `pypi`. Click Add.
4. In GitHub, repo FreeMyID/freemyid > Settings > Environments > New environment, name `pypi` (optionally add yourself as required reviewer so each publish needs one click).
5. Settings > Secrets and variables > Actions > Variables > New repository variable: `PYPI_PUBLISH` = `true`.
6. Next v* tag publishes. The project name is claimed on first publish; check `freemyid` is free on PyPI first (if taken, tell Morgan, the name in step 3 and pyproject must change).

### Test markers for qa-security (CR: pyproject.toml is orchestrator-owned)
Proposed pytest markers, registered under `[tool.pytest.ini_options] markers`: `windows_only`, `posix_only`, `macos_only`, `linux_only`, `browser` (needs Chromium). Skip logic goes in `tests/conftest.py` (`pytest_collection_modifyitems`, skip by `sys.platform`). Real scheduler tests (schtasks / systemd / launchd) must carry the matching OS marker and mock-free ones must only run on that runner, never touching the real user session outside CI (guard with `CI=true`). Until markers exist, tests that fail on macOS/Windows will fail the matrix: expect a first red run and triage it.

## Download redirects (2026-11-07)
`tools/cloudflare_redirects.py` (dry run default, `--apply`, `--rollback`) manages three Cloudflare Single Redirect rules (refs `freemyid-get-*`), merging with any existing rules. Applied and verified live: `/get/windows` 302 to `github.com/FreeMyID/freemyid/releases/latest/download/FreeMyIDSetup.exe`, final 200 `application/octet-stream`, no auth; `/get/linux` and `/get/macos` 302 to `/developers/` (page does not exist yet: web-developer must create it). Rollback: `python tools/cloudflare_redirects.py --rollback` or delete the three rules in the dashboard (Rules > Redirect Rules). domain-health now checks all three weekly.
