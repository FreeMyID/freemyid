# Grok vendor board

Sole writer: the Grok vendor session. Path guard for WO-3NN only. Codex's `BOARD.md` is Nora's. This board grants no extra edit permission.

Last checkpoint: 2026-11-09. Owner said push vendor branches and open pull requests, never main, and then said to pull those remote branches and keep using push and pull while the work is open. Draft pull requests #78 through #106 are open for WO-301 through WO-329 (WO-301 is #78, WO-328 is #105, WO-329 is #106). Those branches and `vendor/grok-channel` were pulled with fast-forward only. They were already up to date. `main` was not pulled and was not pushed. WO-330 was not started. Code lane still not started. CODEX-X-010 was read and needs no reply.

| Work order | Status | Reserved paths | Last update |
| --- | --- | --- | --- |
| WO-301 | delivered (issue pending) | `docs/user/INSTALL.md`; `docs/user/troubleshooting.md` | 2026-11-09 checks 570 passed, 27 skipped, 1 xfailed |
| WO-302 | delivered (issue pending) | `docs/USER_GUIDE.md` | 2026-11-09 checks 562 passed, 66 skipped, 1 xfailed |
| WO-303 | delivered (issue pending) | `docs/CLI.md` | 2026-11-09 checks 219 passed, 1 skipped |
| WO-304 | delivered (issue pending) | `docs/user/GLOSSARY.md` | 2026-11-09 checks 656 passed, 17 skipped, 1 xfailed |
| WO-305 | delivered (issue pending) | `tests/grok/test_gk_user_doc_claims.py`; `tests/grok/__init__.py` | 2026-11-09 checks 7 passed, 12 xfailed; ruff clean |
| WO-306 | delivered (issue pending) | `FAMILY_QUICK_START.md` | 2026-11-09 checks 571 passed, 18 skipped, 1 xfailed |
| WO-307 | delivered (issue pending) | `docs/user/HELPING.md` | 2026-11-09 checks 620 passed, 17 skipped, 1 xfailed |
| WO-308 | delivered (issue pending) | `distro/aur/README.md`; `distro/flatpak/README.md`; `distro/homebrew/README.md`; `distro/scoop/README.md`; `distro/winget/README.md` | 2026-11-09 lint 26 passed; distro filter 23 passed |
| WO-309 | delivered (issue pending) | `tests/grok/test_gk_doc_labels_exist.py`; `tests/grok/__init__.py` | 2026-11-09 checks 14 passed, 3 xfailed; ruff clean |
| WO-310 | delivered (issue pending) | `docs/user/troubleshooting.md` | 2026-11-09 checks 560 passed, 17 skipped, 1 xfailed |

WIP 0/5. WO-301 through WO-329 are delivered. Draft pull requests #78 through #106 are open and their branches are up to date with origin. WO-330 waits for Morgan's rebase note. Code work orders are not started. WO-331..340 wait for the code lane.

## In-house additions, CLAUDE-G-004 (Morgan Reyes, 2026-11-09)

Rows added by in-house when the batch was issued. Helen Ashford owns them from here: update the Status column as work starts and is delivered. Issue numbers: pending until the next tracker sync. WIP limit 5 across all rows.

