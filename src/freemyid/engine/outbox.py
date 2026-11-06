"""Outgoing privacy-request email: compose, queue for approval, send. Never sends in dry runs.

Every email is a `Request`. The rendered letter is stored as encrypted LETTER evidence tied
to the request, so what the user approves is exactly what gets sent.

* dry_run                    -> Request(status=DRAFT, dry_run=True). Nothing is sent, ever.
* email_mode APPROVE_EACH    -> QUEUED_FOR_APPROVAL (default)
* LEGAL_DEMAND               -> always QUEUED_FOR_APPROVAL
* email_mode AUTO + mailer   -> sent now
* after a send               -> EMAIL_SENT evidence (the raw message), Request SENT.

`approve_and_send(store, request_id)` is the user-approved send (CLI `outbox approve`,
dashboard). It refuses unless `config.real_submissions_enabled` (or a mailer is injected,
e.g. the dev fixture run's FakeMailer).

The letter template follows the person's state: CA -> ccpa, a state with a privacy statute
-> state_privacy, else generic_removal. Only fields the listings already show go in
(`letters.letter_vars`).
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime
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
    utcnow,
)
from ..models import ListingState as S
from ..state import can_transition, mark_submitted, transition
from . import letters

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


def law_in_effect(state_law: StateLaw | None, today: date | None = None) -> bool:
    """A verified (`last_verified` set) statute with a deletion right already in effect."""
    if state_law is None or not state_law.statute_name or state_law.last_verified is None:
        return False
    if not any("delet" in r.lower() for r in state_law.rights):
        return False
    return state_law.effective_date is None or state_law.effective_date <= (today or date.today())


def effective_law(profile: Profile, state_law: StateLaw | None,
                  today: date | None = None) -> StateLaw | None:
    """The law to cite: only the CURRENT address's state, only if verified and in effect.
    Anything else -> None (generic voluntary request, no citations). PLAN_V1."""
    if state_law is None or state_law.state.upper() != profile.state_of_residence:
        return None
    return state_law if law_in_effect(state_law, today) else None


def initial_template(profile: Profile, state_law: StateLaw | None,
                     today: date | None = None) -> str:
    """ccpa for CA / state_privacy elsewhere, only with a verified law in effect for the
    current address's state; otherwise generic_removal."""
    law = effective_law(profile, state_law, today)
    if law is None:
        return "generic_removal"
    return "ccpa" if law.state.upper() == "CA" else "state_privacy"


def template_for(kind: RequestKind, profile: Profile, state_law: StateLaw | None) -> str:
    if kind == RequestKind.FOLLOW_UP:
        return "follow_up"
    if kind == RequestKind.LEGAL_DEMAND:
        return "legal_demand"
    return initial_template(profile, state_law)


def compose(profile: Profile, broker: Broker, listings: list[Listing],
            state_law: StateLaw | None, kind: RequestKind = RequestKind.OPT_OUT, *,
            original: Request | None = None) -> tuple[str, str]:
    """(subject, body) for a request letter. Data-minimized via letters.letter_vars.
    Statutes are cited only when `effective_law` says so."""
    law = effective_law(profile, state_law)
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
    for r in store.list_requests(profile_id, broker_id):
        if r.kind != kind or r.dry_run != dry_run:
            continue
        if r.status in (RequestStatus.QUEUED_FOR_APPROVAL, RequestStatus.DRAFT):
            return r
    return None


def needs_approval(profile: Profile, kind: RequestKind, store=None) -> bool:
    """Legal demands and every non-AUTO email wait for approval. SEC-27: in AUTO mode the
    FIRST email for a profile waits too, so the person sees one before any goes out."""
    if kind == RequestKind.LEGAL_DEMAND or profile.email_mode != EmailMode.AUTO:
        return True
    if store is None:
        return True       # can't prove an earlier send: be safe
    return not any(r.status == RequestStatus.SENT for r in store.list_requests(profile.id))


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
    _save_blob(store, profile.id, broker.id, EvidenceKind.LETTER,
               _letter_blob(broker.opt_out_email, subject, body), req.id,
               f"{kind.value} letter", "txt")
    store.log(Event(profile_id=profile.id, broker_id=broker.id, actor=Actor.ENGINE,
                    action="email_drafted" if dry_run else "email_queued",
                    detail={"request_id": req.id, "kind": kind.value, "dry_run": dry_run}))
    if dry_run or mailer is None or needs_approval(profile, kind, store):
        return req
    return send_request(store, req, profile, mailer, now=now)


def send_request(store, req: Request, profile: Profile, mailer, *,
                 now: datetime | None = None) -> Request:
    """Send a stored request letter. Never for dry-run requests."""
    if req.dry_run:
        raise OutboxError("dry-run requests are never sent")
    if req.status not in (RequestStatus.QUEUED_FOR_APPROVAL, RequestStatus.DRAFT):
        raise OutboxError(f"request is {req.status.value}, not sendable")
    if profile.mailbox is None:
        raise OutboxError("profile has no removal mailbox")
    now = now or utcnow()
    to, subject, body = letter_for(store, req)
    try:
        mid = mailer.send(profile, to, subject, body, req.id)
    except Exception as e:  # noqa: BLE001 - any mailer failure marks the request FAILED
        store.save_request(req.model_copy(update={"status": RequestStatus.FAILED}))
        store.log(Event(profile_id=profile.id, broker_id=req.broker_id, actor=Actor.ENGINE,
                        action="email_failed",
                        detail={"request_id": req.id, "error": type(e).__name__}))
        raise OutboxError(f"send failed: {type(e).__name__}") from None
    raw = getattr(mailer, "last_raw", None) or _letter_blob(to, subject, body)
    _save_blob(store, profile.id, req.broker_id, EvidenceKind.EMAIL_SENT, raw, req.id,
               f"{req.kind.value} email sent", "eml")
    sent = req.model_copy(update={"status": RequestStatus.SENT, "sent_at": now,
                                  "reference": req.reference})
    store.save_request(sent)
    store.log(Event(profile_id=profile.id, broker_id=req.broker_id, actor=Actor.ENGINE,
                    action="email_sent", detail={"request_id": req.id,
                                                 "kind": req.kind.value,
                                                 "has_message_id": bool(mid)}))
    return sent


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
