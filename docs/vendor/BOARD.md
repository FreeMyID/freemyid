# Codex vendor work board

Sole writer: Nora Bennett, interactive vendor PM. Last checkpoint: CLAUDE-012, 2026-11-08. v0.2.0 released per owner report.
States are owner reports and local document evidence, not independently verified remote PR state. No git or network used. Local merges are distinguished from pushed merges. Work-order status headers may be stale; latest owner channel controls.

Before dispatch or proposals, check this board, exact work-order paths and Claude's stay-off lists. This board grants no additional edit permission. Completed WO-001/002/005/006 path lists are historical scopes, not active reservations. WO-005 scope is exposure_card and its exclusive helpers only, never all views.py functions.

| Work order | Proposal | Owner | Status | Dependency | Reserved paths / scope | Last update |
| --- | --- | --- | --- | --- | --- | --- |
| WO-001 | — | prior vendor (unconfirmed); in-house accepted | merged (owner report) | none | src/freemyid/wizard/protect.py; src/freemyid/wizard/views.py; src/freemyid/wizard/ui.py; src/freemyid/wizard/static/style.css; tests/test_wizard_v03.py; tests/test_wizard_protect_tips.py | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-002 | — | Elena / Ravi | merged PR #6 (owner report) | none | src/freemyid/engine/exposure.py; tests/test_exposure.py; tests/test_exposure_todos.py; docs/CLI.md; docs/EXPOSURE.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-003 | — | Elena / Kai | merged main PR #7 (owner report) | none; owner reports main c1feaef | web/src/pages/whats-coming/index.astro; tests/test_web_v03_roadmap.py (new); VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-004 | — | Elena / Amara | merged main PR #8 (owner report) | none; owner reports main c1feaef | web/src/components/FaqList.astro; tests/test_web_faq_accessibility.py (new); VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-005 | — | Elena / Felix | merged PR #10 (owner report) | none | src/freemyid/wizard/views.py; tests/test_wizard_exposure_card.py (new); VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-006 | — | Elena / Hannah | merged PR #9 (owner report) | none | tests/test_wizard_summary_regressions.py (new); docs/vendor/WO-006-test-notes.md (new); VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-007 | — | Elena / Kai | merged main PR #11 (owner report) | none; owner reports main c1feaef | web/src/pages/developers/index.astro; tests/test_web_developer_first_run.py | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-008 | — | Elena / Hannah | merged main PR #12 (owner report) | none; owner reports main c1feaef | tests/test_cli_json_serialization_edges.py | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-101 | — | channel | merged main PR #13 (owner report) | none; owner reports main c1feaef | web/src/pages/index.astro; web/src/pages/safety/index.astro; site_src/data/faq.yaml; site_src/templates/pages/home.html; site_src/templates/pages/safety.html; tests/test_web_privacy_wording.py; VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-102 | CP-10 | channel | merged PR #14 (owner report) | none | web/src/art/sections/safety-local.svg; brand/v3/sections/safety-local.svg; tests/test_web_safety_art.py; VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-104 | CP-02 | channel | merged PR #15 (owner report) | none | web/src/components/CopyHash.tsx; tests/test_web_copy_hash.py; VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-105 | CP-05 | channel | merged PR #16 (owner report) | none | tests/test_web_not_found_recovery.py; VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-106 | CP-06 | channel | merged PR #18 on main; in-house PASS (owner report) | none | src/freemyid/wizard/views.py (only `exposure_card` and helpers used only by it); tests/test_wizard_exposure_card_followups.py (new); tests/test_wizard_exposure_card.py (superseded assertions only); VENDOR_STATUS.md | 2026-11-07; CLAUDE-005 / prior owner channel |
| WO-103 | CP-01 | channel | merged PR #17 on main; in-house PASS (owner report) | none | web/src/pages/index.astro; tests/test_web_home_hero_layout.py; worktree VENDOR_STATUS.md | 2026-11-07; CLAUDE-009 |
| WO-107 | CLAUDE-003 follow-up | channel | merged PR #19 on main (owner report) | none | web/src/pages/families/index.astro; web/src/pages/developers/index.astro; web/src/pages/whats-coming/index.astro; site_src/templates/pages/families.html; tests/test_web_privacy_claims_followup.py; own status | 2026-11-07 CLAUDE-008 |
| WO-108 | CP-11 | channel / Maya | delivered; build/site/content/Ruff and 3 browser tests pass; cleanup complete | none; ready worktree | web/src/components/CopyHash.astro; tests/test_web_copy_hash.py; VENDOR_STATUS.md | 2026-11-08 CODEX-033 |
| WO-109 | CP-12 | channel / Iris | delivered; build/site/content/Ruff and 4 metadata tests pass; cleanup complete | none; ready worktree | tests/test_web_download_metadata.py; VENDOR_STATUS.md | 2026-11-08 CODEX-033 |
| WO-110 | CP-13 | channel / Samir | delivered; build/site/content/Ruff and 8 keyboard tests plus 10 existing accessibility tests pass; cleanup complete | none; ready worktree | tests/test_web_faq_keyboard.py; VENDOR_STATUS.md | 2026-11-08 CODEX-033 |
| WO-111 | CP-14 | channel / Maya | delivered; build/site/content/Ruff pass; targeted release tests 13 passed; ready owner review | CLAUDE-014 allowed only one superseded test's assertions | web/src/pages/developers/index.astro; tests/test_web_developer_release_status.py; tests/test_web_developer_first_run.py (one test only); VENDOR_STATUS.md | 2026-11-08 CODEX-037 |
| WO-112 | CP-15 | channel / Iris | delivered; required wizard suite 183 passed, 4 strict xfailed; Ruff pass; ready owner review | SEC-98 product fix in-house; remove xfail marker with fix | tests/test_wizard_flow_a11y_browser.py; VENDOR_STATUS.md | 2026-11-08 CODEX-037 |
| WO-113 | CP-17 | channel | queued; worktree after WO-111/112 merge | CLAUDE-014; byte-identical built `/protect/` output required | web/src/lib/protect.ts; existing no-install test harness only if one exists; VENDOR_STATUS.md | 2026-11-08 CLAUDE-014 |

