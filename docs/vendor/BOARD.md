# Codex vendor work board

Sole writer: Nora Bennett, interactive vendor PM. Last checkpoint: CLAUDE-059b / CODEX-139..148, 2026-11-09. Release and merge states are owner-reported.
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
| WO-119 | — | Copilot / Malik Johnson | in progress (owner report) | none; Copilot team live per CLAUDE-019 | tests/test_site_build_v3_links.py (new) | 2026-11-08 CLAUDE-019 |
| WO-120 | — | Copilot / Claire Dubois | open (owner report) | none | docs/CLI.md; README.md; docs/USER_GUIDE.md; VENDOR_STATUS.md | 2026-11-08 CLAUDE-019 |
| WO-121 | — | Copilot / Malik Johnson | queued after WO-120 (owner report) | WO-120 merge | tests/test_cli_docs_match_source.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-019 |
| WO-122 | — | Copilot / Lucia Ferraro | open (owner report) | none | docs/vendor/web-contrast-audit.md (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-019 |
| WO-180 | CP-31 / #147 | channel / Hannah | accepted by owner; merge pending | none | tests/codex/test_cx_dev_broker_citations.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-031 |
| WO-181 | #150 | channel / Ravi | accepted by owner; merge pending | none | tests/codex/test_cx_cli_profile_scoping.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-031 |
| WO-182 | #151 | channel / Kai | accepted by owner; merge pending | none | docs/dev/TESTING.md (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-031 |
| WO-183 | #152 | channel / Amara | accepted by owner; merge pending | none | tests/codex/test_cx_dev_config_constraints.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-031 |
| WO-187 | CP-32 / #149 | channel / Amara | accepted by owner; merge queue | Iris design images on main | tests/codex/test_cx_developer_og_metadata.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-033 |
| WO-188 | CP-34 / #159 | channel / Kai | accepted by owner; in-house merge queue | WO-180 locally merged (owner/work-order report) | docs/dev/CONTRIBUTING_BROKERS.md; VENDOR_STATUS.md | 2026-11-08 CLAUDE-034 |
| WO-189 | CP-35 / #160 | channel / Hannah | accepted by owner; in-house merge queue | none | tests/codex/test_cx_dev_home_scheduler_examples.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-034 |
| WO-190 | CP-36 / #162 | channel / Ravi | accepted by owner; in-house merge queue | none | tests/codex/test_cx_cli_registry_table.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-034 |
| WO-191 | — / #163 | channel / Hannah | delivered; 4 tests and Ruff pass; owner review requested | none | tests/codex/test_cx_cli_checklist_text.py (new); VENDOR_STATUS.md | 2026-11-08 CODEX-089 |
| WO-192 | — / #164 | channel / Amara | delivered; build, 1 test and Ruff pass; owner review requested | none | tests/codex/test_cx_developer_hero_art.py (new); VENDOR_STATUS.md | 2026-11-08 CODEX-089 |
| WO-194 | #177 | Elena Vasquez | accepted with CLAUDE-036 amendments | none | docs/vendor/CODEX_SITE_REFRESH.md; VENDOR_STATUS.md | 2026-11-08 CLAUDE-037 |
| WO-195 | #178 | Amara Okoye | delivered; build/site check blocked on missing dependencies; owner review requested | WO-194 | web/src/styles/site-refresh.css (new); web/src/components/site-refresh/ (new); VENDOR_STATUS.md | 2026-11-08 CODEX-099 |
| WO-196 | #179 | Amara Okoye | delivered; owner review requested | WO-194 | web/src/art/site-refresh/ (new); VENDOR_STATUS.md | 2026-11-08 CODEX-098 |
| WO-197 | #180 | Kai Nakamura | merged locally; no owner fixups, combined checks pass (owner report) | CLAUDE-040 GO on prepared main | web/src/pages/developers/index.astro; tests/codex/test_cx_developer_hub_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-041 |
| WO-198 | #181 / CP-37 #165 closed | Kai Nakamura | merged locally; no owner fixups, combined checks pass (owner report) | CLAUDE-040 GO on prepared main | web/src/pages/developers/cli/index.astro; tests/codex/test_cx_dev_cli_render.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-041 |
| WO-199 | #182 / CP-42 #170 closed | Kai Nakamura | merged locally; no owner fixups, combined checks pass (owner report) | CLAUDE-040 GO on prepared main | web/src/pages/developers/config/index.astro; tests/codex/test_cx_dev_config_table_semantics.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-041 |
| WO-200 | #183 | Kai Nakamura | merged locally; owner reports combined checks pass | WO-195/196 merged | web/src/pages/index.astro; web/src/art/screenshots/home-hero-v0.2.0.png (new); tests/codex/test_cx_home_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-040 |
| WO-201 | #184 | Kai Nakamura | merged locally; owner reports combined checks pass | WO-200 | web/src/pages/how-it-works/index.astro; tests/codex/test_cx_how_it_works_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-040 |
| WO-202 | #185 | Kai Nakamura | merged locally; owner reports combined checks pass | WO-206 (parallel start authorized by CLAUDE-039) | web/src/pages/families/index.astro; tests/codex/test_cx_families_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-040 |
| WO-203 | #186 | Kai Nakamura | merged locally; no owner fixups, combined checks pass (owner report) | CLAUDE-040 GO on prepared main | web/src/pages/guides/index.astro; web/src/pages/guides/[slug]/index.astro; web/src/pages/guides/get-your-phone-number-off-people-search-sites/index.astro; web/src/pages/guides/help-a-parent-remove-their-information/index.astro; tests/codex/test_cx_guides_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-041 |
| WO-204 | #187 | Hannah Cole | initial audit delivered; repair acceptance held, no source fixes | CLAUDE-041 GO, all ten pages integrated | docs/vendor/site-refresh/QA_REPORT.md (new); VENDOR_STATUS.md | 2026-11-08 CODEX-110 |
| WO-205 | #188 | Kai Nakamura | merged locally; owner reports combined checks pass | WO-201 | web/src/pages/safety/index.astro; tests/codex/test_cx_safety_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-040 |
| WO-206 | #189 | Kai Nakamura | merged locally; owner reports combined checks pass | WO-205 | web/src/pages/download/index.astro; tests/codex/test_cx_download_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-040 |
| WO-207 | #190 | Kai Nakamura | merged locally; no owner fixups, combined checks pass (owner report) | CLAUDE-040 GO on prepared main | web/src/pages/faq/index.astro; tests/codex/test_cx_faq_refresh.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-041 |
| WO-209 | — | Kai Nakamura | merged locally (128f60a; owner report); build/site check and 450 tests pass | CLAUDE-042/045/046 | web/src/pages/safety/index.astro; web/src/pages/families/index.astro; tests/codex/test_cx_audit_trust_pages_followup.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-046 |
| WO-210 | — | Kai Nakamura | merged locally with owner fixup (3ae75d7; owner report); 453 tests pass | CLAUDE-042/045/046 | web/src/pages/download/index.astro; tests/codex/test_cx_audit_download_followup.py (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-046 |
| WO-211 | — | Amara Okoye | merged locally (e91f7ec; owner report); three contract findings assigned in-house | CLAUDE-045/046 | tests/codex/test_cx_monitor_contract.py (new); tests/codex/fixtures/monitor/ (new); VENDOR_STATUS.md | 2026-11-08 CLAUDE-046 |
| WO-212 | — | Nora Bennett | merged locally (a3dfa37; owner report); all 61 citations resolve | CLAUDE-045/046 | docs/dev/ARCHITECTURE.md; VENDOR_STATUS.md | 2026-11-08 CLAUDE-046 |
| WO-204R | #187 | Hannah Cole | accepted; site published as 1d0bebd (owner report) | CLAUDE-046 GO, prepared combined-main build | docs/vendor/site-refresh/QA_REPORT.md; VENDOR_STATUS.md | 2026-11-08 CLAUDE-047 |
| WO-213 | — | Kai Nakamura | delivered; 37 tests and Ruff pass; owner review requested | CLAUDE-048 GO | tests/codex/test_cx_review_card_a11y.py (new); VENDOR_STATUS.md | 2026-11-08 CODEX-121 |
| WO-214 | — | Amara Okoye | delivered; i18n/doc tests pass; owner review requested | CLAUDE-048 GO | docs/i18n/STRINGS.md; docs/i18n/GLOSSARY_ES.md; VENDOR_STATUS.md | 2026-11-08 CODEX-122 |
| WO-215 | — | Owen Park | delivered; testing/doc tests pass; owner review requested | CLAUDE-048 GO | docs/dev/TESTING.md; VENDOR_STATUS.md | 2026-11-08 CODEX-123 |
| WO-216 | CP-47 | Kai Nakamura | merged (owner report, d987570) | CLAUDE-050 | tests/codex/test_cx_review_card_forced_colors.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-054 |
| WO-217 | CP-48 | Owen Park | merged (owner report, 8a9e35a) | CLAUDE-050 | tests/codex/test_cx_dev_source_citations.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-054 |
| WO-218 | — | interactive contributor | accepted and merged (owner report, CLAUDE-055); in-house wording fix; 34 tests pass per owner | CLAUDE-051/053 | tests/codex/test_cx_app_practice_wording.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-055 |
| WO-219 | — | interactive contributor | accepted and merged (owner report, CLAUDE-055); i18n/doc selection passed | CLAUDE-051/053 | docs/i18n/STRINGS.md; docs/i18n/GLOSSARY_ES.md; VENDOR_STATUS.md | 2026-11-09 CLAUDE-055 |
| WO-220 | CP-38 / #166 | Hannah Cole | accepted and merged (owner report, CLAUDE-057) | CLAUDE-056 GO | tests/codex/test_cx_cli_registry_source_text.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-057 |
| WO-221 | CP-39 / #167 | Ravi Menon | accepted and merged (owner report, CLAUDE-057) | CLAUDE-056 GO | tests/codex/test_cx_cli_exposure_text.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-057 |
| WO-222 | CP-40 / #168 | Felix Grant | accepted and merged (owner report, CLAUDE-057) | CLAUDE-056 GO | tests/codex/test_cx_cli_todo_list_text.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-057 |
| WO-223 | CP-41 / #169 | Hannah Cole | accepted and merged (owner report, CLAUDE-057) | CLAUDE-056 GO | tests/codex/test_cx_cli_doctor_text.py; VENDOR_STATUS.md | 2026-11-09 CLAUDE-057 |
| WO-224 | CP-49 | Amara Okoye | accepted and merged (owner report, CLAUDE-057) | CLAUDE-056 GO | docs/i18n/TRANSLATION_GUIDE.md; VENDOR_STATUS.md | 2026-11-09 CLAUDE-057 |
| WO-225 | — | Nora Bennett | delivered; docs/i18n citation selection 521 passed on filtered rerun; initial run had one sandbox-blocked socket test | CLAUDE-058 GO | docs/i18n/STRINGS.md; docs/i18n/GLOSSARY_ES.md; worktree VENDOR_STATUS.md | 2026-11-09 CODEX-139 |
| WO-226 | — | Amara Okoye | delivered; 44 passed, 1 strict xfailed; Ruff passed; xfail finding monitor.py:379 | CLAUDE-059b GO | tests/codex/test_cx_monitor_previous_hardening.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-140 |
| WO-227 | — | Owen Park | delivered; 2 passed; Ruff passed | CLAUDE-059b GO | tests/codex/test_cx_cli_search_engines.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-141 |
| WO-228 | — | Hannah Cole | delivered for review; 5 browser cases skipped (Chromium unavailable); Ruff passed; strict xfail documents 18px hint at style.css:98 | CLAUDE-059b GO | tests/codex/test_cx_proof_note_a11y.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-142 |
| WO-229 | — | Nora Bennett | delivered for owner review; 3 browser cases skipped because Playwright Chromium failed to launch; Ruff passed | CLAUDE-059b GO | tests/codex/test_cx_large_text_pages.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-142 |
| WO-230 | — | Amara Okoye | delivered; citation test 14 passed | CLAUDE-059b queue | docs/dev/ARCHITECTURE.md; VENDOR_STATUS.md | 2026-11-09 CODEX-143 |
| WO-231 | — | Owen Park | delivered; citation test 14 passed | CLAUDE-059b queue | docs/dev/DEPENDENCIES.md (new); VENDOR_STATUS.md | 2026-11-09 CODEX-144 |
| WO-232 | — | Nora Bennett | delivered; filtered i18n/doc/citation selection 521 passed, 6 skipped, 1 xfailed; required run had one sandbox-blocked socket failure | CLAUDE-059b queue | docs/i18n/STRINGS_CLI.md (new); VENDOR_STATUS.md | 2026-11-09 CODEX-145 |
| WO-233 | — | Hannah Cole | delivered; 3 passed; Ruff passed | CLAUDE-059b queue | tests/codex/test_cx_matcher_suffix_nickname.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-146 |
| WO-234 | — | Amara Okoye | delivered; 3 passed; Ruff passed; out-of-scope scan hits reported only | CLAUDE-059b queue | tests/codex/test_cx_windows_path_safety.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-148 |
| WO-235 | — | Owen Park | delivered; 6 passed; Ruff passed | CLAUDE-059b queue | tests/codex/test_cx_today_states.py (new); VENDOR_STATUS.md | 2026-11-09 CODEX-147 |
| WO-270 | issue pending | Hannah Cole | delivered for review; 44 passed; Ruff passed; app scan clean | CLAUDE-063 GO | tests/codex/test_cx_app_practice_wording.py; VENDOR_STATUS.md | 2026-11-09 CODEX-152 |
| WO-236 | issue pending | Imani Reid | delivered for in-house review; Owen PASS; 75 passed, 2 strict xfailed; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_sec_netpolicy_invariants.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-155 |
| WO-237 | issue pending | Imani Reid | delivered for in-house review; Owen PASS; 30 passed; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_sec_redaction_fields.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-155 |
| WO-238 | issue pending | Imani Reid | incomplete; pytest runner produced no result; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_sec_wizard_post_guard.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-157 |
| WO-239 | issue pending | Imani Reid | incomplete; TestClient request hangs before response; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_sec_wizard_headers.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-157 |
| WO-240 | issue pending | Imani Reid | incomplete; TestClient dashboard request hangs; 21 focused + 28 existing consent tests passed; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_sec_consent_gates.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-157 |
| WO-241 | issue pending | Ravi Menon | delivered for in-house review; Owen PASS; 73 passed; Ruff passed | CLAUDE-064 pre-approved | `src/freemyid/engine/letters.py`; `tests/codex/test_cx_letters_hostile_values.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-158 |
| WO-242 | issue pending | Ravi Menon | held; Owen review found AC6 conflict with existing test outside allowed paths; in-house clarification needed | CLAUDE-064 pre-approved; resumed under CLAUDE-065 | `src/freemyid/engine/exposure.py`; `src/freemyid/exposure_models.py`; `tests/codex/test_cx_exposure_rate_limit.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-164 |
| WO-243 | issue pending | Hannah Cole | delivered for in-house review; Owen PASS; 26 targeted, 74 combined passed; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_htmlsel_grammar.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-165 |
| WO-244 | issue pending | Hannah Cole | delivered for in-house review; Owen PASS; 776 passed, 2 strict xfailed, 0 skipped; Ruff passed | CLAUDE-064 pre-approved | `tests/codex/test_cx_state_machine_properties.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CODEX-167 |
| WO-245 | issue pending | Hannah Cole | queued (pre-approved) | after WO-233 merged | `src/freemyid/engine/nicknames.py`; `tests/codex/test_cx_nickname_table.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-246 | issue pending | Owen Park | delivered for in-house review; Owen PASS; 70 passed; Ruff passed | none | `src/freemyid/checklists.py`; `src/freemyid/engine/law_matrix.py`; `tests/codex/test_cx_data_file_hardening.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes); CODEX-167/168/169 |
| WO-247 | issue pending | Owen Park | started; WIP 5/5 | none | `tests/codex/test_cx_paths_cross_platform.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes); CODEX-169 |
| WO-248 | issue pending | Owen Park | queued (pre-approved) | none | `tests/codex/test_cx_firstrun_browser.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-249 | issue pending | Felix Grant | queued (pre-approved) | none | `tests/codex/test_cx_draft_edit_roundtrip.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-250 | issue pending | Amara Okoye | queued (pre-approved) | none | `docs/i18n/STRINGS_APP.md` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-251 | issue pending | Amara Okoye | queued (pre-approved) | after WO-225 merged | `tests/codex/test_cx_glossary_es_consistency.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-252 | issue pending | Kai Nakamura | queued (pre-approved) | none | `docs/dev/STATE_MACHINE.md` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-253 | issue pending | Kai Nakamura | queued (pre-approved) | none | `docs/dev/PROOF_VAULT.md` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-254 | issue pending | Felix Grant | queued (pre-approved) | after WO-225, WO-232, WO-250 merged | `tests/codex/test_cx_i18n_inventory_coverage.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-255 | issue pending | Hannah Cole | queued (pre-approved) | after WO-230, WO-231, WO-232, WO-250, WO-252, WO-253 merged | `tests/codex/test_cx_dev_source_citations.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-256 | issue pending | Imani Reid | queued (pre-approved) | after WO-226 merged | `src/freemyid/monitor.py`; `tests/codex/test_cx_monitor_previous_hardening.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-257 | issue pending | Ravi Menon | queued (pre-approved) | after WO-233, WO-242 merged | `src/freemyid/engine/matcher.py`; `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_matcher_age_ranges.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-258 | issue pending | Felix Grant | queued (pre-approved) | after WO-242 merged | `src/freemyid/exposure_models.py`; `tests/codex/test_cx_coverage_by_category.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-259 | issue pending | Hannah Cole | queued (pre-approved) | after WO-242, WO-257 merged | `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_exposure_variant_rotation.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-260 | issue pending | Owen Park | blocked: needs in-house contract change (doctor/1) | contract change first; after WO-246 merged | `src/freemyid/doctor.py`; `tests/codex/test_cx_doctor_extra_checks.py` (new); `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-064 (appended by Morgan Reyes) |
| WO-271 | issue pending | Ravi Menon | queued (pre-approved) | after WO-256, WO-226, WO-211 merged | `src/freemyid/monitor.py`; `tests/codex/test_cx_monitor_relist.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-272 | issue pending | Ravi Menon | queued (pre-approved) | none | `src/freemyid/engine/exposure_score.py`; `tests/codex/test_cx_exposure_score_edges.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-273 | issue pending | Hannah Cole | queued (pre-approved) | none | `src/freemyid/engine/listing_finder.py`; `tests/codex/test_cx_listing_finder_errors.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-274 | issue pending | Felix Grant | queued (pre-approved) | none | `src/freemyid/engine/search_engines.py`; `tests/codex/test_cx_search_engine_links.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-275 | issue pending | Ravi Menon | queued (pre-approved) | after WO-241, WO-284 merged | `src/freemyid/engine/letters.py`; `tests/codex/test_cx_letter_state_selection.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-276 | issue pending | Ravi Menon | queued (pre-approved) | after WO-233, WO-257 merged | `src/freemyid/engine/matcher.py`; `tests/codex/test_cx_matcher_previous_names.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-277 | issue pending | Ravi Menon | queued (pre-approved) | after WO-276 merged | `src/freemyid/engine/matcher.py`; `tests/codex/test_cx_matcher_old_addresses.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-278 | issue pending | Hannah Cole | queued (pre-approved) | after WO-242, WO-257, WO-259 merged | `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_exposure_dedupe.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-279 | issue pending | Ravi Menon | blocked: needs in-house contract change (state.py and config.py (new stored timestamps and window setting)) | contract change first; after WO-278 merged | `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_exposure_persistent_cache.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-280 | issue pending | Felix Grant | queued (pre-approved) | after WO-242, WO-258 merged | `src/freemyid/exposure_models.py`; `tests/codex/test_cx_coverage_report.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-281 | issue pending | Owen Park | queued (pre-approved) | none | `src/freemyid/checklist_state.py`; `tests/codex/test_cx_checklist_state_recovery.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-282 | issue pending | Hannah Cole | queued (pre-approved) | after WO-246 merged | `src/freemyid/checklists.py`; `tests/codex/test_cx_checklist_validation.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-283 | issue pending | Owen Park | queued (pre-approved) | after WO-260 merged | `src/freemyid/doctor.py`; `tests/codex/test_cx_doctor_error_paths.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-284 | issue pending | Ravi Menon | queued (pre-approved) | after WO-246 merged | `src/freemyid/engine/law_matrix.py`; `tests/codex/test_cx_law_matrix_lookup.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-285 | issue pending | Owen Park | queued (pre-approved) | after WO-243 merged | `src/freemyid/engine/htmlsel.py`; `tests/codex/test_cx_htmlsel_performance.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-286 | issue pending | Hannah Cole | queued (pre-approved) | after WO-245 merged | `src/freemyid/engine/nicknames.py`; `tests/codex/test_cx_nickname_index.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-287 | issue pending | Owen Park | queued (pre-approved) | after WO-278 merged | `tests/codex/test_cx_perf_400_brokers.py`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-288 | issue pending | Kai Nakamura | queued (pre-approved) | none | `docs/dev/EXPOSURE_PIPELINE.md`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-289 | issue pending | Kai Nakamura | queued (pre-approved) | none | `docs/dev/MATCHING.md`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |
| WO-290 | issue pending | Amara Okoye | queued (pre-approved) | none | `docs/i18n/STRINGS_LETTERS.md`; `VENDOR_STATUS.md` | 2026-11-09 CLAUDE-065 (appended by Morgan Reyes) |

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

CLAUDE-059b reports v0.3.1 released and authorizes WO-226..229; WO-230..235 are pre-approved and start in order as WIP slots free. WO-225..235 are delivered for in-house review. WO-228/229 browser limitations and WO-225/232 sandbox socket-test failures are documented. The authorized queue is complete; no merge or push by Codex.

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
| WO-291 | issue pending | Ravi Menon | queued (pre-approved) | after WO-271 merged | `src/freemyid/monitor.py`; `tests/codex/test_cx_recheck_interval.py`; `VENDOR_STATUS.md` | 2026-11-09 E2 epic batch (appended by Morgan Reyes) |
| WO-292 | issue pending | Ravi Menon | queued (pre-approved) | after WO-291 merged | `src/freemyid/monitor.py`; `tests/codex/test_cx_relist_gaps.py`; `VENDOR_STATUS.md` | 2026-11-09 E2 epic batch (appended by Morgan Reyes) |
| WO-293 | issue pending | Ravi Menon | queued (pre-approved) | after WO-292 merged | `src/freemyid/monitor.py`; `tests/codex/test_cx_recheck_suggestion.py`; `VENDOR_STATUS.md` | 2026-11-09 E2 epic batch (appended by Morgan Reyes) |
| WO-294 | issue pending | Hannah Cole | queued (pre-approved) | after WO-293 merged | `tests/codex/test_cx_recheck_properties.py`; `VENDOR_STATUS.md` | 2026-11-09 E2 epic batch (appended by Morgan Reyes) |
| WO-295 | issue pending | Ravi Menon | queued (pre-approved) | after WO-278 merged | `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_exposure_newly_found.py`; `VENDOR_STATUS.md` | 2026-11-09 E2 epic batch (appended by Morgan Reyes) |
| WO-296 | issue pending | Ravi Menon | queued (pre-approved) | after WO-241, WO-275 merged | `src/freemyid/engine/letters.py`; `tests/codex/test_cx_complaint_pack_vars.py`; `VENDOR_STATUS.md` | 2026-11-09 E3 epic batch (appended by Morgan Reyes) |
| WO-297 | issue pending | Ravi Menon | queued (pre-approved) | after WO-246, WO-284 merged | `src/freemyid/engine/law_matrix.py`; `tests/codex/test_cx_law_window.py`; `VENDOR_STATUS.md` | 2026-11-09 E3 epic batch (appended by Morgan Reyes) |
| WO-298 | issue pending | Hannah Cole | queued (pre-approved) | after WO-275 merged | `tests/codex/test_cx_escalation_letters.py`; `VENDOR_STATUS.md` | 2026-11-09 E3 epic batch (appended by Morgan Reyes) |
| WO-299 | issue pending | Ravi Menon | queued (pre-approved) | after WO-258, WO-280 merged | `src/freemyid/exposure_models.py`; `tests/codex/test_cx_report_facts.py`; `VENDOR_STATUS.md` | 2026-11-09 E5 epic batch (appended by Morgan Reyes) |
| WO-401 | issue pending | Ravi Menon | queued (pre-approved) | after WO-295 merged | `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_exposure_first_latest.py`; `VENDOR_STATUS.md` | 2026-11-09 E5 epic batch (appended by Morgan Reyes) |
| WO-402 | issue pending | Ravi Menon | queued (pre-approved) | after WO-401 merged | `src/freemyid/engine/exposure.py`; `tests/codex/test_cx_exposure_event_reads.py`; `VENDOR_STATUS.md` | 2026-11-09 E6 epic batch (appended by Morgan Reyes) |
| WO-403 | issue pending | Ravi Menon | queued (pre-approved) | after WO-402, WO-299 merged | `src/freemyid/engine/exposure.py`; `src/freemyid/exposure_models.py`; `tests/codex/test_cx_exposure_scan_budget.py`; `VENDOR_STATUS.md` | 2026-11-09 E6 epic batch (appended by Morgan Reyes) |
| WO-404 | issue pending | Hannah Cole | queued (pre-approved) | after WO-281 merged | `src/freemyid/checklist_state.py`; `tests/codex/test_cx_checklist_legacy_ticks.py`; `VENDOR_STATUS.md` | 2026-11-09 E6 epic batch (appended by Morgan Reyes) |
| WO-405 | issue pending | Owen Park | queued (pre-approved) | after WO-283 merged | `src/freemyid/doctor.py`; `tests/codex/test_cx_doctor_scan_estimate.py`; `VENDOR_STATUS.md` | 2026-11-09 E6 epic batch (appended by Morgan Reyes) |
| WO-406 | issue pending | Hannah Cole | queued (pre-approved) | after WO-403 merged | `tests/codex/test_cx_scan_event_size.py`; `VENDOR_STATUS.md` | 2026-11-09 E6 epic batch (appended by Morgan Reyes) |
| WO-407 | issue pending | Imani Reid | queued (pre-approved) | none | `tests/codex/test_cx_search_link_minimization.py`; `VENDOR_STATUS.md` | 2026-11-09 E7 epic batch (appended by Morgan Reyes) |
| WO-408 | issue pending | Imani Reid | queued (pre-approved) | after WO-275 merged | `tests/codex/test_cx_letter_minimization_props.py`; `VENDOR_STATUS.md` | 2026-11-09 E7 epic batch (appended by Morgan Reyes) |
| WO-409 | issue pending | Imani Reid | queued (pre-approved) | after WO-402 merged | `tests/codex/test_cx_scan_logs_pii_free.py`; `VENDOR_STATUS.md` | 2026-11-09 E7 epic batch (appended by Morgan Reyes) |
| WO-410 | issue pending | Owen Park | queued (pre-approved) | after WO-405 merged | `src/freemyid/doctor.py`; `tests/codex/test_cx_doctor_scheduler_states.py`; `VENDOR_STATUS.md` | 2026-11-09 E8 epic batch (appended by Morgan Reyes) |
| WO-411 | issue pending | Owen Park | queued (pre-approved) | after WO-410 merged | `src/freemyid/doctor.py`; `tests/codex/test_cx_doctor_windows_home.py`; `VENDOR_STATUS.md` | 2026-11-09 E8 epic batch (appended by Morgan Reyes) |
| WO-412 | issue pending | Owen Park | queued (pre-approved) | after WO-411 merged | `src/freemyid/doctor.py`; `tests/codex/test_cx_doctor_browser_paths.py`; `VENDOR_STATUS.md` | 2026-11-09 E8 epic batch (appended by Morgan Reyes) |
| WO-413 | issue pending | Amara Okoye | queued (pre-approved) | none | `docs/i18n/STRINGS_ENGINE.md`; `VENDOR_STATUS.md` | 2026-11-09 E10 epic batch (appended by Morgan Reyes) |
| WO-414 | issue pending | Amara Okoye | queued (pre-approved) | after WO-214, WO-219, WO-225 merged | `docs/i18n/GLOSSARY_ES.md`; `VENDOR_STATUS.md` | 2026-11-09 E10 epic batch (appended by Morgan Reyes) |
| WO-415 | issue pending | Hannah Cole | queued (pre-approved) | after WO-290 merged | `docs/i18n/STRINGS_BACKEND.md`; `tests/codex/test_cx_i18n_backend_constants.py`; `VENDOR_STATUS.md` | 2026-11-09 E10 epic batch (appended by Morgan Reyes) |
| WO-416 | issue pending | Ravi Menon | blocked: needs in-house message-catalog module and a language setting first | after WO-403, WO-299, WO-415, WO-272, WO-274 merged | `src/freemyid/exposure_models.py`; `src/freemyid/engine/exposure_score.py`; `src/freemyid/engine/search_engines.py`; `tests/codex/test_cx_message_catalog_usage.py`; `VENDOR_STATUS.md` | 2026-11-09 E10 epic batch (appended by Morgan Reyes) |
| WO-417 | issue pending | Amara Okoye | blocked: needs an owner decision on the language of letters sent to brokers, and a native and legal read | none | `docs/i18n/LETTER_EXPLAINERS_ES.md`; `VENDOR_STATUS.md` | 2026-11-09 E10 epic batch (appended by Morgan Reyes) |
| WO-418 | issue pending | Hannah Cole | queued (pre-approved) | after WO-404 merged | `src/freemyid/checklist_state.py`; `tests/codex/test_cx_checkup_stale_ticks.py`; `VENDOR_STATUS.md` | 2026-11-09 E11 epic batch (appended by Morgan Reyes) |
| WO-419 | issue pending | Hannah Cole | queued (pre-approved) | after WO-418 merged | `src/freemyid/checklist_state.py`; `tests/codex/test_cx_checkup_summary.py`; `VENDOR_STATUS.md` | 2026-11-09 E11 epic batch (appended by Morgan Reyes) |
| WO-420 | issue pending | Ravi Menon | queued (pre-approved) | after WO-246, WO-282 merged | `src/freemyid/checklists.py`; `tests/codex/test_cx_checklist_source_age.py`; `VENDOR_STATUS.md` | 2026-11-09 E11 epic batch (appended by Morgan Reyes) |
| WO-421 | issue pending | Felix Grant | queued (pre-approved) | none | `tests/codex/test_cx_checklist_content_rules.py`; `VENDOR_STATUS.md` | 2026-11-09 E11 epic batch (appended by Morgan Reyes) |
| WO-422 | issue pending | Ravi Menon | queued (pre-approved) | after WO-277 merged | `src/freemyid/engine/matcher.py`; `tests/codex/test_cx_matcher_phone_forms.py`; `VENDOR_STATUS.md` | 2026-11-09 E12 epic batch (appended by Morgan Reyes) |
| WO-423 | issue pending | Felix Grant | queued (pre-approved) | after WO-402 merged | `tests/codex/test_cx_value_only_scan.py`; `VENDOR_STATUS.md` | 2026-11-09 E12 epic batch (appended by Morgan Reyes) |
| WO-424 | issue pending | Ravi Menon | blocked: needs an owner and safety decision, a data model and a sourced data file from in-house first | after WO-246, WO-284, WO-297 merged | `src/freemyid/engine/law_matrix.py`; `tests/codex/test_cx_acp_lookup.py`; `VENDOR_STATUS.md` | 2026-11-09 E12 epic batch (appended by Morgan Reyes) |


## Active checkpoint — 2026-11-09 / CODEX-170

This checkpoint supersedes stale WIP counts above; historical rows are retained.
Away-week rules exclude held/runtime-blocked work from active building.

| Work order | Owner | Current state | Reserved paths |
| --- | --- | --- | --- |
| WO-238 (issue pending) | Imani Reid | Runtime-blocked; required checks incomplete; skipped | Existing WO scope only |
| WO-239 (issue pending) | Imani Reid | Runtime-blocked; required checks incomplete; skipped | Existing WO scope only |
| WO-240 (issue pending) | Imani Reid | Runtime-blocked; required checks incomplete; skipped | Existing WO scope only |
| WO-242 (issue pending) | Ravi Menon | Held for in-house acceptance/test conflict; skipped | Existing WO scope only |
| WO-245 (issue pending) | Hannah Cole | Started; predecessor WO-233 (freemyid-pm#199) delivered | `src/freemyid/engine/nicknames.py`; `tests/codex/test_cx_nickname_table.py`; worktree status |
| WO-247 (issue pending) | Owen Brooks, reviewer | Existing implementation under independent review | `tests/codex/test_cx_paths_cross_platform.py`; worktree status |
| WO-248 (issue pending) | Owen Park | Started | `tests/codex/test_cx_firstrun_browser.py`; worktree status |

Active WIP: 3/5, including review. Prepared worktree branch pointers verified without git.
WO-245 starts under AGENT_CHANNEL.md away-week rule 3: delivery satisfies start-after.
WO-233 was test-only, so no predecessor product changes require copying.
Nora owns coordination files; builders write only their WO scopes. CODEX-X-008 acknowledges
GROK-X-006; coordination makes no shared-path changes or work assignments.


## Dispatch checkpoint — 2026-11-09 / CODEX-171

- WO-245 (issue pending): builder complete; 691 passed, Ruff clean; Owen review pending.
- WO-247 (issue pending): review correction complete; 10 passed, Ruff clean; Owen re-review pending.
- WO-248 (issue pending): builder complete; 20 passed, Ruff clean; Owen review pending.
- WO-249 (issue pending): started with Felix Grant in prepared `.vendor-wt/wo-249`; reserved `tests/codex/test_cx_draft_edit_roundtrip.py` and worktree `VENDOR_STATUS.md` only.
- WO-250 (issue pending): started with Amara Okoye in prepared `.vendor-wt/wo-250`; reserved `docs/i18n/STRINGS_APP.md` and worktree `VENDOR_STATUS.md` only.
- Active WIP 5/5 including reviews. Earlier blocked/held orders remain skipped. No next order starts before delivery frees a slot. No overlapping writable paths.


## Delivery checkpoint — 2026-11-09 / CODEX-172

| Work order | Current state | Independent checks | Scope evidence |
| --- | --- | --- | --- |
| WO-245 (issue pending) | Delivered for in-house review; Owen PASS | 691 passed; Ruff clean | New nickname-table test and status; product source unchanged |
| WO-247 (issue pending) | Delivered for in-house review; Owen PASS after AC5 correction | 10 passed; Ruff clean | Cross-platform test and status only |
| WO-248 (issue pending) | Delivered for in-house review; Owen PASS | 20 passed; Ruff clean | First-run test and status only |

Nora compared pre-dispatch and post-review SHA-256 fingerprints of visible regular files
outside each allowed scope: unchanged (1,284 / 1,285 / 1,285 files respectively).
This is a session scope check, not git history verification; hidden/ignored files are not
included. No native Windows run claimed. Active WIP 2/5: WO-249 (issue pending) and
WO-250 (issue pending). Four earlier held/runtime-blocked orders remain skipped.


## Delivery and publishing checkpoint — 2026-11-09 / CODEX-173

- WO-249 (issue pending): delivered for in-house review; Owen PASS; 734 passed, 102 strict xfailed, zero skipped; Ruff clean. Six edit-loss categories reported, no product edits.
- WO-250 (issue pending): delivered for in-house review; Owen PASS; 14 passed; 45 citation spans manually checked, explicit guard zero findings; no source changes. CLI inventory link awaits predecessor integration.
- Outside-scope visible-file SHA-256 fingerprints unchanged for both worktrees (1,285 files each). Active WIP 0/5. Existing held/runtime-blocked orders remain incomplete.
- Owner explicitly authorized commits, pushes to origin and PR creation in this session, superseding the earlier vendor prohibition for publishing. Owner explicitly forbids pushing main. Nora publishes only reviewed `vendor/wo-245`, `vendor/wo-247`, `vendor/wo-248`, `vendor/wo-249`, `vendor/wo-250`; draft PRs target main, without merging. Remote confirmation pending.


## Remote publishing confirmed — 2026-11-09 / CODEX-174

All five orders are delivered for in-house review, committed and pushed to origin;
all PRs are open drafts targeting main, with no merge. Active WIP 0/5.

| Work order | Remote branch | Commit | Draft PR | Independent local checks |
| --- | --- | --- | --- | --- |
| WO-245 (issue pending) | `vendor/wo-245` | `6ae87e2` | https://github.com/FreeMyID/freemyid/pull/73 | 691 passed; Ruff clean |
| WO-247 (issue pending) | `vendor/wo-247` | `3e1566a` | https://github.com/FreeMyID/freemyid/pull/74 | 10 passed; Ruff clean |
| WO-248 (issue pending) | `vendor/wo-248` | `2affc61` | https://github.com/FreeMyID/freemyid/pull/75 | 20 passed; Ruff clean |
| WO-249 (issue pending) | `vendor/wo-249` | `51e81a3` | https://github.com/FreeMyID/freemyid/pull/76 | 734 passed, 102 strict xfailed; Ruff clean |
| WO-250 (issue pending) | `vendor/wo-250` | `61c526f` | https://github.com/FreeMyID/freemyid/pull/77 | 14 passed; 45 citation spans, zero findings |

GitHub confirms exactly two allowed files per PR. Local worktrees are clean; each HEAD,
upstream and PR head match. Company noreply metadata checks pass on all final heads;
initial placeholder author emails were corrected with exact-SHA force-with-lease updates
of our own vendor refs only, with unchanged file trees. Build CI is queued/running, not
reported passed. Main remains `f6e75d5`; no push to main or merge was performed.
CODEX-X-009 updates Grok; acknowledgment of CODEX-X-008/009 is still outstanding.
Main-checkout coordination notes remain local; unrelated dirty files were not staged.


## Team continuation — 2026-11-09 / CODEX-175

Standing user authorization now permits fetch/pull, commits, vendor-branch pushes and
PR creation/update throughout development. No push to main or PR merge is authorized.
Fetched origin; clean prepared worktrees fast-forwarded from origin/main before dispatch.

| Work order | Builder | State | Allowed writes |
| --- | --- | --- | --- |
| WO-251 (issue pending) | Amara Okoye | Started under away-week delivered-predecessor rule; WO-225 (freemyid-pm#207) delivered | New `tests/codex/test_cx_glossary_es_consistency.py`; worktree status |
| WO-252 (issue pending) | Kai Nakamura | Started | New `docs/dev/STATE_MACHINE.md`; worktree status |
| WO-253 (issue pending) | Kai Nakamura, separate session | Started | New `docs/dev/PROOF_VAULT.md`; worktree status |

WIP 3/5. No concurrent shared-file edits. WO-251 will test its own base glossary and
inspect the delivered predecessor read-only; glossary edits are outside its allowed paths.
Earlier runtime-blocked/held orders remain skipped. Grok acknowledged CODEX-X-008/009 in
GROK-X-007: no path concern; publishing its own delivered branches, no main push.
Prior PRs #73..77 remain open drafts; email checks pass, build CI still queued.


## Backend start checkpoint — 2026-11-09 / CODEX-176

- WO-251 (issue pending): building. After origin/main fast-forward its glossary is byte-identical to delivered WO-225 (freemyid-pm#207), so no glossary integration limitation remains.
- WO-252 and WO-253 (issue pending each): builder complete; independent Owen review underway. Required pytest 14 passed per worktree; new guides have 24 and 25 verified citation spans respectively.
- WO-254 (issue pending): skipped for now because its required CLI/app inventory inputs are absent from origin/main and copying them would exceed its test-only allowed paths. Delivered predecessors WO-232 and WO-250 (issue pending each) await integration; no broad fixture substitution or out-of-path copy.
- WO-255 (issue pending): next once its final prerequisite guide deliveries finish; generic glob guard can be implemented within its allowed test file.
- WO-256 (issue pending): started with Imani Reid; prepared clean vendor branch refreshed from origin/main. Allowed writes `src/freemyid/monitor.py`, `tests/codex/test_cx_monitor_previous_hardening.py`, worktree status. Predecessor WO-226 (freemyid-pm#208) is delivered and its test is now in the refreshed base.
- WIP 4/5 including review. No path collision; earlier held/runtime-blocked orders remain skipped.


## Guide delivery and guard dispatch — 2026-11-09 / CODEX-177

- WO-252 (issue pending): delivered for in-house review; Owen PASS; required pytest14passed,24citations/zero findings,24Mermaid edges exact TRANSITIONS. Visible outside-scope fingerprint unchanged (1,395 files).
- WO-253 (issue pending): delivered for in-house review; Owen PASS; required pytest14passed,25citations/34ranges/zero findings. Visible outside-scope fingerprint unchanged (1,395 files).
- WO-255 (issue pending): started with Hannah Cole after all named prerequisite WOs delivered under away-week rules; clean vendor branch refreshed from origin/main. Writes only `tests/codex/test_cx_dev_source_citations.py` and worktree status. Implement glob over its own docs; validate delivered predecessor docs read-only separately where useful, with integration limits explicit. No out-of-path copying.
- WO-251 (issue pending): independent review pending; WO-256 (issue pending): backend fix building. WIP3/5 including review. WO-254 (issue pending) still skipped for absent required inventory inputs.


## Review and publication checkpoint — 2026-11-09 / CODEX-178

- WO-251 (issue pending): delivered for in-house review; Owen PASS;52passed,0skipped/xfail,Ruffclean;115glossaryrows/7guideterms checked. Outside-scope visible-file fingerprint unchanged (1,395files). Commit/push/PR next.
- WO-252 (issue pending): pushed `vendor/wo-252`, `59a45f5`; draft PR https://github.com/FreeMyID/freemyid/pull/108.
- WO-253 (issue pending): pushed `vendor/wo-253`, `e06f769`; draft PR https://github.com/FreeMyID/freemyid/pull/109.
- Both guide commits passed local noreply guard and contain only their new guide/status. Remote CI verification pending.
- WIP2/5: WO-255 and WO-256 (issue pending each), both building. No main push/PR merge.


## Nora restart — 2026-11-10 / CODEX-179

- WO-255 (issue pending): existing builder output in independent read-only Owen review; allowed test and status only.
- WO-256 (issue pending): existing monitor fix in independent read-only Owen review; allowed monitor module, hardening test and status only.
- WIP 2/5. Jules audits next eligible work and tracker IDs before dispatch. No duplicate builders or new scope.
- Grok coordination posted as CODEX-X-011; acknowledgment pending, relay requested. No new GitHub/CI result claimed.


## Reviewed deliveries and next dispatch — 2026-11-10 / CODEX-180

- WO-255 (issue pending): Owen PASS; 17 passed, Ruff clean; 132 predecessor citation spans checked with zero findings. Delivered for in-house review. Five missing prerequisite docs and native Windows remain integration limits.
- WO-256 (issue pending): Owen PASS; 89 passed, Ruff clean; monitor contracts unchanged. Delivered for in-house review. Status citation correction: validator currently monitor.py:329–337. Native Windows/full suite unverified. Reviewers lacked pre-dispatch fingerprints for whole-tree scope certification.
- WO-271 (issue pending): Ravi started in prepared .vendor-wt/wo-271 after delivered WO-256/226/211 under away-week rules. Writes only src/freemyid/monitor.py, tests/codex/test_cx_monitor_relist.py and worktree status. Read-only predecessor monitor source may be copied into the allowed module; predecessor tests cannot be copied outside scope.
- WO-272 (issue pending): separate Ravi session started in prepared .vendor-wt/wo-272. Writes only src/freemyid/engine/exposure_score.py, tests/codex/test_cx_exposure_score_edges.py and worktree status.
- WIP 2/5; no path collision. WO-254,257–260 remain skipped for existing dependency/contract holds; WO-261–269 are not queue entries. WO-233 tracker correction: current map is freemyid-pm#215.


## Partial delivery checkpoint — 2026-11-10 / CODEX-182

- WO-271 (issue pending): independently reviewed partial delivery. New tests 47 passed; required monitor selection 119 passed, 1 strict XPASS failure from carried-forward WO-256 fix and old out-of-scope xfail; Ruff passed. Helper unwired, listing input source unresolved. Scope hash audit clean.
- WO-272 (issue pending): independently reviewed partial/spec-exception delivery. New tests 28 passed; required broad selection 65 passed, 4 socket PermissionError fixture failures; Ruff passed. Literal AC3 direction conflict remains explicit. Scope hash audit clean.
- WIP 0/5; next eligible WO-273/274 (issue pending each). In-house review/integration pending; no full-suite/native Windows claim, no publication/merge.
- Latest Grok inbound GROK-X-008 acknowledged in CODEX-X-013; CODEX-X-014 reports this checkpoint.


## Continued queue dispatch — 2026-11-10 / CODEX-183

- WO-273 (issue pending): Hannah Cole started in prepared wo-273; allowed listing_finder.py, tests/codex/test_cx_listing_finder_errors.py, status only.
- WO-274 (issue pending): Felix Grant started in prepared wo-274; allowed search_engines.py, tests/codex/test_cx_search_engine_links.py, status only.
- WO-281 (issue pending): Owen Park started in prepared wo-281; allowed checklist_state.py, tests/codex/test_cx_checklist_state_recovery.py, status only (builder must confirm exact WO test path before edits).
- WIP 3/5. WO-275 waits for 284; 276/277/278/280 wait on held chain; 279 and 283 blocked. No shared-file overlap. No git/network/install; existing worktree bases retained with limits recorded.


## Review rotation and next dispatch — 2026-11-10 / CODEX-185

- WO-273/274/281 (issue pending each): builders complete, independent Owen review. No delivery claim yet.
- WO-282 (issue pending): Hannah, separate session, started in prepared wo-282 after delivered WO-246 under away-week rule. Exact writes checklists.py, tests/codex/test_cx_checklist_validation.py, status. Carry forward only allowed checklists.py predecessor, inspect predecessor tests read-only.
- WIP 4/5 including reviews. WO-284 next eligible once slot frees; no shared-file collision.


## Recovery review and lookup dispatch — 2026-11-10 / CODEX-186

- WO-281 (issue pending): Owen partial review PASS;13 new/24 direct tests passed,Ruff passed; source unchanged. Required wizard-inclusive run interrupted, JSON/atomic criteria unsupported. Delivered partial for in-house review.
- WO-284 (issue pending): Ravi started prepared wo-284 after delivered WO-246, exact law_matrix.py, tests/codex/test_cx_law_matrix_lookup.py,status. Carry forward only allowed predecessor module; no data edits or external lookup.
- WIP 4/5:273/274 review,282 build,284 build.


## Interactive-path partial deliveries and selector dispatch — 2026-11-10 / CODEX-187

- WO-273 (issue pending): Owen partial PASS;15focused pass,Ruff clean; broader39pass/11socket failures/1browser skip. API limits explicit.
- WO-274 (issue pending): Owen partial PASS;34new/22existing pass,Ruff clean; source unchanged; wizard-inclusive required run incomplete. Missing name-builder contract explicit.
- WO-281 (issue pending): partial already delivered; independent review final confirms13new/24direct pass,Ruff clean.
- WO-285 (issue pending): Owen Park started prepared wo-285 after delivered WO-243 under away-week rule. Only htmlsel.py,new tests/codex/test_cx_htmlsel_performance.py,status. Carry predecessor module only if needed, no out-of-path test copies.
- WIP3/5:282,284,285 building. No shared-file overlap.


## Performance queue continuation — 2026-11-10 / CODEX-188

- WO-282/284/285 (issue pending each): builders complete/finalizing, independent review underway.
- WO-286 (issue pending): Hannah started prepared wo-286 after delivered WO-245, exact nicknames.py,new tests/codex/test_cx_nickname_index.py,status. Allowed predecessor module only; table integrity tests inspect read-only if absent, no test copy.
- WIP4/5 including reviews; no path collision. Current tracker numbers still pending.


## Validation deliveries and pipeline documentation — 2026-11-10 / CODEX-189

- WO-282 (issue pending): independent PASS;18focused/3broad/5read-only predecessor checklist cases passed,Ruff clean. Full predecessor matrix portion and native Windows not claimed. Delivered for review.
- WO-284 (issue pending): independent code PASS, partial AC4 integration;30focused/30broad/48existing letters passed,Ruff clean. Complete predecessor246 suite absent; no out-of-path test copy. Delivered partial for review.
- WO-288 (issue pending): Kai started prepared wo-288; only docs/dev/EXPOSURE_PIPELINE.md,status. Document actual worktree source and explicitly distinguish held future changes; no code changes.
- WIP3/5:285review,286build,288build. WO287 skipped on held278. WO275 now dependency-delivered but cross-module lookup integration requires scope check before builder dispatch.


## Selector delivery — 2026-11-10 / CODEX-190

- WO-285 (issue pending): independent PASS;10focused/12broad/26read-only predecessor grammar cases passed,Ruff clean. Source unchanged delivered243. Scope clean. Delivered for in-house review; Windows/full combined tree unverified.
- WIP2/5:286,288building.


## Nickname partial delivery — 2026-11-10 / CODEX-191

- WO-286 (issue pending): independent partial/spec-exception PASS;203focused,required plural selector1passed/2901deselected,Ruff clean;623read-only predecessor cases and32matcher-variant cases independently passed. Builder supplemental combined68passed.200goldens exactly match predecessor. Set iteration order AC unmet;deterministic membership/public set preserved.
- WIP1/5:288building/review next. No new dispatch yet.


## Remaining-time documentation dispatch — 2026-11-10 / CODEX-192

- User reports about25minutes left; prioritize reviewable bounded work and handoff.
- WO-289 (issue pending): Kai,separate session,started prepared wo-289; only docs/dev/MATCHING.md,status. Source snapshot/held age-range work explicit; exact citations and fake worked examples.
- WIP2/5:288building/review,289building. Required broad checks bounded on known TestClient issue; no false pass claims.


## Pipeline guide delivery — 2026-11-10 / CODEX-193

- WO-288 (issue pending): independent PASS;147lines30citation spans47ranges checked manually/explicit helper zero findings,14citation tests/Ruff passed. Required selection independently201passed63Chromium TargetClosedError skips4deselected1known SEC125 xfailed,exit0. Skips/xfail notpasses. Delivered for in-house review.
- WIP1/5:289building/review.


## Time-limit checkpoint — 2026-11-10 / CODEX-194

- WOs 273/274/281/282/284/285/286/288/289 status is in CODEX-182..193 and each worktree VENDOR_STATUS.md; 282/285/288/289 independently reviewed, 284 code review passed with integration limit; 273/274/281/286 partial/spec limits remain.
- No push attempted: AGENTS.md prohibits vendor Git/push. Owner tooling publishes reviewed changes.
- Resume with issue-map sync, in-house review/integration, Windows and combined-tree reruns, then remaining eligible queue.
