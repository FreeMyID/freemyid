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

| CP-14 | Reconcile developer-page release status copy | release.yaml says v0.2.0 published; developer page still says unreleased | After WO-107 merge; feature-by-feature verification | Delivered in WO-111; 13 targeted tests and build/site/content/Ruff pass |
| CP-15 | Browser checks for wizard-step accessibility | wizard-packager handoff says wizard pages lack browser checks/keyboard pass | Test-only; fake values | Delivered in WO-112; 183 pass, 4 strict xfails track in-house SEC-98 until its fix |
| CP-16 | Regression test per-person Protect progress on Today | server/dashboard render per-profile counts, with no two-profile assertion found | Test-only; fake profiles | Proposed; unallocated |
| CP-17 | Narrow TypeScript hardening for public checklist parser | web/src/lib/protect.ts has `any` at untrusted YAML record/list boundaries despite unknown helper signatures | Audit first; one parser only | Queued as WO-113 after WO-111/112 merge (CLAUDE-012/014) |
| CP-18 | Frontend dependency upgrade planning (owner-run) | web-v3/qa-security handoffs identify SEC-67 pnpm audit/Dependabot as open and audit was skipped offline | In-house owner first; Codex may help with compatibility notes after approved versions are supplied | Owner referral; not a vendor implementation assignment |

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

## Next-wave proposals CP-11 through CP-13

Prepared after WO-103/106 delivery, 2026-11-07. Owner allocation required; all proposed paths are unreserved. Checked against BOARD.md and CLAUDE-002/005/007/008. These do not implement Elena's allocated CP-03/04/07/08/09 or edit WO-107's copy paths.

### CP-11 — Quieter, reliable checksum status announcements

**Evidence:** CLAUDE-007 and docs/handoff/web-qa.md review of PR #15 record optional P3s: repeated "Copying…" announcements and a no-clipboard message inserted after hydration that some screen readers may miss. This is owner-reported feedback, not a reproduced assistive-technology failure here.

**Proposed allowed paths:** `web/src/components/CopyHash.tsx`, `tests/test_web_copy_hash.py`, own worktree `VENDOR_STATUS.md`.

**Deliverable:** review the current status lifecycle, retain visible pending feedback while avoiding unnecessary polite announcements, and establish a stable status region before terminal feedback. Preserve unavailable/rejected/success/retry behavior, selectable no-JavaScript fallback, keyboard activation and truthful success timing. Extend existing meaningful browser tests rather than add tooling. Build/site/content checks, download budget and targeted tests pass. Report actual screen-reader validation as unverified unless performed; DOM checks alone cannot prove announcements.

**Collision/dependency:** WO-104 is merged. Recheck CopyHash ownership with in-house before dispatch; no download-page/CSP/build-config/dependency changes. Optional polish, not a release blocker.

### CP-12 — Published download metadata consistency regression tests

**Evidence:** ROADMAP section 6 says only published release plus release.yaml counts as available. `web/src/pages/download/index.astro` renders version, size, fingerprint, release notes and conditional links; `CtaDownload.astro` branches between published asset and coming-soon state. Current tests focus on copy feedback and developer examples, rather than this combined contract. No metadata defect is claimed.

**Proposed allowed paths:** `tests/test_web_download_metadata.py` (new), own worktree `VENDOR_STATUS.md`.

**Deliverable:** inspect the existing built /download/ and its current checked-in public release/site data. Assert displayed version, optional size/fingerprint, internal checksum fragment, and primary CTA destination agree with the current configuration; test only applicable current branch and clearly state coverage limits. Check the unreleased branch only if an existing isolated harness supports it without editing release data or configuration. No arbitrary exact marketing-text pins, duplicate global link/CSP checks or invented prerelease publication status. stdlib/YAML parsing and existing tooling only. Clearly require built output; `test_web_` prefix uses existing CI convention; Ruff and targeted tests pass.

**Collision/dependency:** test-only, disjoint from active WO-107 and Elena's test paths. Owner retains release.yaml/site data, workflows, release and publishing. A tag by itself must not be treated as a stable release. Report mismatch to owner rather than fix publication metadata.

### CP-13 — FAQ keyboard and zoom interaction regression coverage

**Evidence:** WO-004 is merged. `tests/test_web_faq_accessibility.py` checks native details markup, IDs/open state and token contrast, but does not exercise actual keyboard toggling/focus and wrapped content in a browser. ROADMAP v0.3 includes accessibility. This is a coverage proposal, not a newly observed defect.

**Proposed allowed paths:** `tests/test_web_faq_keyboard.py` (new), own worktree `VENDOR_STATUS.md`.

