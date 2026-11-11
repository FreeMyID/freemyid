"""Outgoing privacy-request email: compose, queue for approval, send. Never sends in dry runs.

Every email is a `Request`. The rendered letter is stored as encrypted LETTER evidence tied
to the request, so what the user approves is exactly what gets sent.

* dry_run                    -> Request(status=DRAFT, dry_run=True). Nothing is sent, ever.
* email_mode APPROVE_EACH    -> QUEUED_FOR_APPROVAL (default)
* LEGAL_DEMAND               -> always QUEUED_FOR_APPROVAL
* email_mode AUTO + mailer   -> sent now
* after a send               -> EMAIL_SENT evidence (the raw message), Request SENT.
* transient mail error       -> status stays; FAILED on the 3rd, or on a permanent error.
* crash after the mailer accepts -> email_handed is stored first; the next drain
  records SENT once and does not send that message again. Not covered: a crash inside
  mailer.send, or a timeout after the server already took the message, can send it twice.

`approve_and_send(store, request_id)` is the user-approved send (CLI `outbox approve`,
dashboard). It refuses unless `config.real_submissions_enabled` (or a mailer is injected,
e.g. the dev fixture run's FakeMailer).

The letter template follows the person's state: CA -> ccpa, a state whose deletion law is
verified in statute text (engine.law_matrix) -> state_privacy, else generic_removal. Only fields the listings already show go in
(`letters.letter_vars`).
"""
from __future__ import annotations

import logging
import os
import smtplib
import socket
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode

from .. import config as cfgmod
from ..models import (
    Actor,
    Broker,
    EmailMode,
    Event,
    Evidence,
    EvidenceKind,
    Listing,
    Method,
    Profile,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    StateLaw,
    Todo,
    TodoKind,
    utcnow,
)
from ..models import ListingState as S
from ..state import can_transition, mark_submitted, transition
from . import law_matrix, letters

log = logging.getLogger(__name__)

DEV_FIXTURES_ENV = "FREEMYID_DEV_FIXTURES"
_DEV_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
_dev_warned = False


def dev_fixture_base() -> str | None:
    """Base URL of the dev fixture server, or None.

    SEC-21: honored only for a plain-http loopback URL and never in a frozen (installed)
    build; anything else is ignored (logged once, value not logged).
    """
    global _dev_warned
    v = os.environ.get(DEV_FIXTURES_ENV)
    if not v:
        return None
    from urllib.parse import urlsplit

    from ..netpolicy import host_of
    try:
        scheme = urlsplit(v).scheme
    except ValueError:
        scheme = ""
    if scheme == "http" and host_of(v) in _DEV_LOOPBACK and not getattr(sys, "frozen", False):
        return v
    if not _dev_warned:
        log.warning("%s ignored (only a loopback http URL in a dev checkout)",
                    DEV_FIXTURES_ENV)
        _dev_warned = True
    return None


class OutboxError(RuntimeError):
    """PII-free reason an email could not be queued or sent."""


# --------------------------------------------------------------------------- composing


def law_in_effect(state_law: StateLaw | None, today: date | None = None,
                  matrix: law_matrix.Matrix | None = None) -> bool:
    """A statute we may cite: the deletion matrix entry for its state has
    `evidence: statute_text`, is in force and gives a deletion right (law_matrix), and the
    state_laws entry names the law, lists a deletion right and is already in effect."""
    if state_law is None or not state_law.statute_name:
        return False
    today = today or date.today()
    entry = (matrix if matrix is not None else law_matrix.default()).get(state_law.state)
    if entry is None or not entry.citable(today):
        return False
    if not any("delet" in r.lower() for r in state_law.rights):
        return False
    return state_law.effective_date is None or state_law.effective_date <= today


