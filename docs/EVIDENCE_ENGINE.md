# Compliance-evidence engine

Owner direction 2026-11-11: engineer the big way, not the small win, and never with evasion. When a broker blocks a lawful request, we don't get past the block. We record it, timestamp it, tie it to the law and the deadline, and hand the person a pre-filled regulator complaint with a tamper-evident evidence annex. The harder a broker blocks, the stronger the case gets. A bypass works the other way: the harder the broker blocks, the weaker it gets.

Roadmap: bar 9 and section 7a in `docs/roadmap/ROADMAP_TO_1.0.md`. Work orders WO-620 to WO-626 below.

## 1. Boundaries (shared rule 5 and this engine)

1. **No evasion.** No CAPTCHA solving, stealth, UA or fingerprint spoofing, proxies or IP rotation, in any form or behind any flag.
2. **Honest identity.** Requests run from the person's own computer, mailbox and browser, as the person or as their authorized agent. The app's own HTTP client names itself; the WO-612 browser session keeps the real UA plus the Free My ID suffix.
3. **Fail loudly, never reshape.** A block is never retried with altered headers, timing tricks or a different client.
   - A transient failure (429, 5xx, timeout) is retried later with the same request. A 429 caused by our own retries is never an obstruction (SEC-EE-2).
   - A real block goes straight to evidence capture.
4. **The person files.** The engine prepares the complaint; the person reviews and sends it. It is a legal act in their name, so it needs one approval. That approval is batched with others and counts toward the bar 9 residual-click budget.
5. **Privacy.**
   - Evidence that holds personal data lives only in the encrypted `evidence/` store.
   - Events and block statistics hold ids, enums, counts and times only.
   - An exported bundle leaves the computer only when the person sends a complaint.

## 2. What already exists (we extend, not rebuild)

| Piece | Where |
|---|---|
| `Evidence` (encrypted file, `sha256`, `request_id`, `kind`) | `models.py:709` |
| `EvidenceKind` (screenshot, html, email sent/received, letter, attestation, call note, postal receipt) | `models.py:209` |
| Authorized-agent authorization document | `Consent.authorization_doc`, `models.py:228` |
| Escalation ladder: resubmit, then follow-up, then legal demand, then COMPLAINT to-do | `state.py:101`, `runner.py` escalation |
| Legal clock: 45 days (15 when stated shorter) plus verified extensions | `runner.py:112`, `legal_window_end` |
| Regulator links per broker (`ag_complaint_url`, `other_complaint_urls`, `authorized_agent_allowed`) | `models.py:608-614` |
| Challenge detection (yes/no) | `browser.detect_challenge`, `browser.py:84` |
| Reply classifier (confirmed / denied / needs_id / needs_more_time / unknown), **not yet called by the loop** | `mail.classify_reply`, `mail.py:406` |
| Search-session outcomes (read, self-cleared, challenge, queued, hand-check) | `engine/search_session.py` (WO-612) |

## 3. Topology (Python, inside the existing package)

There is no new stack. The app is Python 3 with pydantic models, an encrypted SQLite store, and Playwright for the browser. Evidence integrity needs a canonical byte form and a hash; the standard library already gives us `hashlib` and canonical `json.dumps(sort_keys=True, separators=(",", ":"))`.

```
src/freemyid/
  models.py                  CONTRACT (Morgan): ObstructionKind, ObstructionRecord,
                             EvidenceKind.BLOCK_CAPTURE / RESPONSE_TIMELINE, BundleManifest
  evidence_bundle.py         NEW: build, verify and export a tamper-evident bundle
  engine/obstruction.py      NEW: BlockDetector, classify_obstruction(...) -> ObstructionRecord
  engine/complaints.py       NEW: obstruction + state law -> complaint draft + annex
  engine/runner.py           wire: reply codes and obstruction records into the ladder
  engine/mail.py             existing classify_reply, unchanged
brokers/obstruction_law.yaml NEW DATA (from Priya's OBSTRUCTION_LAW.md): per state: statute
                             id, covered obstruction kinds, response days, regulator channel
schema/                      regenerated (tools/gen_schema.py)
```

