# Grok board (Grok-owned per-WO status and path guard)

Update when you start or deliver a WO. One WO = one session.

| WO | Allowed paths | State | Session/notes |
|---|---|---|---|
| WO-301 | `docs/user/INSTALL.md` `docs/user/troubleshooting.md` | GO | |
| WO-302 | `USER_GUIDE.md` | GO | |
| WO-303 | `docs/CLI.md` | GO | |
| WO-304 | `docs/user/GLOSSARY.md` | GO | |
| WO-305 | `tests/grok/test_gk_user_doc_claims.py` `tests/grok/__init__.py` | GO | |
| WO-306 | `FAMILY_QUICK_START.md` | queued | |
| WO-307 | `docs/user/HELPING.md` | queued | |
| WO-308 | `distro/aur/README.md` `distro/flatpak/README.md` `distro/homebrew/README.md` `distro/scoop/README.md` `distro/winget/README.md` | queued | |
| WO-309 | `tests/grok/test_gk_doc_labels_exist.py` | queued | |
| WO-310 | `docs/user/troubleshooting.md` | queued | |

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
