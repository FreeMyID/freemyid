# Compliance-Evidence Engine

Status: spec (owner go 2026-11-11). Serves roadmap bar 9 (hands-off, no staff) and section 7a.
Author: Morgan Reyes. Boundary: shared rule 5 — no evasion, see §9.

## 1. The reframe

A CAPTCHA on a marketing page is ordinary. A CAPTCHA, a silent 403, or an ignored request
standing between a person and a **statutory deletion right** is, in several states, an unlawful
obstruction of that right. We do not try to defeat that gate. We **measure it, timestamp it,
hash it, and turn it into a filed regulator complaint** the broker would rather not have earned.

A bypass gets weaker every time a broker updates its defenses. This gets **stronger** the harder
a broker blocks, and at scale it becomes a dataset — "these N brokers obstruct deletion rights" —
that is leverage with regulators and the press no bypass could ever produce. It also survives the
three things an evasion layer cannot: a lawsuit, an antivirus scan, and the code-signing review.

## 2. What already exists (build on this, do not greenfield)

| Capability | Where |
|---|---|
| `Evidence` record: encrypted file under `FREEMYID_HOME/evidence/`, `sha256`, kind, request/listing id | `models.py:709` |
| `EvidenceKind` (screenshot, html, email_sent/received, letter, attestation, …) | `models.py:209` |
| Authorized-agent authorization doc as evidence | `models.py:228` (`Consent.authorization_doc`) |
| 4-rung escalation ladder incl. `COMPLAINT` | `state.py:_LADDER`, `models.py:702` |
| Legal-window clock (45 / 15 days + verified extension) | `runner.py:legal_window_end`, `_overdue_parts` |
| Regulator endpoints (CPPA, AG directory) + per-broker `ag_complaint_url` | `runner.py:88`, `models.py:612` |
| Challenge detection (yes/no) | `browser.py:detect_challenge` |
| Reply classifier (confirmed/denied/needs_id/needs_more_time) — **built, not wired** | `mail.py:classify_reply` |
| Per-folder encryption key (WO-605) | `crypto.py` |

The engine adds five bricks on top. None of them is a new stack: Python 3.12, Pydantic v2
models, the existing encrypted `Store`, `crypto.py` for at-rest encryption. New deps: none in
the MVP (RFC-3161 timestamping is an optional later brick, §4).

## 3. Architecture — five bricks

```
request sent ──▶ [B1 Request Harness] ──▶ broker
                        │ logs exact payload+headers+ts (PII-min, hashed)
   broker blocks / ignores / replies
                        ▼
   [B2 Block-Detector] classifies: obstruction? vendor? surface?   (extends detect_challenge)
                        ▼
   [B3 Evidence Ledger] captures a tamper-evident EvidenceBundle   (extends Evidence)
                        ▼
   [B5 Reply-wiring] classify_reply → escalation ladder            (wires mail.classify_reply)
                        ▼
   deadline passes / denial / obstruction
                        ▼
   [B4 Complaint Generator] statute map → filled complaint + Bundle annex  (extends COMPLAINT rung)
```

- **B1 Request Harness** — already mostly present in the submitters + `mail.py`. Add: for every
  outbound request, write a `RequestRecord` (sent_at, channel, broker, surface, a SHA-256 over the
  canonical outgoing payload). The payload itself is stored encrypted; only its hash is in the log.
- **B2 Block-Detector** (`engine/block_detector.py`, new) — turns `detect_challenge`'s yes/no into a
  classification: the block CLASS and the DISPOSITION (see WO-621 / §5). Pure function over
  `(status_code, headers, body, frame_urls)`; no interaction with the page.
- **B3 Evidence Ledger** (`engine/evidence_bundle.py`, new) — assembles ordered `Evidence` into an
  `EvidenceBundle` with a hash chain and a bound statutory clock (§4).
- **B4 Complaint Generator** (`engine/complaint.py`, new) — maps an obstruction to the governing
  statute and fills a structured complaint (JSON + a printable letter via the existing jinja2
  letter path), attaching the Bundle as an annex. Always queued for the person's approval, never
  auto-filed (keeps a human in the legal loop; the automation is the drafting + evidence).