def effective_law(profile: Profile, state_law: StateLaw | None,
                  today: date | None = None,
                  matrix: law_matrix.Matrix | None = None) -> StateLaw | None:
    """The law to cite: only the CURRENT address's state, only if `law_in_effect`.
    Anything else -> None (generic voluntary request, no citations). PLAN_V1.

    The returned copy carries the matrix's VERIFIED citation (never the background one
    from state_laws.yaml) and a response window only if that window is verified too."""
    if state_law is None or state_law.state.upper() != profile.state_of_residence:
        return None
    m = matrix if matrix is not None else law_matrix.default()
    if not law_in_effect(state_law, today, m):
        return None
    entry = m.get(state_law.state)
    assert entry is not None
    ok_days = entry.deadline_verified()
    return state_law.model_copy(update={
        "citation": entry.citation,
        "response_days": entry.response_days if ok_days else None,
        "extension_days": entry.extension_days if ok_days else None,
    })


def initial_template(profile: Profile, state_law: StateLaw | None,
                     today: date | None = None,
                     matrix: law_matrix.Matrix | None = None) -> str:
    """ccpa for CA / state_privacy elsewhere, only with a citable law (`effective_law`)
    for the current address's state; otherwise generic_removal."""
    law = effective_law(profile, state_law, today, matrix)
    if law is None:
        return "generic_removal"
    return "ccpa" if law.state.upper() == "CA" else "state_privacy"


def template_for(kind: RequestKind, profile: Profile, state_law: StateLaw | None) -> str:
    """`state_law` must already be the `effective_law` result (or None)."""
    if kind == RequestKind.FOLLOW_UP:
        return "follow_up"
    if kind == RequestKind.LEGAL_DEMAND:
        return "legal_demand"
    if state_law is None:
        return "generic_removal"
    return "ccpa" if state_law.state.upper() == "CA" else "state_privacy"


def compose(profile: Profile, broker: Broker, listings: list[Listing],
            state_law: StateLaw | None, kind: RequestKind = RequestKind.OPT_OUT, *,
            original: Request | None = None, today: date | None = None,
            matrix: law_matrix.Matrix | None = None) -> tuple[str, str]:
    """(subject, body) for a request letter. Data-minimized via letters.letter_vars.
    Statutes are cited only when `effective_law` says so. A phone/email-only removal
    (BL-IN-08) gets the value_removal letter: the value and URLs only, no law cited."""
    if profile.value_only:
        v = letters.value_letter_vars(
            profile, broker, listings, follow_up=kind != RequestKind.OPT_OUT,
            original_request_date=(original.sent_at or original.created_at)
            if original else None,
            reference=original.reference if original else None)
        return letters.split_subject(letters.render("value_removal", **v))
    law = effective_law(profile, state_law, today, matrix)
    v = letters.letter_vars(
        profile, broker, listings, law,
        original_request_date=(original.sent_at or original.created_at) if original else None,
        reference=original.reference if original else None)
    text = letters.render(template_for(kind, profile, law), **v)
    return letters.split_subject(text)


def compose_links(to: str, subject: str, body: str) -> dict[str, str]:
    """Web-mail compose URLs with to/subject/body prefilled (no-mailbox Assisted path)."""
    return {
        "Gmail": "https://mail.google.com/mail/?" + urlencode(
            {"view": "cm", "fs": "1", "to": to, "su": subject, "body": body}, quote_via=quote),
        "Outlook": "https://outlook.live.com/mail/0/deeplink/compose?" + urlencode(
            {"to": to, "subject": subject, "body": body}, quote_via=quote),
        "Yahoo": "https://compose.mail.yahoo.com/?" + urlencode(
            {"to": to, "subject": subject, "body": body}, quote_via=quote),
        "Email app": f"mailto:{quote(to, safe='@')}?" + urlencode(
            {"subject": subject, "body": body}, quote_via=quote),
    }


def _letter_blob(to: str, subject: str, body: str) -> bytes:
    return f"To: {to}\nSubject: {subject}\n\n{body}".encode()


def _parse_letter(blob: bytes) -> tuple[str, str, str]:
    head, _, body = blob.decode().partition("\n\n")
    hdr = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    return hdr.get("To", ""), hdr.get("Subject", ""), body


