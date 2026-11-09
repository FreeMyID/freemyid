# qa-security handoff
Done (earlier): scaffold review (docs/SECURITY_REVIEW.md), conftest, fixtures, test_models,
test_state, test_crypto, test_storage, test_redaction, test_netpolicy, test_consent.
Done (v1 wave 1, 2026-11-06):
- Fixed test_log_file_redacted: CLI tests call logging_setup.setup(), which leaked a StreamHandler
  bound to CliRunner's (closed) stderr into later tests and made setup() a no-op. conftest's
  autouse `freemyid_env` now removes/closes any root handlers a test adds and restores the level.
- Dropped the SEC-04b xfail marker (Store now registers profile PII).
- tests/ ruff clean (dict literals, import order, UTC, InvalidTag instead of blind Exception).
- New tests: Tier, BrokerStatus.tier, new TodoKinds, Todo.copy_fields (models, encrypted store
  round-trip with no plaintext on disk, never logged). SEC-15 strict xfail (copy_fields in repr).
- tests/test_e2e_dryrun.py: scaffold, skips until freemyid.engine.runner.run and a dev module
  exposing fixture_registry() + fixture_server() exist (looks in freemyid.engine._dev, freemyid._dev,
  freemyid.engine.devrun). Asserts D1 tiers, data-minimized copy_fields, nothing sent.
Open CRs: interfaces.py UP037 (orchestrator), engine/mail.py S110 (automation-engineer),
models.py SEC-15 repr=False (orchestrator).
Next: adopt src/freemyid/wizard/_test_drafts and tests/fixtures/test_wizard_server.py (misplaced
test file in fixtures/) once wizard-packager's wave settles; un-skip e2e when runner lands and
align _load_dev() names; tools/registry_health.py; review engine/wizard/scheduler for this wave.
Wave 2 (2026-11-06):
- Step 1 DONE: git mv engine/_test_drafts/test_{outbox_letters,runner,tiers}.py and
  wizard/_test_drafts/test_{scheduler_render,wizard_dashboard,wizard_desktop,wizard_screens,
  wizard_server}.py into tests/; deleted the drafts' conftest/__init__ and both draft dirs.
  tests/fixtures/test_wizard_server.py no longer exists. e2e dry-run now runs (not skipped).
  pytest 220 passed, ruff clean.
- Step 2 tests DONE: tests/test_security_wave2.py (14 pass, 7 strict xfail = SEC-16,18,19,20,
  21,22,24). Redirect bypass (SEC-16) confirmed live with the cached chromium headless shell.
- Step 2 doc DONE: SECURITY_REVIEW.md wave-2 section (SEC-16..29). Verdict BLOCK on SEC-16.
- Orchestrator FYI handled: Windows CI 'Event loop is closed' = SEC-26 (Playwright driver leak on
  failed launch), reproduced + fix verified on Linux; xfail test cleans up after itself.
Next wave: remove xfail markers as SEC fixes land; tools/registry_health.py still TODO.
Wave D9 (2026-11-06):
- A DONE: tests/test_wizard_browser_e2e.py. Real Playwright Chromium (headless) against
  start_background() with FREEMYID_NO_BACKGROUND=1: all 6 screens (Pat Testperson, Raleigh NC) to
  the dashboard, then a Settings permissions save. Asserts each POST → 303 → expected next step,
  real Origin header, no 403/5xx, Referrer-Policy != no-referrer, nothing leaves 127.0.0.1. A
  second test checks that foreign, null and other-port Origins and a bad CSRF still get 403. Skips
  if Chromium can't launch. Negative check (scratch, not committed): forcing no-referrer via an
  ASGI header rewrite gives Origin: null → 403 and the walk stops on step 1, so the test catches
  the 54ff105 bug, including with the context route in place.
- B DONE: engine/_test_drafts/test_fill_for_me.py → tests/test_fill_for_me.py (byte-identical,
  54 pass; no conftest changes needed). Verified it before git rm of engine/_test_drafts.
- C DONE: SECURITY_REVIEW.md D9 section SEC-30..38; tests/test_security_d9.py (3 pass, 4 strict
  xfail = SEC-30,31,32,33). Verdict BLOCK (narrow) on SEC-31 (robot checkbox via broad
  safe_checkboxes selector).
