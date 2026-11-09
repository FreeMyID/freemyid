# Free My ID: three-team backlog (v0.3 → v0.5)

Owner: Morgan Reyes (in-house project engineer). Co-planned with Nora Bennett (Codex PM) and Grace Holloway
(Copilot project engineer): they add items to their own lane through CP-/GP- proposals; Morgan turns accepted items
into work orders. Started 2026-11-08. Source: docs/ROADMAP.md sections 3-6, docs/SECURITY_REVIEW.md, open WR rows.

## Lanes (who may touch what) — the collision rule

Every path belongs to exactly one lane (one temporary exception: see the Copilot-out note under the table). A work order may only list paths in its own lane. BOARD.md stays the per-WO
guard; this table is the standing split so bulk work never collides.

| Lane | Team | Owns (write) | Never touches |
|---|---|---|---|
| **IN** | In-house (Claude agents) | `src/`, `schema/`, `brokers/`, `installer/`, `.github/`, `tools/`, `site_src/`, `web/` (except the vendor subtrees below), `brand/`, `docs/` (except the vendor subtrees below), existing `tests/test_*.py` | `tests/codex/`, `tests/copilot/`, `brand/codex/`, `docs/dev/`, `docs/i18n/`, `distro/`, `docs/user/`, `docs/USER_GUIDE.md`, `docs/CLI.md`, `README.md`, `web/src/components/ui/`, `web/src/components/CopyHash.astro`, `web/src/pages/developers/` (changes there go to the owning team as a request; a one-line fix that must ship with in-house code is noted to the owning lead in the channel) |
| **CX** | Codex team (Nora) | `tests/codex/` (new test suites), `docs/dev/` (developer & architecture docs), `docs/i18n/` (translation prep), `web/src/pages/developers/` (developer site section), `brand/codex/` (Canva design exports + `MANIFEST.md`; in-house graphic-designer promotes approved files into `brand/`, `web/` or the app) | `src/`, everything in IN or CP |
| **CP** | Copilot team (Grace) | `tests/copilot/` (new test suites), `distro/` (community Homebrew/AUR/Nix/Flatpak/winget/Scoop recipes; `packaging/` is the real installer and stays in-house), `docs/user/` (end-user how-tos), `docs/USER_GUIDE.md`, `docs/CLI.md`, `README.md`, `web/src/components/ui/` + `web/src/components/CopyHash.astro` (a11y fixes from audits) | `src/`, everything in IN or CX |

**Until December 2026 (owner, 2026-11-08): the Copilot team is out.** Every CP lane (`docs/user/`, `docs/USER_GUIDE.md`, `docs/CLI.md`, `README.md`, `web/src/components/ui/` + `CopyHash.astro`, `distro/`) and maintenance of `tests/copilot/` move to **IN**. New test suites that would have been CP go to **CX** (Codex). `tools/copilot.sh` and its watcher stay off until the credit reset; Copilot work orders reopen in December. Until then this is the one exception to the "Never touches" column for IN and to the vendor-subtree rule below: IN may write those moved CP paths, and no work is assigned to CP.

Rules: vendors never change product code (`src/`); a vendor test that finds a real bug ends in a strict xfail plus a
SUM-/SEC- row for in-house. In-house agents stay out of vendor subtrees (except the temporary CP-to-IN move above). Cross-lane needs go through the channels.

---

## IN — in-house (Claude agents)

