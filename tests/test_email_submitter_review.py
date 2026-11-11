"""PR #125 (WO-348) review follow-ups: plain "not sent" reasons from the email submitter.

Fake broker (*.example), fake mailers only, nothing is sent anywhere. Fake people only.
"""
from __future__ import annotations

import asyncio
import smtplib
from datetime import timedelta

from freemyid.engine.mail import FakeMailer
from freemyid.models import EmailMode, Method, Request, RequestKind, RequestStatus
from freemyid.submitters import email as email_sub
from tests.test_escalation_timers import (
    MB,
    T0,
    WINDOW,
    escalate,
    person,
    runner,
    sent_email,
    status,
)
from tests.test_escalation_timers import B as BROKER


class Broken(FakeMailer):
    def send(self, *a, **k):
        raise ConnectionRefusedError("smtp down")


def test_failed_resubmit_does_not_climb_the_ladder(store):
    """CodeRabbit #25 (Major): the submitter now returns "not sent" instead of raising, so
    the runner must treat that as a failed rung, exactly like the old OutboxError."""
    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    sent_email(store, p)                               # SEC-27 gate already open
    now = T0 + WINDOW + timedelta(days=1)              # resubmit due
    new = escalate(runner(store, now, Broken()), p, status(p, 0))
    assert new.escalation_level == 0                   # resubmit NOT skipped
    assert new.last_escalated_at == now                # retried one window later
    assert any(e.action == "escalation_failed" for e in store.events(p.id))
    assert not any(e.action == "escalated" for e in store.events(p.id))


def test_successful_resubmit_still_climbs(store):
    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    sent_email(store, p)
    m = FakeMailer()
    new = escalate(runner(store, T0 + WINDOW + timedelta(days=1), m), p, status(p, 0))
    assert new.escalation_level == 1 and len(m.sent) == 1


def test_a_missing_message_id_is_not_reported_as_one(store):
    """_CaughtMailer turned a None message id into the string "None" (truthy)."""
    class NoId(FakeMailer):
        def send(self, *a, **k):
            super().send(*a, **k)

    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    sent_email(store, p)
    new = escalate(runner(store, T0 + WINDOW + timedelta(days=1), NoId()), p, status(p, 0))
    assert new.escalation_level == 1
    sent = [e for e in store.events(p.id) if e.action == "email_sent"]
    assert sent and sent[0].detail["has_message_id"] is False


def test_oserror_subclasses_are_not_all_connection_errors():
    """CodeRabbit #111: every SMTPException and PermissionError has OSError in its MRO."""
    assert email_sub._classify(PermissionError("denied")) == email_sub.REASON_OTHER
    assert email_sub._classify(smtplib.SMTPHeloError(501, b"bad")) == email_sub.REASON_OTHER
    assert email_sub._classify(OSError("down")) == email_sub.REASON_CONNECTION
    assert email_sub._classify(ConnectionResetError()) == email_sub.REASON_CONNECTION
    assert email_sub._classify(TimeoutError()) == email_sub.REASON_CONNECTION


def _ctx(store, p, mailer):
    from freemyid.engine.runner import NullNotifier
    from freemyid.interfaces import RunContext
    from freemyid.netpolicy import NetPolicy
    return RunContext(profile=p, broker=BROKER, store=store, netpolicy=NetPolicy(None),
                      handoff=None, notifier=NullNotifier(), mailer=mailer, dry_run=False,
                      interactive=False, now=T0 + WINDOW)


def test_todo_links_this_request_not_an_older_failure(store):
    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    sent_email(store, p)
    old = Request(profile_id=p.id, broker_id=BROKER.id, kind=RequestKind.FOLLOW_UP,
                  method=Method.EMAIL, status=RequestStatus.FAILED, created_at=T0)
    store.save_request(old)
    out = asyncio.run(email_sub.EmailSubmitter().submit(_ctx(store, p, Broken()), []))
    assert out.message == f"not sent: {email_sub.REASON_CONNECTION}"
    queued = store.list_requests(p.id, BROKER.id, status=RequestStatus.QUEUED_FOR_APPROVAL)
    assert len(queued) == 1                             # WO-332: kept for a retry
    assert out.todos[0].request_id == queued[0].id
    assert out.todos[0].request_id != old.id


def test_first_email_wait_adds_no_card(store):
    """The approval screen already lists the held email; a per-site APPROVE_EMAIL card was
    never closed by approving, so it went stale (and doubled the end-of-run count)."""
    p = person(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)                               # no email sent yet: gate closed
    m = FakeMailer()
    out = asyncio.run(email_sub.EmailSubmitter().submit(_ctx(store, p, m), []))
    assert out.message == f"not sent: {email_sub.REASON_FIRST}"
    assert out.request is not None
    assert out.request.status == RequestStatus.QUEUED_FOR_APPROVAL
    assert out.todos == []
    assert m.sent == []