def record_manual_letter(store, todo: Todo, listings: list[Listing], *,
                         kind: RequestKind = RequestKind.OPT_OUT,
                         original: Request | None = None, dry_run: bool = False,
                         now: datetime | None = None) -> Todo:
    """Proof vault: a "send it yourself" letter (no removal mailbox) becomes a stored
    Request + LETTER evidence, and the to-do carries its request_id, so "I sent it" marks
    that request SENT. The status is DRAFT, not QUEUED_FOR_APPROVAL: there is nothing for
    Free My ID to send, so it must not show up on the approval screens. An open request of
    the same kind is reused (one per letter, not one per run). Other to-dos pass through."""
    if store is None or todo.kind != TodoKind.SEND_EMAIL_MANUALLY or not todo.broker_id:
        return todo
    f = todo.copy_fields or {}
    to, subject, body = f.get("To", ""), f.get("Subject", ""), f.get("Letter", "")
    req = _open_manual(store, todo.profile_id, todo.broker_id, kind, dry_run)
    if req is None:
        req = Request(profile_id=todo.profile_id, broker_id=todo.broker_id, kind=kind,
                      method=Method.EMAIL, listing_ids=[li.id for li in listings],
                      created_at=now or utcnow(), dry_run=dry_run,
                      original_request_id=original.id if original else None,
                      status=RequestStatus.DRAFT)
        store.save_request(req)
        _save_blob(store, todo.profile_id, todo.broker_id, EvidenceKind.LETTER,
                   _letter_blob(to, subject, body), req.id,
                   f"{kind.value} letter (to send yourself)", "txt")
        store.log(Event(profile_id=todo.profile_id, broker_id=todo.broker_id,
                        actor=Actor.ENGINE, action="manual_letter_drafted",
                        detail={"request_id": req.id, "kind": kind.value,
                                "dry_run": dry_run}))
    return todo.model_copy(update={"request_id": req.id})


def letter_for(store, req: Request) -> tuple[str, str, str]:
    """(to, subject, body) stored for a request."""
    for ev in store.list_evidence(req.profile_id, req.broker_id):
        if ev.request_id == req.id and ev.kind == EvidenceKind.LETTER:
            return _parse_letter(store.read_evidence(ev))
    raise OutboxError("no stored letter for this request")


def _save_blob(store, profile_id: str, broker_id: str, kind: EvidenceKind, data: bytes,
               request_id: str, caption: str, ext: str) -> Evidence:
    ev = Evidence(profile_id=profile_id, broker_id=broker_id, kind=kind, request_id=request_id,
                  relpath="x", sha256="", caption=caption)
    ev = ev.model_copy(update={"relpath": f"{profile_id}/{broker_id}/{ev.id}.{ext}"})
    return store.save_evidence(ev, data)


# --------------------------------------------------------------------------- queueing


def _open_request(store, profile_id: str, broker_id: str, kind: RequestKind,
                  dry_run: bool) -> Request | None:
    """The open email request of this kind to reuse: QUEUED_FOR_APPROVAL, or a dry-run
    DRAFT. SEC-117: a non-dry-run DRAFT is a "send it yourself" letter
    (record_manual_letter), never something queue_email may reuse, or the email would never
    reach the approval screen."""
    for r in store.list_requests(profile_id, broker_id):
        if r.kind != kind or r.dry_run != dry_run:
            continue
        if r.status == RequestStatus.QUEUED_FOR_APPROVAL or \
                (r.status == RequestStatus.DRAFT and r.dry_run):
            return r
    return None


def _open_manual(store, profile_id: str, broker_id: str, kind: RequestKind,
                 dry_run: bool) -> Request | None:
    """The open "send it yourself" DRAFT of this kind (record_manual_letter reuses it)."""
    for r in store.list_requests(profile_id, broker_id):
        if r.kind == kind and r.dry_run == dry_run and r.status == RequestStatus.DRAFT:
            return r
    return None


HOLD_ACTION = "email_held_first_approval"   # SEC-27 Event marker (detail: request_id)
RELEASE_ACTION = "held_emails_released"      # SEC-27 Event marker (detail: counts)
HANDOFF_ACTION = "email_handed"              # mailer accepted; SENT row may not exist yet


