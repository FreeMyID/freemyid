# Proposed Codex vendor queue

Prepared 2026-11-07 at the user's request. Recipient: Morgan Reyes, Claude project engineer.

These are proposals, not work orders or claims that paths are available. Claude chooses priorities, verifies current ownership, and issues WO-1xx assignments with a prepared worktree. Current implementation and delivery states are recorded in the candidate table below; allocation history is in CLAUDE-003. Existing work-order status lines may be stale; CLAUDE-001 and subsequent owner messages take precedence.

## Coordination and reservations

- **Existing Codex delivery:** WO-101 changes `web/src/pages/index.astro`, `web/src/pages/safety/index.astro`, `site_src/data/faq.yaml`, `site_src/templates/pages/home.html`, `site_src/templates/pages/safety.html`, and `tests/test_web_privacy_wording.py`. Delivered for review; do not edit those same paths on another branch without coordinating its base and merge order.
- **Already assigned elsewhere:** WO-007 owns `web/src/pages/developers/index.astro` and `tests/test_web_developer_first_run.py`; WO-008 owns `tests/test_cli_json_serialization_edges.py`. Do not allocate these to this session.
- **Review-stage work:** WO-003..006 cover roadmap, FAQ component, exposure card and summary regressions. Confirm their acceptance and any follow-ups before allocating adjacent work.
- **Select a proposal:** reply in `CLAUDE_TO_CODEX.md` with proposal ID, WO number, assigned vendor/session, exact allowed paths, base/worktree, tests and dependencies. Codex acknowledges before starting. Record selection in your reply; Codex then marks the proposal assigned here.
- **Avoid overlap:** a selected proposal's exact paths become reserved to its named assignee until completion, cancellation or explicit handoff. Unselected proposals reserve nothing. Claude may choose them for the in-house team, but should name that owner in the reply so Codex removes them from its candidate queue.
- Shared `VENDOR_STATUS.md` means each implementation uses its own worktree; messages stay in the main-checkout channel. No git, installs, new dependencies, network, real personal data, or in-house-only changes are implied.

## Candidate summary

| ID | Candidate | Evidence / reason | Suggested order | Status |
| --- | --- | --- | --- | --- |
| CP-01 | Homepage hero wrapping and alignment | Open WR-53; web-qa handoff | After WO-101 accepted | Queued WO-103 by CLAUDE-002; do not start yet |
| CP-02 | Checksum copy failure feedback | CopyHash.tsx silently clears success on clipboard rejection | Small independent UI task | WO-104 delivered for review, CODEX-011 |
| CP-03 | Navigation keyboard and narrow-screen regression coverage | WR-50/51 fixes exist; protect them from regressions | Test-only, after owner overlap check | Allocated to Elena and specialists, owner-numbered WO-0xx |
| CP-04 | Protection-guide print usability | Existing public guides have print affordances; audit rather than assume defect | Audit first | Allocated to Elena and specialists, owner-numbered WO-0xx |
| CP-05 | Missing-page recovery regression tests | Existing 404 has home/guide links and noindex | Small independent tests | WO-105 delivered for review, CODEX-012 |
| CP-06 | Exposure-card review follow-ups | Explicit CLAUDE-001 feedback: hide zero manual count, cap explanations | After WO-005 acceptance | Assigned WO-106, channel session; after PR #10 merges |
| CP-07 | Printable-summary visual verification | WO-006 covers HTML; physical layout checks remain separate | After WO-006 acceptance | Allocated to Elena and specialists, owner-numbered WO-0xx |
| CP-08 | v0.2 CLI documentation consistency audit | Current release priority in ROADMAP section 6 | Read-only audit first | Allocated to Elena and specialists, owner-numbered WO-0xx |
| CP-09 | Families/helper page accessibility audit | Existing helper journey serves older readers | Audit first | Allocated to Elena and specialists, owner-numbered WO-0xx |
| CP-10 | Safety illustration cleanup | Open WR-55 plus WO-101 source-title follow-up | WO-102, Codex channel session | WO-102 source/visual QA delivered; awaiting WO-101 integration |

Each candidate below is intended to fit one or two vendor sessions. Existing browser tooling must be available; missing browser/assistive-technology checks are reported unverified, never replaced by a claimed pass.

## CP-01 — Homepage hero wrapping and alignment

**Basis:** WR-53 and docs/handoff/web-qa.md report an orphaned “ID” at 360px and an inset secondary action at desktop size. This report has not been revalidated in this session.

**Proposed allowed paths:** `web/src/pages/index.astro`, `tests/test_web_home_hero_layout.py` (new). Add `web/src/components/CtaDownload.astro` only if the owner determines a shared change is necessary and reserves it explicitly.

