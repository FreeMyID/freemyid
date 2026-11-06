# Vanish — Progress

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
- GitHub repo: the old personal repo (private, pushed 2026-11-06). The empty old personal repo can be deleted.
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
- Done: mypy 31 -> 9 (0d77063); D9 Fill it in for me engine (1255acd); contracts for D9/D10 + `vanish fill` (c8b8b80).
- Windows VM walkthrough (fresh install of CI build 42233985711 on clean snapshot, QMP absolute clicks via scratchpad qmp.py; `extra_args` QMP socket added to ~/VMs/windows-11.conf):
  - SmartScreen -> More info -> Run anyway works; installer appears ~10 s later with no feedback.
  - **BLOCKER fixed (54ff105):** wizard step 1 POST -> "Bad origin". Referrer-Policy no-referrer makes Chromium send `Origin: null`. Reproduced + verified in headless Chromium. TestClient never sends Origin -> real-browser e2e test added (qa).
  - Window larger than 1024x768 screen; dir/ready pages unnecessary; default Python icon; consent copy mentions mailbox as if required. -> wizard-packager.
- Running: wizard-packager (window fit, friendly error pages, installer pages+icon, consent copy, D9 button), qa-security (browser e2e, adopt D9 tests, D9 security review), automation-engineer (D10 listing finder, engine mypy, wire new Broker fields).
- Next: integrate -> push -> CI exe -> redo VM walkthrough through all 6 screens + dashboard + a fill-for-me on a fixture; broker-researcher: success_text/listing patterns for verified web-form brokers.
