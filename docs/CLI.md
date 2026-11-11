# Free My ID command line (v0.2)

The `freemyid` command does everything the app does. The CLI and the dashboard use the
same verbs: `scan`, `run`, `status`, `report`, `todo`.

```
freemyid doctor                         # is this computer ready?
freemyid setup --from setup.yaml        # set someone up without the wizard
freemyid run --dry-run                  # search and report; submit nothing
freemyid run --headless                 # cron / systemd / Docker
freemyid status --json                  # machine-readable status
freemyid app                            # open Free My ID in its own window
freemyid fill spokeo -p "Jane Q Testperson"   # open one site's form, filled in; you press Submit
freemyid exposure -p "Jane Q Testperson" --old-addresses
                                        # one extra previous-address page per site, this run only
freemyid search-engines                 # list Google and Bing steps; there is no list word
freemyid search-engines open google     # open that engine's official page in your browser
freemyid search-engines done google     # record that you finished those steps
freemyid search-engines undo bing       # take that record back
freemyid monitor --json --broker spokeo # maintainer page check; needs no person
freemyid wipe                           # delete everything Free My ID saved here (asks first)
```

* `freemyid app` opens the setup wizard the first time and the dashboard after that. Add
  `--no-window` to use your web browser instead (`cli.py:242-247`).
* `freemyid fill BROKER` opens that site's form in a visible window and fills it in. You tick
  the box and press Submit yourself. `-p` picks the person (needed if more than one is set up;
  otherwise it exits 2). `--timeout` is how many seconds to wait: 30 to 3600, default 600
  (`cli.py:361-376`).
* `freemyid exposure` only reads. `--old-addresses` searches each site once more at a previous
  address (at most one extra page per site). A site already checked in the last 24 hours is
  reused from the saved result unless you also add `--refresh`, so the flag may change nothing
  until then (`src/freemyid/engine/exposure.py:79`, `src/freemyid/engine/exposure.py:599-602`). Leave the flag off and config
  `exposure_old_addresses` decides; that setting is off unless someone turned it on
  (`cli.py:415-418`, `cli.py:447-449`).
* `freemyid search-engines` with no action lists the steps. The word `list` is not a command:
  `freemyid search-engines list` exits 2 (`unknown action`). The only actions are `open`,
  `done` and `undo` (`cli.py:895`, `cli.py:916-921`).
* `freemyid wipe` asks "Delete ALL Free My ID data on this computer? If you keep other Free
  My ID data folders on this computer that use the system keychain, they will stop working
  too." `--yes` skips the question. If the folder does not look like a Free My ID data folder
  it refuses and exits 2. It removes the saved people, evidence, mailbox passwords, the
  encryption key and the background task (`cli.py:581-628`). Each cleanup step is best effort:
  if one cannot finish (a mailbox password the keychain will not release, or a file that is
  in use), the command still carries on and prints "All Free My ID data deleted." Check the
  data folder afterwards if that matters to you.

