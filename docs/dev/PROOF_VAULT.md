# Evidence lifecycle: from a saved item to a receipt

Use the [architecture map](ARCHITECTURE.md) for the wider app flow. This guide follows the evidence entry points and readers in the current worktree. The evidence kinds include received and sent email, letters, user attestations, call notes and postal receipts (`src/freemyid/models.py:209-217`).

## How an item reaches the vault

| Entry point | What is saved | How it is connected |
| --- | --- | --- |
| Matched mailbox reply | `save_replies` saves the reply bytes as `EMAIL_RECEIVED` evidence, skipping a content hash already stored for that profile and broker. The runner passes matched replies from its mailbox scan into this helper (`src/freemyid/engine/runner.py:209-227,725-738`). | The helper links the reply to the latest real sent request eligible for the reply date, when one exists; a reply can also be saved without a request link (`src/freemyid/engine/runner.py:197-206,221-224`). |
| A person marks a hand-completed step done | `mark_resolved` calls `save_attestation` for eligible submission steps. It creates `USER_ATTESTATION` text saying what the person reports doing and when. Failure to save this copy is caught rather than blocking completion (`src/freemyid/engine/handoff.py:193-221,224-237`). | The evidence keeps the to-do's profile, broker and optional request ID. It records the person's account of the action; its text does not say the broker confirmed removal (`src/freemyid/engine/handoff.py:213-219`). |
| Optional call note or mailing receipt | `save_call_note` normalizes whitespace, limits the note to 1,000 characters and saves `PHONE_CALL_NOTE` text. `save_receipt` accepts recognized PDF, JPG or PNG bytes up to 10 MB and saves `POSTAL_RECEIPT` bytes; neither helper saves without a broker ID (`src/freemyid/wizard/proof_input.py:15-27,46-66`). | Both copy the to-do's profile, broker and request ID into the evidence record (`src/freemyid/wizard/proof_input.py:53-55,63-65`). |
| A new email request is queued | `queue_email` saves the request, then saves a `LETTER` copy through `_save_blob`, which delegates to `Store.save_evidence`. A practice request starts as a draft; a real request starts queued for approval (`src/freemyid/engine/outbox.py:239-244,355-369`). | The letter is tied to that request. This queued copy alone is not a sent-email record: after the mailer returns successfully, `send_request` saves separate `EMAIL_SENT` evidence and records the request as sent (`src/freemyid/engine/outbox.py:393-407`). |
| A signed authorization is attached | `save_authorization` saves a `LETTER` evidence item with broker ID `_consent` and returns its evidence ID. Setup stores that ID in `consent.authorization_doc`; the later attach route does the same for an existing profile (`src/freemyid/wizard/draft.py:550-567`; `src/freemyid/wizard/server.py:739-752`). | `authorization_on_file` looks for the named evidence under this same profile and the consent broker, and checks that its stored file exists (`src/freemyid/consent.py:30-31,44-52`). |

## Shared storage and lookup

The writers above save content encrypted through `Store.save_evidence`. It writes the evidence content under the evidence directory, records a content hash and saves its evidence record. The corresponding read is `Store.read_evidence`; `list_evidence` selects records for a profile, optionally narrows them to one broker and orders them by creation time (`src/freemyid/storage/db.py:309-333`).

The common submitter helper builds a relative path from the profile ID, broker ID, evidence ID and extension. The signed-authorization writer uses a separate consent subfolder. Both still use the same evidence storage operation (`src/freemyid/submitters/base.py:142-148`; `src/freemyid/wizard/draft.py:550-556`).

## Viewing a stored receipt

The profile page groups evidence by broker but leaves out `_consent` items. The broker page receives the evidence list for its profile and broker (`src/freemyid/wizard/server.py:261-286`). In that page, received replies have links under “What came back”; the receipts section shows screenshot thumbnails and links to other evidence using the evidence route (`src/freemyid/wizard/views.py:139-170`).

`GET /evidence/{pid}/{eid}` searches evidence belonging to the requested profile, reads the matching item and returns PNG or JPEG bytes as an image. Other content is returned as a download (`application/octet-stream`). Every response carries a sandboxing Content-Security-Policy header. A failed read returns 500; an unknown item returns 404 (`src/freemyid/wizard/server.py:336-354`).

## The progress report is a separate summary

The report does not assemble an evidence bundle. `build_report` uses the person's display label, broker status records, dates and to-dos to build its summary and table; its “asked”, “confirmed or no longer list” and “waiting” counts come from state groups. The generated document contains no evidence images or reply attachments (`src/freemyid/wizard/report.py:21-23,26-71`).

The builder writes generated HTML under `artifacts/`. When PDF is requested it tries the optional PDF renderer; if that import is unavailable, it returns the HTML path instead. The wizard report route requests HTML and returns the resulting file as a download (`src/freemyid/wizard/report.py:72-86`; `src/freemyid/wizard/server.py:729-737`). Treat that generated report as an output file, separately from the encrypted evidence content described above.

## What wipe removes

`freemyid wipe` first checks that the selected data folder is clearly Free My ID's own (a `.freemyid-home` marker or its database, and never a home or system root), then asks for confirmation unless `--yes` is supplied. The confirmation warns that other Free My ID data folders on the same computer that use the system keychain will stop working too, because the wipe deletes this folder's encryption key and the saved mailbox passwords from the keychain, and the keychain entry is shared (a key held for a different folder is left alone, `src/freemyid/crypto.py:116-122`). It also removes the background task. Its file-removal loop then visits only `OWNED_ENTRIES` inside that folder: these include the database, `evidence/`, `artifacts/`, logs and app configuration/cache files. Finally it tries to remove the now-empty folder, leaving other top-level names in place (`src/freemyid/cli.py:582-627`; `src/freemyid/paths.py:30-45`). A copy saved elsewhere is outside that loop (`src/freemyid/cli.py:618-627`).

## What this guide does not cover

Key handling, cipher choices, passwords and other secret-handling internals are reserved to the in-house team. This guide describes evidence flow and the current readers only; it is not a review of those security implementations or a claim that a saved note proves removal. See the [architecture map](ARCHITECTURE.md) for the module overview and the work-order boundary (`docs/vendor/WO-253.md:20-27`).
