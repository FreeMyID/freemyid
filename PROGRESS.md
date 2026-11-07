# Free My ID — Progress

## Phase 1 — Plan ✅ (approved 2026-11-05; orchestrator given full autonomy)
## Phase 2 — Scaffold ✅
Models, state machine, encrypted store (AES-GCM blobs, key in keyring, append-only events), registry loader/updater with schema validation, network allowlist, PII-redacting logs, CLI skeleton, agent contracts. Legacy kit moved to `zzz_legacy/`; its match rules, data-minimization and permission flags were folded into the models.
## Phase 3 — Parallel build 🔄
- broker-researcher: registry + state laws
- automation-engineer: engine + first 10 submitters
- wizard-packager: wizard, dashboard, scheduler, packaging
- qa-security: scaffold review + test suite
- Peer sessions: 9e README + USER_GUIDE ✅ (committed 8a9cab6); 85 broker agent policies 🔄; cf long-tail brokers 🔄
## Phase 4 — Security fixes 🔄 (2026-11-05)
- Done (924a79b): SEC-01 state/escalation, SEC-02 ids+paths, SEC-03 full delete, SEC-05 registry fetch, SEC-07 broker hosts, SEC-08 submitter ns, SEC-09 netpolicy, SEC-11 append-only.
- In progress: SEC-04/10/13 (peer e6, stopping), SEC-06/12/14 consent+cli (peer e8, stopping); qa-security updating tests for new id rules.
- User priority: one-click **Windows** installer + very simple wizard for non-technical older users (wizard-packager).
## Phase 5 — v1 re-plan + build wave 🔄 (2026-11-06, see docs/PLAN_V1.md)
- Review: no runner/submitters yet; 58/63 brokers are bot-protected web forms; packaging not started.
- Decision: 3 tiers (Email auto / Assisted "do it with me" / Automatic browser for verified only); mailbox optional; CA DROP first; Edge + pywebview + PyInstaller + Inno Setup per-user; GitHub Actions builds the exe.
- Running: automation-engineer (runner, tiers, submitters), wizard-packager (6-screen wizard, dashboard, launcher, schtasks, packaging, CI), broker-researcher (privacy emails, plain steps, 3-5 verified forms), qa-security (test/lint fixes, e2e dry-run scaffold).
## Blocked / decisions
- GitHub repo: github.com/FreeMyID/freemyid (private, pushed 2026-11-06). An old empty personal repo can be deleted.
- Code signing: user decided 2026-11-06 to ship unsigned (close family only; user helps install, SmartScreen warning OK).
- License: AGPL-3.0-or-later for the app (decided 2026-11-06, open-source + paid subscription model). Registry data: separate license, TBD (brokers/LICENSE-DATA.md). Repo stays private until rename + public launch.
- Outlook.com mailboxes need OAuth (basic auth retired); v1 supports Gmail app password, Proton Bridge, other IMAP providers.
## Next
Integrate wave → qa review → GitHub repo + first CI exe build (user OK needed) → test on a Windows 11 VM → dry run on a family profile.

## Checkpoint 2026-11-06 ~09:30 (usage limit reached)
- Done: v1 engine + wizard + packaging; 428 brokers; state_laws; SEC-15..29 fixed; AGPL; CI green incl. Windows silent install/uninstall test (run 42232871017).
- Windows test VM: ~/VMs (quickemu; SSH via ~/VMs/vmssh; clean snapshot `clean-ssh-ready`, reset with ~/VMs/reset-clean.sh; GL off). Fixed installer copied to VM Downloads with MOTW; SmartScreen screen confirmed.
- In progress: hands-on install through SmartScreen. Mouse via HMP is relative+accelerated; next: add QMP socket (extra_args) for absolute clicks, or keyboard focus.
- Next: finish VM install + 6-screen wizard walkthrough with screenshots; D9/D10 "fill it in for me"; rename; mypy warnings (24).