Global option: `-v/--verbose` (more detail in the log). The top-level `--help` also shows
Typer's `--install-completion` and `--show-completion`; those are not Free My ID actions.

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
| `scan` | Searches brokers; never submits. `-p/--profile`, `-b/--broker` (repeatable), `--headless`, `--attended` (opens one visible window of your own browser and looks for you now; a site may ask you to tick a box; prints checked / to-check-yourself counts per person; not with `--headless`, `--json` or `--broker`). On Windows the daily scheduled run (`run --scheduled`) does the same search off-screen in the background first (WO-612); `--headless` runs and macOS / Linux scheduled jobs never open a window (until WO-616) | `run/1` |
| `run` | Scan, submit, verify, escalate. `--dry-run`, `--headless`, `-p`, `-b` | `run/1` |
| `exposure` | Which sites show you, with a 0-100 exposure score; reads only (works in practice mode). `-p`, `--offline`, `--refresh`, `--old-addresses` (one extra previous-address page per site; off unless you pass the flag or set config `exposure_old_addresses`), `--headless`. Text prints a score-change line after the drivers when there are 2 or more scans ([EXPOSURE.md](EXPOSURE.md)) | `exposure/1` |
| `monitor` | For maintainers and the weekly CI job: does each broker's opt-out page still load and its form still match? Reads only, needs no profile, never fills in or submits. `--registry`, `--previous last.json`, `--broker ID` (repeatable), `--browser` (headless load of a JavaScript form; opens the page only) ([MONITOR.md](MONITOR.md)) | `monitor/1` |
| `search-engines` | Google and Bing guided steps. No action lists them; there is no `list` word (`list` exits 2). `open ID` opens the official page and records when; `done ID` / `undo ID` record that you did it. ID may be a prefix or `google` / `bing`. `-p` when more than one person is set up. Never searches Google or Bing ([EXPOSURE.md](EXPOSURE.md)) | `search_engines/1` |
| `fill BROKER` | Opens the broker's form in a window and fills it; you submit. `--timeout` is seconds to wait, 30 to 3600, default 600 | |
| `status` | Per-broker state for each person. `-p` | `status/1` |
| `report` | Writes an HTML or PDF report. `-p`, `--format html\|pdf` | `reports/1` |
| `profile list` | Everyone set up | `profiles/1` |
| `profile add [--prefill BUNDLE]` | Add a person. Without `--prefill`: the web wizard. With `--prefill BUNDLE`: imports the bundle with terminal prompts (same as `setup --prefill BUNDLE`) | |
| `profile edit / remove / export` | Manage people. `remove` asks first; `--yes` skips the question. `export PROFILE DEST` writes a passphrase-protected family bundle | |
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
| `registry update / validate` | Update the broker list, or check it. `validate` takes an optional file path | |
| `secrets status` | Which backend holds the encryption key | `secrets/1` |
| `secrets migrate --to B` | Move the key and saved passwords to `keyring`, `passphrase` or `systemd-creds` (exit 2 on failure). `--remove-keychain-key` also deletes the system-keychain copy; only when this is the only Free My ID folder here, because other folders that share that key would no longer open | |
| `config set KEY VALUE` | Change a setting. An unknown key, or `real_submissions_enabled`, is refused; use `enable-submissions` for that opt-in | |
| `config enable-submissions` | One-time opt-in to real submissions (leaves practice mode) | |
| `wipe` | Delete everything Free My ID saved on this computer (`--yes` skips the question) | |

### Where this table comes from

Each statement above was checked against src/freemyid/cli.py (unless another file is named):

* setup options and the --prefill rules: `cli.py:147-176`. With --prefill alone the terminal
  prompts are used (`cli.py:168-169`). --web --prefill prints a pointer to /wizard/import
  and exits 2 (`cli.py:164-167`). --from is handled first (`cli.py:161-163`).
* profile add [--prefill]: `cli.py:536-538` (calls setup with the terminal path when a bundle
  is given).
* search-engines: the three words open, done, undo are `cli.py:895`. The command is
  `cli.py:903-966`. A missing, unknown or misplaced word or id exits 2 (`cli.py:916-921`; an
  unknown id also exits 2 from `cli.py:88-94`). The page could not be opened or recorded exits 1
  (`cli.py:932-933`, `cli.py:937-938`). With no word it lists the steps (`cli.py:946-966`).
* Exit code numbers: `src/freemyid/cli_json.py:25-29`.
* Option lists checked against --help: scan `cli.py:335-343`, run `cli.py:346-358`
  (--scheduled is hidden and is not in --help), exposure `cli.py:409-422`, status
  `cli.py:379-381`, report `cli.py:512-515`, wipe `cli.py:581-584`, fill --timeout
  `cli.py:364`, monitor `cli.py:1052-1062`, secrets migrate `cli.py:988-995`.
* checklist group and -p/--profile: `cli.py:775-779`. list / show / done / undo:
  `cli.py:815-890`.
* doctor --offline; Python 3.12 or newer: `cli.py:179-181`, `src/freemyid/doctor.py:55-64`.
* Exposure text order, coverage wording and the score-change line: `cli.py:458-463`,
  `src/freemyid/engine/exposure.py:847-865` and `src/freemyid/engine/exposure.py:896-903`,
  `src/freemyid/engine/exposure_score.py:185-215`, `src/freemyid/exposure_models.py:81-114`.
