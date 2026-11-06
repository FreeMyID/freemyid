<!-- Status: done all sections (first draft) / next: lead review; resolve TODO verify markers as engine, wizard and scheduler land -->

# Free My ID

Free My ID is a local-first tool that finds your listings on data-broker and people-search sites, files opt-out requests with each broker, and keeps checking so it can re-file when listings come back.

It runs on your own computer. There is no AI or cloud service at runtime: every step is deterministic Python driven by a broker registry (YAML) and a per-listing state machine. Your personal data stays in an encrypted database on your machine.

> **Status:** pre-release (0.1.0). The contracts and storage layer are in place. The engine, wizard, scheduler and packaging are still being built, so sections that describe them are planned behavior and are marked `TODO verify`. See [PROGRESS.md](PROGRESS.md).

Non-technical users should start with the [User Guide](docs/USER_GUIDE.md) or `FAMILY_QUICK_START.md`.

## What it does, and what it doesn't

**It does:**

- Search each broker in the registry for each person (a "profile"), scoring candidate listings against names, nicknames, previous names, city/state, age, relatives, phone and email.
- Submit opt-outs through the broker's own channel (web form, email, postal letter, phone script, or a to-do when an account is required), sending only what the listing already shows.
- Click email verification links in a dedicated removal mailbox, but only links on that broker's own domains.
- Escalate requests that get ignored: resubmit, then a state-law follow-up email, then a formal legal demand (always held for your approval), then a to-do with the right Attorney General or CPPA complaint links.
- Re-scan on a schedule and file again when a listing reappears.
- Keep encrypted evidence: screenshots of every listing found and every confirmation page, plus copies of every email sent.

**Honest limits:**

- **"Removed" means removed from that one broker.** It does not mean removed from the internet, from search engines, from public records, or from brokers that aren't in the registry.
- **Listings come back.** Brokers re-ingest data from their sources, and clone sites copy one another. That is why Free My ID keeps re-checking rather than running once.
- **Some brokers need you.** CAPTCHAs, ID requests, login walls, postal letters and phone calls are handed to a person. Free My ID never solves or bypasses a CAPTCHA or other bot protection.
- **The registry goes stale.** Brokers move opt-out pages and change forms. Entries carry a `verification_status` (`verified`, `unverified` or `broken`), and a weekly health check flags breakage, but some entries will be wrong at any given time.
- **Matching is fuzzy.** Only `CONFIRMED` matches (name plus at least 2 other signals) are submitted automatically. `POSSIBLE` matches (name plus 1 signal) wait for you to confirm.
- **It's not legal advice.** The letter templates cite state privacy laws, but you are responsible for what you send.

## Install

Requires Python 3.11+ (development uses 3.12). Free My ID drives your installed Chrome or Edge first. It only downloads Playwright's bundled browser if neither is present, and it asks before doing so. <!-- TODO verify: first-run browser prompt is wizard-packager work -->

### With pipx (users)

```bash
pipx install git+https://github.com/<OWNER>/freemyid.git   # <!-- TODO verify: repo URL not set yet -->
freemyid setup
```

Prebuilt installers (PyInstaller) for Linux, macOS and Windows are planned. They will ship unsigned for now; see `FAMILY_QUICK_START.md` for how to open an unsigned app. <!-- TODO verify -->

### Dev environment

```bash
python3.12 -m venv .venv            # or: uv venv --python 3.12 .venv
.venv/bin/pip install -e '.[dev]'   # or: uv pip install --python .venv -e '.[dev]'
.venv/bin/freemyid --help
.venv/bin/pytest -q
.venv/bin/ruff check src tests
```

Optional extras: `.[pdf]` (WeasyPrint, for PDF reports) and `.[package]` (PyInstaller).

For development, point Free My ID at a throwaway data directory and a test key so you never touch your real data or OS keychain:

```bash
export FREEMYID_HOME="$(mktemp -d)"
export FREEMYID_TEST_KEY=dev-only-not-a-secret
```

`FREEMYID_TEST_KEY` is for tests and development only. Never set it on a real install, because it replaces the keychain-held database key with one derived from that string.

## Commands