def email_sent_before(store, profile_id: str) -> bool:
    """True once a real (non-dry) EMAIL request for this profile has gone out. A web-form
    submission does not count: the person must have seen one of Free My ID's emails."""
    return any(r.status == RequestStatus.SENT and r.method == Method.EMAIL and not r.dry_run
               for r in store.list_requests(profile_id))


def needs_approval(profile: Profile, kind: RequestKind, store=None) -> bool:
    """Legal demands and every non-AUTO email wait for approval. SEC-27: in AUTO mode the
    FIRST email for a profile waits too, so the person sees one before any goes out."""
    if kind == RequestKind.LEGAL_DEMAND or profile.email_mode != EmailMode.AUTO:
        return True
    if store is None:
        return True       # can't prove an earlier send: be safe
    return not email_sent_before(store, profile.id)


def held_by_first_approval(profile: Profile, req: Request, store) -> bool:
    """A queued email that is waiting only because the profile's first email has not been
    approved yet (AUTO mode). Approving any email of the profile releases it."""
    return (profile.email_mode == EmailMode.AUTO and not req.dry_run
            and req.method == Method.EMAIL
            and req.status == RequestStatus.QUEUED_FOR_APPROVAL
            and req.kind != RequestKind.LEGAL_DEMAND
            and not email_sent_before(store, profile.id))


def _auto_releasable(profile: Profile, req: Request) -> bool:
    return (profile.email_mode == EmailMode.AUTO and not req.dry_run
            and req.method == Method.EMAIL
            and req.status == RequestStatus.QUEUED_FOR_APPROVAL
            and req.kind != RequestKind.LEGAL_DEMAND)


def released_by_approval(store, profile: Profile, req: Request) -> list[Request]:
    """SEC-47: the OTHER queued emails that approving `req` would also send (AUTO profile,
    first approval). The approve card must list or count these. Empty when approving `req`
    sends only `req` (approve_each, gate already open, legal demand, dry run)."""
    if (req.kind == RequestKind.LEGAL_DEMAND or req.dry_run
            or profile.email_mode != EmailMode.AUTO or email_sent_before(store, profile.id)):
        return []
    return [r for r in store.list_requests(profile.id, status=RequestStatus.QUEUED_FOR_APPROVAL)
            if r.id != req.id and _auto_releasable(profile, r)]


def first_email_pending(store, profile: Profile) -> Request | None:
    """The oldest email held for the profile's first approval (dashboard: "approve this one
    and the rest go out by themselves"), or None."""
    for r in store.list_requests(profile.id, status=RequestStatus.QUEUED_FOR_APPROVAL):
        if held_by_first_approval(profile, r, store):
            return r
    return None


