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

## 2026-11-07 first CI matrix triage (build 42400577310, docker 42400577313, main@29e68c7)
- docker.yml smoke: ENTRYPOINT is `freemyid`, so `docker run image freemyid --help` became `freemyid freemyid --help`. Fixed the smoke args (`--help`, `doctor --json`) and `id -u` now uses `--entrypoint id`. Dockerfile is correct: HEALTHCHECK exec-form CMD runs directly and does not get the ENTRYPOINT prepended.
- build.yml macOS browser test: the Playwright install was fine; tests/test_security_wave2.py `_browser_exe()` globs only the Linux path `~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell`. macOS (`~/Library/Caches/ms-playwright`) and Windows (`%LOCALAPPDATA%\ms-playwright`, `.exe`) are never found. Workflow now exports FREEMYID_BROWSER_EXECUTABLE after install. Optional test cleanup for qa-security: make `_browser_exe()` OS-aware.
- macOS mail/bridge-trust failures (test_mail_tls_pin.py, test_wizard_bridge_trust.py): ROOT CAUSE in the test fixture, reproduced on Linux by making `socket.getfqdn` sleep 11s. `smtplib.SMTP` calls `socket.getfqdn()` AFTER connecting and BEFORE sending EHLO; macOS runners take >10s to resolve their hostname. `FakeServer._handle` uses `c.settimeout(10)`, so the fake server times out and closes, and the client sees SMTPServerDisconnected. IMAP never calls getfqdn, so IMAP tests pass; implicit-TLS "rejected" tests pass because they fail in the handshake before getfqdn.
  - Fix for qa-security (tests/test_mail_tls_pin.py): raise the idle timeout in `FakeServer._handle` (`c.settimeout(10)`) and `lsock.settimeout(10)` to 60.
  - Product note for automation-engineer (not a ship blocker; Bridge has no 10s idle limit): `SmtpImapMailer.send` and `fetch_loopback_fingerprint` build `smtplib.SMTP(...)` / `SMTP_SSL(...)` without `local_hostname`. Passing `local_hostname="localhost"` avoids the slow DNS lookup on Macs and stops EHLO from sending the computer's hostname to the mail server (small privacy win).
- Windows: run aborted at collection (fcntl import in test_social_poster.py); no other Windows results exist yet. Re-triage after the next push.

## Design note: release announcements to Discord #announcements (2026-11-07, not built)
Preferred: a channel webhook, no bot.
- Owner: Discord server > #announcements > Edit Channel > Integrations > Webhooks > New Webhook (name "Free My ID releases") > Copy Webhook URL. Put it in GitHub only: repo FreeMyID/freemyid > Settings > Secrets and variables > Actions > New repository secret `DISCORD_RELEASE_WEBHOOK`. Optionally also store it in the keyring (`freemyid-social`, key `discord_release_webhook`) for manual posts. Never in the repo, chat or logs. The URL is a bearer secret: if it leaks, delete the webhook and make a new one.
- Workflow: new job `announce` in build.yml (or a small `announce.yml` on `release: published`, so pre-releases are skipped via `if: !github.event.release.prerelease`). `needs: [release, site-release-info]` so it posts only after assets and the site are live. Skips cleanly when the secret is empty (forks, PRs). Permissions `contents: read`.
- Step: pass the secret and release fields through `env:`, never interpolate `${{ }}` into the shell script. Build the JSON with `jq -n --arg` (so release notes cannot break or inject), post with `curl -fsS -H 'Content-Type: application/json' -d @- "$HOOK"`. Payload: `username` "Free My ID", one embed (title "Free My ID vX.Y.Z", url = release page, description = first ~800 chars of the notes, fields: download link `https://freemyid.org/download/`, SHA256), and `allowed_mentions: {"parse": []}` so no @everyone or role pings. Never `set -x`; no output of the URL.
- Link to freemyid.org/download, not github.com (users need no GitHub account).
- Bot alternative (only if we later want edits, threads or reactions): reuse the existing least-privilege bot (token in keyring `freemyid-social`) and `POST /channels/{id}/messages` from a script run by the owner or an agent. Not suitable for CI: it would put the bot token into GitHub secrets, a bigger blast radius than a single-channel webhook. Hence webhook.
- Rollback: delete the `announce` job or the secret; nothing else depends on it.
- Cost: free. Rate limit is irrelevant (one post per release).

