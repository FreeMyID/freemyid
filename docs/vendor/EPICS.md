# Vendor epics for the in-house offline week (0.4, Pat's journey and backend quality)

Written by Morgan Reyes, 2026-11-09. In-house is offline until about 2026-11-14; the owner wants the deepest useful vendor queue.
Structure: **epic -> work orders (WO-NNN.md) -> task checklists** (the `## Tasks` list inside each WO, numbered 1., 1.1, 1.2). Process: `docs/VENDOR.md`. Lanes: `AGENTS.md` "Your lane".

## How to work this queue
1. Work in epic order (E1 first) at WIP 5, after the earlier queue (Codex WO-230..290, Grok WO-306..360) is done. Note each start on `BOARD.md` (Codex) or `GROK_BOARD.md` (Grok) first.
2. A WO with an `Order:` line waits for the named WOs to be merged; no two open WOs touch the same file. Rebase on main before starting.
3. **Blocked WOs are not startable.** They say what in-house must provide first. Do not work around them; say what you need in your channel file.
4. Tick the boxes in the WO's `## Tasks` list as you go and mirror the list in `VENDOR_STATUS.md`.
5. Numbering: Codex WO-291..299 then WO-401 upward; Grok WO-501 upward. Never reuse a number.

## Totals (written so far)
- Work orders written: 61 (52 queued, 9 blocked).
- Codex: 30. Grok: 31.

## E1. Helper setup bundle backend ("Set it up for someone else")
**Owner team:** Grok (backend-core, test-writer)
**Goal:** ROADMAP 0.4 order item 1 and 3.1/3.7. A helper prepares a bundle, the relative opens it. This epic makes every check around the bundle (shape, forbidden keys, plain-words dry-run summary, conversion to a setup file) pure, tested and PII-free, so the in-house screens only wire it up.

**Sub-work-orders:**
- WO-501 [grok, Derek Olsen]: Helper bundle: check a bundle file's shape before anyone tries to open it (after WO-336, WO-352)
- WO-502 [grok, Derek Olsen]: Helper bundle: a plain "here is what will be imported" summary (dry run) (after WO-501)
- WO-503 [grok, Derek Olsen]: Helper bundle: turn a bundle's profile into a setup file a helper can edit (after WO-502)
- WO-504 [grok, Ethan Brandt]: Helper bundle: end-to-end round-trip tests with the real export and import (after WO-503)
- WO-505 [grok, Derek Olsen]: CLI JSON: a PII-free "bundle check" document **(blocked)** (after WO-340, WO-357, WO-502)
- WO-506 [grok, Derek Olsen]: Helper bundle: open a bundle file with typed, plain errors **(blocked)** (after WO-503)

**Dependencies:** WO-336 and WO-352 (both edit `setup_config.py`; every E1 setup_config WO starts after them). WO-340/357 for the cli_json item.

**What in-house must do:**
- Add the `bundle_check/1` schema, `freemyid bundle check` in `cli.py` and the `docs/CLI.md` section (unblocks WO-505).
- Change `crypto.py` to raise typed errors and add a format version byte to the bundle header; decide the passphrase rules (unblocks WO-506).
- Build the helper and relative screens (wizard) on top of `bundle_plan_lines` and `open_bundle_file`; run the Windows VM pass.
- Unblock WO-505: In-house must (1) add the `bundle_check/1` JSON schema under `schema/` and register it in the `--json` contract, (2) add the `freemyid bundle check FILE [--json]` command in `cli.py` that calls the WO-501/502 helpers and `cli_json.emit`, and (3) add the `docs/CLI.md` section so Grok can write `bundle_check_doc(header, doc_check, plan_lines) -> dict` in `cli_json.py` against a fixed shape.
- Unblock WO-506: In-house must change `crypto.py` (`export_with_passphrase` / `import_with_passphrase`, `crypto.py:182-205`) so that (1) a wrong passphrase, a damaged file and "not a bundle" raise three distinct exception classes instead of one `ValueError` with a message (today `import_with_passphrase` collapses wrong-passphrase, truncation and tampering on purpose, `crypto.py:203-205`; in-house decides whether telling them apart is acceptable, and that is a security decision), (2) the header carries a one-byte format version (a `VP2` magic or a version byte) so scrypt cost can be raised later, and (3) a documented helper exists to estimate time cost so the UI can show "this takes a few seconds".