def queue_email(store, profile: Profile, broker: Broker, listings: list[Listing], *,
                kind: RequestKind = RequestKind.OPT_OUT, state_law: StateLaw | None = None,
                dry_run: bool, mailer=None, original: Request | None = None,
                now: datetime | None = None) -> Request:
    """Create (or reuse) the Request for this letter; send it now only in AUTO mode.

    Does NOT change the BrokerStatus: the runner does that from the returned request
    (status SENT = a real send happened).
    """
    if not broker.opt_out_email:
        raise OutboxError("broker has no opt-out email address")
    now = now or utcnow()
    existing = _open_request(store, profile.id, broker.id, kind, dry_run)
    if existing:
        # The mailer already took this letter. Finish the SENT row; do not send it again.
        if not existing.dry_run and _handed_off(store, existing):
            return send_request(store, existing, profile, mailer, now=now)
        # SEC-27: an AUTO email that was held for the first approval goes out once the
        # profile has an approved send (approve_and_send also releases them right away).
        if (mailer is not None and _auto_releasable(profile, existing)
                and not needs_approval(profile, kind, store)):
            return send_request(store, existing, profile, mailer, now=now)
        return existing
    subject, body = compose(profile, broker, listings, state_law, kind, original=original)
    attempt = 1 + sum(1 for r in store.list_requests(profile.id, broker.id)
                      if r.kind == kind and r.status == RequestStatus.SENT)
    req = Request(profile_id=profile.id, broker_id=broker.id, kind=kind, method=Method.EMAIL,
                  listing_ids=[li.id for li in listings], created_at=now, dry_run=dry_run,
                  attempt=attempt,
                  original_request_id=original.id if original else None,
                  status=RequestStatus.DRAFT if dry_run else RequestStatus.QUEUED_FOR_APPROVAL)
    store.save_request(req)
    if not dry_run and (manual := _open_manual(store, profile.id, broker.id, kind, False)):
        # SEC-117: a mailbox now exists, so this email replaces the "send it yourself" copy
        store.save_request(manual.model_copy(update={"status": RequestStatus.CANCELLED}))
        store.log(Event(profile_id=profile.id, broker_id=broker.id, actor=Actor.ENGINE,
                        action="manual_letter_replaced",
                        detail={"request_id": manual.id, "by": req.id}))
    _save_blob(store, profile.id, broker.id, EvidenceKind.LETTER,
               _letter_blob(broker.opt_out_email, subject, body), req.id,
               f"{kind.value} letter", "txt")
    store.log(Event(profile_id=profile.id, broker_id=broker.id, actor=Actor.ENGINE,
                    action="email_drafted" if dry_run else "email_queued",
                    detail={"request_id": req.id, "kind": kind.value, "dry_run": dry_run}))
    if dry_run or mailer is None:
        return req
    if needs_approval(profile, kind, store):
        if _auto_releasable(profile, req):
            store.log(Event(profile_id=profile.id, broker_id=broker.id, actor=Actor.ENGINE,
                            action=HOLD_ACTION, detail={"request_id": req.id}))
        return req
    return send_request(store, req, profile, mailer, now=now)


# Attempts are email_failed rows in the event log, not a Request field.
# Backoff after a transient failure: 15 minutes, then 1 hour. The third is FAILED.
_TRANSIENT_ATTEMPTS = 3
_BACKOFF_FIRST = timedelta(minutes=15)
_BACKOFF_LATER = timedelta(hours=1)
_FAILURE_EVENT_LIMIT = 2000


def is_transient_mail_error(exc: BaseException) -> bool:
    """True for a timeout, a dropped connection, or an SMTP 4xx.

    Permanent: everything else, including SMTPAuthenticationError (even a 4xx auth code)
    and any 5xx. ``socket.timeout`` aliases ``TimeoutError`` on Python 3.10+; both names
    are listed so the check matches the spec on a runtime that still separates them.
    """
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return False
    transient = (TimeoutError, socket.timeout, ConnectionError, smtplib.SMTPServerDisconnected)
    if isinstance(exc, transient):
        return True
    if isinstance(exc, smtplib.SMTPResponseException):
        code = exc.smtp_code
        return isinstance(code, int) and 400 <= code < 500
    return False


def _mail_failure(exc: BaseException) -> BaseException:
    """Exception to classify. The real mailer wraps SMTP errors in MailError."""
    from .mail import MailError
    if not isinstance(exc, MailError):
        return exc
    inner = exc.__cause__ if exc.__cause__ is not None else exc.__context__
    return inner if isinstance(inner, BaseException) else exc


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


def _transient_failures(store, req: Request) -> list[Event]:
    """Newest-first transient email_failed rows for this request."""
    found: list[Event] = []
    rows = store.events(req.profile_id, req.broker_id, limit=_FAILURE_EVENT_LIMIT)
    for ev in rows:
        if ev.action != "email_failed" or ev.detail.get("request_id") != req.id:
            continue
        if ev.detail.get("transient") is True:
            found.append(ev)
    return found


def _retry_waiting(store, req: Request, now: datetime) -> bool:
    """True when the last transient failure is newer than this request's backoff."""
    failures = _transient_failures(store, req)
    if not failures:
        return False
    wait = _BACKOFF_FIRST if len(failures) == 1 else _BACKOFF_LATER
    # events() is newest-first, so the first row is the last failure.
    return _as_utc(now) - _as_utc(failures[0].ts) < wait


