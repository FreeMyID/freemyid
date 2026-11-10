# Grok vendor board

Sole writer: the Grok vendor session. Path guard for WO-3NN only. Codex's `BOARD.md` is Nora's. This board grants no extra edit permission.

Last checkpoint: 2026-11-09. WO-301..305 delivered in their worktrees (GROK-007). Checks confirmed in this session. Nothing merged. WO-306..310 started. Code WOs WO-331..340 stay closed. First-start sentence: "The first time can take up to a minute. Please wait; there is no need to click it again."

| Work order | Status | Reserved paths | Last update |
| --- | --- | --- | --- |
| WO-301 | delivered (issue pending) | `docs/user/INSTALL.md`; `docs/user/troubleshooting.md` | 2026-11-09 checks 570 passed, 27 skipped, 1 xfailed |
| WO-302 | delivered (issue pending) | `docs/USER_GUIDE.md` | 2026-11-09 checks 562 passed, 66 skipped, 1 xfailed |
| WO-303 | delivered (issue pending) | `docs/CLI.md` | 2026-11-09 checks 219 passed, 1 skipped |
| WO-304 | delivered (issue pending) | `docs/user/GLOSSARY.md` | 2026-11-09 checks 656 passed, 17 skipped, 1 xfailed |
| WO-305 | delivered (issue pending) | `tests/grok/test_gk_user_doc_claims.py`; `tests/grok/__init__.py` | 2026-11-09 checks 7 passed, 12 xfailed; ruff clean |
| WO-306 | in progress | `FAMILY_QUICK_START.md` | 2026-11-09 start |
| WO-307 | in progress | `docs/user/HELPING.md` | 2026-11-09 start |
| WO-308 | in progress | `distro/*/README.md` (five files) | 2026-11-09 start |
| WO-309 | in progress | `tests/grok/test_gk_doc_labels_exist.py` | 2026-11-09 start |
| WO-310 | in progress, on a copy of WO-301's troubleshooting page | `docs/user/troubleshooting.md` | 2026-11-09 start |

WIP 5/5 on WO-306..310. WO-329 waits until WO-304's glossary is copied onto that worktree. WO-330 waits for Morgan's rebase note. WO-331..340 wait for the code lane.

## In-house additions, CLAUDE-G-004 (Morgan Reyes, 2026-11-09)

Rows added by in-house when the batch was issued. Helen Ashford owns them from here: update the Status column as work starts and is delivered. Issue numbers: pending until the next tracker sync. WIP limit 5 across all rows.

