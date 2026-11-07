"""Draft tests (qa to adopt): IMAP reply matcher edge cases + ID-request routing.

Fake brokers (*.example), fake mailbox (example.org), FakeMailer only.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import handoff as hmod
from freemyid.engine.mail import FakeMailer, ReplyScan, asks_for_id, scan_replies
from freemyid.engine.runner import ID_REQUEST_REASON, Runner
from freemyid.models import (
    Broker,
    BrokerStatus,
    Consent,
    ConsentBasis,
    ListingState,
    MailboxConfig,
    Registry,
    Tier,
    TodoKind,
)
from tests.conftest import make_profile

B = Broker.model_validate({
    "id": "fakeb", "name": "Fake B", "url": "https://fakeb.example/",
    "category": "data_broker", "domains": ["fakeb.example"], "method": "email",
    "opt_out_email": "privacy@fakeb.example", "confirmation_domains": ["mail.fakeb.example"]})
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")
SUBMITTED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def mail(html: str, *, when: datetime | None = None, mid: str | None = None,
         sender: str = "Fake B <no-reply@fakeb.example>", subject: str = "Your request") -> bytes:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = MB.address
    m["Subject"] = subject
    if when is not None:
        m["Date"] = format_datetime(when)
    if mid is not None:
        m["Message-ID"] = mid
    m.set_content("see html")
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def confirm(token: str, **kw) -> bytes:
    return mail(f'<a href="https://mail.fakeb.example/confirm?t={token}">Confirm</a>', **kw)


# ----------------------------------------------------------------- pure matcher
def test_duplicate_reply_counts_once():
    raw = confirm("1", mid="<a1@fakeb.example>", when=SUBMITTED_AT + timedelta(hours=2))
    scan = scan_replies([raw, raw, raw], B, SUBMITTED_AT)
    assert scan.links == ["https://mail.fakeb.example/confirm?t=1"]
    assert scan.messages == 1 and scan.duplicates == 2


def test_same_bytes_without_message_id_dedupes():
    raw = confirm("1")
    assert scan_replies([raw, raw], B).duplicates == 1


def test_broker_answers_twice_newest_link_first():
    old = confirm("old", mid="<o@fakeb.example>", when=SUBMITTED_AT + timedelta(hours=1))
    new = confirm("new", mid="<n@fakeb.example>", when=SUBMITTED_AT + timedelta(days=2))
    scan = scan_replies([old, new], B, SUBMITTED_AT)       # IMAP order: oldest first
    assert scan.links[0].endswith("t=new") and len(scan.links) == 2


def test_reply_to_an_earlier_submission_is_ignored():
    stale = confirm("stale", when=SUBMITTED_AT - timedelta(days=40))
    fresh = confirm("fresh", when=SUBMITTED_AT + timedelta(minutes=5))
    skew = confirm("skew", when=SUBMITTED_AT - timedelta(minutes=20))   # inside DATE_SLACK
    scan = scan_replies([stale, fresh, skew], B, SUBMITTED_AT)
    assert scan.stale == 1
    assert {u.rsplit("=", 1)[1] for u in scan.links} == {"fresh", "skew"}


def test_naive_since_and_undated_mail_are_handled():
    raw = confirm("x")                                     # no Date header: kept
    assert scan_replies([raw], B, SUBMITTED_AT.replace(tzinfo=None)).links


def test_spoofed_sender_is_ignored():
    raw = confirm("1", sender="Fake B <no-reply@fakeb.example.evil.example>")
    assert scan_replies([raw], B).links == []


ID_MAILS = [
    "Please reply with a copy of your government-issued photo ID.",
    "We need a scan of your driver's license before we can proceed.",
    "Attach a copy of your passport to verify the request.",
    "Provide the last four digits of your Social Security number.",
    "Please send a notarized statement and a utility bill as proof of address.",
]


def test_id_request_detected_in_html_and_plain_text():
    for text in ID_MAILS:
        assert asks_for_id(mail(f"<p>{text}</p>")), text
    plain = EmailMessage()
    plain["From"] = "no-reply@fakeb.example"
    plain.set_content(ID_MAILS[0])
    assert asks_for_id(plain.as_bytes())


def test_ordinary_confirmation_is_not_an_id_request():
    for html in (('<p>Please confirm your email address.</p>'
                  '<a href="https://mail.fakeb.example/confirm?t=1">Verify my request</a>'),
                 "<p>Your opt-out is complete. The listing will be removed in 72 hours.</p>"):
        assert not asks_for_id(mail(html))


def test_id_request_mail_contributes_no_links():
    raw = mail('<p>Upload a photo of your driver license here:</p>'
               '<a href="https://mail.fakeb.example/verify-identity?t=9">Verify</a>')
    scan = scan_replies([raw], B, None)
    assert scan.id_requested and scan.links == []


def test_fake_mailer_wait_for_confirmation_never_returns_links_with_id_request():
    m = FakeMailer(inbox={"fakeb": [confirm("1"), mail("<p>Send a copy of your ID.</p>")]})
    p = make_profile(mailbox=MB)
    assert asyncio.run(m.wait_for_confirmation(p, B, SUBMITTED_AT)) == []
    scan = asyncio.run(m.scan_replies(p, B, SUBMITTED_AT))
    assert isinstance(scan, ReplyScan) and scan.id_requested


# ----------------------------------------------------------------- runner routing
def _person():
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    return make_profile(consent=c, mailbox=MB)


class Clicker(Runner):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.clicked: list[str] = []

    async def _click(self, profile, broker, url):
        self.clicked.append(url)
        return True


def _runner(store, mailer, dry_run=False):
    reg = Registry(version="t", updated=SUBMITTED_AT.date(), brokers=[B])
    from freemyid import config as cfgmod
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    return Clicker(store, reg, scan_only=False, dry_run=dry_run, interactive=False,
                   broker_ids=None, only_due=False, mailer=mailer, cfg=cfg,
                   now=SUBMITTED_AT + timedelta(days=3))


def _submitted(store, p):
    st = BrokerStatus(profile_id=p.id, broker_id=B.id, state=ListingState.SUBMITTED,
                      last_submitted_at=SUBMITTED_AT)
    store.save_status(st)
    return st


def test_runner_routes_id_request_to_human_todo_and_never_clicks(store):
    p = _person()
    store.save_profile(p)
    st = _submitted(store, p)
    m = FakeMailer(inbox={"fakeb": [confirm("1", when=SUBMITTED_AT + timedelta(hours=1)),
                                    mail("<p>Send a copy of your driver's license.</p>",
                                         when=SUBMITTED_AT + timedelta(days=1))]})
    r = _runner(store, m)
    new = asyncio.run(r._verify(p, B, B, st, Tier.EMAIL))
    assert r.clicked == [] and m.sent == []
    assert new.state == ListingState.NEEDS_HUMAN
    assert new.needs_human_reason == ID_REQUEST_REASON
    todos = [t for t in store.list_todos(p.id) if t.kind == TodoKind.ID_UPLOAD]
    assert len(todos) == 1 and todos[0].links == []
    # duplicate reply on the next run: still one to-do
    asyncio.run(r._verify(p, B, B, st, Tier.EMAIL))
    assert len([t for t in store.list_todos(p.id) if t.kind == TodoKind.ID_UPLOAD]) == 1
    assert r._id_hold(p, B)
    # person says "I did it": back to SUBMITTED, hold lifted once the to-do is closed
    store.save_status(new)
    hmod.mark_resolved(store, todos[0])
    store.complete_todo(todos[0].id)
    assert store.get_status(p.id, B.id).state == ListingState.SUBMITTED
    assert not r._id_hold(p, B)


def test_runner_dry_run_id_request_only_logs(store):
    p = _person()
    store.save_profile(p)
    st = _submitted(store, p)
    m = FakeMailer(inbox={"fakeb": [mail("<p>Attach a copy of your passport.</p>")]})
    r = _runner(store, m, dry_run=True)
    new = asyncio.run(r._verify(p, B, B, st, Tier.EMAIL))
    assert new.state == ListingState.SUBMITTED and store.list_todos(p.id) == []
    assert any(e.action == ID_REQUEST_REASON for e in store.events(p.id))


def test_runner_clicks_only_newest_confirmation(store):
    p = _person()
    store.save_profile(p)
    st = _submitted(store, p)
    m = FakeMailer(inbox={"fakeb": [
        confirm("stale", when=SUBMITTED_AT - timedelta(days=30)),
        confirm("a", mid="<a@fakeb.example>", when=SUBMITTED_AT + timedelta(hours=1)),
        confirm("a", mid="<a@fakeb.example>", when=SUBMITTED_AT + timedelta(hours=1)),
        confirm("b", mid="<b@fakeb.example>", when=SUBMITTED_AT + timedelta(days=1))]})
    r = _runner(store, m)
    new = asyncio.run(r._verify(p, B, B, st, Tier.EMAIL))
    assert r.clicked == ["https://mail.fakeb.example/confirm?t=b"]
    assert new.state == ListingState.CONFIRMED
    ev = [e for e in store.events(p.id) if e.action == "mail_replies_skipped"]
    assert ev and ev[0].detail == {"duplicates": 1, "stale": 1}
