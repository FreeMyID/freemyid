"""BL-IN-10: no letter cites state law before the statutory response window has passed
(45 days from the first request, 90 once the broker says it is extending). Before that, a
follow-up is a polite reminder and a legal demand waits. Fake people and brokers only."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from freemyid import config as cfgmod
from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import mail, outbox
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import EXTENSION_EVENT, Runner
from freemyid.models import (
    Actor,
    Address,
    Broker,
    BrokerStatus,
    Consent,
    ConsentBasis,
    EmailMode,
    Event,
    ListingState,
    MailboxConfig,
    Method,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    StateLaw,
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
WINDOW = timedelta(days=3 + 15)          # the broker's ladder window (processing + grace)


def _person(store, **over):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    p = make_profile(consent=c, mailbox=MB, email_mode=EmailMode.AUTO, **over)
    store.save_profile(p)
    return p


def _runner(store, now, laws=None):
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    return Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
                  broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
                  state_laws=laws or {}, now=now)


def _sent(store, p, at=T0):
    store.save_request(Request(profile_id=p.id, broker_id=B.id, kind=RequestKind.OPT_OUT,
                               method=Method.EMAIL, status=RequestStatus.SENT,
                               created_at=at, sent_at=at))


def _status(p, level, escalated):
    return BrokerStatus(profile_id=p.id, broker_id=B.id, state=ListingState.SUBMITTED,
                        last_submitted_at=T0, escalation_level=level,
                        last_escalated_at=escalated)


def _escalate(r, p, st):
    return asyncio.run(r._escalate(p, B, B, st, Tier.EMAIL, scanned=False))


def _events(store, p, action):
    return [e for e in store.events(p.id, B.id) if e.action == action]


def _claim_extension(store, p):
    store.log(Event(profile_id=p.id, broker_id=B.id, actor=Actor.ENGINE,
                    action=EXTENSION_EVENT))


# ------------------------------------------------------------------ window


def test_window_is_45_days_from_the_first_request(store):
    p = _person(store)
    _sent(store, p)
    _sent(store, p, at=T0 + timedelta(days=20))       # a later resubmit does not restart it
    r = _runner(store, T0 + timedelta(days=30))
    assert r.legal_window_end(p, B, _status(p, 1, None), None) == T0 + timedelta(days=45)


def test_window_is_90_days_once_the_broker_extends(store):
    p = _person(store)
    _sent(store, p)
    _claim_extension(store, p)
    r = _runner(store, T0 + timedelta(days=30))
    assert r.legal_window_end(p, B, _status(p, 1, None), None) == T0 + timedelta(days=90)


def test_window_falls_back_to_last_submitted_when_no_request_is_stored(store):
    p = _person(store)
    r = _runner(store, T0)
    assert r.legal_window_end(p, B, _status(p, 0, None), None) == T0 + timedelta(days=45)
    st = _status(p, 0, None).model_copy(update={"last_submitted_at": None})
    assert r.legal_window_end(p, B, st, None) is None


# ------------------------------------------------------------------ ladder


def test_early_legal_demand_waits_for_the_window(store):
    p = _person(store)
    _sent(store, p)
    now = T0 + timedelta(days=40)                     # rung due, window not over
    st = _escalate(_runner(store, now), p, _status(p, 2, now - WINDOW))
    assert st.escalation_level == 2
    ev = _events(store, p, "escalation_waiting")
    assert ev and ev[0].detail["why"] == "legal_window"
    assert ev[0].detail["until"] == (T0 + timedelta(days=45)).date().isoformat()
    assert not [q for q in store.list_requests(p.id, B.id)
                if q.kind == RequestKind.LEGAL_DEMAND]


def test_legal_demand_goes_after_the_window(store):
    p = _person(store)
    _sent(store, p)
    now = T0 + timedelta(days=46)
    st = _escalate(_runner(store, now), p, _status(p, 2, now - WINDOW))
    assert st.escalation_level == 3
    assert [q for q in store.list_requests(p.id, B.id) if q.kind == RequestKind.LEGAL_DEMAND]


def test_extension_keeps_the_legal_demand_waiting_past_45_days(store):
    p = _person(store)
    _sent(store, p)
    _claim_extension(store, p)
    now = T0 + timedelta(days=60)
    st = _escalate(_runner(store, now), p, _status(p, 2, now - WINDOW))
    assert st.escalation_level == 2
    assert _events(store, p, "escalation_waiting")


def test_early_follow_up_is_a_reminder_without_law(store, monkeypatch):
    seen = []
    real = outbox.queue_email

    def spy(*a, **k):
        seen.append(k.get("state_law"))
        return real(*a, **k)

    monkeypatch.setattr(outbox, "queue_email", spy)
    law = StateLaw(state="IL", statute_name="Fake Privacy Act", citation="Fake 1-2",
                   response_days=45)
    p = _person(store)
    _sent(store, p)
    now = T0 + timedelta(days=20)
    st = _escalate(_runner(store, now, {"IL": law}), p, _status(p, 1, now - WINDOW))
    assert st.escalation_level == 2                   # the reminder goes out
    assert seen == [None]
    ev = _events(store, p, "escalated")
    assert ev and ev[0].detail["reminder"] is True


# ------------------------------------------------------------------ template


def test_reminder_letter_has_no_legal_claim():
    p = make_profile(addresses=[Address(street="742 Evergreen Terrace", city="Springfield",
                                        state="il", zip="62704", current=True)])
    orig = Request(profile_id=p.id, broker_id=B.id, kind=RequestKind.OPT_OUT,
                   method=Method.EMAIL, status=RequestStatus.SENT, sent_at=T0)
    _subject, body = outbox.compose(p, B, [], None, RequestKind.FOLLOW_UP, original=orig)
    assert body.count("friendly reminder") == 1
    low = body.lower()
    assert "under the" not in low and "response period ended" not in low
    assert "statute" not in low and "law" not in low


# ------------------------------------------------------------------ reply detection


def _mail(text: str) -> bytes:
    return ("From: privacy@fakeb.example\r\nTo: removals@example.org\r\n"
            "Subject: Your request\r\nDate: Mon, 01 Jun 2026 13:00:00 +0000\r\n"
            "Message-ID: <x1@fakeb.example>\r\n\r\n" + text).encode()


def test_reply_that_extends_is_detected():
    for text in ["We are extending the response period by 45 days.",
                 "We need additional time and will respond within an additional 45 days.",
                 "This notice is an extension of our deadline."]:
        assert mail.scan_replies([_mail(text)], B).extension_claimed, text


def test_ordinary_reply_is_not_an_extension():
    for text in ["Your request has been completed.",
                 "Please confirm your request by clicking the link."]:
        assert not mail.scan_replies([_mail(text)], B).extension_claimed, text