- Full suite: 320 passed, 4 xfailed; ruff clean.
Next: remove xfail markers as SEC-30..33 land; tools/registry_health.py still TODO.
Post-v0.1.0 wave (2026-11-07):
- SEC status table in SECURITY_REVIEW.md: SEC-01..45 = 41 Fixed, 4 Accepted (38, 41, 44, 45), 0 Open.
  Rulings recorded (SEC-38 accepted + one-time confirm 8637941; SEC-41 accepted by peer ruling +
  regenerated 450bb34; SEC-44/45 INFO). SEC-40/42/43 confirmed with tests.
- tools/registry_health.py DONE (offline default; --online HEAD via NetPolicy, polite; --selectors;
  --report md/json; exit 1 on ERROR). tests/test_registry_health.py (33, no network). Real
  registries: 0 errors, 447 warnings (mostly no last_verified). CR: weekly CI workflow (below).
- Adopted drafts: test_first_email_approval.py (7), test_reply_matcher.py (13),
  test_escalation_timers.py (6); tracked engine/_test_drafts removed (a6c6869). An untracked
  test_search_guard.py appeared there afterwards (automation-engineer WIP): adopt next time.
- New: SEC-46 (fixed 85e1f74 by O), SEC-47 MED open (approve card hides held AUTO emails it also
  sends), SEC-48 LOW open (approve sends on the event loop), SEC-49 LOW open (/safety/ report
  copy omits the label). tests/test_security_wave3.py: 3 strict xfails (47, 48, 49) + guards.