## Session 2026-11-06 afternoon (orchestrator)
- Done: mypy 31 -> 9 (0d77063); D9 Fill it in for me engine (1255acd); contracts for D9/D10 + `freemyid fill` (c8b8b80).
- Windows VM walkthrough (fresh install of CI build 42233985711 on clean snapshot, QMP absolute clicks via scratchpad qmp.py; `extra_args` QMP socket added to ~/VMs/windows-11.conf):
  - SmartScreen -> More info -> Run anyway works; installer appears ~10 s later with no feedback.
  - **BLOCKER fixed (54ff105):** wizard step 1 POST -> "Bad origin". Referrer-Policy no-referrer makes Chromium send `Origin: null`. Reproduced + verified in headless Chromium. TestClient never sends Origin -> real-browser e2e test added (qa).
  - Window larger than 1024x768 screen; dir/ready pages unnecessary; default Python icon; consent copy mentions mailbox as if required. -> wizard-packager.
- Running: wizard-packager (window fit, friendly error pages, installer pages+icon, consent copy, D9 button), qa-security (browser e2e, adopt D9 tests, D9 security review), automation-engineer (D10 listing finder, engine mypy, wire new Broker fields).
- Next: integrate -> push -> CI exe -> redo VM walkthrough through all 6 screens + dashboard + a fill-for-me on a fixture; broker-researcher: success_text/listing patterns for verified web-form brokers.

## Checkpoint 2026-11-06 evening (quota ~97%)
- Committed: D9 SEC-30..33 fixes (xfails removed), PLAN_V1 registry-distribution decision + feed-token no-PII rule.
- NOT public yet: history still holds zzz_legacy/ and the full brokers/registry.yaml. User decisions: drop both from history (filter-repo, force-push with user OK), sample-only public registry (CC BY-NC 4.0).
- In flight: automation-engineer registry split (uncommitted, see docs/handoff/automation-engineer.md "Registry split").
- Next session: install git-filter-repo (.venv) + gitleaks (blocked by auto-mode, needs user OK) -> filter-repo fresh clone -> gitleaks -> force-push (ask) -> CI green -> tag v0.1.0 -> VM check -> ping data-removal-f8 for site re-check -> flip public + Pages.

## Session 2026-11-06 night (orchestrator)
- Registry split: brokers/registry.yaml + docs/research/{broker_policies,broker_candidates}.md + success_signals.yaml untracked (gitignored, kept on disk). Load order now update > family (registry.yaml beside the exe) > bundled full > sample; size cap on load.
- Old repo handles removed at HEAD. History scrub dry run by peer d7: 0 gitleaks findings; family states found in OLD history and rewritten; handles, example email and research files added to the rules.
- Full suite hung in a Playwright test (no browser launched); qa-security fixing in tests/.
- Next: qa green (with and without full registry) -> commit split -> d7 re-runs scrub -> force-push (user OK) -> CI -> tag v0.1.0.

## LAUNCH 2026-11-06 ~19:19 EST: repo PUBLIC
- Fresh repo FreeMyID/freemyid (cleaned history: no full registry, zzz_legacy, family states, handles, private host hashes; all commits "Free My ID" + noreply; gitleaks 0). Old repo = FreeMyID/freemyid-old (private, archived; still holds 5 CI artifacts WITH the full registry -> delete).
- Pages live: https://freemyid.github.io/freemyid/. README license fixed (AGPL code, CC BY-NC data). Topics/description/labels set.
- Registry hardening 42d44ee (alias bomb, fallback chain, opt-in full bundling + CI sample assert, family registry via iscc define).
- BLOCKER for v0.1.0: SEC-39 fill-for-me freezes on normal form-POST submit (automation-engineer fixing). qa test fixes (hang guard, browser probe, 13 registry tests, adopted _test_drafts) applied in tree, to commit after a green run; then delete src/freemyid/engine/_test_drafts/.
- Next: SEC-39 fix -> qa commit -> CI green (add playwright install + FREEMYID_REQUIRE_BROWSER=1) -> tag v0.1.0 -> release.yaml for site -> VM walkthrough. User: social preview upload, old-repo artifacts, collaborator re-invite, trademark.