| Work order | Status | Reserved paths | Agent | Last update |
| --- | --- | --- | --- | --- |
| WO-311 | delivered (issue pending) | `docs/user/whats-new-0.3.md` | Simon Fairley | 2026-11-09 links 324 passed; one expected reachability failure |
| WO-312 | delivered (issue pending) | `docs/user/what-to-do-when.md` | Linda Moreau | 2026-11-09 links 370 passed; one expected reachability failure |
| WO-313 | delivered (issue pending) | `docs/user/is-this-you.md` | Simon Fairley | 2026-11-09 links 314 passed; one expected reachability failure |
| WO-314 | delivered (issue pending) | `docs/user/practice-mode.md` | Margaret Lund | 2026-11-09 links 344 passed; one expected reachability failure |
| WO-315 | delivered (issue pending) | `docs/user/google-and-bing.md` | Simon Fairley | 2026-11-09 links 364 passed; one expected reachability failure |
| WO-316 | delivered (issue pending) | `docs/user/protect-yourself.md` | Wesley Tran | 2026-11-09 links 306 passed; one expected reachability failure |
| WO-317 | delivered (issue pending) | `docs/user/larger-text.md` | Rosa Delgado | 2026-11-09 links 288 passed; one expected reachability failure |
| WO-318 | delivered (issue pending) | `docs/user/never-asks.md` | Linda Moreau | 2026-11-09 links 318 passed; one expected reachability failure |
| WO-319 | delivered (issue pending) | `docs/user/printable-checklist.md` | Margaret Lund | 2026-11-09 links 286 passed; one expected reachability failure |
| WO-320 | delivered (issue pending) | `docs/user/helping-by-phone.md` | Linda Moreau | 2026-11-09 links 364 passed; one expected reachability failure |
| WO-321 | delivered (issue pending) | `tests/grok/test_gk_reading_level.py` | Ethan Brandt | 2026-11-09 checks 8 passed; ruff clean; baseline empty |
| WO-322 | delivered (issue pending) | `tests/grok/test_gk_links_gaps.py` | Ethan Brandt | 2026-11-09 checks 22 passed; ruff clean |
| WO-323 | delivered (issue pending) | `tests/grok/test_gk_root_doc_citations.py` | Ethan Brandt | 2026-11-09 checks 56 passed, 6 xfailed; ruff clean |
| WO-324 | delivered (issue pending) | `tests/grok/test_gk_never_asks_user_docs.py` | Ethan Brandt | 2026-11-09 checks 24 passed; ruff clean |
| WO-325 | delivered (issue pending) | `tests/grok/test_gk_markdown_a11y.py` | Rosa Delgado | 2026-11-09 checks 102 passed, 1 xfailed; ruff clean |
| WO-326 | delivered (issue pending) | `docs/user/mail-gmail.md`; `docs/user/mail-proton.md`; `docs/user/mail-other.md` | Wesley Tran | 2026-11-09 checks 420 passed |
| WO-327 | delivered (issue pending) | `distro/nix/README.md`; `distro/CHECKLIST.md` | Wesley Tran | 2026-11-09 packaging and wording 64 passed |
| WO-328 | delivered (issue pending) | `tests/grok/test_gk_distro_readme_matches_recipe.py` | Ethan Brandt | 2026-11-09 checks 15 passed, 1 xfailed; ruff clean |
| WO-329 | delivered (issue pending) | `docs/user/GLOSSARY.md` | Margaret Lund | 2026-11-09 checks 410 passed |
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
| WO-505 | blocked: needs in-house schema, cli.py command and docs/CLI.md section first; none | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_bundle.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-506 | blocked: needs in-house crypto change first (typed errors and a format version in the bundle header); none | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_open.py` | Derek Olsen | 2026-11-09 E1 epic batch |
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
| WO-518 | queued (pre-approved); after WO-514 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_time_budget.py` | Derek Olsen | 2026-11-09 E6 epic batch |
| WO-519 | queued (pre-approved); none | `tests/grok/test_gk_filler_plan_minimization.py` | Ethan Brandt | 2026-11-09 E7 epic batch |
| WO-520 | queued (pre-approved); after WO-349 merged | `tests/grok/test_gk_notifications_pii_free.py` | Ethan Brandt | 2026-11-09 E7 epic batch |
| WO-521 | queued (pre-approved); none | `tests/grok/test_gk_setup_errors_no_values.py` | Ethan Brandt | 2026-11-09 E7 epic batch |
| WO-522 | queued (pre-approved); after WO-342 merged | `src/freemyid/engine/outbox.py`; `tests/grok/test_gk_outbox_compose_links.py` | Paul Kessler | 2026-11-09 E8 epic batch |
| WO-523 | queued (pre-approved); after WO-503 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_setup_windows_files.py` | Derek Olsen | 2026-11-09 E8 epic batch |
| WO-524 | queued (pre-approved); after WO-335, WO-350 merged | `src/freemyid/scheduler/__init__.py`; `tests/grok/test_gk_scheduler_run_helper.py` | Derek Olsen | 2026-11-09 E8 epic batch |
| WO-525 | queued (pre-approved); none | `tests/grok/test_gk_windows_import_safety.py` | Ethan Brandt | 2026-11-09 E8 epic batch |
| WO-526 | blocked: needs in-house to build the helper-bundle screens first (no label may be invented); after WO-506 merged | `docs/user/helper-prepares-setup.md` | Simon Fairley | 2026-11-09 E9 epic batch |
| WO-527 | blocked: needs in-house to build the open-a-setup-file screens first (no label may be invented); after WO-526 merged | `docs/user/open-a-setup-file.md` | Margaret Lund | 2026-11-09 E9 epic batch |
| WO-528 | blocked: needs in-house to build read-aloud and the full-wizard large-text pass first; none | `docs/user/read-aloud.md` | Simon Fairley | 2026-11-09 E9 epic batch |
| WO-529 | blocked: needs in-house to build the print-ready report page first; after WO-299 merged | `docs/user/printable-report.md` | Margaret Lund | 2026-11-09 E9 epic batch |
| WO-530 | queued (pre-approved); after WO-358 merged | `docs/user/listing-came-back.md` | Linda Moreau | 2026-11-09 E9 epic batch |
| WO-531 | queued (pre-approved); after WO-517 merged | `docs/user/monthly-update.md` | Linda Moreau | 2026-11-09 E9 epic batch |
| WO-532 | queued (pre-approved); none | `tests/grok/test_gk_value_only_runner.py` | Ethan Brandt | 2026-11-09 E12 epic batch |
