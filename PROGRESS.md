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
## Blocked / decisions
- Registry GitHub repo URL: not set yet (placeholder).
- Code signing for macOS/Windows: undecided (ship unsigned + Quick Start instructions for now).
- License: pyproject says MIT but there is no LICENSE file; user to confirm (MIT default).
- Outlook.com mailboxes need OAuth (basic auth retired); v1 supports Gmail app password, Proton Bridge, other IMAP providers.
## Next
Phase 4 QA fixes → Phase 5 integration + dry run against the user's profile.