def _note_send_failure(store, req: Request, profile: Profile,
                       failure: BaseException) -> None:
    transient = is_transient_mail_error(failure)
    detail: dict[str, Any] = {
        "request_id": req.id,
        "error": type(failure).__name__,
        "transient": transient,
    }
    give_up = not transient
    if transient:
        attempt = len(_transient_failures(store, req)) + 1
        detail["attempt"] = attempt
        give_up = attempt >= _TRANSIENT_ATTEMPTS
    if give_up:
        store.save_request(req.model_copy(update={"status": RequestStatus.FAILED}))
    store.log(Event(profile_id=profile.id, broker_id=req.broker_id, actor=Actor.ENGINE,
                    action="email_failed", detail=detail))


def _matching_events(store, req: Request, action: str) -> list[Event]:
    """Events for this request, newest first, within the same cap as retry rows."""
    found: list[Event] = []
    rows = store.events(req.profile_id, req.broker_id, limit=_FAILURE_EVENT_LIMIT)
    for ev in rows:
        if ev.action == action and ev.detail.get("request_id") == req.id:
            found.append(ev)
    return found


def _has_sent_evidence(store, req: Request) -> bool:
    for ev in store.list_evidence(req.profile_id, req.broker_id):
        if ev.request_id == req.id and ev.kind == EvidenceKind.EMAIL_SENT:
            return True
    return False


def _handed_off(store, req: Request) -> bool:
    """True once the mailer has accepted this request.

    Stored with the calls the store already has: an ``email_handed`` event written
    before the SENT row, or EMAIL_SENT evidence if the crash was after that blob.
    """
    if _has_sent_evidence(store, req):
        return True
    return bool(_matching_events(store, req, HANDOFF_ACTION))


def _accepted_at(store, req: Request) -> datetime | None:
    rows = _matching_events(store, req, HANDOFF_ACTION)
    if not rows:
        return None
    return min(rows, key=lambda ev: _as_utc(ev.ts)).ts


def _record_sent(store, req: Request, profile: Profile, sent_at: datetime, *,
                 raw: bytes | None, has_mid: bool) -> Request:
    """Write one EMAIL_SENT blob and the SENT row. A second call does not duplicate them."""
    if not _has_sent_evidence(store, req):
        if raw is None:
            to, subject, body = letter_for(store, req)
            raw = _letter_blob(to, subject, body)
        _save_blob(store, profile.id, req.broker_id, EvidenceKind.EMAIL_SENT, raw, req.id,
                   f"{req.kind.value} email sent", "eml")
    current = store.get_request(req.id) or req
    if current.status != RequestStatus.SENT:
        current = current.model_copy(update={"status": RequestStatus.SENT, "sent_at": sent_at,
                                             "reference": current.reference})
        store.save_request(current)
    if not _matching_events(store, req, "email_sent"):
        store.log(Event(profile_id=profile.id, broker_id=req.broker_id, actor=Actor.ENGINE,
                        action="email_sent",
                        detail={"request_id": req.id, "kind": req.kind.value,
                                "has_message_id": has_mid}))
    log.info("outbox code=%s count=%s", "email_sent", 1)
    return current


