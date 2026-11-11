# Grok vendor board

Sole writer: the Grok vendor session. Path guard for WO-3NN only. Codex's `BOARD.md` is Nora's. This board grants no extra edit permission.

Last checkpoint: 2026-11-09. Owner said start the team, tie every pull request to its `FreeMyID/freemyid-pm` issue, and make those issues match this board. Draft pull requests #78 through #106 stay open for WO-301 through WO-329. `main` is not pulled and is not pushed. The code lane is open in `.grok/config.toml` and in `tools/vendor.sh` (`GROK_LANE` includes the delivery files; `DENY_PREFIXES` does not refuse them). WO-330 still waits for Morgan's rebase note. CODEX-X-010 was read and needs no reply.

| Work order | Status | Reserved paths | Last update |
| --- | --- | --- | --- |
| WO-301 (freemyid-pm#218) | delivered | `docs/user/INSTALL.md`; `docs/user/troubleshooting.md` | 2026-11-09 checks 570 passed, 27 skipped, 1 xfailed; draft PR #78 |
| WO-302 (freemyid-pm#219) | delivered | `docs/USER_GUIDE.md` | 2026-11-09 checks 562 passed, 66 skipped, 1 xfailed; draft PR #79 |
| WO-303 (freemyid-pm#220) | delivered | `docs/CLI.md` | 2026-11-09 checks 219 passed, 1 skipped; draft PR #80 |
| WO-304 (freemyid-pm#221) | delivered | `docs/user/GLOSSARY.md` | 2026-11-09 checks 656 passed, 17 skipped, 1 xfailed; draft PR #81 |
| WO-305 (freemyid-pm#222) | delivered | `tests/grok/test_gk_user_doc_claims.py`; `tests/grok/__init__.py` | 2026-11-09 checks 7 passed, 12 xfailed; ruff clean; draft PR #82 |
| WO-306 (freemyid-pm#223) | delivered | `FAMILY_QUICK_START.md` | 2026-11-09 checks 571 passed, 18 skipped, 1 xfailed; draft PR #83 |
| WO-307 (freemyid-pm#224) | delivered | `docs/user/HELPING.md` | 2026-11-09 checks 620 passed, 17 skipped, 1 xfailed; draft PR #84 |
| WO-308 (freemyid-pm#225) | delivered | `distro/aur/README.md`; `distro/flatpak/README.md`; `distro/homebrew/README.md`; `distro/scoop/README.md`; `distro/winget/README.md` | 2026-11-09 lint 26 passed; distro filter 23 passed; draft PR #85 |
| WO-309 (freemyid-pm#226) | delivered | `tests/grok/test_gk_doc_labels_exist.py`; `tests/grok/__init__.py` | 2026-11-09 checks 14 passed, 3 xfailed; ruff clean; draft PR #86 |
| WO-310 (freemyid-pm#227) | delivered | `docs/user/troubleshooting.md` | 2026-11-09 checks 560 passed, 17 skipped, 1 xfailed; draft PR #87 |

WIP 5/5. WO-301 through WO-329 are delivered (draft PRs #78 through #106). Every Grok row on this board has a freemyid-pm issue, and the project Status matches the status column. WO-330 (freemyid-pm#250) waits for Morgan's rebase note. WO-331, WO-332, WO-333, WO-334, and WO-336 are delivered on draft PRs #113, #111, #110, #114, and #112. WO-335 stays queued: it edits `scheduler/__init__.py`, which WO-334 changed on a branch that is not on main. WO-337, WO-338, WO-339, WO-340, and WO-343 are delivered on draft PRs #115, #119, #117, #116, and #118. WO-341 is delivered on draft PR #120. It copies `mail.py` from the delivered WO-331 worktree, so merge #113 before #120. WO-342, WO-344, and WO-345 are delivered on draft PRs #123, #121, and #122. Merge #111 before #123. WO-346 is delivered on draft PR #124. WO-348 is delivered on draft PR #125. A failed resubmit used to raise, and runner.py:858-874 can now treat that rung as success. runner.py was not edited. WO-347 is delivered on draft PR #126. WO-350 is delivered on draft PR #127. It is a new file and is not wired into install. WO-349 is delivered on draft PR #128. It copies notify.py from the delivered WO-333 worktree. Merge #110 before #128. Checkpoint 2026-11-10 09:51 ET. Builders stopped. Still in progress, not delivered: WO-351 and WO-352 have uncommitted files. WO-353, WO-354, and WO-355 worktrees are still clean. No pull request was opened for those five. WO-355 copies handoff.py from the delivered WO-333 worktree. Rebase is not available. Merge #110 before that pull request. WO-354 copies filler.py from the delivered WO-338 worktree. Rebase is not available. Merge #119 before that pull request. WO-353 copies web_form.py from the delivered WO-337 worktree. Rebase is not available. Merge #115 before that pull request. WO-352 copies setup_config.py from the delivered WO-336 worktree. Rebase is not available. Merge #112 before that pull request. WO-351 copies `render.py` from the delivered WO-334 worktree. Rebase is not available. WO-349 copies `notify.py` from the delivered WO-333 worktree. Rebase is not available. WO-335 stays queued: `scheduler/__init__.py` on WO-334 calls the new `cron_lines` signature in `render.py`, and `render.py` is not in WO-335's allowed paths.

## In-house additions, CLAUDE-G-004 (Morgan Reyes, 2026-11-09)

Rows added by in-house when the batch was issued. Helen Ashford owns them from here: update the Status column as work starts and is delivered. Issue numbers are in the work-order column. Project Status matches this board: delivered is In review, in progress is In progress, queued is Backlog, blocked is Blocked. WIP limit 5 across all rows.

| Work order | Status | Reserved paths | Agent | Last update |
| --- | --- | --- | --- | --- |
| WO-311 (freemyid-pm#231) | delivered | `docs/user/whats-new-0.3.md` | Simon Fairley | 2026-11-09 links 324 passed; one expected reachability failure |
| WO-312 (freemyid-pm#232) | delivered | `docs/user/what-to-do-when.md` | Linda Moreau | 2026-11-09 links 370 passed; one expected reachability failure |
| WO-313 (freemyid-pm#233) | delivered | `docs/user/is-this-you.md` | Simon Fairley | 2026-11-09 links 314 passed; one expected reachability failure |
| WO-314 (freemyid-pm#234) | delivered | `docs/user/practice-mode.md` | Margaret Lund | 2026-11-09 links 344 passed; one expected reachability failure |
| WO-315 (freemyid-pm#235) | delivered | `docs/user/google-and-bing.md` | Simon Fairley | 2026-11-09 links 364 passed; one expected reachability failure |
| WO-316 (freemyid-pm#236) | delivered | `docs/user/protect-yourself.md` | Wesley Tran | 2026-11-09 links 306 passed; one expected reachability failure |
| WO-317 (freemyid-pm#237) | delivered | `docs/user/larger-text.md` | Rosa Delgado | 2026-11-09 links 288 passed; one expected reachability failure |
| WO-318 (freemyid-pm#238) | delivered | `docs/user/never-asks.md` | Linda Moreau | 2026-11-09 links 318 passed; one expected reachability failure |
| WO-319 (freemyid-pm#239) | delivered | `docs/user/printable-checklist.md` | Margaret Lund | 2026-11-09 links 286 passed; one expected reachability failure |
| WO-320 (freemyid-pm#240) | delivered | `docs/user/helping-by-phone.md` | Linda Moreau | 2026-11-09 links 364 passed; one expected reachability failure |
| WO-321 (freemyid-pm#241) | delivered | `tests/grok/test_gk_reading_level.py` | Ethan Brandt | 2026-11-09 checks 8 passed; ruff clean; baseline empty |
| WO-322 (freemyid-pm#242) | delivered | `tests/grok/test_gk_links_gaps.py` | Ethan Brandt | 2026-11-09 checks 22 passed; ruff clean |
| WO-323 (freemyid-pm#243) | delivered | `tests/grok/test_gk_root_doc_citations.py` | Ethan Brandt | 2026-11-09 checks 56 passed, 6 xfailed; ruff clean |
| WO-324 (freemyid-pm#244) | delivered | `tests/grok/test_gk_never_asks_user_docs.py` | Ethan Brandt | 2026-11-09 checks 24 passed; ruff clean |
| WO-325 (freemyid-pm#245) | delivered | `tests/grok/test_gk_markdown_a11y.py` | Rosa Delgado | 2026-11-09 checks 102 passed, 1 xfailed; ruff clean |
| WO-326 (freemyid-pm#246) | delivered | `docs/user/mail-gmail.md`; `docs/user/mail-proton.md`; `docs/user/mail-other.md` | Wesley Tran | 2026-11-09 checks 420 passed |
| WO-327 (freemyid-pm#247) | delivered | `distro/nix/README.md`; `distro/CHECKLIST.md` | Wesley Tran | 2026-11-09 packaging and wording 64 passed |
| WO-328 (freemyid-pm#248) | delivered | `tests/grok/test_gk_distro_readme_matches_recipe.py` | Ethan Brandt | 2026-11-09 checks 15 passed, 1 xfailed; ruff clean |
| WO-329 (freemyid-pm#249) | delivered | `docs/user/GLOSSARY.md` | Margaret Lund | 2026-11-09 checks 410 passed |
| WO-330 (freemyid-pm#250) | queued (pre-approved); start last, after WO-301 and WO-311..320 merge and in-house rebases it | `docs/user/help-topics.md`; `docs/user/INSTALL.md` | Simon Fairley | 2026-11-09 CLAUDE-G-004 |
| WO-331 (freemyid-pm#251) | delivered | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_reply_matcher.py` | Paul Kessler | 2026-11-09 full suite 2490 passed, 206 skipped, 2 xfailed; draft PR #113 |
| WO-332 (freemyid-pm#252) | delivered | `src/freemyid/engine/outbox.py`; `tests/grok/test_gk_outbox_retry.py` | Paul Kessler | 2026-11-09 full suite 2522 passed, 206 skipped, 2 xfailed; draft PR #111 |
| WO-333 (freemyid-pm#253) | delivered | `src/freemyid/notify.py`; `src/freemyid/engine/handoff.py`; `tests/grok/test_gk_notify_throttle.py` | Paul Kessler | 2026-11-09 full suite 2494 passed, 206 skipped, 2 xfailed; draft PR #110. flush() still needs a runner.py call from in-house |
| WO-334 (freemyid-pm#254) | delivered | `src/freemyid/scheduler/render.py`; `src/freemyid/scheduler/__init__.py`; `tests/grok/test_gk_scheduler_catchup.py` | Derek Olsen | 2026-11-09 full suite 2488 passed, 206 skipped, 2 xfailed; draft PR #114. Windows FREEMYID_HOME still needs a cli.py change |
| WO-335 (freemyid-pm#255) | queued (pre-approved); code lane must open; start after WO-334 is delivered | `src/freemyid/scheduler/status_parse.py`; `src/freemyid/scheduler/__init__.py`; `tests/grok/test_gk_scheduler_status.py` | Derek Olsen | 2026-11-09 CLAUDE-G-004 |
| WO-336 (freemyid-pm#256) | delivered | `src/freemyid/setup_config.py`; `tests/grok/test_gk_setup_config_messages.py` | Derek Olsen | 2026-11-09 full suite 2493 passed, 206 skipped, 2 xfailed; draft PR #112 |
| WO-337 (freemyid-pm#257) | delivered | `src/freemyid/submitters/web_form.py`; `src/freemyid/submitters/assisted.py`; `tests/grok/test_gk_web_form_fallback.py` | Paul Kessler | 2026-11-10 full suite 2492 passed, 206 skipped, 2 xfailed; draft PR #115. New to-do sentences are not in the string inventory. The wizard still shows the machine code at runner.py:698 |
| WO-338 (freemyid-pm#258) | delivered | `src/freemyid/engine/filler.py`; `tests/grok/test_gk_filler_classify.py` | Derek Olsen | 2026-11-10 full suite 2594 passed, 206 skipped, 2 xfailed; draft PR #119. Password, payment, and ID fields stay unfilled |
| WO-339 (freemyid-pm#259) | delivered | `src/freemyid/submitters/base.py`; `tests/grok/test_gk_data_minimization.py` | Paul Kessler | 2026-11-10 full suite 2529 passed, 206 skipped, 2 xfailed; draft PR #117. Removal mailbox still allowed when the broker needs email |
| WO-340 (freemyid-pm#260) | delivered | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_no_pii.py` | Derek Olsen | 2026-11-10 full suite 2482 passed, 206 skipped, 2 xfailed; draft PR #116. cli_json.py unchanged. check_url can already contain a name or email |
| WO-341 (freemyid-pm#261) | delivered | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_classify_reply.py` | Paul Kessler | 2026-11-10 full suite 2618 passed, 206 skipped, 5 xfailed; draft PR #120. Copies mail.py from WO-331; merge #113 first |
| WO-342 (freemyid-pm#262) | delivered | `src/freemyid/engine/outbox.py`; `tests/grok/test_gk_outbox_idempotent.py` | Paul Kessler | 2026-11-10 full suite 2493 passed, 206 skipped, 5 xfailed; draft PR #123. Copies outbox.py from WO-332; merge #111 first. A crash before email_handed is stored still needs a contract change |
| WO-343 (freemyid-pm#263) | delivered | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_escalation_due.py` | Derek Olsen | 2026-11-10 full suite 2513 passed, 206 skipped, 5 xfailed; draft PR #118. A shorter verified window counts as 15 days |
| WO-344 (freemyid-pm#264) | delivered | `src/freemyid/engine/mail_tls.py`; `tests/grok/test_gk_mail_tls_reasons.py` | Paul Kessler | 2026-11-10 full suite 2522 passed, 206 skipped, 5 xfailed; draft PR #121. Certificate checks unchanged |
| WO-345 (freemyid-pm#265) | delivered | `src/freemyid/engine/tiers.py`; `tests/grok/test_gk_tier_reason.py` | Derek Olsen | 2026-11-10 full suite 2524 passed, 206 skipped, 5 xfailed; draft PR #122. Automatic tier has no reason code |
| WO-346 (freemyid-pm#266) | delivered | `src/freemyid/engine/plugins.py`; `tests/grok/test_gk_plugins_robust.py` | Derek Olsen | 2026-11-10 full suite 2512 passed, 206 skipped, 5 xfailed; draft PR #124. A plugin file outside the data folder or the repo is refused |
| WO-347 (freemyid-pm#267) | delivered | `src/freemyid/engine/fill_for_me.py`; `tests/grok/test_gk_fill_for_me_reasons.py` | Derek Olsen | 2026-11-10 draft PR #126; full suite 2509 passed, 206 skipped, 5 xfailed |
| WO-348 (freemyid-pm#268) | delivered | `src/freemyid/submitters/email.py`; `tests/grok/test_gk_email_submitter_reasons.py` | Paul Kessler | 2026-11-10 draft PR #125; full suite 2499 passed, 206 skipped, 5 xfailed |
| WO-349 (freemyid-pm#269) | delivered | `src/freemyid/notify.py`; `tests/grok/test_gk_notify_missing_backend.py` | Paul Kessler | 2026-11-10 draft PR #128; full suite 2507 passed, 206 skipped, 5 xfailed; merge #110 first |
| WO-350 (freemyid-pm#270) | delivered | `src/freemyid/scheduler/pathcheck.py`; `tests/grok/test_gk_scheduler_pathcheck.py` | Derek Olsen | 2026-11-10 draft PR #127; full suite 2517 passed, 206 skipped, 5 xfailed |
| WO-351 (freemyid-pm#271) | in progress | `src/freemyid/scheduler/render.py`; `tests/grok/test_gk_scheduler_render_escape.py` | Derek Olsen | 2026-11-10 checkpoint: uncommitted; render.py copied from WO-334 then edited; test file present; not pushed |
| WO-352 (freemyid-pm#272) | in progress | `src/freemyid/setup_config.py`; `tests/grok/test_gk_setup_config_helper_safety.py` | Derek Olsen | 2026-11-10 checkpoint: uncommitted; setup_config.py copied from WO-336 then edited; test file present; not pushed |
| WO-353 (freemyid-pm#273) | in progress | `src/freemyid/submitters/web_form.py`; `tests/grok/test_gk_web_form_timeouts.py` | Paul Kessler | 2026-11-10 checkpoint: worktree still clean; builder stopped before a write |
| WO-354 (freemyid-pm#274) | in progress | `src/freemyid/engine/filler.py`; `tests/grok/test_gk_filler_ambiguity.py` | Derek Olsen | 2026-11-10 checkpoint: worktree still clean; builder stopped before a write |
| WO-355 (freemyid-pm#275) | in progress | `src/freemyid/engine/handoff.py`; `tests/grok/test_gk_handoff_overdue.py` | Paul Kessler | 2026-11-10 checkpoint: worktree still clean; builder stopped before a write |
| WO-356 (freemyid-pm#276) | blocked: needs in-house contract change first (interfaces.py (result type) and schema/ (new reason field)) | `src/freemyid/submitters/base.py`; `tests/grok/test_gk_submit_reason_codes.py` | Paul Kessler | 2026-11-09 CLAUDE-G-006 |
| WO-357 (freemyid-pm#277) | blocked: needs in-house contract change first (schema/ and the --json contract (new field, version bump)) | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_reason.py` | Derek Olsen | 2026-11-09 CLAUDE-G-006 |
| WO-358 (freemyid-pm#278) | queued (pre-approved); none | `docs/user/site-ignores-request.md` | Linda Moreau | 2026-11-09 CLAUDE-G-006 |
| WO-359 (freemyid-pm#279) | queued (pre-approved); after WO-334, WO-351 merged | `tests/grok/test_gk_scheduler_cross_os.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-006 |
| WO-360 (freemyid-pm#280) | queued (pre-approved); none | `tests/grok/test_gk_backend_offline_guard.py` | Ethan Brandt | 2026-11-09 CLAUDE-G-006 |
| WO-501 (freemyid-pm#281) | queued (pre-approved); after WO-336, WO-352 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_validate.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-502 (freemyid-pm#282) | queued (pre-approved); after WO-501 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_plan.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-503 (freemyid-pm#283) | queued (pre-approved); after WO-502 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_to_setup.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-504 (freemyid-pm#284) | queued (pre-approved); after WO-503 merged | `tests/grok/test_gk_bundle_roundtrip.py` | Ethan Brandt | 2026-11-09 E1 epic batch |
| WO-505 (freemyid-pm#285) | blocked: needs in-house schema, cli.py command and docs/CLI.md section first; none | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_bundle.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-506 (freemyid-pm#286) | blocked: needs in-house crypto change first (typed errors and a format version in the bundle header); none | `src/freemyid/setup_config.py`; `tests/grok/test_gk_bundle_open.py` | Derek Olsen | 2026-11-09 E1 epic batch |
| WO-507 (freemyid-pm#287) | queued (pre-approved); after WO-343 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_complaint_links.py` | Derek Olsen | 2026-11-09 E3 epic batch |
| WO-508 (freemyid-pm#288) | queued (pre-approved); after WO-507 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_escalation_waiting_events.py` | Derek Olsen | 2026-11-09 E3 epic batch |
| WO-509 (freemyid-pm#289) | queued (pre-approved); none | `tests/grok/test_gk_outbox_legal_demand_gate.py` | Ethan Brandt | 2026-11-09 E3 epic batch |
| WO-510 (freemyid-pm#290) | queued (pre-approved); after WO-341 merged | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_imap_fetch.py` | Paul Kessler | 2026-11-09 E4 epic batch |
| WO-511 (freemyid-pm#291) | queued (pre-approved); after WO-510 merged | `src/freemyid/engine/mail.py`; `tests/grok/test_gk_mail_poll_retry.py` | Paul Kessler | 2026-11-09 E4 epic batch |
| WO-512 (freemyid-pm#292) | queued (pre-approved); after WO-333, WO-349 merged | `src/freemyid/notify.py`; `tests/grok/test_gk_notify_monthly_counts.py` | Derek Olsen | 2026-11-09 E4 epic batch |
| WO-513 (freemyid-pm#293) | queued (pre-approved); after WO-508 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_broker_timeout.py` | Derek Olsen | 2026-11-09 E4 epic batch |
| WO-514 (freemyid-pm#294) | queued (pre-approved); after WO-513 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_error_backoff.py` | Derek Olsen | 2026-11-09 E4 epic batch |
| WO-515 (freemyid-pm#295) | queued (pre-approved); after WO-511 merged | `tests/grok/test_gk_mailer_fake_protocols.py` | Ethan Brandt | 2026-11-09 E4 epic batch |
| WO-516 (freemyid-pm#296) | blocked: needs in-house schema, cli.py command and docs/CLI.md section first; after WO-340, WO-357, WO-505, WO-299, WO-401 merged | `src/freemyid/cli_json.py`; `tests/grok/test_gk_cli_json_report_facts.py` | Derek Olsen | 2026-11-09 E5 epic batch |
| WO-517 (freemyid-pm#297) | queued (pre-approved); after WO-512 merged | `src/freemyid/notify.py`; `tests/grok/test_gk_notify_relisted.py` | Derek Olsen | 2026-11-09 E5 epic batch |
| WO-518 (freemyid-pm#298) | queued (pre-approved); after WO-514 merged | `src/freemyid/engine/runner.py`; `tests/grok/test_gk_runner_time_budget.py` | Derek Olsen | 2026-11-09 E6 epic batch |
| WO-519 (freemyid-pm#299) | queued (pre-approved); none | `tests/grok/test_gk_filler_plan_minimization.py` | Ethan Brandt | 2026-11-09 E7 epic batch |
| WO-520 (freemyid-pm#300) | queued (pre-approved); after WO-349 merged | `tests/grok/test_gk_notifications_pii_free.py` | Ethan Brandt | 2026-11-09 E7 epic batch |
| WO-521 (freemyid-pm#301) | queued (pre-approved); none | `tests/grok/test_gk_setup_errors_no_values.py` | Ethan Brandt | 2026-11-09 E7 epic batch |
| WO-522 (freemyid-pm#302) | queued (pre-approved); after WO-342 merged | `src/freemyid/engine/outbox.py`; `tests/grok/test_gk_outbox_compose_links.py` | Paul Kessler | 2026-11-09 E8 epic batch |
| WO-523 (freemyid-pm#303) | queued (pre-approved); after WO-503 merged | `src/freemyid/setup_config.py`; `tests/grok/test_gk_setup_windows_files.py` | Derek Olsen | 2026-11-09 E8 epic batch |
| WO-524 (freemyid-pm#304) | queued (pre-approved); after WO-335, WO-350 merged | `src/freemyid/scheduler/__init__.py`; `tests/grok/test_gk_scheduler_run_helper.py` | Derek Olsen | 2026-11-09 E8 epic batch |
| WO-525 (freemyid-pm#305) | queued (pre-approved); none | `tests/grok/test_gk_windows_import_safety.py` | Ethan Brandt | 2026-11-09 E8 epic batch |
| WO-526 (freemyid-pm#306) | blocked: needs in-house to build the helper-bundle screens first (no label may be invented); after WO-506 merged | `docs/user/helper-prepares-setup.md` | Simon Fairley | 2026-11-09 E9 epic batch |
| WO-527 (freemyid-pm#307) | blocked: needs in-house to build the open-a-setup-file screens first (no label may be invented); after WO-526 merged | `docs/user/open-a-setup-file.md` | Margaret Lund | 2026-11-09 E9 epic batch |
| WO-528 (freemyid-pm#308) | blocked: needs in-house to build read-aloud and the full-wizard large-text pass first; none | `docs/user/read-aloud.md` | Simon Fairley | 2026-11-09 E9 epic batch |
| WO-529 (freemyid-pm#309) | blocked: needs in-house to build the print-ready report page first; after WO-299 merged | `docs/user/printable-report.md` | Margaret Lund | 2026-11-09 E9 epic batch |
| WO-530 (freemyid-pm#310) | queued (pre-approved); after WO-358 merged | `docs/user/listing-came-back.md` | Linda Moreau | 2026-11-09 E9 epic batch |
| WO-531 (freemyid-pm#311) | queued (pre-approved); after WO-517 merged | `docs/user/monthly-update.md` | Linda Moreau | 2026-11-09 E9 epic batch |
| WO-532 (freemyid-pm#312) | queued (pre-approved); none | `tests/grok/test_gk_value_only_runner.py` | Ethan Brandt | 2026-11-09 E12 epic batch |