- **B5 Reply-wiring** — in `runner.py`, call `mail.classify_reply` on each matched broker reply and
  branch: `denied` → jump to the legal-demand rung with the denial quoted; `needs_id` → templated
  reply offering only permitted fields (never auto-sends an ID document); `needs_more_time` → extend
  the clock once within statutory limits; `unknown` → keep the timer, surface in the monthly summary.

## 4. EvidenceBundle schema (Pydantic, our stack)

The Gemini draft used a free JSON schema; we express it as Pydantic v2 to match `models.py` and
get validation + the existing encrypted-relpath guard for free.

```python
class BlockClass(StrEnum):
    OPEN = "open"                    # not a block; recorded for completeness
    HARD_BLOCK = "hard_block"        # 403/429/451 or vendor block page, no challenge widget
    JS_CHALLENGE = "js_challenge"    # interstitial that may self-clear
    CHECKBOX_CAPTCHA = "checkbox_captcha"
    INVISIBLE_CAPTCHA = "invisible_captcha"
    PUZZLE_CAPTCHA = "puzzle_captcha"
    HUMAN_VERIFY = "human_verify"    # phone/email/SMS code
    GEO_BLOCK = "geo_block"
    GONE = "gone"                    # DNS fail / seized / parked
    UNKNOWN = "unknown"              # unrecognised page

class BlockObservation(_Base):
    surface: Literal["search", "optout_form", "confirm_link", "email"]
    observed_at: datetime
    http_status: int | None = None
    block_class: BlockClass
    vendor: str | None = None        # "cloudflare" | "recaptcha-v3" | "perimeterx" | …
    transport: Literal["http", "browser"]   # blocked over plain HTTP only, or in a real browser too
    body_evidence_id: Id | None = None       # encrypted snapshot (Evidence, kind=HTML/SCREENSHOT)
    note_source: Literal["detector"] = "detector"   # PII-free; no names ever

class StatutoryClock(_Base):
    statute: str                     # e.g. "Cal. Civ. Code 1798.105" (machine key, see WO-623)
    request_sent_at: datetime
    deadline_at: datetime            # reuse runner.legal_window_end
    extension_applied_days: int = 0
    breached: bool = False

class EvidenceBundle(_Base):
    id: Id = Field(default_factory=new_id)
    profile_id: Id
    broker_id: BrokerId
    created_at: datetime = Field(default_factory=utcnow)
    # ordered chain: each item's hash covers the previous item's hash (tamper-evident)
    request_hash: str                # SHA-256 over the canonical outgoing request
    items: list[Id]                  # Evidence ids, in happened order
    blocks: list[BlockObservation]
    clock: StatutoryClock
    bundle_sha256: str               # SHA-256 over the canonical manifest below
    tsa_token_relpath: str | None = None   # optional RFC-3161 timestamp (later brick)
```

**Tamper-evidence design (honest about its limits):**
- Each `Evidence` already carries its own file SHA-256. The bundle adds `bundle_sha256` = a hash
  over the *canonical manifest* (sorted keys, the ordered list of `{id, kind, sha256, created_at}`
  plus `request_hash` and the clock). Any later edit to any item changes the bundle hash.
- A local hash proves **internal integrity**, not **time**, to a third party. For court-grade time
  we add an **RFC-3161 trusted timestamp** (free TSAs exist; e.g. a public TSA over `bundle_sha256`)
  as an optional field — MVP ships the hash chain, the TSA token is WO-625. We do **not** claim a
  local-only hash is independently time-proven; the docs and any complaint say exactly what it is.
- No blockchain, no external upload of personal data. The TSA only ever sees `bundle_sha256`, never
  content.

**Privacy:** the bundle's `blocks` and manifest hold ids, enums, hashes, timings — never a name,
address, phone, or the broker's page content in the clear. The page snapshot lives only as an
encrypted `Evidence` file, decryptable solely with the person's own key, and is attached to a
complaint only when the person approves filing it.

## 5. Statutory obstruction vs a plain 404/500 (the hard classification)