* `monitor/1` fields: `src/freemyid/monitor.py:197-212` (one broker) and
  `src/freemyid/monitor.py:376-386` (the document).

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
   "score": 28, "explanation": [{"points": 15, "text": "1 site shows a listing that is you …"},
     {"points": 13, "text": "… (more lines like this add up to the score)"}],
   "counts": {"confirmed_sites": 1, "possible_sites": 0, "check_by_hand": 1, "not_found": 0},
   "coverage": {"sites_total": 2, "sites_checked": 1, "found": 1, "not_found": 0,
     "check_by_hand": 1, "uncertain": 0},
   "coverage_note": "This score is based on the 1 site we could check, out of 2. A low score does not mean you are safe. 1 site needs checking by hand.",
   "score_version": 2, "band": "medium",
   "headline": "Your exposure is medium on the 1 site we could check. 1 site was not checked, so there may be more.",
   "drivers": [{"points": 15, "text": "Spokeo shows a listing of you", "broker_id": "spokeo"}],
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
sites_total`). `sites_checked` counts sites whose status is `found` or `not_found` and whose
`from_store` is false (`exposure_models.py:84-85`): a same-day cache of a real read still
counts, and a page this run could not read but filled from an earlier run (`from_store: true`)
counts in `found` but not in `sites_checked`. Show `coverage_note` next to the score.
`drop_first` is true and `first_checklist` is `"ca_drop"` when the person's current address
is in California. `old_address_checked` is true when one previous-address search was read
for that site. The `--old-addresses` flag forces that extra page on for this run (at most one
per site). Leaving the flag off passes the choice to config `exposure_old_addresses`, which
is off unless it was set (`cli.py:447-449`, `src/freemyid/engine/exposure.py:580-581`). There is no
previous-name flag. `previous_name_checked` is true when one previous-name search was read
(config `exposure_previous_names`, off by default). These fields were added in v0.3; `counts`
is unchanged.

`coverage_note` (`exposure_models.py:98-114`) is one plain line. It never says you are safe;
when at least one site is in the list it says this score does not mean you are safe:

* no sites (`sites_total` 0): "No sites could be searched for you yet."
* none read automatically: "We could not check any of the N site(s) automatically, so this
  score does not mean you are safe."
* otherwise: "This score is based on the N site(s) we could check, out of TOTAL. A low score
  does not mean you are safe." That second sentence is fixed. It still says "a low score"
  when the band is medium or high.
* then, if `check_by_hand` is not 0: "N site needs checking by hand." (or "sites need").
* then, if `uncertain` is not 0: "N site may show you; please tell us if it is you." (or
  "sites" / "they are").

`headline` (`src/freemyid/engine/exposure_score.py:197-215`) is one line shown with the number. It never
says "safe", "clean" or "protected". It does not always contain a site count:

* no sites: "No sites could be searched for you yet, so there is no score yet."
* band `not_checked`: "We could not check any sites automatically, so this score tells you
  nothing yet. Please check the sites listed below by hand."
* band `none_found`: "We found no listings of you on the N site(s) we could check."
* `low`, `medium` or `high`: "Your exposure is {band} on the N site(s) we could check."
* when `sites_checked` is 0 but the band is not `not_checked`, the place is "on the sites we
  could check" with no count.
* when `check_by_hand` is not 0, it adds "N site was not checked, so there may be more."
  (or "sites were").

`band` is `not_checked` (score 0 and nothing checked, found or uncertain), `none_found`
(score 0 otherwise), `low` (1-24), `medium` (25-59) or `high` (60-100)
(`src/freemyid/engine/exposure_score.py:185-194`).

Text output for one person (`cli.py:458-491`), in this order:

1. `{label}: exposure score N / 100`, plus ` (practice mode)` when that is on.
2. `headline`, then `coverage_note`.
3. When there are drivers: "What adds most to your score:" and one `+points text` line each
   (top 3, biggest first; `broker_id` is null for the relatives line). Weights: docs/EXPOSURE.md.
4. The score-change line, which is `trend.note`, only when there are 2 or more points. It is
   printed after the driver lines, not between the coverage note and the drivers
   (`cli.py:462-463`).
5. The point-by-point explanation, then Found, "Please check these yourself", and Not found.
6. If Google or Bing steps are still to do: "Google and Bing: N step(s) to do. Run freemyid
   search-engines." (`cli.py:494-509`).

`trend` (additive; the schema stays `exposure/1`) is the score over time. `points` has
one entry per day (the day's last scan), oldest first, and offline scans are skipped.
`change` is the latest score minus the previous day's score (negative when it went down).
`since` is that previous day. Both are null with fewer than 2 points. `note` is always set
in JSON. Text prints it only for 2 or more points. The line is one of:

* no points (JSON only): "No scans yet."
* one point (JSON only): "This is the first scan. Later scans will show whether your score
  goes down."
* down: "Your score went down N point(s) since DATE."
* up: "Your score went up N point(s) since DATE."
* same: "Your score is the same as on DATE."

DATE is the previous point's day. "point" is singular only when N is 1. If fewer sites could
be checked than last time, it adds "Fewer sites could be checked this time, so the change may
not be real." If `score_version` differs between those two scans, it adds "The way the score
is worked out changed between these scans, so part of the change comes from that."
(`src/freemyid/engine/exposure.py:847-865`). `points` do not carry `score_version`; that difference shows
up only in `note`.

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

There is no `list` subcommand. `freemyid search-engines` with no action prints the steps.
`freemyid search-engines list` is an unknown action and exits 2. Usage from `--help`:
`freemyid search-engines [action] [step_id]`, and the action help is "open ID | done ID |
undo ID (leave out to list the steps)".

With no action and no `--json`, the text is the intro, then one block per step: `[x]` or
`[ ]`, the step id, the engine and the title, why it matters now, a status line, the https
address, and the numbered steps. A done step adds `(done DATE)`; an opened step adds
`(opened DATE)`. It ends with
"{label}: N of M to do. Open one with: freemyid search-engines open ID, then: freemyid search-engines done ID".
If no step is available it prints
"No Google or Bing steps are available right now." (`cli.py:946-966`). open prints
"Opened {engine}'s page in your browser. If nothing opened, copy this address: {url}".
done prints "Done: {title}". undo prints "Not done: {title}". Those three do not print the list again. With
`--json` the same line goes to stderr and stdout is the document below (`cli.py:931-945`).

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

`freemyid exposure` (text output only) adds "Google and Bing: N step(s) to do. Run freemyid
search-engines." when N > 0. "step" is singular when N is 1. With more than one person the
line starts with that person's label and the command includes `-p` plus the first 12
characters of the profile id (`cli.py:505-509`).

### `doctor/1`

```json
{"schema": "doctor/1", "ok": true, "counts": {"ok": 6, "warn": 2, "fail": 0},
 "checks": [{"id": "browser", "title": "Browser for automatic removals",
   "status": "warn", "detail": "no Chrome, Edge or Playwright Chromium found",
   "fix": "Run `playwright install chromium` …"}]}