## 2026-11-07 commit-email guard (SEC-93c follow-up)
`.github/workflows/commit-email-check.yml` + `tools/ci/check_commit_emails.sh BASE HEAD`: on push to main (before..after) and PRs (base.sha..head.sha) fails if any new commit's author or committer email is not `*@users.noreply.github.com` or `noreply@github.com`. Offenders are masked (`s***@e***`). Allowlisted SHAs: d647b58, f8f19a2, c52cab2 (full SHAs in the script). New-branch push (zero before) checks only commits not already on origin. Tested on a scratch repo (fails on a foreign address, passes on noreply forms) and on the real history tail (passes). Known: two other historical commits use `noreply@freemyid.org` (d6a6cf3, c3068f7); they are not flagged unless re-included in a range. Decision for orchestrator: add `noreply@freemyid.org` to the allowlist regex if it should count as acceptable. Not yet run on GitHub (unpushed).

## 2026-11-07 dependency audit, Dependabot, pnpm audit gate (SEC-67)

**Advisories (real ones only): none.**
- npm (`cd web && pnpm audit --json`, 310 packages, registry.npmjs.org): 0 info/low/moderate/high/critical. `pnpm outdated`: nothing (every direct dependency is already at latest allowed by minimumReleaseAge 1440).
- Python (`uvx pip-audit` against `pip freeze --exclude-editable` of `.venv`, PyPI/OSV): "No known vulnerabilities found". `pip list --outdated` only shows the rows in the matrix below.