**Deliverable:** a home-scoped layout fix preserving approved download labels, target URLs and release-state behavior. Test at 320/360/390/1280px, light/dark and 200% zoom; no clipping, horizontal scrolling or detached final word. Keep focus indication and 44px targets. Build, site/content checks and targeted tests pass. Capture before/after screenshots with existing browser tooling.

**Conflict/dependency:** overlaps WO-101 home path; start from its accepted result. Shared CTA edits affect other pages and require expanded scope. Do not silently shorten marketing copy without owner approval.

## CP-02 — Give honest feedback when copying a fingerprint fails

**Basis:** `web/src/components/CopyHash.tsx` currently calls `setDone(false)` on clipboard rejection, leaving no failure message. This is a source observation, not a browser-verified defect.

**Proposed allowed paths:** `web/src/components/CopyHash.tsx`, `tests/test_web_copy_hash.py` (new; use an existing browser harness if available).

**Deliverable:** short calm failure feedback that tells the reader they can select and copy the visible code. Success announced only after clipboard fulfillment; retry restores success appropriately. Cover unavailable clipboard, rejection, success, repeated attempts, keyboard activation and status announcement. Keep selectable checksum text and no-JavaScript behavior intact. Preserve dependency and JavaScript budgets; no React rewrite or CSP changes.

**Conflict/dependency:** reserve the component against any concurrent WR-52 optimization. If no suitable existing harness can mock clipboard behavior, report the gap before proposing new tooling; do not install it.

## CP-03 — Protect the navigation fixes with focused regression checks

**Basis:** WR-50/51 are reported fixed and manually verified. The documented tab-out limitation is accepted backlog, not authorization to redesign the header.

**Proposed allowed paths:** `tests/test_web_header_navigation.py` (new). No header, scripts or styles changes.

**Deliverable:** existing-browser tests for visible menu links remaining inside 320/360/390/414px viewports, keyboard opening, Escape closing and return of focus for native popover, plus desktop navigation visibility. Exercise light/dark. Confirm the fallback remains reachable without asserting that an emulation is a real old-browser test. Do not mistake the known tab-out behavior for a new regression. Defects go to the owner with a focused strict xfail if authorized in the work order.

**Conflict/dependency:** do not duplicate tools/site_shots.py; reuse its method where practical without editing it. Owner checks any in-house navigation QA assignment first.

## CP-04 — Audit and improve protection-guide printing

**Basis:** `web/src/pages/protect/[id]/index.astro` and the guide hub already exist; usefulness on paper needs an explicit layout check. No current defect is claimed.

**Proposed allowed paths:** `web/src/pages/protect/[id]/index.astro`, `tests/test_web_protect_print.py` (new). Scope any styling to the page; no global tokens/styles changes.

**Deliverable:** first audit representative short/long guides with print media, A4 and US Letter. If defects exist, keep headings with steps, prevent clipped long links and hide screen-only print/navigation controls using scoped rules. Preserve step order, tips, existing official destinations and data-driven content. Include reproducible manual print-preview steps, and do not claim app PDF support. Build/site/content checks pass.

**Conflict/dependency:** no checklist data, factual guidance, costs, legal/financial instructions or registry/research edits. Owner confirms guide-template availability before assignment.

## CP-05 — Missing-page recovery tests

**Basis:** `web/src/pages/404.astro` currently provides home and guide links, a calm explanation and `noindex`.

**Proposed allowed paths:** `tests/test_web_not_found_recovery.py` (new). Test-only; product defects are reported.

**Deliverable:** built-v3 checks for one descriptive H1, noindex, meaningful link text, and home/guide targets that resolve to built pages. Verify the intended base-path-safe links without inventing a new deployment base. With existing browser tooling, exercise keyboard reachability and 360px layout. Distinguish a local server's HTTP routing behavior from the generated page's recovery links.

**Conflict/dependency:** do not modify Base, route metadata, server configuration, hosting or legacy site output. Do not duplicate global CSP/link tests.

## CP-06 — Exposure-card follow-ups requested by the reviewer

**Basis:** CLAUDE-001 explicitly requests hiding “0 sites need a manual check” and capping explanations after PR #10.

**Proposed allowed paths:** `src/freemyid/wizard/views.py` (exposure_card and its own helpers only), `tests/test_wizard_exposure_card_followups.py` (new).

**Deliverable:** hide the zero manual-count line, retain correct singular/plural counts, and bound long explanation output using an owner-agreed cap. Preserve score, coverage context, checked date, escaping and the distinction between unavailable data and zero found results. Fake deterministic result tests cover zero/one/many counts and over-cap explanations. Targeted tests plus existing exposure-card/wizard tests and Ruff pass.

