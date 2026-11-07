"""SEC-27 (adopted from engine/_test_drafts): first real email per profile needs explicit approval.

Fake people, fake brokers (*.example), FakeMailer only. Nothing leaves the machine.
"""
from __future__ import annotations

import smtplib
from datetime import date

import pytest

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import _dev, outbox
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import run
from freemyid.models import (
    Broker,
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
)
from tests.conftest import make_profile

MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")


def _broker(bid: str) -> Broker:
    return Broker.model_validate({
        "id": bid, "name": bid.title(), "url": f"https://{bid}.example/",
        "category": "data_broker", "domains": [f"{bid}.example"], "method": "email",
        "opt_out_email": f"privacy@{bid}.example"})


B1, B2, B3 = _broker("fakeone"), _broker("faketwo"), _broker("fakethree")
REG = Registry(version="t", updated=date(2026, 11, 7), brokers=[B1, B2, B3])


def person(**over):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    return make_profile(consent=c, mailbox=MB, **over)


@pytest.fixture
def no_smtp(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("SMTP used")
    monkeypatch.setattr(smtplib, "SMTP", boom)
    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)


def _queued(store, pid):
    return store.list_requests(pid, status=RequestStatus.QUEUED_FOR_APPROVAL)


def test_auto_profile_holds_every_email_until_first_approval(store, no_smtp):
    p = person(email_mode=EmailMode.AUTO)
    store.save_profile(p)
    m = FakeMailer()
    reqs = [outbox.queue_email(store, p, b, [], dry_run=False, mailer=m) for b in (B1, B2)]
    assert [r.status for r in reqs] == [RequestStatus.QUEUED_FOR_APPROVAL] * 2
    assert m.sent == []
    assert outbox.first_email_pending(store, p).id == reqs[0].id
    assert all(outbox.held_by_first_approval(p, r, store) for r in reqs)
    holds = [e for e in store.events(p.id) if e.action == outbox.HOLD_ACTION]
    assert {e.detail["request_id"] for e in holds} == {r.id for r in reqs}


def test_approving_first_releases_the_rest_but_not_legal_demands(store, no_smtp):
    p = person(email_mode=EmailMode.AUTO)
    store.save_profile(p)
    m = FakeMailer()
    first = outbox.queue_email(store, p, B1, [], dry_run=False, mailer=m)
    second = outbox.queue_email(store, p, B2, [], dry_run=False, mailer=m)
    demand = outbox.queue_email(store, p, B3, [], kind=RequestKind.LEGAL_DEMAND,
                                dry_run=False, mailer=m)
    outbox.approve_and_send(store, first.id, mailer=m, registry=REG)
    assert {s.to for s in m.sent} == {"privacy@fakeone.example", "privacy@faketwo.example"}
    assert store.get_request(second.id).status == RequestStatus.SENT
    assert store.get_request(demand.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert outbox.first_email_pending(store, p) is None
    rel = [e for e in store.events(p.id) if e.action == outbox.RELEASE_ACTION]
    assert rel and rel[0].detail == {"sent": 1, "failed": 0}
    # later emails go straight out
    third = outbox.queue_email(store, p, B3, [], dry_run=False, mailer=m)
    assert third.status == RequestStatus.SENT


def test_approve_each_never_releases_others(store, no_smtp):
    p = person(email_mode=EmailMode.APPROVE_EACH)
    store.save_profile(p)
    m = FakeMailer()
    first = outbox.queue_email(store, p, B1, [], dry_run=False, mailer=m)
    second = outbox.queue_email(store, p, B2, [], dry_run=False, mailer=m)
    outbox.approve_and_send(store, first.id, mailer=m, registry=REG)
    assert len(m.sent) == 1
    assert store.get_request(second.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert outbox.first_email_pending(store, p) is None     # not an AUTO hold


def test_web_form_send_does_not_open_the_email_gate(store, no_smtp):
    p = person(email_mode=EmailMode.AUTO)
    store.save_profile(p)
    store.save_request(Request(profile_id=p.id, broker_id="fakeone", kind=RequestKind.OPT_OUT,
                               method=Method.WEB_FORM, status=RequestStatus.SENT))
    m = FakeMailer()
    r = outbox.queue_email(store, p, B2, [], dry_run=False, mailer=m)
    assert r.status == RequestStatus.QUEUED_FOR_APPROVAL and m.sent == []


def test_failed_first_send_keeps_the_gate_closed(store, no_smtp):
    class Broken(FakeMailer):
        def send(self, *a, **k):
            raise OSError("down")

    p = person(email_mode=EmailMode.AUTO)
    store.save_profile(p)
    first = outbox.queue_email(store, p, B1, [], dry_run=False, mailer=FakeMailer())
    second = outbox.queue_email(store, p, B2, [], dry_run=False, mailer=FakeMailer())
    with pytest.raises(outbox.OutboxError):
        outbox.approve_and_send(store, first.id, mailer=Broken(), registry=REG)
    assert store.get_request(first.id).status == RequestStatus.FAILED
    assert store.get_request(second.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert outbox.needs_approval(p, RequestKind.OPT_OUT, store)


def test_one_release_failure_does_not_stop_the_others(store, no_smtp):
    class FlakyOnTwo(FakeMailer):
        def send(self, profile, to, *a, **k):
            if "faketwo" in to:
                raise OSError("down")
            return super().send(profile, to, *a, **k)

    p = person(email_mode=EmailMode.AUTO)
    store.save_profile(p)
    m = FlakyOnTwo()
    reqs = [outbox.queue_email(store, p, b, [], dry_run=False, mailer=m) for b in (B1, B2, B3)]
    outbox.approve_and_send(store, reqs[0].id, mailer=m, registry=REG)
    got = [store.get_request(r.id).status for r in reqs]
    assert got == [RequestStatus.SENT, RequestStatus.FAILED, RequestStatus.SENT]


def test_runner_queues_first_auto_email_then_sends_after_approval(store, no_smtp):
    """End to end with the dev fixtures: AUTO mode, real (non-dry) run, FakeMailer."""
    p = person(email_mode=EmailMode.AUTO)
    store.save_profile(p)
    reg = _dev.fixture_registry()
    extra = reg.get("devmail").model_copy(update={"id": "devmail2", "name": "Dev Mail 2",
                                                  "opt_out_email": "privacy@devmail2.example",
                                                  "domains": ["devmail2.example"]})
    reg = reg.model_copy(update={"brokers": [*reg.brokers, extra]})
    m = FakeMailer()
    with _dev.fixture_server():
        run(store, reg, [p], scan_only=False, dry_run=False, interactive=False, mailer=m)
    assert m.sent == []
    held = [r for r in _queued(store, p.id) if r.method == Method.EMAIL]
    assert {r.broker_id for r in held} >= {"devmail", "devmail2"}
    outbox.approve_and_send(store, held[0].id, mailer=m, registry=reg)
    assert {s.to for s in m.sent} >= {"privacy@devmail.example", "privacy@devmail2.example"}
    for bid in ("devmail", "devmail2"):
        assert store.get_status(p.id, bid).state == ListingState.SUBMITTED