Run `freemyid --help` or `freemyid <command> --help` for full options. `-v/--verbose` turns on debug logging (still redacted).

| Command | What it does |
|---|---|
| `freemyid setup [--no-web] [--prefill FILE]` | Add a person. Opens the local web wizard by default; `--no-web` uses terminal prompts. `--prefill` imports a family bundle. |
| `freemyid dashboard` | Open the local dashboard: status, evidence, to-dos, outbox approvals. |
| `freemyid scan [-p PROFILE] [-b BROKER ...]` | Search brokers for listings. Never submits anything. |
| `freemyid run --dry-run [-p ...] [-b ...]` | Full pipeline, but submits nothing. Run this first. |
| `freemyid run [-p ...] [-b ...]` | Scan, submit opt-outs, check verifications, escalate ignored requests. Refuses to run until real submissions are enabled. |
| `freemyid status [-p PROFILE]` | Per-broker state, last update, next check and escalation level for each person. |
| `freemyid report [-p PROFILE] [--format html\|pdf]` | Export a report to the artifacts folder. |
| `freemyid profile add [--prefill FILE]` | Same as `setup`. |
| `freemyid profile list` | List people, consent basis and whether a mailbox is configured. |
| `freemyid profile edit PROFILE` | Edit a person (terminal flow). |
| `freemyid profile remove PROFILE [--yes]` | Delete a person, all their evidence, and their mailbox password from the keychain. |
| `freemyid profile export PROFILE DEST` | Write a passphrase-protected `.freemyid-profile` bundle for a family member's install. |
| `freemyid schedule install\|remove\|status` | Manage the background re-check job. |
| `freemyid registry show` | List brokers: method, verification, CAPTCHA, `covered_by`. |
| `freemyid registry validate [PATH]` | Validate a registry file against the model and JSON Schema. |
| `freemyid registry update` | Fetch and validate a new registry from `registry_url`. |
| `freemyid todo list [-p PROFILE]` | Items that need a person. |
| `freemyid todo done ID` | Mark a to-do done (an ID prefix is enough). |
| `freemyid outbox list` | Emails waiting for your approval. |
| `freemyid outbox approve ID` | Approve and send one queued email. |
| `freemyid config set KEY VALUE` | Change a setting in `config.yaml`. Protected keys are rejected. |
| `freemyid config enable-submissions` | One-time explicit opt-in to real submissions. |

`PROFILE` matches an ID prefix or the profile's label (e.g. `Mom`). Profiles that fail the consent gate are skipped with a message.

### Safety gates, in order

1. **Consent gate** (`cli.consent_ok`, re-checked in the runner). Every profile needs an attesting name. A minor needs `guardian_of_minor` consent. An `authorized_agent` needs a signed authorization attached.
2. **Dry run first.** `freemyid run` without `--dry-run` exits until `freemyid config enable-submissions` has been confirmed interactively. `real_submissions_enabled` can't be set with `config set`.
3. **Email approval.** With `email_mode: approve_each` (the default), every outgoing email waits in the outbox. Legal demands always wait, even in `auto` mode.
4. **Match gate.** Only `CONFIRMED` listings are auto-submitted.
5. **Permission flags.** ID upload, account creation and phone disclosure are off by default per profile. When a broker needs one of them, you get a `permission_needed` to-do instead.

## Architecture

```
src/freemyid/
  cli.py              Typer CLI (thin; all logic lives in modules)
  models.py           Pydantic models: Profile, Broker, Registry, StateLaw, Listing, Request, ...
  state.py            Pure state machine + escalation ladder + re-check timing
  interfaces.py       Contracts between modules (Submitter, Mailer, HumanHandoff, Notifier, entry points)
  registry.py         Load/validate/update brokers/registry.yaml and state_laws.yaml
  netpolicy.py        Network allowlist; every request goes through NetPolicy.is_allowed
  crypto.py           AES-256-GCM; key in the OS keychain; passphrase export (scrypt)
  secrets.py          Mailbox passwords in the OS keychain
  storage/db.py       Encrypted SQLite store (Store)
  logging_setup.py    PII-redacting log filter
  config.py, paths.py Non-PII settings and file locations
  engine/             runner, matcher, browser (Playwright), mail, handoff, outbox, letters, plugins
  submitters/         web_form, email, postal, phone, account_required + per-broker classes
  templates/          jinja2 letters: generic, ccpa, state_privacy, follow_up, legal_demand, postal_letter, phone_script
  wizard/             FastAPI wizard + dashboard (localhost only), flows, report
  scheduler/          systemd user timer / cron, launchd, schtasks
  notify.py           Desktop notifications (PII-free)
brokers/              registry.yaml, state_laws.yaml, SOURCES.md
schema/               JSON Schemas generated from models (tools/gen_schema.py)
tools/                gen_schema.py, registry_health.py
tests/                pytest suite
packaging/            PyInstaller spec, installers
```