## 4. Data schema

Contract, written as pydantic sketches. The JSON Schema files are generated from these.

```python
class ObstructionKind(StrEnum):
    CAPTCHA_ON_REQUEST = "captcha_on_request"     # a challenge that stays on an opt-out/deletion form
    BLOCKED_REQUEST = "blocked_request"           # 403 or a vendor block page on the request surface, real browser
    ACCOUNT_REQUIRED = "account_required"
    PHONE_REQUIRED = "phone_required"             # the request needs a phone call or SMS
    EXCESS_VERIFICATION = "excess_verification"   # ID document or more data than the law allows
    AGENT_REFUSED = "agent_refused"               # an authorized agent was refused (from a reply)
    REQUEST_DENIED = "request_denied"             # a reply denies a lawful request
    DEADLINE_MISSED = "deadline_missed"           # the legal clock ran out with no confirmation
    UNAVAILABLE = "unavailable"                   # the request surface is down repeatedly (>= 3 runs over >= 7 days)

class ObstructionRecord(_Base):          # PII-free by construction: safe for Events and statistics
    id: Id
    profile_id: Id
    broker_id: BrokerId
    request_id: Id | None                # the lawful request that was obstructed
    surface: Literal["optout_form", "deletion_form", "email", "postal", "confirmation_link"]
    kind: ObstructionKind
    vendor: ObstructionVendor | None     # fixed enum: recaptcha-v2/v3/enterprise, hcaptcha, turnstile, arkose, datadome, perimeterx, cloudflare-block, akamai-block, other
    http_status: int | None
    observed_at: list[datetime]          # every sighting; technical kinds need >= 2 on different days
    request_sent_at: datetime | None
    legal_due_on: date | None            # from runner.legal_window_end
    state: str                           # the person's state (2 letters): picks the law
    statute_ids: list[str]               # from brokers/obstruction_law.yaml
    evidence_ids: list[Id]               # Evidence rows (encrypted) that prove it
    confidence: Literal["observed", "confirmed"]

class BundleEntry(_Base):
    seq: int
    evidence_id: Id
    kind: EvidenceKind
    created_at: datetime
    sha256: str                          # of the decrypted evidence bytes
    prev_hash: str                       # hash chain: sha256(prev_hash + canonical(entry without prev_hash))

class BundleManifest(_Base):
    version: Literal[1] = 1
    bundle_id: Id
    obstruction_id: Id
    created_at: datetime
    app_version: str
    entries: list[BundleEntry]           # ordered: request sent, broker replies, block captures, clock
    chain_head: str                      # the last entry's chained hash
    manifest_sha256: str                 # over the canonical manifest without this field
    timestamp_token: str | None = None   # optional RFC 3161 token over manifest_sha256 (owner decision E2)
```

**Why a hash chain, and what it does and doesn't prove.** The chain makes any later edit, reorder or deletion detectable, and `verify_bundle()` re-derives every hash. On its own it can't prove *when* the bundle was made, because the person's own computer could have produced it at any time. For that the bundle sends only `manifest_sha256`, a hash with no personal data in it, to an RFC 3161 timestamp authority. The token proves the bundle existed at that moment. This adds a network host to the allowlist, so it waits for owner decision E2; the hash chain is the MVP. The emails in the bundle carry their own server timestamps and DKIM signatures, which the bundle keeps verbatim as independent proof.

**Export (SEC-EE-4).** A zip with the readable complaint (text, then PDF in WO-624), `manifest.json`, the decrypted evidence files named by `seq`, and a plain `HOW_TO_VERIFY.txt` (sha256sum commands).
- Written only at the person's send step, to a place the person chooses, with a plain warning that it holds their personal data.
- Temp copies are deleted afterwards.
- It holds only that obstruction's `evidence_ids`.
- A passphrase-encrypted variant (the existing `crypto.export_with_passphrase` pattern) is offered.
- Captured broker pages can include third-party data (relatives). That is accepted on purpose, because it is the evidence, and `HOW_TO_VERIFY.txt` says so.
- Hash-chain details: the genesis value is `BUNDLE_GENESIS` = sha256(`freemyid-bundle-v1`); `manifest_sha256` excludes both itself and `timestamp_token`.
- Timestamping (E2, later): only `manifest_sha256` is sent, to one NetPolicy-allowlisted host, with no client identity. The timestamp server still learns the person's IP address and the time, and the complaint screen will say so.

