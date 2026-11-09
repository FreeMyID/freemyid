# Free My ID architecture map

This guide is a short map for contributors. Source references use repository-relative paths and line numbers. The modules named below describe the current code in this worktree; check the cited lines if the code changes.

## Main path through the app

The `freemyid` command is registered to `freemyid.cli:app` (`pyproject.toml:56-57`). The CLI can start the local wizard or run setup in the terminal (`src/freemyid/cli.py:147-176`). The wizard is a FastAPI app bound to loopback (`src/freemyid/wizard/server.py:831-849`). When the wizard reaches Finish, it validates and saves the draft through the Store, then starts the configured follow-up (`src/freemyid/wizard/server.py:785-811`; `src/freemyid/wizard/draft.py:559-583`).

```mermaid
flowchart TD
    Person["Person using CLI or local wizard"] --> Setup["Setup and review profile"]
    Setup --> Store["Store: profile, status, requests, evidence"]
    Store --> Consent["Consent check"]
    Consent --> Runner["Runner: process enabled brokers"]
    Runner --> Net["Network policy and broker registry"]
    Net --> Tier{"Submission route"}
    Tier --> Web["Automatic: browser submitter"]
    Tier --> Email["Email: outbox request"]
    Tier --> Assisted["Assisted: person gets a to-do"]
    Email --> Approval["Approval and submission setting"]
    Web --> Store
    Approval --> Store
    Assisted --> Store
    Monitor[Monitor: maintainer check] --> Net
    Exposure[Exposure scan for a profile] --> Net
    Exposure --> Store
```

The runner checks each profile's consent before processing it, then visits enabled brokers one at a time (`src/freemyid/engine/runner.py:322-346`). For each broker it determines a tier, scans when the broker is eligible, and submits only when the state allows it (`src/freemyid/engine/runner.py:405-440`). The consent rules are centralized in `consent_ok` (`src/freemyid/consent.py:55-82`).

## Module map

| Area | What it does | Source |
|---|---|---|
| CLI and configuration | Exposes the `freemyid` command; the CLI delegates app settings to `config.py`. | `pyproject.toml:56-57`; `src/freemyid/cli.py:1-22,147-176`; `src/freemyid/config.py:1-13,16-38` |
| Wizard and dashboard | Accepts setup and settings forms, saves a profile, and shows its status, to-dos and queued requests. | `src/freemyid/wizard/server.py:134-150,217-239,477-495,785-811`; `src/freemyid/wizard/draft.py:559-583` |
| Runner | Checks consent, selects enabled brokers, updates status, and asks a submitter to handle eligible requests. | `src/freemyid/engine/runner.py:322-346,405-440,545-573` |
| Tier selection | Chooses automatic browser work, email, or assisted steps from the broker, profile, permissions and configuration. | `src/freemyid/engine/tiers.py:3-12,59-85`; `src/freemyid/engine/plugins.py:53-68` |
| Browser and network boundary | Builds a per-run allow-list from broker, confirmation, mailbox and configured hosts; broker runs are narrowed to that allow-list. | `src/freemyid/netpolicy.py:1-11,57-100`; `src/freemyid/submitters/web_form.py:1-9` |
| Broker monitor | Checks enabled brokers' public opt-out page/form selectors and emits a `monitor/1` report; it does not load a profile or use the Store. | `src/freemyid/monitor.py:1-21,39-55,321-362`; `docs/MONITOR.md:1-9,11-24` |
| Exposure lookup | Uses a consenting profile to look for matching public broker listings, scores the findings, saves a result, and exposes read-only dashboard/history helpers. | `src/freemyid/engine/exposure.py:559-624,784-810,906-912`; `src/freemyid/exposure_models.py:46-68,144-163` |
| Email and outbox | Creates a request and stored letter; queued requests are presented in the outbox, where an approval action can send them. The default mailer requires real submissions to be enabled. | `src/freemyid/engine/outbox.py:277-319,357-365,384-410`; `src/freemyid/wizard/server.py:477-514` |
| Assisted work | Creates a local to-do for a person to complete in their own browser; the Assisted submitter does not search the web. It supports manual-email resume tokens, and optional call notes or postal receipts can be stored as evidence. | `src/freemyid/submitters/assisted.py:1-10,94-118,180-197`; `src/freemyid/wizard/proof_input.py:31-65` |
| Evidence kinds | Records replies received by the mailbox, user attestations, phone-call notes, and postal receipts; content is saved in the Store's encrypted evidence files. | `src/freemyid/models.py:209-217`; `src/freemyid/engine/runner.py:209-227`; `src/freemyid/engine/handoff.py:206-220`; `src/freemyid/wizard/proof_input.py:46-65`; `src/freemyid/storage/db.py:309-322` |
| Local scheduler | Renders scheduled re-check instructions for supported operating systems. | `src/freemyid/scheduler/__init__.py:1-45`; `src/freemyid/scheduler/render.py:1-93` |

## Monitor and exposure data flows

