"""Proof vault: matched broker replies are saved as encrypted EMAIL_RECEIVED evidence tied to
the request they answer, and the confirmation-page screenshot carries its request. Fake
people and brokers (*.example) only; nothing is sent."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from freemyid import config as cfgmod
from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import mail
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import Runner, answered_request, save_replies
from freemyid.models import (
    Broker,
    BrokerStatus,
    Consent,
    ConsentBasis,
    EvidenceKind,
    ListingState,
    MailboxConfig,
    Method,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    Tier,
)
from tests.conftest import make_profile

B = Broker.model_validate({
    "id": "fakeb", "name": "Fake B", "url": "https://fakeb.example/",
    "category": "data_broker", "domains": ["fakeb.example"], "method": "email",
    "opt_out_email": "privacy@fakeb.example", "typical_processing_days": 3})
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")
T0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _person(store):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    p = make_profile(consent=c, mailbox=MB)
    store.save_profile(p)
    return p


def _req(store, p, at, *, dry_run=False, kind=RequestKind.OPT_OUT):
    r = Request(profile_id=p.id, broker_id=B.id, kind=kind, method=Method.EMAIL,
                status=RequestStatus.SENT, created_at=at, sent_at=at, dry_run=dry_run)
    store.save_request(r)
    return r


def _mail(text, when=T0 + timedelta(days=1), sender="privacy@fakeb.example", mid="x1"):
    d = when.strftime("%a, %d %b %Y %H:%M:%S +0000")
    return (f"From: {sender}\r\nTo: removals@example.org\r\nSubject: Re: request\r\n"
            f"Date: {d}\r\nMessage-ID: <{mid}@fakeb.example>\r\n\r\n{text}").encode()


def _received(store, p):
    return [e for e in store.list_evidence(p.id, B.id) if e.kind == EvidenceKind.EMAIL_RECEIVED]


# ------------------------------------------------------------------ answered_request


def test_answered_request_is_the_latest_real_one_sent_before(store):
    p = _person(store)
    first = _req(store, p, T0)
    _req(store, p, T0 + timedelta(days=2), dry_run=True)
    later = _req(store, p, T0 + timedelta(days=10), kind=RequestKind.FOLLOW_UP)
    assert answered_request(store, p.id, B.id, T0 + timedelta(days=3)).id == first.id
    assert answered_request(store, p.id, B.id, T0 + timedelta(days=11)).id == later.id
    assert answered_request(store, p.id, B.id, None).id == later.id
    assert answered_request(store, p.id, B.id, T0 - timedelta(days=1)) is None


# ------------------------------------------------------------------ scan + save


def test_scan_keeps_matched_raw_replies_only():
    good = _mail("Your request is complete.")
    off = _mail("spam", sender="someone@elsewhere.example", mid="x2")
    old = _mail("old", when=T0 - timedelta(days=5), mid="x3")
    scan = mail.scan_replies([good, off, old, good], B, T0)
    assert [raw for _, raw in scan.replies] == [good]
    assert "replies" not in repr(scan)            # raw mail never in a log line


def test_save_replies_links_request_and_dedups(store):
    p = _person(store)
    r = _req(store, p, T0)
    raw = _mail("Your request is complete.")
    replies = mail.scan_replies([raw], B, T0).replies
    assert save_replies(store, p.id, B.id, replies, T0 + timedelta(days=2)) == 1
    assert save_replies(store, p.id, B.id, replies, T0 + timedelta(days=3)) == 0
    (ev,) = _received(store, p)
    assert ev.request_id == r.id and ev.relpath.startswith(f"{p.id}/{B.id}/")
    assert store.read_evidence(ev) == raw


def test_verify_saves_the_reply_as_evidence(store):
    p = _person(store)
    r = _req(store, p, T0)
    inbox = {B.id: [_mail("We received your request and will process it.")]}
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    run = Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
                 broker_ids=None, only_due=False, mailer=FakeMailer(inbox=inbox), cfg=cfg,
                 state_laws={}, now=T0 + timedelta(days=2))
    st = BrokerStatus(profile_id=p.id, broker_id=B.id, state=ListingState.SUBMITTED,
                      last_submitted_at=T0)
    asyncio.run(run._verify(p, B, B, st, Tier.EMAIL))
    (ev,) = _received(store, p)
    assert ev.request_id == r.id
    saved = [e for e in store.events(p.id, B.id) if e.action == "replies_saved"]
    assert saved and saved[0].detail == {"count": 1}


class _Page:
    async def screenshot(self, full_page=True):
        return b"png-bytes"


class _Ctx:
    async def new_page(self):
        return _Page()

    async def close(self):
        pass


class _BM:
    async def new_context(self, domains, extra=None):
        return _Ctx()

    async def goto(self, page, url):
        return None


def test_confirmation_screenshot_carries_its_request(store):
    p = _person(store)
    r = _req(store, p, T0)
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    run = Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
                 broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
                 state_laws={}, now=T0 + timedelta(days=2))

    async def bm():
        return _BM()

    run.browser = bm
    assert asyncio.run(run._click(p, B, "https://fakeb.example/confirm?t=1"))
    (ev,) = [e for e in store.list_evidence(p.id, B.id) if e.kind == EvidenceKind.SCREENSHOT]
    assert ev.request_id == r.id and ev.caption == "confirmation link page"


# ------------------------------------------------------------------ send it yourself


def _no_mailbox_person(store):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    p = make_profile(consent=c, mailbox=None)
    store.save_profile(p)
    return p


def _run_once(store, p, now=T0):
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    r = Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
               broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
               state_laws={}, now=now)
    return asyncio.run(r.process(p, B))


def _manual_todo(store, p):
    from freemyid.models import TodoKind
    return next(t for t in store.list_todos(p.id) if t.kind == TodoKind.SEND_EMAIL_MANUALLY)


def test_send_it_yourself_creates_a_request_with_its_letter(store):
    from freemyid.engine import outbox
    p = _no_mailbox_person(store)
    _run_once(store, p)
    todo = _manual_todo(store, p)
    assert todo.request_id
    req = store.get_request(todo.request_id)
    assert req.status == RequestStatus.DRAFT and not req.dry_run
    assert req.kind == RequestKind.OPT_OUT
    to, subject, body = outbox.letter_for(store, req)
    assert to == "privacy@fakeb.example" and subject == todo.copy_fields["Subject"]
    assert body == todo.copy_fields["Letter"]
    # never on the approval screens (nothing for Free My ID to send)
    assert not store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)
    # a second run reuses the same request
    _run_once(store, p, T0 + timedelta(days=8))
    assert len(store.list_requests(p.id, B.id)) == 1


def test_i_sent_it_marks_the_request_sent_and_saves_an_attestation(store):
    from freemyid.engine import handoff
    p = _no_mailbox_person(store)
    _run_once(store, p)
    todo = _manual_todo(store, p)
    handoff.mark_resolved(store, todo)
    req = store.get_request(todo.request_id)
    assert req.status == RequestStatus.SENT and req.sent_at is not None
    assert store.get_status(p.id, B.id).state == ListingState.SUBMITTED
    (att,) = [e for e in store.list_evidence(p.id, B.id)
              if e.kind == EvidenceKind.USER_ATTESTATION]
    assert att.request_id == req.id
    assert b"sent the removal letter from their own email" in store.read_evidence(att)


def test_manual_follow_up_is_recorded_and_marked_sent(store):
    from freemyid.engine import handoff
    from freemyid.models import TodoKind
    p = _no_mailbox_person(store)
    orig = _req(store, p, T0)
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    r = Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
               broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
               state_laws={}, now=T0 + timedelta(days=50))
    assert r._letter(p, B, [], None, RequestKind.FOLLOW_UP, orig) == "manual_todo"
    todo = next(t for t in store.list_todos(p.id) if t.kind == TodoKind.SEND_EMAIL_MANUALLY)
    req = store.get_request(todo.request_id)
    assert req.kind == RequestKind.FOLLOW_UP and req.original_request_id == orig.id
    handoff.mark_resolved(store, todo)
    assert store.get_request(req.id).status == RequestStatus.SENT


def test_dry_run_request_is_never_marked_sent(store):
    from freemyid.engine import handoff
    p = _no_mailbox_person(store)
    r = Request(profile_id=p.id, broker_id=B.id, kind=RequestKind.OPT_OUT,
                method=Method.EMAIL, status=RequestStatus.DRAFT, dry_run=True)
    store.save_request(r)
    store.save_status(BrokerStatus(profile_id=p.id, broker_id=B.id, state=ListingState.FOUND))
    handoff.mark_manual_submitted(store, p.id, B.id, r.id)
    assert store.get_request(r.id).status == RequestStatus.DRAFT


def test_sec117_mailbox_added_later_replaces_the_manual_letter(store):
    from freemyid.models import TodoKind
    p = _no_mailbox_person(store)
    _run_once(store, p)
    draft_id = _manual_todo(store, p).request_id
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    _run_once(store, p, T0 + timedelta(days=8))
    assert store.get_request(draft_id).status == RequestStatus.CANCELLED
    live = [r for r in store.list_requests(p.id, B.id)
            if r.status == RequestStatus.QUEUED_FOR_APPROVAL]
    assert len(live) == 1 and live[0].id != draft_id
    assert not [t for t in store.list_todos(p.id) if t.kind == TodoKind.SEND_EMAIL_MANUALLY]
    acts = [e.action for e in store.events(p.id, B.id)]
    assert "manual_letter_superseded" in acts and "manual_letter_replaced" in acts


def test_sec117_already_sent_manual_letter_is_left_alone(store):
    from freemyid.engine import handoff
    p = _no_mailbox_person(store)
    _run_once(store, p)
    todo = _manual_todo(store, p)
    handoff.mark_resolved(store, todo)                     # the person sent it themselves
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    _run_once(store, p, T0 + timedelta(days=8))
    assert store.get_request(todo.request_id).status == RequestStatus.SENT
    assert not store.list_requests(p.id, B.id, status=RequestStatus.QUEUED_FOR_APPROVAL)