## 5. BlockDetector (WO-621): an obstruction, or just an error?

**Rule 1: only a request surface can be an obstruction.** A CAPTCHA on a *search* page is a site protecting its search, which is lawful and normal; it goes to the search router (WO-612/614), never to a complaint. The same CAPTCHA on an *opt-out or deletion form* can obstruct a statutory right. `surface` is always set by the caller, never guessed from the page.

| What we saw (on a request surface) | Result |
|---|---|
| 200, form submitted, acknowledgement shown | not an obstruction; Evidence `HTML` + `SCREENSHOT` |
| 404 on the listing URL after a request | not an obstruction; the listing may be gone, so re-scan it |
| 5xx, timeout, connection reset | TRANSIENT: same request on the next run; `UNAVAILABLE` only after >= 3 failures over >= 7 days |
| DNS failure, seizure banner, parked page | broker GONE (router), not a complaint |
| Challenge widget still there after the grace period, a fixed passive wait (as in WO-612) for a challenge that clears by itself, never extended and never waiting for a solver (SEC-EE-5) | `CAPTCHA_ON_REQUEST` |
| 403 or a vendor block page in the person's real browser, with no widget; 429 counts only if it repeats on different days (SEC-EE-2) | `BLOCKED_REQUEST` |
| The form wants an account or login | `ACCOUNT_REQUIRED` |
| The form or reply needs a phone call or SMS | `PHONE_REQUIRED` |
| The reply asks for an ID document or more data than the law allows (`classify_reply` needs_id, plus a law check) | `EXCESS_VERIFICATION` |
| `classify_reply` returns denied | `REQUEST_DENIED`, or `AGENT_REFUSED` when the request went as an agent |
| `legal_due_on` passed with no confirmation and no verified extension | `DEADLINE_MISSED` |

**Confidence.**
- Technical kinds (CAPTCHA, block, unavailable) start as `observed` and become `confirmed` after a second sighting on a different day. Only a `confirmed` record can produce a complaint.
- Reply and clock kinds are confirmed at once: the email or the calendar is the proof.

**Capture.** On every sighting the detector saves, through the existing encrypted `Evidence` path:
- the page (`HTML`)
- a `SCREENSHOT`
- a `BLOCK_CAPTURE` JSON with status, final URL, redirect chain, the response headers that identify the vendor (an allowlisted set, no cookies), frame hosts, the timestamp, and the outgoing request as field NAMES and value LENGTHS only. Hashes of short values like names and ZIP codes can be reversed, so none are stored (SEC-EE-3). URLs keep scheme, host and path only; query strings and fragments are dropped. Captures (URLs, headers) never reach events, statistics or the atlas

It never captures cookies, auth tokens or the person's other tabs.

**Never.** The detector never clicks, types, scrolls, waits for a solve or retries with changes. It reads what the site sent, the same way `detect_challenge` does today.

## 6. The loop: replies and obstructions in the ladder (WO-622)

| Event | Ladder effect |
|---|---|
| `confirmed` reply | REMOVED once a re-scan agrees; the ladder resets |
| `denied` reply | `REQUEST_DENIED` record; skip to the legal-demand rung (still inside the legal window rules, BL-IN-10) |
| `needs_id` reply | template answer: cite the statute's verification limits and offer only the fields the person allowed (rule 6), never an ID document; if the broker insists, `EXCESS_VERIFICATION` |
| `needs_more_time` reply | one extension, capped at what the law allows (`extension_days` verified, else 45) |
| `unknown` reply | keep the timer; listed in the monthly summary |
| a `confirmed` obstruction | the COMPLAINT rung becomes due at once for request-surface obstructions; for `DEADLINE_MISSED` it follows the existing window |

