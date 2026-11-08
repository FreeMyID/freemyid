# Free My ID command line (v0.2)

The `freemyid` command does everything the app does. The CLI and the dashboard use the
same verbs: `scan`, `run`, `status`, `report`, `todo`.

```
freemyid doctor                         # is this computer ready?
freemyid setup --from setup.yaml        # set someone up without the wizard
freemyid run --dry-run                  # practice run: search and report, send nothing
freemyid run --headless                 # cron / systemd / Docker
freemyid status --json                  # machine-readable status
freemyid app                            # open Free My ID in its own window
freemyid fill spokeo -p "Jane Q Testperson"   # open one site's form, filled in; you press Submit
freemyid wipe                           # delete everything Free My ID saved here (asks first)
```

* `freemyid app` opens the setup wizard the first time and the dashboard after that. Add
  `--no-window` to use your web browser instead (`cli.py:242-247`).
* `freemyid fill BROKER` opens that site's form in a visible window and fills it in. You tick
  the box and press Submit yourself. `-p` picks the person (needed if more than one is set up;
  otherwise it exits 2), and `--timeout` is the seconds to wait, 30 to 3600 (`cli.py:361-376`).
* `freemyid wipe` asks "Delete ALL Free My ID data on this computer?" before it deletes
  anything. `--yes` skips the question. It removes the saved people, evidence, mailbox
  passwords, the encryption key and the background task, so use it only when you are done
  (`cli.py:578-626`).

Global option: `-v/--verbose` (more detail in the log).

## Exit codes

| Code | Meaning | Typical cause |
|---|---|---|
| 0 | OK | |
| 1 | Error | a check failed (`doctor`), a save failed, a headless run had broker errors |
| 2 | Usage | bad option or file, ambiguous id, `setup --from` not confirmed |
| 3 | Needs a person | headless: nobody has valid permission, or the run left items that need a person |
| 4 | Not configured | headless: nobody set up, practice mode on a real run, encryption key unavailable |

Codes are stable: a number never changes meaning.

## Commands