**Changes**
- `.github/dependabot.yml`: github-actions, pip (/), npm (/web), plus docker (/packaging/docker, the Dockerfile now exists). Weekly. Minor/patch are grouped per ecosystem (`actions-minor-patch`, `python-minor-patch`, `web-minor-patch`); majors are not in any group, so each arrives as its own PR. SHA pins are kept (Dependabot rewrites SHA and `# vX.Y.Z` comment together; SEC-61).
- `.github/workflows/pages.yml`: new step `Dependency audit` before the build: `pnpm audit --audit-level=high` fails the job on high/critical. Ignore list: `web/audit-ignore.txt` (one CVE id per line, `#` comments; pnpm's `--ignore` takes CVE ids). It is empty. Any entry needs a reason and an expiry date in a comment, and a note here. Note the step sends the dependency list to npm, so it runs in CI only (SEC-67 offline concern). If the registry errors the step fails; rerun, do not add `--ignore-registry-errors`.
- Not done on purpose: no audit on a schedule yet (pages.yml only runs when web/** changes). Proposal: add a weekly `schedule` to pages.yml's audit, or rely on Dependabot security alerts (owner: turn on "Dependabot alerts" in repo Settings > Code security).

**Upgrade matrix**

| Package | Current | Target | Advisory / source | Risk | Rollback |
|---|---|---|---|---|---|
| astro, @tailwindcss/vite, tailwindcss, yaml, cva, clsx, tailwind-merge (npm) | exact, see web/package.json | none | no advisory, nothing outdated | none | n/a |
| click (py, transitive of typer) | 8.5.0 | 8.5.1 | pip list --outdated, no advisory | low, patch | pin `click==8.5.0` in the venv |
| fastapi | 0.162.0 | 0.162.2 | no advisory | low, patch; wizard server relies on it, run full pytest | `uv pip install fastapi==0.162.0` |
| typer | 0.27.3 | 0.28.0 | no advisory | medium: 0.x minor, CLI surface and `--help` output tests | `uv pip install typer==0.27.3` |
| pyee (transitive of playwright) | 14.0.0 | 16.0.1 | no advisory | do not touch: playwright pins its range; let playwright upgrade it | n/a |
| pip | 26.2.2 | 26.3 | no advisory | dev tool only | n/a |
| GitHub Actions, 14 actions (PR #4) | v4-era SHAs | see below | Dependabot PR #4 | medium: several majors | close PR, or `git revert` the merge commit |

No patch-level security fix was needed, so I upgraded nothing. pyproject.toml uses lower bounds only (orchestrator-owned), so Python versions in CI float to latest anyway; the Windows installer build is the place a floating major would bite.

**Dependabot PR #4 (actions group, 14 updates), branch dependabot/github_actions/actions-ad74ac4c96**
- All 14 new SHAs resolve to the tag named in their `# vX` comment (checked with `git ls-remote`, peeled commit for annotated tags): cache v6.1.0, checkout v7.0.1, deploy-pages v5.0.1, download-artifact v8.0.2, setup-node v7.1.0, setup-python v7.1.0, upload-artifact v7.0.2, upload-pages-artifact v5.0.0, anchore/sbom-action v0.24.3, build-push-action v7.4.0, login-action v4.8.0, setup-buildx-action v4.4.1, pnpm/action-setup v6.1.1, cosign-installer v4.1.3. All pins preserved (SEC-61 holds), only the PR bot authored the commits. 5 workflows touched (build, docker, pages, pypi, registry-health), no non-action lines.
- PR checks: build, build-smoke, dist, pipx smoke (ubuntu, macos), test (macos, windows) pass. NOT exercised by the PR: deploy (skipped), release publish (skipped), site-release-info (skipped), docker push/cosign/SBOM (tag only), pypi.
- Verdict: pins are safe; the PR is mostly majors, so merge it only as a deliberate step. Things to check first: (1) upload-artifact v7 / download-artifact v8 must stay a compatible pair (both bumped here, fine) and artifact names must be unique per job; (2) upload-pages-artifact v5 with deploy-pages v5 (bumped together, fine); (3) pnpm/action-setup v6 with `version: 10.32.1`: read its release notes, this is the one third-party action that runs where the site is built; (4) checkout/setup-node/setup-python v7 need a recent runner (ubuntu-latest, macos-latest, windows-latest all fine). Recommendation: merge after a manual `workflow_dispatch` of pages.yml on the PR branch and a dry docker run; if the owner wants lower risk, close it and let the new config re-open it as minor/patch only (majors then come one PR each). Not merged.

## 2026-11-08 Dependabot #20-24 triage, Bing file, health (Dana Ortiz)

Verdicts (changelogs read; our usage: name+path uploads, ghcr login with github.token, cosign sign/attest on image digest, hosted runners):
- #20 anchore/sbom-action 0.24.0 -> 0.24.3: SAFE (patch).
- #21 actions/deploy-pages 4.0.5 -> 5.0.1: SAFE. v5 only moves to Node 24; still needs upload-pages-artifact v3+ (we use v3.0.1) and `actions: read` (already set).
- #22 docker/login-action 3.7 -> 4.8.0: SAFE. v4 = Node 24 + ESM, needs runner >= 2.327.1 (GitHub-hosted fine); inputs unchanged.
- #23 actions/upload-artifact 4.6.2 -> 7.0.2: SAFE. v5/v6 Node 24; v7 adds optional `archive: false` and ESM; default zip behaviour unchanged. download-artifact v4 stays compatible (same artifact backend). Names are unique per job.
- #24 sigstore/cosign-installer 3.9.1 -> 4.1.3: HOLD (not a code problem). v4 installs Cosign v3 by default; `cosign sign --yes` and `cosign attest --type spdxjson` on a digest need no change (the `sign-blob --bundle` note does not apply), no `cosign verify` or `cosign-release` in repo. But it runs only on a v* tag push and cannot be tested by PR checks; Cosign 3 writes the new bundle format, so consumers verifying need cosign >= 2.6/3. Merge only just before a release, then watch the docker.yml run (workflow_dispatch pushes to GHCR, so run on a tag).

Prepared (local, not pushed): branch `devops/actions-bumps-2026-11` (commit 2af6f37) applies #20-#23 with the exact SHAs Dependabot chose (pins kept, SEC-61); no tweaks needed. 5 workflow files, 7 lines. Merge locally --no-ff; Dependabot will then auto-close #20-23.

Bing: BingSiteAuth.xml was the repo root. Astro `publicDir` is `site_src/static` (not web/public), served at the site root. Content is only `<users><user>HEXTOKEN</user></users>`, a public verification token, same class as the IndexNow key file. Moved to `site_src/static/BingSiteAuth.xml` and committed on main. Goes live on the next pages deploy (owner: then click Verify in Bing Webmaster Tools; do not delete the file afterwards).

Health: domain-health last run 2026-11-07 success (workflow_dispatch). Live cert Let's Encrypt (YE1) notAfter 2027-02-05 (auto-renews; quarterly check due Feb 2027). security.txt live, Expires 2027-11-07 (renew before Oct 2027). Site returns HTTP/2 200.

## 2026-11-08 checkpoint for Morgan (Dana Ortiz)

1. CI on origin/main 9f89fea: commit-email-check and pages green; build RED only on `test (windows-latest)` (run 42483828490; ubuntu, macos, dist, pipx all green; windows-installer/release skipped because of it). Cause: `bash` on windows-latest resolves to the WSL launcher (System32\bash.exe, no distro), which prints UTF-16 text, so 3 tests in tests/test_qa_wave_20261107.py (commit-email guard: passes_noreply, checks_committer, zero_before) fail with rc 1. The "Event loop is closed" lines are teardown noise, not failures. Fix committed locally f324bfd: build.yml step before Tests prepends `C:\Program Files\Git\bin` to GITHUB_PATH on Windows. Unverified until pushed (owner go). Alternative if it does not take: test passes `shutil.which("bash")` resolved path (qa-security). Same Windows failure existed on PR #24's run and on copilot/wo-121.
2. GHCR `ghcr.io/freemyid/freemyid`: still private (anonymous pull token refused; my gh token lacks read:packages so I cannot read the flag directly). Docker published on tag v0.2.0 (run 42437493605). Owner click path: github.com > FreeMyID org > Packages > `freemyid` > Package settings (right side) > Danger Zone > Change visibility > Public > type the package name > confirm. Then, same page, "Connect repository" > FreeMyID/freemyid. Owner-only; not attempted.
3. Dependabot: only #24 open (cosign-installer 3.9.1 -> 4.1.3). GO for the next pre-release tag, conditional: v4 installs Cosign v3; our usage (`cosign sign --yes`, `cosign attest --type spdxjson` on the digest) is unaffected; no `verify`/`sign-blob`/`cosign-release` in repo. Merge locally --no-ff just before the pre-release tag, watch that tag's docker run, then `cosign verify` the image with cosign >= 2.6 to prove the bundle. PR #24 shows failing checks (windows test, same bash cause). Also still prepared: branch `devops/actions-bumps-2026-11` (#20-23). No new Dependabot PRs. PRs #39-41 (Copilot) and #5 are not Dependabot; their workflow runs show `action_required` (first-time-contributor approval, owner-only).
4. SEC-66: transform rule (cloudflare_harden.py, live) already sends X-Frame-Options DENY, nosniff, Referrer-Policy strict-origin-when-cross-origin, COOP same-origin, Permissions-Policy, HSTS (max-age 15552000). That covers the framing risk (XFO DENY replaces frame-ancestors for the browsers that matter), nosniff and referrer. NOT covered: a CSP header (only the meta CSP), `frame-ancestors` itself, Referrer-Policy `no-referrer` (QA asked; current value is a reasonable choice, site has no sensitive URLs). The site is behind Cloudflare, so the "host move" premise in SECURITY_REVIEW SEC-66 is already satisfied. Proposal (needs go, one change, rollback = re-PUT the old rule): extend the rule with `Content-Security-Policy` mirroring the meta CSP plus `frame-ancestors 'none'`, after web-developer confirms the exact meta string (any mismatch breaks pages); raise HSTS to 31536000 + includeSubDomains only once the owner accepts preload-level commitment.
5. Health: domain-health last ran 2026-11-07 success (workflow_dispatch; next scheduled weekly). Live cert notAfter 2027-02-05 (quarterly re-check due Feb 2027). security.txt Expires 2027-11-07 (renew before Oct 2027). Site HTTP/2 200 with headers above.
6. REMINDER: keyring `github_token` expires 2026-12-08. Rotate by 2026-12-01 (fine-grained token, same least-privilege scopes, store with `secret-tool` service `freemyid-github`), verify with `gh auth status`, add read:packages only if wanted for the GHCR check.
