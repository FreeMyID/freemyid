"""Adopted from engine/_test_drafts: runner escalation-ladder timer edge cases.

Fake broker (*.example), FakeMailer only, nothing is sent anywhere.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from freemyid import config as cfgmod
from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import outbox
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import Runner
from freemyid.models import (
    Broker,
    BrokerStatus,
    Consent,
    ConsentBasis,
    EmailMode,
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
    "opt_out_email": "privacy@fakeb.example", "typical_processing_days": 30})
WINDOW = timedelta(days=30 + 15)
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")
T0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def person(**over):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    return make_profile(consent=c, **over)


def runner(store, now, mailer=None):
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    return Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
                  broker_ids=None, only_due=False, mailer=mailer or FakeMailer(), cfg=cfg,
                  state_laws={}, now=now)


def status(p, level, *, escalated=None):
    return BrokerStatus(profile_id=p.id, broker_id=B.id, state=ListingState.SUBMITTED,
                        last_submitted_at=T0, escalation_level=level,
                        last_escalated_at=escalated)


def sent_email(store, p, kind=RequestKind.OPT_OUT, at=T0):
    r = Request(profile_id=p.id, broker_id=B.id, kind=kind, method=Method.EMAIL,
                status=RequestStatus.SENT, created_at=at, sent_at=at)
    store.save_request(r)
    return r


def escalate(r, p, st):
    return asyncio.run(r._escalate(p, B, B, st, Tier.EMAIL, scanned=False))


def test_failed_letter_does_not_climb_the_ladder(store):
    class Broken(FakeMailer):
        def send(self, *a, **k):
            raise OSError("smtp down")

    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    sent_email(store, p)                               # SEC-27 gate already open
    now = T0 + 2 * WINDOW + timedelta(days=1)
    st = status(p, 1, escalated=T0 + WINDOW)           # resubmit done; follow-up due
    new = escalate(runner(store, now, Broken()), p, st)
    assert new.escalation_level == 1                   # follow-up NOT skipped
    assert new.last_escalated_at == now                # retried one window later
    assert any(e.action == "escalation_failed" for e in store.events(p.id))


def test_successful_follow_up_climbs(store):
    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    sent_email(store, p)
    now = T0 + 2 * WINDOW + timedelta(days=1)
    m = FakeMailer()
    new = escalate(runner(store, now, m), p, status(p, 1, escalated=T0 + WINDOW))
    assert new.escalation_level == 2 and len(m.sent) == 1


def test_unapproved_letter_blocks_the_next_rung(store):
    p = person(mailbox=MB, email_mode=EmailMode.APPROVE_EACH)
    store.save_profile(p)
    sent_email(store, p)
    store.save_request(Request(profile_id=p.id, broker_id=B.id, kind=RequestKind.FOLLOW_UP,
                               method=Method.EMAIL,
                               status=RequestStatus.QUEUED_FOR_APPROVAL))
    now = T0 + 4 * WINDOW
    st = status(p, 2, escalated=T0 + 2 * WINDOW)       # legal demand would be due
    new = escalate(runner(store, now), p, st)
    assert new == st
    assert not [r for r in store.list_requests(p.id, B.id)
                if r.kind == RequestKind.LEGAL_DEMAND]
    ev = [e for e in store.events(p.id) if e.action == "escalation_waiting"]
    assert ev and ev[0].detail["why"] == "awaiting_approval"


def test_open_manual_letter_todo_blocks_the_next_rung(store):
    p = person()                                       # no mailbox: letters are to-dos
    store.save_profile(p)
    r = runner(store, T0 + 2 * WINDOW + timedelta(days=1))
    st = escalate(r, p, status(p, 1, escalated=T0 + WINDOW))
    assert st.escalation_level == 2                    # follow-up to-do created
    later = runner(store, T0 + 4 * WINDOW)
    assert escalate(later, p, st) == st                # demand waits for that to-do


def test_late_approval_restarts_the_wait_from_the_real_send(store):
    p = person(mailbox=MB, email_mode=EmailMode.APPROVE_EACH)
    store.save_profile(p)
    sent_email(store, p)
    queued_at = T0 + 2 * WINDOW
    approved_at = queued_at + timedelta(days=40)       # person approved it 40 days later
    sent_email(store, p, RequestKind.FOLLOW_UP, at=approved_at)
    st = status(p, 2, escalated=queued_at)
    # one window after queueing, but only 5 days after the follow-up really went out
    soon = runner(store, queued_at + WINDOW)
    assert escalate(soon, p, st) == st
    due = runner(store, approved_at + WINDOW + timedelta(days=1))
    new = escalate(due, p, st)
    assert new.escalation_level == 3                   # legal demand queued for approval
    demand = [r for r in store.list_requests(p.id, B.id) if r.kind == RequestKind.LEGAL_DEMAND]
    assert demand and demand[0].status == RequestStatus.QUEUED_FOR_APPROVAL
    assert outbox.needs_approval(p, RequestKind.LEGAL_DEMAND, store)


# ----------------------------------------------------------------- SEC-47 helper
def test_released_by_approval_lists_the_other_held_emails(store):
    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    b2 = B.model_copy(update={"id": "faketwo", "opt_out_email": "privacy@faketwo.example"})
    m = FakeMailer()
    first = outbox.queue_email(store, p, B, [], dry_run=False, mailer=m)
    second = outbox.queue_email(store, p, b2, [], dry_run=False, mailer=m)
    demand = outbox.queue_email(store, p, b2, [], kind=RequestKind.LEGAL_DEMAND,
                                dry_run=False, mailer=m)
    assert [r.id for r in outbox.released_by_approval(store, p, first)] == [second.id]
    assert outbox.released_by_approval(store, p, demand) == []
    each = p.model_copy(update={"email_mode": EmailMode.APPROVE_EACH})
    assert outbox.released_by_approval(store, each, first) == []