## E2. Relist detection and smart re-check
**Owner team:** Codex (engine-tests, test-quality)
**Goal:** ROADMAP 3.3 "Smart re-check" (0.4). Detect a listing that came back after removal, learn how often each broker relists, and turn that into a suggested re-check interval. Pure helpers in `monitor.py` and `engine/exposure.py` with tests; no schema change.

**Sub-work-orders:**
- WO-291 [codex, Ravi Menon]: Smart re-check: a learned interval from how fast a site relists (after WO-271)
- WO-292 [codex, Ravi Menon]: Smart re-check: read removal-to-relist gaps out of the event history (after WO-291)
- WO-293 [codex, Ravi Menon]: Smart re-check: a plain-words suggestion for one broker (after WO-292)
- WO-294 [codex, Hannah Cole]: Smart re-check: property tests for the whole chain (after WO-293)
- WO-295 [codex, Ravi Menon]: Exposure: say which sites newly show a person since the last scan (after WO-278)

**Dependencies:** WO-271 (relist helper in monitor.py), WO-256, WO-242, WO-257, WO-259, WO-278 (all touch the same files).

**What in-house must do:**
- Wire the learned interval into `state.next_check_at` (state.py is in-house) behind a config flag.
- Surface "relisted" in the dashboard and the monthly summary (wizard).

## E3. Escalation and legal follow-ups
**Owner team:** Codex (engine-tests) for letters/law_matrix; Grok (backend-core, backend-mail) for runner/outbox
**Goal:** ROADMAP 3.3 "Legal escalation pack" (0.4). Statute selection, verified deadlines, a complaint data pack and calmer escalation events. The ladder itself (`state.py:100-139`) stays in-house.

**Sub-work-orders:**
- WO-296 [codex, Ravi Menon]: Letters: the data for a complaint pack (no template needed yet) (after WO-241, WO-275)
- WO-297 [codex, Ravi Menon]: Law matrix: one verified-window lookup for letters, outbox and runner (after WO-246, WO-284)
- WO-298 [codex, Hannah Cole]: Escalation letters: a reminder never cites a statute; a demand cites only what is verified (after WO-275)
- WO-507 [grok, Derek Olsen]: Runner: a tested helper for the complaint links (after WO-343)
- WO-508 [grok, Derek Olsen]: Runner: do not log the same "escalation waiting" note every day (after WO-507)
- WO-509 [grok, Ethan Brandt]: Outbox: a legal demand never goes out by itself (guard tests)

**Dependencies:** WO-241, WO-275, WO-284 (letters, law_matrix); WO-343, WO-355 (runner, handoff).

**What in-house must do:**
- Add `complaint.txt.j2` under `templates/` and a TEMPLATES entry decision (blocked WO).
- Decide whether the ladder windows in `state.py` should take the matrix's verified response days.

## E4. Delivery reliability (mail, retries, scheduler on three systems)
**Owner team:** Grok (backend-mail, backend-core, test-writer)
**Goal:** Make sending, reading replies and scheduled re-checks fail calmly and retry sensibly: reply de-duplication, SMTP/IMAP timeouts, outbox bookkeeping, scheduler status, a monthly update that counts correctly.

**Sub-work-orders:**
- WO-510 [grok, Paul Kessler]: Mail: read the mailbox without downloading huge messages or losing what was fetched (after WO-341)
- WO-511 [grok, Paul Kessler]: Mail: one failed poll does not end the wait for a broker's reply (after WO-510)
- WO-512 [grok, Derek Olsen]: Monthly update: count what happened in the last month, not everything ever (after WO-333, WO-349)
- WO-513 [grok, Derek Olsen]: Runner: one stuck site never stalls a whole scheduled run (after WO-508)
- WO-514 [grok, Derek Olsen]: Runner: try again sooner after an error, then back off (after WO-513)
- WO-515 [grok, Ethan Brandt]: Mailer: guards for the real SMTP/IMAP code, using only fakes (after WO-511)