def send_request(store, req: Request, profile: Profile, mailer, *,
                 now: datetime | None = None) -> Request:
    """Send a stored request letter. Never for dry-run requests.

    A transient mail error leaves the status as it is, logs email_failed with
    transient and the attempt number, and still raises OutboxError. The third
    transient failure for this request, and any permanent error, marks it FAILED.

    Once the mailer returns, ``email_handed`` is stored before the SENT row. If
    that row is still missing on a later call, the message is recorded and not sent.
    """
    if req.dry_run:
        raise OutboxError("dry-run requests are never sent")
    if req.status not in (RequestStatus.QUEUED_FOR_APPROVAL, RequestStatus.DRAFT):
        raise OutboxError(f"request is {req.status.value}, not sendable")
    now = now or utcnow()
    if _handed_off(store, req):
        log.info("outbox code=%s count=%s", "already_handed", 1)
        handed = _matching_events(store, req, HANDOFF_ACTION)
        has_mid = any(ev.detail.get("has_message_id") is True for ev in handed)
        return _record_sent(store, req, profile, _accepted_at(store, req) or now,
                            raw=None, has_mid=has_mid)
    if profile.mailbox is None:
        raise OutboxError("profile has no removal mailbox")
    to, subject, body = letter_for(store, req)
    try:
        mid = mailer.send(profile, to, subject, body, req.id)
    except Exception as e:  # noqa: BLE001 - classified, then re-raised as OutboxError
        failure = _mail_failure(e)
        _note_send_failure(store, req, profile, failure)
        raise OutboxError(f"send failed: {type(failure).__name__}") from None
    store.log(Event(profile_id=profile.id, broker_id=req.broker_id, actor=Actor.ENGINE,
                    ts=now, action=HANDOFF_ACTION,
                    detail={"request_id": req.id, "has_message_id": bool(mid)}))
    raw = getattr(mailer, "last_raw", None) or _letter_blob(to, subject, body)
    return _record_sent(store, req, profile, now, raw=raw, has_mid=bool(mid))


# --------------------------------------------------------------------------- approval


def _default_mailer(profile: Profile, registry: Registry | None):
    from ..netpolicy import NetPolicy
    from .mail import FakeMailer, SmtpImapMailer
    if dev_fixture_base():
        return FakeMailer()
    if not cfgmod.load().real_submissions_enabled:
        raise OutboxError("real email sending is not enabled yet "
                          "(freemyid config enable-submissions)")
    return SmtpImapMailer(NetPolicy(registry, [profile]))


def apply_sent(store, req: Request, broker: Broker | None, now: datetime) -> None:
    """After an approved OPT_OUT/RESUBMIT send, move the broker status to SUBMITTED."""
    if req.kind not in (RequestKind.OPT_OUT, RequestKind.RESUBMIT):
        return
    st = store.get_status(req.profile_id, req.broker_id)
    if not can_transition(st.state, S.SUBMITTED):
        return
    new = mark_submitted(st, now)
    if broker is not None and broker.needs_email_verification:
        new = transition(new, S.AWAITING_VERIFICATION, now)
    store.save_status(new)
    store.log(Event(profile_id=req.profile_id, broker_id=req.broker_id, actor=Actor.USER,
                    action="submitted", from_state=st.state, to_state=new.state,
                    detail={"request_id": req.id, "via": "email"}))


def approve_and_send(store, request_id: str, *, mailer=None, registry: Registry | None = None,
                     now: datetime | None = None) -> None:
    """User-approved send of a QUEUED_FOR_APPROVAL email (interfaces.py entry point)."""
    req = store.get_request(request_id)
    if req is None:
        raise OutboxError("unknown request")
    if req.status != RequestStatus.QUEUED_FOR_APPROVAL or req.dry_run:
        raise OutboxError("request is not waiting for approval")
    profile = store.get_profile(req.profile_id)
    if profile is None:
        raise OutboxError("profile no longer exists")
    from ..consent import consent_ok
    ok, _why = consent_ok(profile, store)
    if not ok:
        raise OutboxError("consent check failed for this profile")
    if registry is None:
        from ..registry import load_registry
        registry = load_registry()
    try:
        broker: Broker | None = registry.get(req.broker_id)
    except KeyError:
        broker = None
    mailer = mailer or _default_mailer(profile, registry)
    now = now or utcnow()
    store.log(Event(profile_id=req.profile_id, broker_id=req.broker_id, actor=Actor.USER,
                    action="email_approved", detail={"request_id": req.id}))
    sent = send_request(store, req, profile, mailer, now=now)
    apply_sent(store, sent, broker, now)
    if profile.email_mode == EmailMode.AUTO:
        release_held(store, profile, mailer=mailer, registry=registry, now=now)


def _broker_from(registry: Registry | None, broker_id: str) -> Broker | None:
    if registry is None:
        return None
    try:
        return registry.get(broker_id)
    except KeyError:
        return None