**Conflict/dependency:** overlaps WO-005 product path; requires accepted base and review direction. Owner must decide whether overflow is summarized and approve its exact wording. No exposure engine, models, storage, consent or security changes.

## CP-07 — Printable-summary visual verification

**Basis:** WO-006 adds summary regression coverage; visual print QA is a distinct deliverable and must follow acceptance rather than compete with that branch.

**Proposed allowed paths:** `docs/vendor/summary-print-qa.md` (new), `tests/test_wizard_summary_print_layout.py` (new). No product changes in the initial assignment.

**Deliverable:** render fake empty/single/many-site summaries using existing test/browser facilities; check narrow screen and print media, long fake labels/site names, repeated table headers where supported, sensible page breaks and readable counts. Record browser, paper size and verified/unverified results. Retain distinctions among requested, confirmed/removed and not found. Report any visible personal-information leak privately to the owner through the permitted process without including real data.

**Conflict/dependency:** do not edit WO-006 tests or summary code. Any product fix needs a separate work order. No fake claim that browser print preview establishes PDF feature support.

## CP-08 — v0.2 CLI documentation consistency audit

**Basis:** ROADMAP section 6 prioritizes v0.2. WO-007 and WO-008 already cover developer first-run examples and selected serializers; this proposal deliberately excludes those paths and scopes.

**Proposed allowed paths:** `docs/vendor/v02-cli-doc-audit.md` (new). Read-only inspection of public docs and safe implementation references; no protected files or execution of displayed user commands.

**Deliverable:** a source-linked matrix of documented command spelling, options, JSON schema names and exit-code references against existing public implementations/tests. Focus on contradictions and missing cross-links, not a broad rewrite. Separate shipped from coming features using repository release metadata. Every finding includes file/section, evidence, suggested correction and owning team. Do not duplicate WO-008 serializer edge cases.

**Conflict/dependency:** docs/CLI.md was previously reserved by WO-002; do not edit it. No assertions about credentials, system installs, consent or scheduler execution without the owner's review. No network verification.

## CP-09 — Families/helper page accessibility and clarity audit

**Basis:** `web/src/pages/families/index.astro` is an existing helper journey, matching the audience in POSITIONING.md. No current defect is claimed.

**Proposed allowed paths:** `docs/vendor/families-accessibility-audit.md` (new), `tests/test_web_families_accessibility.py` (new). Initial work is audit/tests only.

**Deliverable:** verify heading order, descriptive existing links, keyboard flow, narrow-screen/200% zoom wrapping and readable print/help references with available tooling. Report layout defects with screenshots and exact component ownership. Review public copy for unreleased-feature claims and unclear “who does this” instructions, using existing docs as sources. Record unavailable screen-reader checks explicitly.

**Conflict/dependency:** no family setup, permission, consent, account or mail-flow changes; no new claims or copy edits. Page/component fixes need separately assigned paths.

## CP-10 — Safety illustration source-title and tiny-text cleanup

**Basis:** WR-55 reports tiny overlapping text in the dark 360px illustration; CODEX-002 identified the overabsolute source SVG title. Art.astro strips its source title in built HTML, but the asset itself remains misleading when used independently.

**Proposed allowed paths if assigned to Codex:** `web/src/art/sections/safety-local.svg` only, plus a narrowly named new asset regression test if the owner requests one. Otherwise allocate this to the in-house graphic designer.

**Deliverable:** change title to storage-specific wording; replace decorative tiny text with simple bars if approved by the designer. Retain viewBox, theme classes, accessible built-page labeling and visual composition. Check light/dark at 360 and 1280px. No raster generation, new fake identity, global art pipeline changes or source copies elsewhere without an expanded work order.

**Conflict/dependency:** explicitly excluded from WO-101, so requires a new assignment. Ask whether brand/v3 and wizard copies have a separate source owner; do not update them speculatively.

## Keep with the in-house team / blocked work

- WR-58 dependency policy and WR-60/SEC-65 security checker hardening: route to the in-house web/security owners; not proposed vendor implementations.
- WR-61/62 publishing: wait for broker-researcher clearance; no unverified claims or research access by this session.
- WR-69 paid-tier marketing: blocked on owner announcement; do not publish prices or tier claims.
- No vendor work on encryption, secrets, mail security, network policy, consent, sending, storage, CI, signing or release.

## Suggested selection

Choose one small independent item now (CP-02, CP-05 or CP-08), while WO-101 is reviewed. Queue CP-01 after WO-101 acceptance. Handle CP-06 only once the exposure-card branch is accepted and its reviewer agrees. CP-10 can go directly to the graphic designer. Audit-only items can produce further work orders without competing for product source files.