**Dependencies:** WO-331/341 (mail), WO-332/342 (outbox), WO-333/349 (notify), WO-334/335/350/351 (scheduler).

**What in-house must do:**
- Decide the outbox retry policy fields in `models.Request` if the retry count must be stored (contract).
- tools/vendor.sh still refuses `engine/mail*` paths: lift that for E4 mail WOs or in-house merges them by hand.

## E5. Printable "what we did for you" report: data layer
**Owner team:** Codex (engine-tests) and Grok (backend-core)
**Goal:** ROADMAP 0.4 order item 3 and 3.5. This epic builds only the data: a pure summary of requests, confirmations and relists per person, and the JSON document. Layout, print CSS and PDF are in-house.

**Sub-work-orders:**
- WO-299 [codex, Ravi Menon]: Report data: plain facts for "what we did for you" (counts only) (after WO-258, WO-280)
- WO-401 [codex, Ravi Menon]: Exposure: the first and the newest scan for one person, honest about a truncated history (after WO-295)
- WO-516 [grok, Derek Olsen]: CLI JSON: the report facts as a document **(blocked)** (after WO-340, WO-357, WO-505, WO-299, WO-401)
- WO-517 [grok, Derek Olsen]: Monthly update: say how many came back, not only how many were sent (after WO-512)

**Dependencies:** WO-258, WO-280 (exposure_models), WO-340/357 (cli_json).

**What in-house must do:**
- Build the print-ready report page (wizard/report.py, templates) on the data layer.
- Add `report_summary/1` schema and the CLI command (blocks WO-517).
- Unblock WO-516: In-house must (1) add the `report_facts/1` schema under `schema/` and register it in the `--json` contract, (2) add `freemyid report --facts --json` (or the name in-house prefers) to `cli.py`, which gathers the activity counts from the store and calls `exposure.first_and_latest_scan` (WO-401) and `exposure_models.report_facts` (WO-299), and (3) document the shape in `docs/CLI.md`.

## E6. Registry scale (400+ brokers)
**Owner team:** Codex (engine-tests, test-quality, windows-tests); Grok (backend-core)
**Goal:** The registry is moving toward 400+ brokers. Bound every per-broker loop: scan-event reads, per-broker event scans in the runner, selector compilation, registry load time, doctor checks.

**Sub-work-orders:**
- WO-402 [codex, Ravi Menon]: Exposure: read only as many past events as the question needs (after WO-401)
- WO-403 [codex, Ravi Menon]: Exposure: a time budget per scan, and the rest resume next time (after WO-402, WO-299)
- WO-404 [codex, Hannah Cole]: Checklist ticks: first-version ticks must not fall out of the history window (after WO-281)
- WO-405 [codex, Owen Park]: Doctor: tell the person how long a full scan will take (after WO-283)
- WO-406 [codex, Hannah Cole]: Scan event size budget (guard) (after WO-403)
- WO-518 [grok, Derek Olsen]: Runner: a run-time budget that never starves low-priority sites (after WO-514)

**Dependencies:** WO-278, WO-287 (offline benchmark guard), WO-285, WO-286 (perf), WO-343 (runner).

**What in-house must do:**
- If `Store.events` needs an action filter or index (storage/ is in-house), add it so scan-event reads stop scanning thousands of rows.

## E7. Data minimization and privacy proofs
**Owner team:** Codex (security-tests, engine-tests) and Grok (test-writer, backend-core)
**Goal:** Offline tests and small fixes proving a request carries only what the site already shows: search URLs, letters, form variables, evidence logs, JSON documents.

**Sub-work-orders:**
- WO-407 [codex, Imani Reid]: Privacy proof: search links carry only name, town and (with permission) phone
- WO-408 [codex, Imani Reid]: Privacy proof: a letter never mentions a field the listing does not show (after WO-275)
- WO-409 [codex, Imani Reid]: Privacy proof: scan, monitor and match leave no personal values in logs or events (after WO-402)
- WO-519 [grok, Ethan Brandt]: Privacy proof: "Fill it in for me" values come only from what the listing shows
- WO-520 [grok, Ethan Brandt]: Privacy proof: every notification is free of names and sites (after WO-349)
- WO-521 [grok, Ethan Brandt]: Privacy proof: a setup file error never repeats what the person typed