A complaint is only credible if we never cry foul over an ordinary error. Rules (WO-621):
- A block is a **candidate obstruction** only on the **opt-out surface** of a broker we have a
  **verified lawful route** for, and only when a **lawful request was actually due or sent**.
- `404` on a listing URL ≠ obstruction (the listing may simply be gone — that's success-adjacent).
- `500`/`503`/timeouts → `TRANSIENT`: retried with backoff; counted as obstruction only after it
  persists across **≥3 observations over ≥N days** (stops a flaky night becoming a false complaint).
- `403`/`429`/`451` or a named vendor block page on the opt-out surface, persisting, with no
  CAPTCHA-free route available → `HARD_BLOCK`, obstruction candidate.
- A CAPTCHA/JS challenge on the opt-out form that does not self-clear → obstruction candidate.
- Every candidate needs: the statutory right invoked, the request on record, the deadline, and the
  persisted block capture. Missing any → not an obstruction, just a routing fact.
- Confidence rises with agreeing observations; a class flips only after 2–3 that agree.

## 6. Work orders

| WO | Title | Owner | Collision |
|---|---|---|---|
| WO-620 | `EvidenceBundle` + `BlockClass`/`BlockObservation`/`StatutoryClock` models, schema, hash-chain helper, validators | Morgan (contract) | models.py — do on this branch, after wave-1111c lands |
| WO-621 | `block_detector.py`: classify block + disposition; obstruction-vs-error rules; fixtures | automation-engineer | browser.py/exposure.py — after wave-1111c |
| WO-622 | `evidence_bundle.py`: assemble + hash + bind clock; capture a block as encrypted Evidence | automation-engineer | new file |
| WO-623 | Legal research: statute map (right → code section → regulator → filing channel), per state in scope (NC/SC/AZ + CA/CO/CT), GPC state-law table (also clears CR-EXT-6) | broker-researcher (Priya) | **none — dispatch now** |
| WO-624 | Reply-wiring: `classify_reply` → escalation branches, with tests | automation-engineer | runner.py/mail.py — after wave-1111c |
| WO-625 | `complaint.py`: statute map → filled complaint (JSON + jinja2 letter) + Bundle annex; always queued for approval | automation-engineer | after WO-620/623 |
| WO-626 | RFC-3161 trusted timestamp over `bundle_sha256` (optional dep, evaluate) | Morgan + qa | later |

Sequencing: WO-623 (research) runs now, collision-free. WO-620 (my contract models) lands after
`integrate/wave-1111c` merges to main, to avoid a models.py three-way merge. WO-621/622/624 follow.

## 7. What the person sees

Nothing new to do. When a broker blocks a lawful request, the app keeps working the other routes.
Once the legal clock breaches, a **complaint is drafted for them** with the evidence attached, and
appears as a single "review and file?" to-do — one click, batched, on their own account, never
auto-filed. The monthly summary counts obstructions by broker.

## 8. Metrics (into the release gate from 0.6)

Obstructions captured, complaints drafted, median days request→breach, share of brokers with a
CAPTCHA-free lawful route, and (public) the per-broker obstruction list.

## 9. Boundaries (rule 5, unchanged)

No CAPTCHA solving, no solver services, no stealth or fingerprint spoofing, no proxies or IP
rotation, no user-agent masking. The harness **only reads** what a site returns. When blocked, it
**fails loudly** into evidence capture — it never retries with altered headers to get through. We
identify honestly; the leverage is legal, not technical.

## 10. Open legal questions (for WO-623 / an attorney, decision D6)

1. Does a CAPTCHA on a statutory opt-out form itself violate CA's ban on opt-out being harder than
   opt-in, or only when it blocks completion? Cite the regulation.
2. For NC/SC/AZ (no comprehensive consumer-privacy statute today), what is the governing right and
   regulator for a people-search deletion — CFPB/FCRA where applicable, state UDAP, FTC?
3. Which states treat GPC as a binding opt-out of sale (verify the table Nina drafted, NOT VERIFIED).
4. Authorized-agent: what identity proof must a broker accept, and may one agent request cover a
   whole site family?
5. Is an RFC-3161 timestamp over a local hash persuasive to these regulators, or is a filed-receipt
   sufficient on its own?