**Deliverable:** offline existing-browser tests of representative home and /faq/ disclosures with JavaScript disabled: Tab focus, visible focus indicator, Enter/Space expansion and collapse, answer visibility and reachable answer links. Exercise narrow light/dark views and explicitly modeled 200% reflow; distinguish equivalent viewport checks from native toolbar zoom. Assert no clipped question/answer text or horizontal overflow. Reuse current built metadata and avoid repeating static-markup/contrast tests. No dependencies or network requests; build/site/content and focused tests pass. Report product defects for separate owner-scoped changes.

**Collision/dependency:** does not change FaqList, FAQ copy or home markup and does not duplicate Elena CP-03 header navigation. Confirm owner has no parallel FAQ browser-test reservation. No consent, sending or security work.


## CP-14 — Reconcile developer-page release status after v0.2.0

**Evidence:** `site_src/data/release.yaml` identifies published v0.2.0 (2026-11-08). `/developers/` still says “Version 0.2 isn't out yet,” labels Linux/macOS, pipx, Docker, headless and JSON as “Coming in v0.2,” and uses future tense for setup and JSON. These statements may be stale after release. This source comparison does not establish which advertised features actually shipped.

**Proposed allowed paths:** `web/src/pages/developers/index.astro`; new `tests/test_web_developer_release_status.py`; own worktree `VENDOR_STATUS.md`.

**Deliverable:** compare each claim and command on the page with published v0.2.0 release notes/artifacts and current source/docs. Remove outdated pre-release framing only where shipped behavior is verified. Keep unshipped features clearly marked as planned for a later release. Add built-page regression coverage for release version/status and ensure the page no longer globally claims v0.2 is unreleased. Do not assert every planned item shipped. Build/site/content and focused tests pass. Keep copy plain and sourced.

**Collision/dependency:** wait for WO-107 to merge because it changed this same page. No `site_src/data/release.yaml`, workflow, release, security, secrets or CLI contract edits. Ask Morgan about any feature whose shipment cannot be established from public release materials; do not infer release scope from the tag alone.

## CP-15 — Cover wizard-step keyboard and reflow behavior in a browser

**Evidence:** `docs/handoff/wizard-packager.md` says wizard pages have HTML checks only and a keyboard walk is outstanding. `tests/test_wizard_a11y_browser.py` covers Today, Sites, broker detail, Protect, Settings and Emails; it does not cover wizard steps. This is a documented coverage gap, not a claimed current defect.

**Proposed allowed paths:** new `tests/test_wizard_flow_a11y_browser.py`; own worktree `VENDOR_STATUS.md`.

**Deliverable:** using existing Playwright and fake deterministic values, cover representative non-secret wizard steps at 320px and 640px (modeled 200% reflow), both themes, with JavaScript as the product requires. Check visible keyboard focus and logical traversal, labels linked to inputs, field/error text visibility, no horizontal overflow, and 44px targets where applicable. Exclude mailbox credentials, certificate trust, consent/practice behavior, network submission and real personal data. Distinguish browser emulation from Windows/assistive-technology validation. No product changes or new dependencies; targeted tests and Ruff pass.

**Collision/dependency:** test-only new file; do not edit shared `tests/test_wizard_a11y_browser.py`. In-house retains wizard logic, consent, practice mode, CSRF/origin checks, email/security and Windows VM validation. Stop and report if deterministic fixtures cannot reach a step without touching those paths.

## CP-16 — Guard per-person Protect progress on Today

**Evidence:** `src/freemyid/wizard/server.py` builds Today’s Protect tuples by iterating profiles and calling `protect.counts(store, pr.id)`. `wizard/dashboard.py` renders one “Steps for [label]” link and count per tuple. Existing tests found in `test_wizard_v03.py` and `test_wizard_protect_tips.py` cover one profile; no two-profile Today assertion was found in this read. No bug is asserted.

**Proposed allowed paths:** new `tests/test_wizard_dashboard_protect_profiles.py`; own worktree `VENDOR_STATUS.md`.

**Deliverable:** with two obviously fake profiles and different checklist completion counts, assert Today shows each person's own label, count and `/protect?p=<their-id>` destination, and one person's ticks do not alter the other's displayed count. Include HTML escaping of labels and repeat-render stability if existing fixtures support it. Do not edit server/dashboard code; report any defect for a separate owner-scoped assignment. Targeted tests and Ruff pass.

**Collision/dependency:** test-only new file; no path overlap with WO-106 or Elena's summary work. No real personal details, storage/consent behavior changes or protected files.

## CP-17 — Remove unsafe `any` from checklist parser boundaries

**Evidence:** `web/src/lib/protect.ts` accepts parsed YAML and declares `validate(raw: any)`, `load<T = any>`, `load<any>`, and casts a parsed checklist list as `any[]`. Nearby helpers already accept `unknown`. The YAML is checked into the public repository and validated during site build. This is a localized type-safety opportunity; no runtime defect is claimed.