WO-107 workspace: .vendor-wt/wo-107. Merged PR #19, owner report (103d79a).

## Elena next wave (not yet numbered)

CP-03 navigation tests; CP-04 guide-print audit; CP-07 printable-summary visual checks; CP-08 CLI-doc audit; CP-09 families accessibility audit. Allocated to Elena in CLAUDE-003; startup unconfirmed. See CODEX_PROPOSALS.md for proposed paths; proposals do not reserve them. Recheck at WO-106 delivery and notify Morgan if still unstarted.

## Collision and dispatch controls

- CLAUDE-007 resolved both prior holds: use .vendor-wt/wo-103 and .vendor-wt/wo-106 inside repo; WO-106 permits narrow superseded assertions in existing tests/test_wizard_exposure_card.py.
- WO-106: Iris owns exposure_card/exclusive helpers, new followup test, authorized old assertions and its worktree status. SEC-93a remains held for in-house; no security edits.
- WO-103: Maya owns home page, new hero-layout test and its worktree status. Shared components remain excluded; request scope change with evidence if needed.
- Nora reviewed WO-103/106 actual changes and relevant verification; owner handoff requested. WO-103: 10 layout + 7 privacy tests/build/site/content/Ruff pass; WO-106: 194 required tests/Ruff pass. Owen confirmed scoped inventories and borrowed-link cleanup; no git diff audit claimed.
- Main status/board: Nora only. Channel receipts: Jules during active window. Workers write only their own scoped worktree paths.
- Owner reports #14/15/16 merged main b633bda and rc1 tagged, release workflows running. No vendor release/git/network operations.

## Next checkpoint

WO-108..110 are delivered; owner reports PRs #25–27 merged on main, with final full-suite result pending in latest channel. WO-111/112 are delivered for owner review; their worker status files contain all check details. WO-112 preserves SEC-98 as four strict expected failures pending the in-house product fix. WO-113 is written and its worktree follows the 111/112 merge. Morgan has also been asked for a docs-only work order to implement the shared team workflow; none is recorded yet. CP-18 moved in-house to SEC-67. Elena wave remains owner-run; current status requested.

## Elena proposed path collision reference

These remain proposed, unreserved scopes pending owner-numbered work orders:

- CP-03: header navigation regression test.
- CP-04: protect/[id] page and protect-print regression test.
- CP-07: summary-print QA document and summary-print-layout regression test.
- CP-08: v0.2 CLI documentation audit document.
- CP-09: families accessibility audit document and regression test.

Use exact proposed paths in CODEX_PROPOSALS.md when checking a new assignment. Samir independently audited statuses against CLAUDE-005; no remote state checked.

## Proposed next wave (unreserved)

CP-11..13 are delivered as WO-108..110; CP-14/15 queued as WO-111/112; CP-16 declined (existing QA test covers it); CP-17 queued as WO-113; CP-18 moved in-house to SEC-67. Details and boundaries are in CODEX_PROPOSALS.md. No new allocation is pending beyond these queued WOs.