| Work order | Status | Reserved paths | Agent | Last update |
| --- | --- | --- | --- | --- |
| WO-311 | queued (pre-approved) | `docs/user/whats-new-0.3.md` | Simon Fairley | 2026-11-09 CLAUDE-G-004 |
| WO-312 | queued (pre-approved) | `docs/user/what-to-do-when.md` | Linda Moreau | 2026-11-09 CLAUDE-G-004 |
| WO-313 | queued (pre-approved) | `docs/user/is-this-you.md` | Simon Fairley | 2026-11-09 CLAUDE-G-004 |
| WO-314 | queued (pre-approved) | `docs/user/practice-mode.md` | Margaret Lund | 2026-11-09 CLAUDE-G-004 |
| WO-315 | queued (pre-approved) | `docs/user/google-and-bing.md` | Simon Fairley | 2026-11-09 CLAUDE-G-004 |
| WO-316 | queued (pre-approved) | `docs/user/protect-yourself.md` | Wesley Tran | 2026-11-09 CLAUDE-G-004 |
| WO-317 | queued (pre-approved) | `docs/user/larger-text.md` | Rosa Delgado | 2026-11-09 CLAUDE-G-004 |
| WO-318 | queued (pre-approved) | `docs/user/never-asks.md` | Linda Moreau | 2026-11-09 CLAUDE-G-004 |
| WO-319 | queued (pre-approved) | `docs/user/printable-checklist.md` | Margaret Lund | 2026-11-09 CLAUDE-G-004 |
| WO-320 | queued (pre-approved) | `docs/user/helping-by-phone.md` | Linda Moreau | 2026-11-09 CLAUDE-G-004 |
| WO-321 | queued (pre-approved) | `tests/grok/test_gk_reading_level.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-004 |
| WO-322 | queued (pre-approved) | `tests/grok/test_gk_links_gaps.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-004 |
| WO-323 | queued (pre-approved) | `tests/grok/test_gk_root_doc_citations.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-004 |
| WO-324 | queued (pre-approved) | `tests/grok/test_gk_never_asks_user_docs.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-004 |
| WO-325 | queued (pre-approved) | `tests/grok/test_gk_markdown_a11y.py` | Rosa Delgado | 2026-11-09 CLAUDE-G-004 |
| WO-326 | queued (pre-approved) | `docs/user/mail-gmail.md`; `docs/user/mail-proton.md`; `docs/user/mail-other.md` | Wesley Tran | 2026-11-09 CLAUDE-G-004 |
| WO-327 | queued (pre-approved) | `distro/nix/README.md`; `distro/CHECKLIST.md` | Wesley Tran | 2026-11-09 CLAUDE-G-004 |
| WO-328 | queued (pre-approved) | `tests/grok/test_gk_distro_readme_matches_recipe.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-004 |
| WO-329 | queued (pre-approved); start after WO-304 is delivered | `docs/user/GLOSSARY.md` | Margaret Lund | 2026-11-09 CLAUDE-G-004 |
| WO-330 | queued (pre-approved); start last, after WO-301 and WO-311..320 merge and in-house rebases it | `docs/user/help-topics.md`; `docs/user/INSTALL.md` | Simon Fairley | 2026-11-09 CLAUDE-G-004 |
| WO-331 | queued (pre-approved); waits for the code lane to open | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_reply_matcher.py` | Paul Kessler | 2026-11-09 CLAUDE-G-004 |
| WO-332 | queued (pre-approved); waits for the code lane to open | `src/freemyid/engine/outbox.py`; `tests/grok/test_gk_outbox_retry.py` | Paul Kessler | 2026-11-09 CLAUDE-G-004 |
| WO-333 | queued (pre-approved); waits for the code lane to open | `src/freemyid/notify.py`; `src/freemyid/engine/handoff.py`; `tests/grok/test_gk_notify_throttle.py` | Paul Kessler | 2026-11-09 CLAUDE-G-004 |
| WO-334 | queued (pre-approved); waits for the code lane to open | `src/freemyid/scheduler/render.py`; `src/freemyid/scheduler/__init__.py`; `tests/grok/test_gk_scheduler_catchup.py` | Derek Olsen | 2026-11-09 CLAUDE-G-004 |
| WO-335 | queued (pre-approved); code lane must open; start after WO-334 is delivered | `src/freemyid/scheduler/status_parse.py`; `src/freemyid/scheduler/__init__.py`; `tests/grok/test_gk_scheduler_status.py` | Derek Olsen | 2026-11-09 CLAUDE-G-004 |
| WO-336 | queued (pre-approved); waits for the code lane to open | `src/freemyid/setup_config.py`; `tests/grok/test_gk_setup_config_messages.py` | Derek Olsen | 2026-11-09 CLAUDE-G-004 |
| WO-337 | queued (pre-approved); waits for the code lane to open | `src/freemyid/submitters/web_form.py`; `src/freemyid/submitters/assisted.py`; `tests/grok/test_gk_web_form_fallback.py` | Paul Kessler | 2026-11-09 CLAUDE-G-004 |
| WO-338 | queued (pre-approved); waits for the code lane to open | `src/freemyid/engine/filler.py`; `tests/grok/test_gk_filler_classify.py` | Derek Olsen | 2026-11-09 CLAUDE-G-004 |
| WO-339 | queued (pre-approved); waits for the code lane to open | `src/freemyid/submitters/base.py`; `tests/grok/test_gk_data_minimization.py` | Paul Kessler | 2026-11-09 CLAUDE-G-004 |
| WO-340 | queued (pre-approved); waits for the code lane to open | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_no_pii.py` | Derek Olsen | 2026-11-09 CLAUDE-G-004 |
| WO-341 | queued (pre-approved); after WO-331 merged | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_classify_reply.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-342 | queued (pre-approved); after WO-332 merged | `src/freemyid/engine/outbox.py`; `tests/grok/test_gk_outbox_idempotent.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-343 | queued (pre-approved); none | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_escalation_due.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-344 | queued (pre-approved); none | `src/freemyid/engine/mail_tls.py`; `tests/grok/test_gk_mail_tls_reasons.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-345 | queued (pre-approved); none | `src/freemyid/engine/tiers.py`; `tests/grok/test_gk_tier_reason.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-346 | queued (pre-approved); none | `src/freemyid/engine/plugins.py`; `tests/grok/test_gk_plugins_robust.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-347 | queued (pre-approved); none | `src/freemyid/engine/fill_for_me.py`; `tests/grok/test_gk_fill_for_me_reasons.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-348 | queued (pre-approved); none | `src/freemyid/submitters/email.py`; `tests/grok/test_gk_email_submitter_reasons.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-349 | queued (pre-approved); after WO-333 merged | `src/freemyid/notify.py`; `tests/grok/test_gk_notify_missing_backend.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-350 | queued (pre-approved); none | `src/freemyid/scheduler/pathcheck.py`; `tests/grok/test_gk_scheduler_pathcheck.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-351 | queued (pre-approved); after WO-334 merged | `src/freemyid/scheduler/render.py`; `tests/grok/test_gk_scheduler_render_escape.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-352 | queued (pre-approved); after WO-336 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_setup_config_helper_safety.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-353 | queued (pre-approved); after WO-337 merged | `src/freemyid/submitters/web_form.py`; `tests/grok/test_gk_web_form_timeouts.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-354 | queued (pre-approved); after WO-338 merged | `src/freemyid/engine/filler.py`; `tests/grok/test_gk_filler_ambiguity.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-355 | queued (pre-approved); after WO-333, WO-343 merged | `src/freemyid/engine/handoff.py`; `tests/grok/test_gk_handoff_overdue.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-356 | blocked: needs in-house contract change first (interfaces.py (result type) and schema/ (new reason field)) | `src/freemyid/submitters/base.py`; `tests/grok/test_gk_submit_reason_codes.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-357 | blocked: needs in-house contract change first (schema/ and the --json contract (new field, version bump)) | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_reason.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-358 | queued (pre-approved); none | `docs/user/site-ignores-request.md` | Linda Moreau | 2026-11-09 CLAUDE-G-006 |
| WO-359 | queued (pre-approved); after WO-334, WO-351 merged | `tests/grok/test_gk_scheduler_cross_os.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-006 |
| WO-360 | queued (pre-approved); none | `tests/grok/test_gk_backend_offline_guard.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-006 |
| WO-501 | queued (pre-approved); after WO-336, WO-352 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_validate.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-502 | queued (pre-approved); after WO-501 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_plan.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-503 | queued (pre-approved); after WO-502 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_to_setup.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-504 | queued (pre-approved); after WO-503 merged | `tests/grok/test_gk_bundle_roundtrip.py` | Ethan Brandt | 2026-11-09 E1 epic batch |
| WO-505 | blocked: needs in-house schema, cli.py command and docs/CLI.md section first; after WO-340, WO-357, WO-502 merged | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_bundle.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-506 | blocked: needs in-house crypto change first (typed errors and a format version in the bundle header); after WO-503 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_open.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-507 | queued (pre-approved); after WO-343 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_complaint_links.py` | Derek Olsen | 2026-11-09 E3 epic batch |
| WO-508 | queued (pre-approved); after WO-507 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_escalation_waiting_events.py` | Derek Olsen | 2026-11-09 E3 epic batch |
| WO-509 | queued (pre-approved); none | `tests/grok/test_gk_outbox_legal_demand_gate.py` | Ethan Brandt | 2026-11-09 E3 epic batch |
| WO-510 | queued (pre-approved); after WO-341 merged | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_imap_fetch.py` | Paul Kessler | 2026-11-09 E4 epic batch |
| WO-511 | queued (pre-approved); after WO-510 merged | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_poll_retry.py` | Paul Kessler | 2026-11-09 E4 epic batch |
| WO-512 | queued (pre-approved); after WO-333, WO-349 merged | `src/freemyid/notify.py`; `tests/grok/test_gk_notify_monthly_counts.py` | Derek Olsen | 2026-11-09 E4 epic batch |
| WO-513 | queued (pre-approved); after WO-508 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_broker_timeout.py` | Derek Olsen | 2026-11-09 E4 epic batch |
| WO-514 | queued (pre-approved); after WO-513 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_error_backoff.py` | Derek Olsen | 2026-11-09 E4 epic batch |
| WO-515 | queued (pre-approved); after WO-511 merged | `tests/grok/test_gk_mailer_fake_protocols.py` | Ethan Brandt | 2026-11-09 E4 epic batch |
| WO-516 | blocked: needs in-house schema, cli.py command and docs/CLI.md section first; after WO-340, WO-357, WO-505, WO-299, WO-401 merged | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_report_facts.py` | Derek Olsen | 2026-11-09 E5 epic batch |
| WO-517 | queued (pre-approved); after WO-512 merged | `src/freemyid/notify.py`; `tests/grok/test_gk_notify_relisted.py` | Derek Olsen | 2026-11-09 E5 epic batch |