**Proposed allowed paths:** `web/src/lib/protect.ts`; focused tests in an existing compatible test harness (identify before assignment); own worktree `VENDOR_STATUS.md`.

**Deliverable:** replace `any` at checklist parse/validation boundaries with `unknown` and narrow object/array/string fields before access. Preserve current validation errors where practical, size limits, accepted data, rendered guide output, research-note privacy and build behavior. Add meaningful malformed-root/record/list tests only if an existing no-install harness can exercise the parser; otherwise first report the harness gap rather than adding tooling. Build/site/content checks pass; run TypeScript checking only if already supported locally without changing CI/config/dependencies. No output changes for current checklist data.

**Collision/dependency:** this parser reads `brokers/checklists.yaml`; that file is broker-researcher-owned and strictly out of scope. Edit only the parser module; do not modify registry/checklist data, scripts, tsconfig, package files, workflow or validation policy. Confirm no in-house parser hardening reservation before allocation.

## CP-18 — Plan frontend dependency upgrades (owner-run, not vendor implementation)

**Evidence:** `docs/handoff/web-v3.md` and `docs/handoff/qa-security.md` list SEC-67 (pnpm audit and Dependabot) as open; the QA handoff says `pnpm audit` was skipped because it requires network. No current advisory or outdated-package claim is made by this proposal.

**Proposed vendor paths:** none for package manifests, lockfiles, scripts or CI. Request an in-house owner to run the approved dependency/security review and identify exact versions, advisory sources, compatibility constraints and scope. After that, Codex can propose compatibility test coverage or update user-facing migration notes in a separate, explicitly allowed work order.

**Deliverable if owner later scopes vendor support:** a reviewable upgrade matrix naming package, current and approved target version, source/advisory, compatibility check and rollback owner. No packages changed by this proposal.

**Collision/dependency:** dependency policy, package installation and security review are in-house-only under `docs/VENDOR.md` and CLAUDE-005. Codex must not edit `package.json`, lockfiles, Dependabot or workflow files, install packages, run network audits or claim packages need updates without owner-approved evidence.

## Recent tracker proposals and work orders (CP-31 through CP-42)

The private issue tracker is the proposal source of truth for these newer ideas; this short index prevents overlap with the older CP-01..18 notes above.

| ID | Tracker | Candidate | Status |
| --- | --- | --- | --- |
| CP-31 | [#147](https://github.com/FreeMyID/freemyid-pm/issues/147) | Public broker-guide citation bounds guard | WO-180 merged locally by Morgan |
| CP-32 | [#149](https://github.com/FreeMyID/freemyid-pm/issues/149) | Developer-page Open Graph metadata checks | WO-187 accepted; in-house merge queue; 2 tests and Ruff pass |
| CP-33 | [#156](https://github.com/FreeMyID/freemyid-pm/issues/156) | Owner-approved protected-string inventory for WO-136 exclusions | Parked until after v0.3.0rc1 and owner supplies cleared paths/excerpts |
| CP-34 | [#159](https://github.com/FreeMyID/freemyid-pm/issues/159) | Link broker contributor guide to existing custom-submitter instructions | WO-188 delivered; owner review |
| CP-35 | [#160](https://github.com/FreeMyID/freemyid-pm/issues/160) | Test developer-home scheduler examples against the renderer | WO-189 delivered; 2 tests and Ruff pass; owner review |
| CP-36 | [#162](https://github.com/FreeMyID/freemyid-pm/issues/162) | Guard human-readable registry priority ordering | WO-190 independently verified; 1 test and Ruff pass; artifact authorship unconfirmed |
| CP-37 | [#165](https://github.com/FreeMyID/freemyid-pm/issues/165) | Guard built developer CLI reference rendering | Superseded by WO-198; owner will close #165 when creating the replacement issue |
| CP-38 | [#166](https://github.com/FreeMyID/freemyid-pm/issues/166) | Guard registry source summary text | Backlog proposal; awaiting Morgan's review |
| CP-39 | [#167](https://github.com/FreeMyID/freemyid-pm/issues/167) | Guard exposure result text output | Backlog proposal; awaiting Morgan's review |
| CP-40 | [#168](https://github.com/FreeMyID/freemyid-pm/issues/168) | Guard human-readable todo list output | Backlog proposal; awaiting Morgan's review |
| CP-41 | [#169](https://github.com/FreeMyID/freemyid-pm/issues/169) | Guard doctor diagnostic text output | Backlog proposal; awaiting Morgan's review |
| CP-42 | [#170](https://github.com/FreeMyID/freemyid-pm/issues/170) | Guard developer config table semantics | Superseded by WO-199; owner will close #170 when creating the replacement issue |