### Engine / automation-engineer (Theo)
- BL-IN-01 Exposure scan across the full registry: cached, rate-limited, per-broker adapters (0.3).
- BL-IN-02 Exposure score 0-100 with coverage (checked / by hand / uncertain), trend over time (0.3).
- BL-IN-03 State-law letters per state (CCPA/CPRA, VA, CO, TX, OR, CT, UT...) with statute cited; generic fallback (0.3).
- BL-IN-04 California DROP integration flow (0.3).
- BL-IN-05 Relist detection with per-broker cadence learned from history (0.4).
- BL-IN-06 Broker monitoring: weekly headless check that each opt-out page still works, flag changes (0.4).
- BL-IN-07 Legal escalation pack: prefilled AG/CPPA complaint when a broker ignores a lawful request (0.4).
- BL-IN-08 Phone-only and email-only removal mode (0.4).
- BL-IN-09 Outlook / Microsoft 365 OAuth device-code mail (0.4).
- BL-IN-10 Escalation timing vs the 45-day legal window (Priya's note: day-18 follow-up cites law early) — decide + fix.
- BL-IN-11 SEC-103/104 matcher (in progress).

### App / wizard-packager (Nina)
- BL-IN-20 Proof vault: per broker, every email/screenshot/confirmation, dated and hashed (0.4).
- BL-IN-21 One-page PDF "what we did for you" report (0.4).
- BL-IN-22 Read-aloud and large-text mode across the wizard (0.4).
- BL-IN-23 Tray icon with status and "check now" (0.4).
- BL-IN-24 "Set it up for someone else" helper bundle flow polish (0.4).
- BL-IN-25 Monthly progress toast/summary (0.4).
- BL-IN-26 Map of exposure grouped by site type (0.4).
- BL-IN-27 Windows VM checks: silent uninstall while running; Bridge-off wording (owner VM).
- BL-IN-28 Installer 10-second silent gap fix ("every wait has a reason").
- BL-IN-29 i18n plumbing: extract wizard strings into a catalogue (prepares Spanish, 0.5). Codex CX-I18N docs feed this.

### Platform / devops-engineer (Dana)
- BL-IN-40 Push f324bfd (Windows CI bash fix) and verify.
- BL-IN-41 SEC-66: CSP header via the Cloudflare transform rule, mirroring the meta CSP + frame-ancestors.
- BL-IN-42 Reproducible builds + published SBOM (0.3).
- BL-IN-43 .deb/.rpm/AppImage packages in CI (0.4) — CP writes recipes in distro/, Dana wires CI.
- BL-IN-44 PR #24 cosign v4 at next pre-release.
- BL-IN-45 Serve BingSiteAuth.xml; GHCR public (owner).

### Orchestrator (Morgan)
- BL-IN-60 SEC-108 full fix: builders in a separate clone, not a linked worktree.
- BL-IN-61 SEC-109: `--no-renames` in scope checks, print previous_filename.
- BL-IN-62 Copilot builder shell refused in non-interactive runs: find the sandbox approval setting.
- BL-IN-63 Contracts for BL-IN-02/05/20 (models + schema).

### Research / broker-researcher (Priya)
- BL-IN-70 Whitepages processing time verified in a browser (blocked to tools).
- BL-IN-71 Credit-freeze specifics: Innovis, ChexSystems, NCTUE, LexisNexis, protected-consumer freeze.
- BL-IN-72 Data-broker registry states (CA, VT, OR, TX) cross-check for unknown brokers (0.5 prep).
- BL-IN-73 Address confidentiality program guidance by state (0.4).
- BL-IN-74 IRS IP PIN, SSA lock, USPS Informed Delivery checklist sources (0.4).

### Web / brand / growth (Leo, Jordan, Iris, Sam)
- BL-IN-80 /whats-new/ after the 0.3 release (WR-74).
- BL-IN-81 Guides for the 10 most-searched brokers not yet covered (sources first).
- BL-IN-82 Article A/B/C drafts → pages after features ship.
- BL-IN-83 Summary screenshot fix ("sent 0" next to "7 confirmed").
- BL-IN-84 Ready-to-send listings queue (owner approves).

---

## CX — Codex team (bulk, see WO-127..WO-138)

Tests (tests/codex/, new files only; real bugs → strict xfail + report):
- CX-01 Fuzz/property tests for the reply matcher (mail parsing edge cases, encodings, quoted replies).
- CX-02 Property tests for the registry loader and schema validation (malformed YAML, size caps, unknown keys).
- CX-03 Prefill/import bundle robustness tests (wrong passphrase, truncated, tampered, oversized).
- CX-04 YAML `setup --from` config tests against schema/ (every field, every invalid shape).
- CX-05 CLI `--json` contract tests: every read command emits one JSON object, documented exit codes.
- CX-06 App accessibility sweep: every wizard/dashboard screen with keyboard-only + axe-style checks (offline).
- CX-07 Matcher name-variant tests (nicknames, hyphenated, suffixes, diacritics) as a table-driven suite.
Docs (docs/dev/, docs/i18n/):
- CX-08 docs/dev/ARCHITECTURE.md: module map, data flow, trust boundaries (from code, cite file:line).
- CX-09 docs/dev/CONTRIBUTING_BROKERS.md: how to add/verify a broker entry and a submitter.
- CX-10 docs/i18n/: string inventory of the wizard + Spanish glossary for privacy terms (no product edits).
Developer site (web/src/pages/developers/):
- CX-11 /developers/cli/ reference generated from Click introspection data checked into the page.
- CX-12 /developers/config/ YAML schema reference page from schema/.

## CP — Copilot team (bulk, see WO-139..WO-150)

Packaging (distro/, recipes only; CI wiring stays in-house):
- CP-01 Homebrew tap formula (pipx-style, from the PyPI sdist).
- CP-02 AUR PKGBUILD.
- CP-03 Nix flake.
- CP-04 Flatpak manifest (draft; desktop app later).
- CP-05 winget + Scoop manifests for the Windows installer.
End-user docs (docs/user/, USER_GUIDE, README, CLI.md):
- CP-06 docs/user/ how-tos: Gmail app password, Proton Bridge, Outlook (current state), with plain steps.
- CP-07 USER_GUIDE timeline wording per docs/research/timeline-claims-2026-11.md (lines 248/250).
- CP-08 docs/user/ troubleshooting: the 15 most likely errors and what to do (from source strings).
- CP-09 docs/CLI.md refresh for CLI-A04 (`--prefill` implies terminal) and `search-engines`.
Tests + UI a11y (tests/copilot/, web/src/components/ui/):
- CP-10 tests/copilot/ docs-match-source guards (every command in docs exists; every flag documented).
- CP-11 Remaining contrast-audit items (CA-2, CA-3...) in web/src/components/ui/.
- CP-12 tests/copilot/ packaging recipe lint (versions match pyproject, sha fields present).