**Dependencies:** WO-339 (submitters/base.py), WO-340 (cli_json), WO-237 (redaction).

**What in-house must do:**
- Review any finding marked as an in-house defect and fix it in the in-house module (strict xfail tells you where).

## E8. Windows robustness
**Owner team:** Codex (windows-tests) and Grok (backend-core, test-writer)
**Goal:** Pat is on Windows 10. Doctor checks, data-file reading, task XML, toast fallback and path handling must behave there. Offline tests render for all three systems; nothing touches the real OS.

**Sub-work-orders:**
- WO-410 [codex, Owen Park]: Doctor: "background checks" is only OK when the timer is really running (after WO-405)
- WO-411 [codex, Owen Park]: Doctor: advice that works on Windows, and a warning when the data folder syncs to the cloud (after WO-410)
- WO-412 [codex, Owen Park]: Doctor: find Edge and Chrome where Windows really puts them (after WO-411)
- WO-522 [grok, Paul Kessler]: Mail links: line breaks and length that Windows mail apps accept (after WO-342)
- WO-523 [grok, Derek Olsen]: Setup file: a password file saved by Notepad still works (after WO-503)
- WO-524 [grok, Derek Olsen]: Scheduler: a hung or missing system tool gives a plain message, not a traceback (after WO-335, WO-350)
- WO-525 [grok, Ethan Brandt]: Windows import-safety guard for the delivery and scheduling modules

**Dependencies:** WO-260, WO-283 (doctor), WO-334, WO-351, WO-359 (scheduler), WO-349 (notify).

**What in-house must do:**
- Run the Windows 10 VM pass for each shipped item (vendors cannot).

## E9. User docs for the 0.4 features
**Owner team:** Grok (user-guide-writer, support-writer, plain-language-editor, reference-writer, accessibility-reviewer)
**Goal:** Plain-language pages for what 0.4 adds. Pages whose screen does not exist yet are blocked until in-house builds the screen, so no label is invented.

