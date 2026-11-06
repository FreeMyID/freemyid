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
## Blocked / decisions
- Registry GitHub repo URL: not set yet (placeholder).
- Code signing for macOS/Windows: undecided (ship unsigned + Quick Start instructions for now).
- License: pyproject says MIT but there is no LICENSE file; user to confirm (MIT default).
- Outlook.com mailboxes need OAuth (basic auth retired); v1 supports Gmail app password, Proton Bridge, other IMAP providers.
## Next
Phase 4 QA fixes → Phase 5 integration + dry run against the user's profile.