## 7. Complaint generator (WO-624)

Input: one `confirmed` ObstructionRecord, the person's state, and `brokers/obstruction_law.yaml`. Output:
- a complaint draft in the regulator's own field order (CPPA, the state AG, or the FTC for states with no law), in plain words, quoting the statute;
- the bundle zip as an annex;
- a COMPLAINT to-do with one "Review and send" step.

States with no comprehensive privacy law (NC, SC and AZ today) get the FTC and broker-policy route, saying honestly what that can and can't do.

## 8. Work orders

| WO | What | Who | Depends on |
|---|---|---|---|
| WO-620 | Contracts: the models in section 4, `EvidenceKind` additions, schema regeneration | Morgan | none |
| WO-621 | BlockDetector `engine/obstruction.py` plus synthetic fixtures for every row in section 5 | Theo, then a Marcus review | 620 |
| WO-622 | Reply and obstruction wiring in the runner (section 6) | Theo, then Marcus | 620 |
| WO-623 | `evidence_bundle.py`: build, verify, export; hash chain; golden tests for tamper detection | Theo, then Marcus | 620 |
| WO-624 | Complaint generator plus the review screen | Theo (engine), Nina (screen), Jordan (wording), Marcus | 621-623, 625 |
| WO-625 | Research: OBSTRUCTION_LAW.md, regulator channels, GPC state table | Priya | none (running) |
| WO-626 | Block atlas: nightly LOAD-ONLY checks of request pages (never fill, never submit, never retry); `CanaryObservation` with no profile; results labelled datacenter-origin and never used for complaints or the public index unless real-user records confirm them (SEC-EE-1) | Theo, then Dana for scheduling | 621 |
| WO-631 | Evidence viewing: friendly labels for the new kinds; in-app escaped view instead of plaintext download | Nina, then Marcus | 620 |

## 8a. Law findings that bind the engine (WO-625, Priya, 95ca9c8; docs/research/OBSTRUCTION_LAW.md)

1. **Facts, not conclusions.** No statute names "CAPTCHA". An express friction rule exists only in California (11 CCR 7004(a)(5)). Obstruction records, events and complaint drafts state facts (what was sent, what blocked it, when) and never assert that the broker broke the law. Statute citations come only from the per-state law data, never from code.
2. **Suppression counts as done.** Kentucky and Maryland let a broker satisfy deletion by suppression or opt-out. A suppression or opt-out reply is the "done" path (verified by re-scan), never `REQUEST_DENIED`.
3. **Authorized agents.** Outside CA and RI, agent rules cover opt-out only. `AGENT_REFUSED` on a deletion request is recorded as a fact everywhere, but cited as a legal claim only in CA and RI.
4. **Pre-fill, never submit.** Regulator forms block automated clients, and complaints filed in TX, OR and NC can become public. Drafts minimise personal details, and the person gets a plain warning before sending (E1 approval).
5. **Never record phone calls** (two-party-consent states). Only the fact that a call was demanded is recorded.
6. **What is express in the law data:**
   - in every law state: the deadline (45 days plus one 45-day extension; Iowa 90 plus 45);
   - no new account required (about 11 states plus CA);
   - no verification on opt-outs (CA, OR, MT, DE, NH, NJ, MN, MD, RI).
   The per-state YAML shape is in `docs/handoff/broker-researcher-obstruction.md`; the `obstruction_law` model contract arrives with WO-624.

**Upgrade note.** From 0.5 the evidence table can hold `block_capture` and `response_timeline`. An older app version will fail to list that evidence, so downgrading below 0.5 is not supported (qa-security LOW).

## 9. Owner decisions (DECIDED 2026-11-11, as recommended)

- **E1. DECIDED 2026-11-11:** filing a complaint needs one approval from the person (a legal act in their name). Approvals are batched and count toward the bar 9 residual.
- **E2. DECIDED 2026-11-11:** RFC 3161 timestamping comes later; the local hash chain is the MVP.
- **E3. DECIDED 2026-11-11:** the per-broker obstruction index (PII-free) is published after 0.9, after attorney review (D6).