- **Monitor:** the `freemyid monitor` command accepts an optional prior JSON report, calls `run_monitor`, and prints the report as JSON (`src/freemyid/cli.py:1045-1112`). The monitor checks enabled web brokers and returns schema `monitor/1`; its output contains broker health and selector/fingerprint information, but no profile data or page text (`src/freemyid/monitor.py:1-21,321-367`; `docs/MONITOR.md:1-9,23-24`). It makes network requests through the allow-list policy and may use one headless page load when requested; it never fills, clicks, or submits a form (`src/freemyid/monitor.py:4-18,321-343,370-380`; `docs/MONITOR.md:11-34`). The weekly job is an external scheduled caller, not a scheduler inside this command (`docs/MONITOR.md:3-9`).
- **Exposure lookup:** `scan_exposure` requires a profile and consent, queries the configured broker registry through network fetchers unless run offline, and persists the resulting score and entries (`src/freemyid/engine/exposure.py:559-624`). Entries may include listing URLs, matching signals, hand-check URLs, and whether previous-address or previous-name searches were used (`src/freemyid/exposure_models.py:46-68`). The dashboard helpers read stored results and do not perform network requests (`src/freemyid/engine/exposure.py:784-803,906-912`).
- **Assisted requests and evidence:** the Assisted submitter creates local to-dos and does not search; `manual_email_token` identifies manual email tasks (`src/freemyid/submitters/assisted.py:100-118,180-197`). Marking an eligible hand-completed task done can save a `USER_ATTESTATION` (`src/freemyid/engine/handoff.py:206-220`). Matched mailbox replies are saved as `EMAIL_RECEIVED` evidence (`src/freemyid/engine/runner.py:209-227`); an optional call note or postal receipt is saved as `PHONE_CALL_NOTE` or `POSTAL_RECEIPT` (`src/freemyid/wizard/proof_input.py:46-65`). Evidence file contents are encrypted through `Store.save_evidence` (`src/freemyid/storage/db.py:309-322`).

## Local data and encryption

The data directory can be set with `FREEMYID_HOME`; otherwise the code uses `.freemyid` under the user's home directory on Linux/macOS and an application-data directory on Windows (`src/freemyid/paths.py:9-18`). The SQLite database is `freemyid.db`; evidence is kept under `evidence/`, and generated letters, scripts and reports under `artifacts/` (`src/freemyid/paths.py:46-60`). The app configuration is the non-PII `config.yaml` file in that same directory (`src/freemyid/config.py:1,46-50,71-76`).

The storage module describes itself as an encrypted SQLite store. It says model data is stored in encrypted blobs and IDs, enums and timestamps remain in clear index columns (`src/freemyid/storage/db.py:1-15,49-75`). Saving a profile uses the store's encrypted serialization path (`src/freemyid/storage/db.py:184-191`). Evidence files are encrypted when saved (`src/freemyid/storage/db.py:310-325`), and generated artifacts are described as encrypted unless the person exports them (`src/freemyid/paths.py:56-60`). This guide does not describe key storage, passwords, cipher details, or secrets handling: those implementation areas are reserved to the in-house team (`docs/VENDOR.md:13-17`).

## Trust boundaries

- **Local interface:** the wizard server binds to loopback. Its request guard checks the host and session, and checks origin/CSRF on POSTs (`src/freemyid/wizard/server.py:1-7,167-202,831-849`).
- **Network destinations:** `NetPolicy` limits the hosts used by browser and mail work; each broker run uses a narrower broker-specific set (`src/freemyid/netpolicy.py:1-11,57-100`). This is a high-level boundary map, not a review of the policy implementation.
- **Consent:** the runner checks consent before working on a profile, and the email approval path checks it again before sending (`src/freemyid/engine/runner.py:323-333`; `src/freemyid/engine/outbox.py:384-410`; `src/freemyid/consent.py:55-82`).
- **Approval and real requests:** email requests are queued or drafted before sending; the outbox approval path calls the send operation, and the default mailer refuses real email until the setting is enabled (`src/freemyid/engine/outbox.py:300-319,357-365,384-410`; `src/freemyid/wizard/server.py:497-514,557-581`).
- **Data minimization:** shared submitter helpers limit fields by what the broker requires and what a listing already shows, and honor the phone-sharing permission (`src/freemyid/submitters/base.py:1-10,29-44`).
- **Monitor versus profile data:** the monitor needs no profile and does not touch the Store; it makes constrained network checks against broker pages and emits broker-level status only (`src/freemyid/monitor.py:1-21,321-362`). Exposure scanning is different: it is profile-specific, consent-gated, may contact broker pages, and saves profile-linked results (`src/freemyid/engine/exposure.py:559-624`).
- **Assisted and evidence:** the Assisted submitter itself does not search or access the network, but it creates to-dos with profile/broker content (`src/freemyid/submitters/assisted.py:1-10,94-118,180-197`). The Store encrypts evidence contents before writing evidence files (`src/freemyid/storage/db.py:309-322`); evidence metadata remains associated with profile and broker records (`src/freemyid/storage/db.py:316-322`).

## Ownership boundary

The vendor rules reserve security, storage, network policy, consent and real sending to the in-house team; vendor work is appropriate for documentation, tests and other specifically scoped paths (`docs/VENDOR.md:13-17`). This architecture guide documents those boundaries at a high level; it does not authorize changes to those modules or describe their sensitive internals.

## Example convention

If an example is needed in a future edit, use obviously fake details such as “Jane Q Testperson, Springfield IL.” Never copy data from a real profile (`AGENTS.md:14-16`; `docs/vendor/WO-134.md`, “Acceptance criteria”).