## Wave 2026-11-07 (orchestrator data-removal-5e): post-v0.1.0 polish
- Baseline: 432 passed, ruff + mypy clean, v0.1.0 released, CI green. 92 local commits unpushed (website v2 from peer data-removal-46): push needs user OK.
- Rulings: SEC-38 accepted as designed + one-time practice-mode "real request" confirm; SEC-41 accepted (peer) + reshoot from sample-only brokers anyway.
- Running: wizard-packager (SEC-38, Windows VM walkthrough of v0.1.0 + real screenshots, "Click Install" check), automation-engineer (SEC-27 first-email approval, reply-matcher edge cases), broker-researcher (sample re-verify, web-form success signals, state laws), web-developer (release 0.1.0 info + checksum, WR-8, leftovers), brand-marketing (claims audit, README, launch-week drafts), graphic-designer (SEC-41 reshoot, social preview), qa-security (SEC status table, tools/registry_health.py, review of this wave).
- 2026-11-07 user request: site v3 = Tailwind + shadcn/ui + Magic UI/Aceternity. Decision: Astro static + React islands in web/, branch site-v3 (worktree), no-JS parity, calm motion (reduced-motion off), CSP script-src 'self', no runtime third parties, budgets 300 KB first view / 80 KB JS / 20 KB CSS. Old site_src/ stays live until v3 passes web-qa + qa-security (incl. npm supply-chain review). graphic-designer making brand/v3/ assets.
- 2026-11-07 ~11:55: PUSHED main (user OK) incl. website v2, R13 release info, SEC-38, SEC-41, SEC-46 fix. "Tell us what confuses you" -> GitHub issue chooser (user decision).
- VM walkthrough v0.1.0 (wizard-packager): all 6 screens OK, screenshots in brand/screenshots/vm-v0.1.0/ (reviewed: fake data only). Ready page shows despite DisableReadyPage -> ShouldSkipPage fix, unverified until next CI build. UX follow-ups dispatched.
- Decision (user deferred to O): after v3, app + installer reuse the v3 LOOK (shared tokens.css, type, icons, illustrations, Inno wizard images) but NOT the stack: app stays server-rendered HTML, no React/Tailwind runtime, no motion.
- 2026-11-07 wave close: qa-security PASS for v0.1.1. SEC-01..49: 45 fixed, 4 accepted, 0 open, no strict xfails. 508 passed (505 + 3 skipped without full registry), ruff + mypy clean. tools/registry_health.py + weekly offline CI (registry-health.yml). Engine: SEC-27 first-email gate, reply matcher hardening, ID-request -> human todo, escalation timer fixes. Wizard: SEC-38 confirm, consent <details>, first-run dashboard copy, toast icon, CR-W1. Site: release 0.1.0 info, WR-37/38, SEC-49, families "never sent" claim corrected.
- Next: CI exe from main -> VM re-check (Ready page skipped? toast icon? consent at 1024x768) -> propose v0.1.1 tag to user. Site v3 (web-developer, branch site-v3) still running. CR-M1 Request.held_reason deferred. Open user Q: "relatives" home card needs a source or goes.
- 2026-11-07 decision: ONE installer (x64). Covers x64 Win10/11 natively and Windows 11 on ARM via Prism emulation. No 32-bit (Win11 has none, Win10 EOL Oct 2025, Playwright has no 32-bit Windows) and no native ARM64 build for now (revisit only if ARM users report problems; GitHub has windows-11-arm runners). Installer gets ArchitecturesAllowed=x64compatible so unsupported Windows gets a clear message. Site download page should say "64-bit Windows 10 or 11 (Windows 11 on ARM works too)": web v3.