### Module ownership

Each area has one owner. Others send change requests rather than editing it. Agent definitions are in `.claude/agents/`.

| Owner | Files |
|---|---|
| orchestrator | `models.py`, `state.py`, `interfaces.py`, `registry.py`, `netpolicy.py`, `crypto.py`, `secrets.py`, `logging_setup.py`, `config.py`, `paths.py`, `cli.py`, `storage/`, `schema/`, `pyproject.toml`, `PROGRESS.md` |
| broker-researcher | `brokers/registry.yaml`, `brokers/state_laws.yaml`, `brokers/SOURCES.md` |
| automation-engineer | `engine/`, `submitters/`, `templates/` |
| wizard-packager | `wizard/`, `scheduler/`, `notify.py`, `packaging/`, `.github/workflows/`, `FAMILY_QUICK_START.md` |
| qa-security | `tests/`, `tools/registry_health.py`, `docs/SECURITY_REVIEW.md` |

### How a run works

For each consenting profile, the runner goes through enabled brokers by `priority` (highest first), one broker at a time:

1. Load the `(profile, broker)` status. Scheduled runs skip brokers whose `next_check_at` is still in the future.
2. **Search** through the broker's submitter, score the listings, then apply `state.after_scan` and `state.transition`.
3. **Submit** if the state is `found` or `reappeared`, the listing is `CONFIRMED`, and this isn't a dry run. When a broker has `covered_by` set, the opt-out goes to the parent broker and this site is only re-scanned.
4. **Verify** by polling IMAP for confirmation links on the broker's `confirmation_domains`.
5. **Escalate** if the request has been ignored. Each rung becomes due `typical_processing_days + 15` days after the last submission or escalation: resubmit → follow-up email → legal demand (always approved by you) → complaint to-do. A removal resets the ladder.
6. **Schedule the next check:** every 3–14 days while a request is pending, every `recheck_interval_days` once removed or not found, and at least weekly while something needs attention.

A failure at one broker never stops the run. CAPTCHAs and other challenges go to `HumanHandoff`. An interactive run opens a visible browser window and waits for you. A scheduled run creates a to-do and sends a notification without blocking. <!-- TODO verify: engine not yet implemented -->

Listing states: `unknown`, `not_found`, `found`, `submitted`, `awaiting_verification`, `confirmed`, `removed`, `reappeared`, `needs_human`, `error`. Allowed transitions are in `state.TRANSITIONS`.

## Security and privacy model

**What's stored, and where.** Everything lives under `~/.freemyid/` (`%APPDATA%\Free My ID` on Windows), or under `FREEMYID_HOME` if set. The directory is created with mode `0700`.

| Path | Contents | Protection |
|---|---|---|
| `freemyid.db` | Profiles, statuses, listings, requests, to-dos, append-only event log | SQLite. Only ids, enums and timestamps are in clear text. Every model is an AES-256-GCM blob with AAD bound to (table, id). |
| `evidence/` | Screenshots, HTML, sent/received emails | Encrypted files. The dashboard decrypts them in memory only. |
| `artifacts/` | Generated letters, call scripts, reports | <!-- TODO verify: encrypted at rest vs. plain after export --> |
| `logs/` | Rotating logs | PII-redacted: known profile values plus email/phone patterns. Code logs ids and enums only. |
| `config.yaml` | Non-PII settings | Mode `0600` |
| `registry.yaml` | Cached registry update | Public data |