def _bump(counts: dict[str, int], key: str) -> None:
    """``deferred`` is added only when used: older release events are exactly {sent, failed}."""
    counts[key] = counts.get(key, 0) + 1


def _finish_send(store, profile: Profile, req: Request, mailer, registry: Registry | None,
                 now: datetime) -> str:
    """Send or, if the mailer already accepted it, only record.

    ``sent``, ``failed`` (the request is FAILED for good) or ``deferred`` (a 1st or 2nd
    transient failure: the request stays queued and is tried again after its backoff).
    """
    try:
        sent = send_request(store, req, profile, mailer, now=now)
    except OutboxError:
        current = store.get_request(req.id)
        if current is not None and current.status != RequestStatus.FAILED:
            return "deferred"
        return "failed"
    apply_sent(store, sent, _broker_from(registry, req.broker_id), now)
    return "sent"


def release_held(store, profile: Profile, *, mailer, registry: Registry | None = None,
                 now: datetime | None = None) -> dict[str, int]:
    """SEC-27: after the profile's first approved send, send the AUTO emails that were held
    for it. Legal demands, dry-run and non-AUTO requests are never touched. One failure
    never stops the rest.

    A request still inside its backoff (15 minutes after the first transient failure, one
    hour after the second) is skipped and counted as deferred on the release event.
    deferred is omitted when nothing was skipped. A permanent error, or the third
    transient failure, is marked FAILED by send_request and counted as failed.

    Once this pass runs (a real email is already on record), a request the mailer
    already accepted is recorded and not sent again, including during its backoff.
    """
    counts: dict[str, int] = {"sent": 0, "failed": 0}
    if profile.email_mode != EmailMode.AUTO or not email_sent_before(store, profile.id):
        return counts
    from ..consent import consent_ok
    if not consent_ok(profile, store)[0]:
        return counts
    now = now or utcnow()
    for r in store.list_requests(profile.id, status=RequestStatus.QUEUED_FOR_APPROVAL):
        if not _auto_releasable(profile, r):
            continue
        # Already accepted: do not wait out backoff, and do not hand it to the mailer.
        if _handed_off(store, r):
            _bump(counts, _finish_send(store, profile, r, mailer, registry, now))
            continue
        # Omitted when zero: existing release events are exactly {sent, failed}.
        if _retry_waiting(store, r, now):
            _bump(counts, "deferred")
            continue
        _bump(counts, _finish_send(store, profile, r, mailer, registry, now))
    if counts["sent"] or counts["failed"] or counts.get("deferred"):
        store.log(Event(profile_id=profile.id, actor=Actor.ENGINE, action=RELEASE_ACTION,
                        detail=dict(counts)))
    return counts


def drain(store, profile: Profile, mailer, *, registry: Registry | None = None,
          now: datetime | None = None) -> dict[str, int]:
    """One pass over this profile's queued email.

    A message the mailer already accepted is recorded once and not sent again.
    A message that never reached the mailer is sent when the approval rules and
    the WO-332 backoff already allow it. Counts and codes only.
    """
    counts: dict[str, int] = {"sent": 0, "recorded": 0, "failed": 0, "deferred": 0}
    now = now or utcnow()
    from ..consent import consent_ok
    allowed = consent_ok(profile, store)[0]
    queued = store.list_requests(profile.id, status=RequestStatus.QUEUED_FOR_APPROVAL)
    for req in queued:
        if req.dry_run or req.method != Method.EMAIL:
            continue
        if _handed_off(store, req):
            outcome = _finish_send(store, profile, req, mailer, registry, now)
            counts["recorded" if outcome == "sent" else "failed"] += 1
            continue
        if not allowed or not _auto_releasable(profile, req) or needs_approval(
                profile, req.kind, store):
            continue
        if _retry_waiting(store, req, now):
            counts["deferred"] += 1
            continue
        outcome = _finish_send(store, profile, req, mailer, registry, now)
        counts[outcome] += 1
    log.info("outbox drain sent=%s recorded=%s failed=%s deferred=%s",
             counts["sent"], counts["recorded"], counts["failed"], counts["deferred"])
    return counts