- Use FREEMYID_TEST_NO_FULL_REGISTRY=1 to run as a public checkout (never rename registry.yaml).
- CR (orchestrator, .github/workflows): weekly job `python tools/registry_health.py --report
  registry-health.md` (offline; add --online only if the runner's egress is acceptable), upload
  the report as an artifact.
- Later in the wave: SEC-47 (1fd51c2, d84ac04), SEC-48 (f2783ee) and SEC-49 (c27463b) fixed by their owners, markers
  removed. Also adopted test_search_guard.py (3) and test_assisted_no_mailbox.py (2); engine/_test_drafts gone.
  SEC-01..49: 45 Fixed, 4 Accepted, 0 Open; no strict xfails. LAUNCH_CHECKLIST lines 38 and 53 ticked, line 8 annotated.
- Final runs at d84ac04: 508 passed (full registry); 505 passed, 3 skipped (FREEMYID_TEST_NO_FULL_REGISTRY=1);
  ruff and mypy clean. v0.1.1 verdict: PASS.
Next: weekly registry_health CI job (CR to O); adopt any new _test_drafts; review the next wave.
R8 site-v3 (2026-11-07, branch site-v3, web/ at 4533a5c):
- Verdict: BLOCK (narrow), for the switch-over only, on SEC-60. Astro build telemetry is on (no
  ASTRO_TELEMETRY_DISABLED; CI runs are still reported as `CI.<name>`). The built site passes.
- SEC-60 MED (BLOCK), SEC-61 MED (actions not SHA-pinned), SEC-62 LOW (no strictDepBuilds or
  onlyBuiltDependencies), SEC-63 LOW (unused TimelineBeam/motion chunk deployed), SEC-64 LOW (checkout
  persist-credentials), SEC-65 LOW (check-site on*= regex too narrow), SEC-66 INFO (meta CSP: no
  frame-ancestors; move it after charset; headers once on freemyid.org), SEC-67 INFO (no pnpm audit in
  CI). SEC-50..59 are reserved for the Proton TLS work on main. WR-56..49 filed (WR-59 overlaps web-qa
  WR-52).
- Verified: 43/43 pages have a meta CSP with no unsafe-*. 42 pages have script-src 'none'. /download/
  hashes match its 2 island scripts and 1 style. Playwright over all 43 pages with external requests
  aborted: 0 CSP violations, 0 errors, 0 external requests. CopyHash hydrates and copies after the
  panel opens. External origins in dist are navigational hrefs only.
- Dependencies: 12 direct (exact pins). Lockfile: 322 entries / 295 names (165 optional platform
  binaries), 219 installed on linux-x64, 322/322 with sha512 integrity, 0 install scripts.
  pnpm audit skipped (not offline).
- Build note: `astro build --outDir <scratchpad>` fails with EXDEV (cross-device rename). Build in
  web/dist (gitignored), then copy it.
Next: re-check SEC-60/61 when the workflow is renamed; clear SEC-62..65 as the WR rows land.
R8 re-check site-v3 (971b1ec..cd35f9c): PASS, the BLOCK is lifted. SEC-60 (f683e12; egress hook: 0 attempts
  via `pnpm build`, the control `pnpm exec astro build` tried telemetry.astro.build), SEC-61/64 (845bcd0;
  6/6 SHAs match their tags via ls-remote, persist-credentials false) and SEC-63 (7808e13; lockfile only
  removes motion*, the guard catches a planted unreferenced .js) are verified. WR-51 popover: 42 pages still
  'none', /download/ hashes match, 0 CSP violations. Still open: SEC-62, SEC-65 (LOW) and SEC-66, SEC-67 (INFO).
  Dev machines: run `pnpm exec astro telemetry disable` (a direct astro run still reports).
  WR rows were renumbered +11 by 971b1ec (WR-45..49 became WR-56..60).

## Checkpoint 2026-11-07 (orchestrator, session end)
- Bluesky poster reviewed: PASS (2a5bb23, bbf96b1). SEC-57 (MED), SEC-58 (LOW) open for automation-engineer; SEC-59 decided by lead (read-only install + sha256 pin via install.sh).
- Next: once automation-engineer lands SEC-57/58 + install.sh, re-check SEC-57/58/59 only, remove the strict xfails in tests/test_social_poster.py, verify install.sh on a temp HOME (never the real one), report PASS/BLOCK to the lead. The lead installs the timer only after that PASS.
- Spot-check docs/marketing/seo/bluesky-queue.md content now and then (it is the only content review point; owner chose fully autonomous).
- SEC numbering: main uses 50–59 (all used up to 59); continue at SEC-70+. 60–69 belong to the site-v3 branch.

## 2026-11-07 secrets backends review + CI markers (Marcus Webb)
- Secrets backends (9a81313, f60625a, 0703216) reviewed: **PASS**. SEC-70 (MED, migrate verify reads the cache, not the disk: wrap damage -> keychain key deleted -> data lost), SEC-71 (MED, a killed migrate strands mailbox passwords and a re-run is a no-op; config.save isn't atomic), SEC-72 (MED, the global keychain entry gets overwritten/deleted across FREEMYID_HOMEs), SEC-73 (LOW, a FIFO passphrase file hangs open()), SEC-74 (LOW, secrets.enc lost update / shared tmp name), SEC-75/76 INFO. All owned by orchestrator (secret_backends.py/config.py). Strict xfails in tests/test_qa_secret_backends_review.py (657d770). Remove each marker when its fix lands. SEC-70/71 should land before `freemyid secrets migrate` is user-facing.
- CI markers (9d387f7): conftest `pytest_collection_modifyitems` skips windows_only/posix_only/macos_only/linux_only by sys.platform. New conftest-registered `real_scheduler` marker runs only with CI=true and an OS marker. CR: add `real_scheduler` to pyproject markers. Autouse `_no_real_scheduler` makes `scheduler._run` raise in every unmarked test, so nothing reaches schtasks/systemctl/launchctl/crontab on a dev machine. The existing `skipif(win32)` mode tests are now `posix_only`. Rendering and fake-subprocess scheduler tests stay cross-platform. New tests/test_scheduler_ci.py has the Windows real task install/status/remove (runs only on the windows-latest runner).
- Left alone: tests/test_scheduler_real.py has another session's uncommitted `[-2]` edit matching their uncommitted render.py (SuccessExitStatus=3). tests/test_social_poster.py belongs to the poster engineer.
- Next: first matrix run on macOS/Windows. Triage red tests into the right OS marker, or fix them if they're real portability bugs.

## 2026-11-08 wave review (Marcus Webb), commit 63a0bd4
- Reviewed da0816e..6a40368. PASS: WO-111 (Docker shown as Planned/not public; shipped items correct), WO-112 (test only, local POSTs only), SEC-98 (no injection via mark_invalid).
- Closed SEC-93d (bc058b3), SEC-95 (6386dd6), SEC-96 (d417e1f), SEC-97 (8ce1069; planted payloads all flagged). SEC-66 stays open (Pages, no headers).
- New: SEC-99 MED (matcher: household member CONFIRMED on city + shared relative; nickname groups cross genders; no age veto) -> automation-engineer, 2 strict xfails in tests/test_qa_wave_20261108.py. SEC-100 INFO (email guard empty-range message), SEC-101 INFO (stacked codings cap), SEC-102 LOW non-security (test_site_build red from 6a40368 legacy faq link to developers/).
- Not done: action SHA re-verification for 2af6f37 (sandbox has no network for git ls-remote).
- Left alone: untracked tests/test_exposure_previous_names.py (another agent's WIP).

## 2026-11-08 re-check (4450775)
- SEC-99/101/102 fixed and verified. New LOW SEC-103 (close-age spouse via cross-gender nickname; 2 strict xfails) and SEC-104 (stored match levels not re-scored; escalation uses them). Full suite at ac559fd: 1359 passed, 2 skipped; ruff clean.

## 2026-11-08 push-candidate review 0afced7..18eaa65 (Marcus Webb)
- Ran: full suite at 4b8361c (2146 passed, 163 skipped, 8 xfailed; web tests SKIPPED because `pnpm build` failed there: checklist freeze_child_equifax had no /protect/ group; fixed in d2d9584). ruff src tests tools clean. Web build + wizard/web tests at 18eaa65: 1 FAIL (test_wo178_step_art_on_how_it_works, added in 18eaa65, page + SVGs land in a0939c8). At 2b3f0f2: build OK, site check OK, 553 passed.
- PASS: SEC-118 fix (636a42d; scan-only/practice all set self.dry_run) -> closed. Exposure score v2 (headline always "on the sites we could check", never "safe"; JSON/CLI/wizard always carry coverage). Upload cap (373bd16, read(limit+1) + len check). OG (names regex-limited, from a dir listing). Repro build + SBOM (all actions SHA-pinned, job permissions least-privilege, no `|| true`, SEC-111 hash checks intact in build.yml and pypi.yml). /more route behind the global token/CSRF guard. Codex/Copilot tests offline, no PII. Step SVGs have no script/handlers/external refs. actionlint not available; workflows reviewed by hand.
- SEC-119 MED (Morgan): .github/workflows/claude.yml runs on @claude comments on PRs (issue_comment, pull_request_review_comment). claude-code-action checks out the PR head for PR events, so a fork PR's own `.claude/settings.json` (hooks run shell commands regardless of --disallowedTools) and CLAUDE.md would be loaded with CLAUDE_CODE_OAUTH_TOKEN and a pull-requests/issues: write token in the environment. Not verified against the action source at c0949c50 (no network). Fix before this goes live: skip PR events (`github.event.issue.pull_request == null`, drop pull_request_review_comment) or pass `--setting-sources user`; close as INFO if the pinned action is shown to restore .claude/ and CLAUDE.md from the base branch. Also the header says the label works on PRs, but only `issues: labeled` is wired.
- SEC-120 LOW (Morgan): tools/pm_sync.py apply_plan adopts any issue whose title starts with "KEY:" (public repo: anyone can open "WO-200: ..." first and it gets added to the Project, closed and commented on). Filter by author (owner/bot logins) before adopting.
- SEC-121 INFO (Dana): twine is installed unpinned/unhashed next to the hash-checked toolchain (build.yml dist, pypi.yml build); anchore/sbom-action downloads syft v1.18.1 at runtime without a hash. Pin twine in build-requirements.txt.
- Re-check beaf662 (Marcus Webb): SEC-119 closed (7c83c81: issues/issue_comment only, both gated on `issue.pull_request == null`, review-comment trigger gone, so no PR-head checkout). SEC-120 closed (beaf662: adopt only when author login is in FREEMYID_PM_TRUSTED; test_pm_sync 13 passed). INFO: claude.yml can drop `pull-requests: write` now that PRs are not handled.

## 2026-11-08 CodeRabbit inline findings, PRs #55/#57/#60/#61 (Marcus Webb, branch inhouse/fix-review-minor)
37 inline comments, 21 unique once duplicates are merged. Each was checked against the current file at 2f525b7/cfc273d, not the reviewed commit. Result: 17 VALID and fixed, 1 ALREADY FIXED, 0 INVALID, 3 out of scope (handled elsewhere). 21 unique findings in total.

| # | Finding (dupes) | File:line now | Class | Commit |
|---|---|---|---|---|
| 1 | Bank/card regex crosses passages (`.*` + DOTALL). HELPER_GUIDE and /families/ only passed this way (#55) | tests/copilot/test_cp_never_asks_parity.py:24-28 | VALID | d2a1365 |
| 2 | FAMILY_QUICK_START.md missing from the core-concept test (#55) | test_cp_never_asks_parity.py:80-88 (skip while absent) | VALID | d2a1365 |
| 3 | Bare "passwords" passes if any allowed phrase is in the same sentence (#55) | test_cp_never_asks_parity.py:38-45, 108 | VALID | d2a1365 |
| 4 | Truncated HTTP error body: IncompleteRead escapes `api()` (#60, #61) | tools/cloudflare_redirects.py:51; main() moved behind `__name__` so it can be tested | VALID | 1ef1981 |
| 5 | Adopted closed issue stays closed for an open item (#55, #57) | tools/pm_sync.py:462-468 | VALID | a1880e0 |
| 6 | Adoption skips labels, milestone and mirror body (#57, plus SDLC.md:64 #55) | pm_sync.py:452-461 (add-label, milestone, mirror as a comment, opener's text kept); docs/SDLC.md:64 | VALID | a1880e0, 311ecea |
| 7 | `gh issue list` default 30 and dict result shape (#60 :431, #61) | pm_sync.py:437-443 (`--limit 200`, list guard) | VALID | a1880e0 |
| 8 | SDLC "Codex never edits those folders" ignores Codex-owned subtrees (#55, #60) | docs/SDLC.md:70 | VALID | 311ecea |
| 9 | Approved exports moved, not copied (#60) | brand/codex/MANIFEST.md:3, docs/SDLC.md:70 | VALID | 311ecea |
| 10 | Design-only WOs never close in the tracker (no Merge WO-NNN) (#55) | channel CLAUDE_TO_CODEX.md:449 kept as record; rule in docs/SDLC.md Canva section; test | VALID | 19ff20c |
| 11 | No single writer for brand/codex/MANIFEST.md with parallel design WOs (#55) | channel :476 kept as record; rule in docs/SDLC.md Canva section | VALID | 19ff20c |
| 12 | `mark-dark.svg` is badge-only, not a dark wordmark lockup (#55 :10, #57 :69, #60 :129, #61 :10) | docs/design/CANVA_BRIEFS.md:10, 69, 129 | VALID | 444553b |
| 13 | CB-04 alt text differs from the WO-177 card (#55 :104) | CANVA_BRIEFS.md CB-04 alt (now points to WO-177) | VALID | 444553b |
| 14 | WO-177 overrides the list but not the alt text (#55, #57, #60, #61) | docs/vendor/WO-177.md:34 | VALID | ba4a100 |
| 15 | WO-175 Windows claim: release.yaml has no OS versions; no fallback headline or alt (#55, #57) | docs/vendor/WO-175.md:34 (source is download page; fallback headline + alt) | VALID | ba4a100 |
| 16 | CBS-01 sample output is not what `freemyid status` prints (#57, #60) | docs/design/CANVA_BRIEFS_SEO.md:32-33 | VALID | 444553b |
| 17 | CBS-03 "No account needed" is wrong for account_required guides (#55) | CANVA_BRIEFS_SEO.md:57 | VALID | 444553b |
| 18 | SEC-118 marked "in review" but missing from the handoff (#55) | docs/pm/tracked.json:47-51 is now `closed`; handoff has SEC-118 (this file, 0afced7..18eaa65 section) | ALREADY FIXED | n/a |
| 19 | runner.py:506/509 manual state through scan (MAJOR, #55 #57 #60 #61) | src/freemyid/engine/runner.py | OUT OF SCOPE (another engineer) | n/a |
| 20 | FRIDGE_CARD.md:17 test MAJOR (#57) | docs/FRIDGE_CARD.md | OUT OF SCOPE (fixed in 6deb3e8) | n/a |
| 21 | USER_GUIDE.md:84 test before trust prompt (#60) | docs/USER_GUIDE.md | OUT OF SCOPE (Jordan's branch) | n/a |

- Context for rows 10-12: the owner moved WO-170..179 in-house (CLAUDE-030, brand/README.md:44), so no Codex MANIFEST rows exist yet. The fixes still apply to future Codex design WOs and to the briefs Iris works from.
- For the orchestrator: WO-170..179 still say `Status: open` although Iris delivered several in-house. Set `Status: done (<delivery commit>)` per the new SDLC rule so pm_sync closes #137/#138/#142/#143/#144.
- For the Codex lead (BACKLOG line 14 note): brand/codex/MANIFEST.md:3 had a one-line wording fix (copy, not move), made at the orchestrator's request.
- Tests: tests/test_pm_sync.py (17), tests/test_cloudflare_redirects.py (new, fails without the fix), tests/copilot/test_cp_never_asks_parity.py (2 new self-tests). The FRIDGE_CARD strict xfail is unchanged ("never charges you" is still missing there).
- Results at 19ff20c: full suite `PYTHONPATH=src pytest -q` 2207 passed, 175 skipped, 1 xfailed (FRIDGE_CARD strict xfail); affected tests 442 passed, 32 skipped, 1 xfailed; `ruff check src tests tools` clean.