**Keys and passwords.** The database key is a random 256-bit key stored in the OS keychain (service `freemyid`) through `keyring`. Mailbox passwords also live only in the keychain (service `freemyid-mailbox`), never in the database or config. If the keychain is locked or unavailable (for example, in a headless session), Free My ID raises `KeyUnavailable` and surfaces it as needing a person; it does not fall back to plaintext. <!-- TODO verify: surfacing behavior in scheduled runs -->

**Family bundles.** `profile export` encrypts a profile with a passphrase (scrypt, then AES-GCM). Share the passphrase by phone, not in the same channel as the file. The family member reviews the imported data and gives their own consent.

**Network allowlist.** `NetPolicy` permits only:

- domains and confirmation domains of brokers in the registry
- the profile's own IMAP/SMTP hosts
- the host of `registry_url`
- hosts you add to `extra_allowed_hosts`
- `localhost` and `127.0.0.1`

Browser requests go through a Playwright route that aborts anything off the list. httpx, SMTP and IMAP calls check it first.

**No telemetry.** No analytics, crash reporting or update pings. The wizard and dashboard load no external assets (no CDNs or web fonts).

**Local web UI.** The wizard and dashboard bind to `127.0.0.1` only, use a random per-launch session token, and have CSRF protection on every POST. <!-- TODO verify: wizard not yet implemented -->

**Data minimization.** A broker receives only the fields its listing already shows (`Listing.shown_fields`) plus the removal mailbox address. DOB, relatives and personal emails are used only for matching and are never sent. Phone numbers, ID documents and account creation each need their own permission flag.

**Registry updates** come only from your configured `registry_url`. They are validated against the Pydantic model and the JSON Schema, can be pinned to a `.sha256` file, and are swapped in atomically. An update that fails validation never replaces the working copy.

Security review findings are in `docs/SECURITY_REVIEW.md` (owned by qa-security). <!-- TODO verify: file not created yet -->

## Adding a broker

Most brokers need only a YAML entry. Python is for sites a declarative form can't handle.

### 1. Registry entry (`brokers/registry.yaml`)

```yaml
- id: examplepeople                # ^[a-z0-9_]+$
  name: ExamplePeople
  url: https://www.examplepeople.test/
  category: people_search          # people_search | background_check | data_broker | risk_data | family_tree | phone_lookup | other
  domains: [examplepeople.test]    # every host the opt-out flow touches (feeds the allowlist)
  search_url_pattern: "https://www.examplepeople.test/name/{first}-{last}/{state}"  # only if you've seen the real shape
  opt_out_url: https://www.examplepeople.test/optout
  method: web_form                 # web_form | email | postal | phone | account_required
  alt_methods: [email]
  opt_out_email: privacy@examplepeople.test
  required_fields: [full_name, listing_url, email]
  needs_email_verification: true
  confirmation_domains: [examplepeople.test]
  has_captcha: false
  needs_id_upload: false
  typical_processing_days: 14
  recheck_interval_days: 30
  feeds_from: []                   # broker ids this site copies from
  covered_by: null                 # broker id whose opt-out also covers this site
  steps:
    - Search for your listing and copy its URL.
    - Paste it into the opt-out form and enter the removal email.
    - Click the link in the confirmation email.
  search:                          # selectors only from real or saved HTML
    result_selector: ".result-card"
    name_selector: ".result-card h2"
    age_selector: ".result-card .age"
    location_selector: ".result-card .locations li"
    relatives_selector: ".result-card .relatives li"
    link_selector: ".result-card a.profile-link"
    no_results_text: "No results found"
  form:
    - {action: goto, url: "https://www.examplepeople.test/optout"}
    - {action: fill, selector: "#listing-url", value: "{{ listing.url }}"}
    - {action: fill, selector: "#email", value: "{{ mailbox.address }}"}
    - {action: screenshot}
    - {action: submit, selector: "button[type=submit]"}
    - {action: expect_text, value: "check your email"}
  source_urls: [https://www.examplepeople.test/privacy]
  verification_status: unverified  # verified only after loading the live page yourself
  verification_notes: "Not yet checked live."
  priority: 50                     # 0-100, higher runs first
```