| Command | What it does | `--json` |
|---|---|---|
| `setup` | Opens the web wizard. `--web/--no-web`, `--from FILE [--yes] [--check] [--update]`. `--prefill BUNDLE` implies terminal prompts (`freemyid setup --prefill BUNDLE`). `--web --prefill` exits 2 and points to the wizard's Import screen (`/wizard/import`) | |
| `app` | Opens the app window (`--no-window` uses the browser) | |
| `dashboard` | Opens the local dashboard | |
| `doctor` | Readiness checks (`--offline` skips the mail server check) | `doctor/1` |
| `scan` | Searches brokers; never submits. `-p/--profile`, `-b/--broker` (repeatable), `--headless` | `run/1` |
| `run` | Scan, submit, verify, escalate. `--dry-run`, `--headless`, `-p`, `-b` | `run/1` |
| `exposure` | Which sites show you, with a 0-100 exposure score; reads only (works in practice mode). `-p`, `--offline`, `--refresh`, `--old-addresses` (also search each site once at your previous address; off by default), `--headless` ([EXPOSURE.md](EXPOSURE.md)) | `exposure/1` |
| `search-engines` | Google and Bing guided steps: on its own it lists them (there is no `list` word; `-p` picks the person). `open ID` opens the official page in your browser and records when; `done ID` / `undo ID` record that you did it. ID may be a prefix or `google` / `bing`. Never searches Google or Bing ([EXPOSURE.md](EXPOSURE.md)) | `search_engines/1` |
| `fill BROKER` | Opens the broker's form in a window and fills it; you submit | |
| `status` | Per-broker state for each person. `-p` | `status/1` |
| `report` | Writes an HTML or PDF report. `-p`, `--format html\|pdf` | `reports/1` |
| `profile list` | Everyone set up | `profiles/1` |
| `profile add [--prefill BUNDLE]` | Add a person. Without `--prefill`: the web wizard. With `--prefill BUNDLE`: imports the bundle with terminal prompts (same as `setup --prefill BUNDLE`) | |
| `profile edit / remove / export` | Manage people | |
| `checklist list` | Identity-safety checklists and which are done. `-p/--profile` (needed only when more than one person is set up) | [`checklists/1`](#checklists1) |
| `checklist show ID` | Steps for one checklist. `-p/--profile`. ID may be a prefix | [`checklist/1`](#checklist1) |
| `checklist done ID` / `checklist undo ID` | Mark a checklist done, or not done again. `-p/--profile` | [`checklist/1`](#checklist1) |
| `todo list` | Things that need a person. `-p` | `todos/1` |
| `todo done ID` | Mark a to-do done | |
| `outbox list` | Emails waiting for approval | `outbox/1` |
| `outbox approve ID` | Approve and send one | |
| `schedule install / remove` | Background job (systemd timer, launchd agent, Task Scheduler) | |
| `schedule status` | Is the job installed | `schedule/1` |
| `registry show` | Every broker in the list in use | `registry/1` |
| `registry source` | Which list is in use (`--plain` prints just the name) | `registry-source/1` |
| `registry update / validate` | Update or check the broker list | |
| `secrets status` | Which backend holds the encryption key | `secrets/1` |
| `secrets migrate --to B` | Move the key and saved passwords to `keyring`, `passphrase` or `systemd-creds` (exit 2 on failure; nothing is lost) | |
| `config set KEY VALUE` | Change a setting | |
| `config enable-submissions` | One-time opt-in to real submissions (leaves practice mode) | |
| `wipe` | Delete everything Free My ID saved on this computer (`--yes` skips the question) | |

### Where this table comes from

Each statement above was checked against `src/freemyid/cli.py` (unless another file is named):

* `setup` options and the `--prefill` rules: `cli.py:148-176`. With `--prefill` alone the terminal
  prompts are used (`cli.py:168-169`). `--web --prefill` prints a pointer to `/wizard/import`
  and exits 2 (`cli.py:164-167`). `--from` is handled first (`cli.py:161-163`).
* `profile add [--prefill]`: `cli.py:520-522`.
* `search-engines`: `cli.py:879` (the three words `open`, `done`, `undo`), `cli.py:887-953`
  (a missing, unknown or misplaced word or id exits 2: `cli.py:901-905`; the page could not be
  opened or recorded exits 1: `cli.py:917`, `cli.py:922`). With no word it lists the steps
  (`cli.py:932-950`).
* Exit code numbers: `src/freemyid/cli_json.py:25-29`.
* `scan`, `run`, `exposure`, `status`, `report`, `wipe` options: `cli.py:328-344`, `cli.py:402-408`,
  `cli.py:372`, `cli.py:497-498`, `cli.py:566`.
* `checklist` commands and `-p/--profile`: `cli.py:761-762`, `cli.py:799-872`.
* `doctor --offline`; Python 3.12 or newer: `cli.py:181`, `src/freemyid/doctor.py:56-62`.

## `--json` rules

* A successful command prints exactly one JSON object on stdout. A failure exits nonzero.
  Most failures print an `error/1` object, but some usage or selection errors (exit 2, for
  example an unknown or ambiguous id) print nothing on stdout and a message on stderr. Check
  the exit code before parsing stdout. Messages for people (warnings, "Skipping ...") go to
  stderr.
* Every object has `"schema": "<name>/<version>"`. Within a version fields are only ever
  added, never renamed or removed. Treat unknown fields as optional.
* Timestamps are ISO 8601 (UTC) or `null`. Ids are full ids (the human output shortens them).
* No personal details beyond what the human output shows (profile labels like "Mom", broker
  names, to-do titles). Never secrets, mailbox addresses, letters, copy-fields, names,
  addresses, phone numbers or birth dates.
* Profiles that fail the consent check are listed in `skipped` with a plain reason, never
  silently dropped.

### `status/1`

```json
{"schema": "status/1",
 "profiles": [{"profile_id": "…", "label": "Mom", "open_todos": 2,
   "brokers": [{"broker_id": "spokeo", "broker_name": "Spokeo", "state": "submitted",
     "tier": "automatic", "updated_at": "…", "last_scan_at": "…",
     "last_submitted_at": "…", "next_check_at": "…", "attempts": 1,
     "escalation_level": 0}]}],
 "skipped": [{"profile_id": "…", "label": "Kid", "reason": "…"}]}
```

`state`: unknown, not_found, found, submitted, awaiting_verification, confirmed, removed,
reappeared, needs_human, error. `tier`: email, assisted, automatic or null.
`escalation_level`: 0 none, 1 resubmitted, 2 follow-up, 3 legal demand, 4 complaint.

### `run/1` (from `run` and `scan`)

```json
{"schema": "run/1", "dry_run": true, "scan_only": false, "headless": true, "exit_code": 0,
 "profiles": [{"profile_id": "…", "label": "Mom",
   "states": {"not_found": 12, "submitted": 3}, "tiers": {"email": 9, "assisted": 6}}],
 "needs_human": 0, "errors": 0, "skipped_not_due": 4, "skipped_profiles": 0,
 "submitted": 3, "queued_emails": 1, "drafted_emails": 0, "open_todos": 2,
 "skipped": [], "summary": ["Dry run: nothing was sent or submitted.", "…"]}
```

When a headless run fails closed before starting, `--json` prints
`{"schema": "error/1", "exit_code": 4, "reason": "…"}` instead.

### `profiles/1`

```json
{"schema": "profiles/1", "profiles": [{"id": "…", "label": "Mom",
  "state_of_residence": "NC", "consent_basis": "self", "consent_ok": true,
  "has_mailbox": true, "email_mode": "approve_each", "created_at": "…"}]}
```

### `todos/1`

```json
{"schema": "todos/1", "todos": [{"id": "…", "profile_id": "…", "label": "Mom",
  "broker_id": "spokeo", "kind": "captcha", "title": "…", "request_id": null,
  "created_at": "…"}], "skipped": []}
```

### `outbox/1`

```json
{"schema": "outbox/1", "requests": [{"id": "…", "profile_id": "…", "broker_id": "…",
  "kind": "opt_out", "method": "email", "status": "queued_for_approval", "attempt": 1,
  "created_at": "…"}]}
```

### `reports/1`

```json
{"schema": "reports/1", "reports": [{"profile_id": "…", "label": "Mom",
  "format": "html", "path": "/…/reports/…html"}], "skipped": []}
```

### `registry/1` and `registry-source/1`

```json
{"schema": "registry/1", "version": "2026.11.06", "updated": "2026-11-06",
 "source": "full", "warnings": [],
 "brokers": [{"id": "spokeo", "name": "Spokeo", "url": "https://www.spokeo.com/",
   "category": "people_search", "method": "web_form", "verification_status": "verified",
   "has_captcha": true, "covered_by": null, "priority": 90, "enabled": true}]}

{"schema": "registry-source/1", "source": "full", "version": "…", "updated": "…",
 "brokers": 428, "warnings": []}
```

### `schedule/1`

```json
{"schema": "schedule/1", "platform": "linux", "installed": true,
 "detail": "systemd timer: active"}
```

### `secrets/1`

```json
{"schema": "secrets/1", "backend": "passphrase", "configured": null, "usable": true,
 "keychain_available": false}
```

`configured` is the `secrets_backend` setting (null = chosen automatically).

### `exposure/1`

```json
{"schema": "exposure/1", "offline": false, "headless": false, "exit_code": 0,
 "profiles": [{"profile_id": "…", "label": "Mom", "created_at": "…", "practice_mode": true,
   "score": 17, "explanation": [{"points": 15, "text": "1 site shows a listing that is you …"}],
   "counts": {"confirmed_sites": 1, "possible_sites": 0, "check_by_hand": 1, "not_found": 0},
   "coverage": {"sites_total": 2, "sites_checked": 1, "found": 1, "not_found": 0,
     "check_by_hand": 1, "uncertain": 0},
   "coverage_note": "This score is based on the 1 site we could check, out of 2. …",
   "drop_first": false, "first_checklist": null,
   "trend": {"change": -12, "since": "2026-10-01",
     "note": "Your score went down 12 points since 2026-10-01.",
     "points": [{"day": "2026-10-01", "score": 40, "sites_total": 2, "sites_checked": 1,
       "found": 1}, {"day": "2026-10-31", "score": 28, "sites_total": 2,
       "sites_checked": 1, "found": 1}]},
   "entries": [{"broker_id": "spokeo", "broker_name": "Spokeo", "status": "found",
     "reason": null, "match_level": "confirmed", "signals": ["age", "city"],
     "from_store": false, "old_address_checked": false,
     "previous_name_checked": false, "checked_at": "…",
     "check_url": "https://…",
     "listings": [{"url": "https://…", "match_level": "confirmed", "signals": ["age", "city"],
       "contact_shown": false, "relatives_shown": 1}]}]}],
 "skipped": []}
```

`status` is `found`, `not_found` or `check_by_hand`, and `reason` is one of the codes in
docs/EXPOSURE.md. Listing and check URLs are included because the person needs to open
them; the text output shows them too.

`coverage` says what the score is based on (`found + uncertain + not_found + check_by_hand ==
sites_total`; `sites_checked` = read automatically); show `coverage_note` next to the score.
`drop_first` is true and `first_checklist` is `"ca_drop"` when the person's current address
is in California. `old_address_checked` is true when one previous-address search was read
for that site (`--old-addresses` or config `exposure_old_addresses`, off by default); `previous_name_checked` is
true when one previous-name (maiden name) search was read (config `exposure_previous_names`,
off by default). These fields were added in v0.3; `counts` is unchanged.

`trend` (additive; the schema stays `exposure/1`) is the score over time. `points` has
one entry per day (the day's last scan), oldest first, and offline scans are skipped.
`change` and `since` compare the latest point with the one before it; both are null with
fewer than 2 points. `note` is one plain line, and it warns when fewer sites could be
checked than last time. The text output prints `note` under the coverage note once
there are 2 or more points.

### `checklists/1`

`freemyid checklist list --json`:

```json
{"schema": "checklists/1", "version": "…", "profile_id": "…", "done": 0, "total": 1,
 "start_with": null,
 "checklists": [{"id": "example_checklist", "title": "Example checklist", "done": false,
   "done_at": null, "url": "https://example.com/", "cost": "Free",
   "time_needed": "10 minutes"}]}
```

`start_with` is the checklist to do first, or null: `"ca_drop"` for a person whose current
address is in California (it is then also listed first). `done` at the top level counts completed checklists; each item's `done` is a boolean.
`done_at` is an ISO timestamp when done, otherwise null. `profile_id` is always the selected person (the command asks for `--profile` when more than one is set up). `version` is the checklist
file version.

### `checklist/1`

`freemyid checklist show ID --json` (also returned by `checklist done` and `checklist undo`
with `--json`):

```json
{"schema": "checklist/1", "profile_id": "…", "id": "example_checklist",
 "title": "Example checklist", "done": false, "done_at": null,
 "url": "https://example.com/", "cost": "Free", "time_needed": "10 minutes",
 "why": "Why this step helps", "need_on_hand": ["What you need"],
 "steps": ["Open the page"], "how_to_undo": "How to change it back",
 "source_urls": ["https://example.com/help"], "date_checked": "2026-11-07",
 "verification": "official_page", "notes": null, "status_note": null}
```

Includes the list item's fields plus the full instructions. `need_on_hand`, `steps` and
`source_urls` are arrays of strings; `date_checked` is an ISO date. `profile_id` and
`done_at` have the same meaning as in `checklists/1`.
`verification` is `official_page` or `partial`; `notes` and `status_note` may be null.

### `search_engines/1`

`freemyid search-engines --json` (also returned by `open`, `done` and `undo` with `--json`,
after the action):

```json
{"schema": "search_engines/1", "profile_id": "…", "intro": "Google and Bing can show …",
 "pending": 1,
 "steps": [{"id": "google_results_about_you", "engine": "Google",
   "title": "…", "why_now": "…", "url": "https://goo.gle/…",
   "status": "done", "status_text": "Done.", "opened_at": "…", "done_at": "…",
   "steps": ["…"], "tips": ["…"]}]}
```

`status` is `not_started`, `opened` (the page was opened, not yet ticked), `done`, or
`do_again` (Bing only: a site removed a listing after the last tick, so Bing may still show
the old copy). `pending` counts steps that are not `done`. `opened_at` / `done_at` are ISO
timestamps or null. A step is listed only when its checklist entry exists and its URL is
https on that engine's own hosts. `done` / `undo` use the normal checklist tick, so
`freemyid checklist` shows the same state. Exit codes: unknown action, missing or unknown
id, unknown or ambiguous profile: 2; checklist file missing or the step could not be opened
or recorded: 1; nobody set up: 4.

`freemyid exposure` (text output only) ends with "Google and Bing: N steps to do. Run
freemyid search-engines." when N > 0 for that person.

### `doctor/1`

```json
{"schema": "doctor/1", "ok": true, "counts": {"ok": 6, "warn": 2, "fail": 0},
 "checks": [{"id": "browser", "title": "Browser for automatic removals",
   "status": "warn", "detail": "no Chrome, Edge or Playwright Chromium found",
   "fix": "Run `playwright install chromium` …"}]}
```

## `run --headless`

For cron, systemd timers and containers. It never prompts and never opens a window
(anything that needs a person becomes a to-do), and it fails closed with a one-line reason
on stderr:

| Situation | Exit |
|---|---|
| Nobody set up yet | 4 |
| Encryption key unavailable (locked keychain, missing passphrase) | 4 |
| Practice mode and no `--dry-run` | 4 (use `--dry-run`, or `freemyid config enable-submissions` once) |
| Nobody has valid permission | 3 |
| Run finished, something needs a person (`needs_human > 0`) | 3 |
| Run finished, some brokers had errors (retried next run) | 1 |
| Run finished cleanly | 0 |

Consent and practice mode work exactly as in the app: profiles without valid permission are
skipped, and nothing real is sent until `freemyid config enable-submissions`. Add `--json`
for the `run/1` document. Interactive `run` (without `--headless`) keeps exit 0 after a run.

Example systemd user service (`freemyid schedule install` writes its own; this is for people
who manage their own units):

```ini
[Service]
Type=oneshot
ExecStart=%h/.local/bin/freemyid run --headless
SuccessExitStatus=3
```

## `doctor`

Checks, each `ok`, `warn` or `fail` with one plain fix line:

| id | Checks |
|---|---|
| python | Python 3.12+, or the installed (frozen) app |
| home | data folder exists, is writable and private (0700 on Linux/macOS) |
| secrets | the secrets backend can hold the encryption key (OS keychain, or the v0.2 pluggable backend) |
| store | the encrypted data opens; how many people, all with valid permission |
| browser | system Chrome/Edge or Playwright Chromium for the Automatic tier (`playwright install chromium`) |
| scheduler | background job installed |
| mailbox | each removal mailbox's servers answer (TCP + TLS hello only, never a login); `--offline` skips |
| registry | which broker list, how old (warns after 120 days) |

Exit 1 if any check fails, else 0. Doctor never installs anything and never creates the
database.

## `setup --from`

Non-interactive setup from a YAML file: one file, one person. Schema:
[`schema/setup-config.schema.json`](../schema/setup-config.schema.json). Example (fake data):
[`docs/examples/setup-config.example.yaml`](examples/setup-config.example.yaml).

* The file goes through exactly the same checks as the wizard.
* Consent is explicit: `consent.agreed: true` and a typed `consent.signed_name`. The command
  prints what will happen and the permission text, then asks to confirm. `--yes` confirms
  without a prompt (automation); without `--yes` and without a terminal, nothing is saved
  (exit 2).
* Passwords never go in the file: `mailbox.password_env` (environment variable name) or
  `mailbox.password_file` (first line of a file; relative to the YAML file). A `password`
  key is rejected.
* `--check` validates and prints the plan, and saves nothing.
* A person with the same label already set up is refused unless `--update`.
* `schedule.install_job: true` also installs the background job.
* Error messages name the field, never its value.

## Secrets

The encryption key lives in a secrets backend:

* `keyring`: the OS keychain (Windows Credential Manager, macOS Keychain, GNOME Keyring /
  KWallet). The default where one works.
* `passphrase`: the key is wrapped with a passphrase (scrypt). The passphrase comes from a
  prompt, or from `FREEMYID_PASSPHRASE_FILE` (a file only you can read, chmod 600) for
  headless runs. A plain `FREEMYID_PASSPHRASE` variable is refused.
* `systemd-creds`: same wrap, passphrase from the systemd credential `freemyid-passphrase`
  (`LoadCredential=freemyid-passphrase:<path>`).

`freemyid secrets status` shows which one is in use, `freemyid secrets migrate --to ...` moves
the key safely, and `freemyid doctor` says whether it is usable here and how to fix it.