```

### `monitor/1`

`freemyid monitor --json [--registry FILE] [--previous last.json] [--broker ID] [--browser]`
(for maintainers and the weekly CI job; details in docs/MONITOR.md). `--broker` may be
repeated. `--browser` loads a JavaScript-built form once in a headless browser and only
opens the page. Without `--json` the text is one summary line ("N broker page(s) checked:"
plus the counts that are not zero), then one line per broker that is not `ok` or that
changed, and lines for new and removed ids when a previous file was compared. An unchanged
`ok` broker is left off that list (`cli.py:1094-1108`).

```json
{"schema": "monitor/1", "generated_at": "2026-11-09T06:17:00+00:00",
 "previous_generated_at": "2026-11-02T06:17:00+00:00",
 "counts": {"ok": 40, "moved": 1, "form_changed": 1, "blocked": 3, "unreachable": 0,
   "unknown": 2},
 "changed": ["spokeo"], "demote_suggested": [],
 "new_brokers": ["newbroker"], "removed_brokers": [],
 "brokers": [{"broker_id": "spokeo", "health": "form_changed",
   "detail": "1 form selector(s) not found", "http_status": 200,
   "page": "https://www.spokeo.com/optout", "selectors_missing": ["#email"],
   "selectors_unchecked": 1, "fingerprint": "3f2a9c0d1e4b5a67", "used_browser": false,
   "previous_health": "ok", "changed": true, "first_seen_bad": "2026-11-09",
   "weeks_bad": 1, "demote_suggested": false}]}
```

Every field is listed with its type in [MONITOR.md, Output](MONITOR.md#output-monitor1)
(`monitor.py:197-212` for one broker, `monitor.py:376-386` for the document). `new_brokers`
and `removed_brokers` are additive, so the schema stays `monitor/1`. With `--broker`, only
those ids count as new or removed (`monitor.py:399-400`). A `--previous` file that cannot be
read, is not monitor/1, is not valid JSON, or is over 2 MB is not compared. Stderr says
`freemyid: --previous is not a monitor/1 file; not compared (<reason>)` and the run goes on
(`monitor.py:404-420`, `cli.py:1076-1080`).

Exit 0 whenever the run finishes, whatever the health values are (the CI job reads the file),
1 when the registry can't be read (`error/1` on stdout with `--json`), 2 for a bad option.

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