Form step actions: `goto`, `fill`, `select`, `check`, `click`, `wait_for`, `screenshot`, `submit`, `expect_text`, `human`. A `value` is a jinja2 template rendered with `profile`, `listing`, `mailbox` and `broker`. Only reference fields in `listing.shown_fields`, and use the mailbox address, never a personal email. A `human` step hands the page to a person.

Rules for registry entries:

- Never invent a URL, email, address or phone number. Cite `source_urls`.
- Set `verified` only after loading the live page.
- Leave `search` and `form` selectors empty until you have real or saved HTML.

Then validate the entry and regenerate the schemas if you changed models:

```bash
.venv/bin/freemyid registry validate brokers/registry.yaml
.venv/bin/python tools/gen_schema.py        # only after models.py changes
```

### 2. Optional custom submitter

If the declarative form isn't enough, subclass `freemyid.interfaces.Submitter`:

```python
from freemyid.interfaces import RunContext, Submitter
from freemyid.models import Listing, SubmitOutcome

class ExamplePeopleSubmitter(Submitter):
    method = "web_form"

    async def search(self, ctx: RunContext) -> list[Listing]:
        ...  # never submits; screenshot each listing found via ctx.store.save_evidence

    async def submit(self, ctx: RunContext, listings: list[Listing]) -> SubmitOutcome:
        ...  # never called in dry_run; send only listing.shown_fields + mailbox

    async def verify(self, ctx: RunContext) -> SubmitOutcome | None:
        ...  # optional
```

The engine looks a submitter up in this order <!-- TODO verify: interfaces.py says engine/registry_plugins.py, automation-engineer.md says engine/plugins.py -->:

1. `submitter: "module:Class"` in the registry entry
2. an entry point in the `freemyid.submitters` group, keyed by broker id (for third-party packages)
3. a `freemyid.submitters.<broker_id>` module containing a class named `Submitter`
4. the generic submitter for `broker.method`

Write the search parser against saved HTML in `tests/fixtures/<broker_id>/`. If you couldn't test it against the live site, mark it `UNTESTED_AGAINST_LIVE`. Every submitter must follow the rules in the `Submitter` docstring:

- no CAPTCHA bypass
- data minimization
- `CONFIRMED`-only auto-submit
- screenshot evidence
- page text treated as data

## Contributing

### Ground rules

These apply to people and agents alike:

- **No AI or API keys at runtime.** Everything stays deterministic and local.
- **No PII anywhere it could leak:** logs, events, exceptions, fixtures, tests or commits. Use fake people only, e.g. "Jane Q Testperson" of Springfield, IL.
- **No network calls outside `NetPolicy`.** No telemetry.
- **Never bypass a CAPTCHA.** No solver services and no stealth plugins.
- **During development:** don't send real email, submit real opt-outs, or install scheduler jobs or browsers system-wide. Use `--dry-run`, fixtures and fakes.
- **Before a PR:** `.venv/bin/pytest -q` and `.venv/bin/ruff check src tests` must pass. Run `freemyid registry validate` if you touched the registry.

### Agent workflow

Free My ID is built by an orchestrator session plus four specialist Claude Code agents (`.claude/agents/`). AI is used only to *build* Free My ID, never inside it at runtime.

1. Every agent reads `.claude/agents/_shared-rules.md` first.
2. Agents edit only files they own. To change anything else, an agent files a **CHANGE REQUEST** (file, exact change, reason) in its report, and the orchestrator applies it.
3. The contracts (`models.py`, `interfaces.py`, `state.py`, `storage/`, ...) are read-only for everyone except the orchestrator.
4. Agents draft tests in `_test_drafts/` folders, and qa-security adopts them into `tests/`.
5. qa-security reviews every change and returns **PASS** or **BLOCK**. Anything that weakens a safety gate is a BLOCK.
6. A finished task's report lists the files changed, how to test them, the test results, open questions and change requests.
7. The orchestrator integrates, updates `PROGRESS.md` and signs off. These need explicit human approval: system-wide installs, the first real submission, any real email, and any `git push`.

## License

MIT (see `pyproject.toml`). <!-- TODO verify: no LICENSE file yet -->