**Sub-work-orders:**
- WO-526 [grok, Simon Fairley]: User page: set it up for someone else (the helper's side) **(blocked)** (after WO-506)
- WO-527 [grok, Margaret Lund]: User page: you were sent a setup file (the relative's side) **(blocked)** (after WO-526)
- WO-528 [grok, Simon Fairley]: User page: large text and read-aloud **(blocked)**
- WO-529 [grok, Margaret Lund]: User page: your "what we did for you" printout **(blocked)** (after WO-299)
- WO-530 [grok, Linda Moreau]: Help page: a site put my details back (after WO-358)
- WO-531 [grok, Linda Moreau]: Help page: the monthly update message, line by line (after WO-517)

**Dependencies:** WO-330 (help topics hub), WO-311..320 (the 0.3 pages).

**What in-house must do:**
- Build the screens (helper bundle, read-aloud, printable report, tray) so the blocked docs WOs can quote real labels.
- Link the new pages from `docs/user/help-topics.md` after merge.
- Unblock WO-526: In-house must ship the "Set it up for someone else" screens in the app (ROADMAP 0.4 order item 1; helper side: pick the person, enter their details, choose a passphrase, save the file) and say so in a GO message with the exact button and heading labels and their file:line in `src/freemyid/wizard/`.
- Unblock WO-527: In-house must ship the relative's side of the helper flow (double-click the file, type the passphrase, see the summary, give consent, set up the mailbox) and provide the exact labels with file:line, including the wrong-passphrase and damaged-file messages (from WO-506's typed errors).
- Unblock WO-528: In-house must ship read-aloud (ROADMAP 0.4 order item 2) and the full-wizard large-text pass, and provide the control labels with file:line, which keys or buttons start and stop reading, which voices are used on Windows 10 and Windows 11, whether it works offline, and the known limits.
- Unblock WO-529: In-house must ship the print-ready report page (ROADMAP 0.4 order item 3; `wizard/report.py` and its template) and provide the exact headings, button labels and sentences with file:line, the print steps for Windows 10 (browser print dialog, "Save as PDF" if offered), and what the page says in practice mode.

## E10. Spanish readiness (i18n)
**Owner team:** Codex (i18n, test-quality, dev-docs)
**Goal:** ROADMAP 3.1 Spanish UI (0.5). Get ready: inventories of every backend string, a Spanish glossary for the new 0.4 terms, guards that keep user text out of logic, and drafts that a native speaker reviews.

**Sub-work-orders:**
- WO-413 [codex, Amara Okoye]: String inventory: the sentences the engine, runner and notifications produce
- WO-414 [codex, Amara Okoye]: Spanish glossary: the words the 0.4 features add (after WO-214, WO-219, WO-225)
- WO-415 [codex, Hannah Cole]: Guard: every user-facing constant in the finding and matching code is in an inventory (after WO-290)
- WO-416 [codex, Ravi Menon]: Message catalog: move the finding code's sentences out of the logic **(blocked)** (after WO-403, WO-299, WO-415)
- WO-417 [codex, Amara Okoye]: Spanish explainers for each letter (what this letter says) **(blocked)**

**Dependencies:** WO-232, WO-250, WO-254, WO-290 (inventories), WO-251 (glossary check).

**What in-house must do:**
- Pick the message-catalog mechanism and add it (new module, wizard and CLI wiring) to unblock WO-416.
- Wire Spanish letter templates and get a legal read (unblocks WO-417).
- Unblock WO-416: In-house must (1) choose the mechanism and add the module (for example `src/freemyid/messages.py` with `t(key, **params)` and an English catalog file under `src/freemyid/` or `locales/`), including plural handling that does not rely on English "one/many" pairs (Spanish and later Vietnamese, Tagalog and Chinese differ), (2) add a language setting to `config.py` (default English, so nothing changes today) and the wizard and CLI wiring, (3) tell Codex the key naming scheme and that `HAND_REASONS` and `STATUS_TEXT` keep their dict shapes for existing readers (`--json` output must not change when the language is English).
- Unblock WO-417: The owner must decide whether letters to US brokers stay in English with a Spanish explanation shown next to them (this WO's assumption), or are sent in Spanish too.

## E11. Identity-safety checklists and the yearly check-up
**Owner team:** Codex (engine-tests, test-quality)
**Goal:** ROADMAP 3.4 (annual privacy check-up, lock-down checklist). The IRS IP PIN, SSA and USPS entries already exist in `brokers/checklists.yaml:253-317`. Backend only: tick-age logic, check-up summary data, source-freshness checks and a content guard. New checklist entries and screens are in-house.

**Sub-work-orders:**
- WO-418 [codex, Hannah Cole]: Yearly check-up: which "done" steps are old enough to do again (after WO-404)
- WO-419 [codex, Hannah Cole]: Yearly check-up: the summary as plain lines and a JSON document (after WO-418)
- WO-420 [codex, Ravi Menon]: Checklists: tell maintainers which steps were last checked too long ago (after WO-246, WO-282)
- WO-421 [codex, Felix Grant]: Guard: the public text of every checklist follows the house rules

**Dependencies:** WO-246, WO-282 (checklists.py), WO-281 (checklist_state.py).

**What in-house must do:**
- Write the new checklist entries in `brokers/checklists.yaml` and the check-up screen/reminder wiring.

## E12. Phone/email-only removals and the address-confidentiality helper
**Owner team:** Codex (engine-tests) and Grok (backend-core)
**Goal:** ROADMAP 3.3 (phone number and email-only removals; ACP guidance). Make the value-only path (BL-IN-08) solid and add backend data for state ACP guidance.

**Sub-work-orders:**
- Codex: WO-422..424. Grok: WO-532. (to be written in this wave; see `git log docs/vendor/EPICS.md`)

**Dependencies:** WO-275 (letters), WO-345 (tiers), WO-338/354 (filler).

**What in-house must do:**
- Add the ACP guidance entries and screen; decide whether ACP is a checklist or its own flow.
