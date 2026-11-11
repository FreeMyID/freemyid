"""WO-332: retry a transient outbox send, with backoff. Fake people, no network."""
from __future__ import annotations

import logging
import smtplib
import socket
from datetime import date, timedelta

import pytest

from freemyid.engine import outbox
from freemyid.engine.mail import MailError
from freemyid.models import (
    Actor,
    Broker,
    EmailMode,
    Event,
    MailboxConfig,
    Method,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    utcnow,
)
from tests.conftest import make_profile

MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")

# Words that would mean a letter, address, or link leaked into an event.
_PII = (
    "Jane", "Testperson", "Springfield", "Evergreen", "217-555-0142",
    "jane.testperson", "privacy@", "http://", "https://", "@",
)


@pytest.fixture(autouse=True)
def block_network(monkeypatch, freemyid_env):
    """socket.connect and create_connection always raise. Runs after the suite guard."""
    assert freemyid_env is not None

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class RaisingMailer:
    """Raises `exc` for the first `failures` sends, then returns a message id."""

    def __init__(self, exc: BaseException | None = None, failures: int = 100) -> None:
        self.exc = exc
        self.failures = failures
        self.calls = 0

    def send(self, _profile, _to, _subject, _body, _request_id: str) -> str:
        self.calls += 1
        if self.exc is not None and self.calls <= self.failures:
            raise self.exc
        return "mid"


def _broker(bid: str) -> Broker:
    return Broker.model_validate({
        "id": bid, "name": bid.title(), "url": f"https://{bid}.example/",
        "category": "data_broker", "domains": [f"{bid}.example"], "method": "email",
        "opt_out_email": f"privacy@{bid}.example"})


def _profile():
    return make_profile(mailbox=MB, email_mode=EmailMode.AUTO)


def _queued(store, bid: str = "fakeb"):
    p = _profile()
    store.save_profile(p)
    req = outbox.queue_email(store, p, _broker(bid), [], dry_run=False, mailer=None)
    assert req.status == RequestStatus.QUEUED_FOR_APPROVAL
    return p, req


def _open_gate(store, p) -> None:
    store.save_request(Request(
        profile_id=p.id, broker_id="gateopen", kind=RequestKind.OPT_OUT,
        method=Method.EMAIL, status=RequestStatus.SENT))


def _held(store, *bids: str):
    """AUTO profile whose first email is already sent, plus queued letters."""
    p = _profile()
    store.save_profile(p)
    _open_gate(store, p)
    reqs = [outbox.queue_email(store, p, _broker(bid), [], dry_run=False, mailer=None)
            for bid in bids]
    assert all(r.status == RequestStatus.QUEUED_FOR_APPROVAL for r in reqs)
    return p, reqs


def _wrap(inner: Exception) -> MailError:
    """Same shape as SmtpImapMailer: MailError from None, original kept as context."""
    err = MailError(f"smtp failed: {type(inner).__name__}")
    err.__cause__ = None
    err.__context__ = inner
    err.__suppress_context__ = True
    return err


def _failed(store, pid: str, bid: str | None = None) -> list:
    return [e for e in store.events(pid, bid) if e.action == "email_failed"]


def _codes_only(store, pid: str) -> None:
    for ev in store.events(pid):
        blob = repr(ev.detail)
        for word in _PII:
            assert word not in blob, (ev.action, word)
        if ev.action == "email_failed":
            assert set(ev.detail) <= {"request_id", "error", "transient", "attempt"}
            assert isinstance(ev.detail["error"], str)
            assert ev.detail["error"].isidentifier()


def test_sockets_cannot_connect():
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.mark.parametrize("exc,transient", [
    (TimeoutError("t"), True),
    (socket.timeout("t"), True),  # noqa: UP041 - spec name; alias of TimeoutError on 3.10+
    (ConnectionError("t"), True),
    (ConnectionResetError("t"), True),
    (smtplib.SMTPServerDisconnected("t"), True),
    (smtplib.SMTPResponseException(400, b"x"), True),
    (smtplib.SMTPResponseException(450, b"x"), True),
    (smtplib.SMTPResponseException(499, b"x"), True),
    (smtplib.SMTPDataError(451, b"x"), True),
    (smtplib.SMTPResponseException(399, b"x"), False),
    (smtplib.SMTPResponseException(500, b"x"), False),
    (smtplib.SMTPResponseException(550, b"x"), False),
    (smtplib.SMTPDataError(550, b"x"), False),
    (smtplib.SMTPAuthenticationError(535, b"x"), False),
    (smtplib.SMTPAuthenticationError(454, b"x"), False),
    (smtplib.SMTPException("x"), False),
    (smtplib.SMTPRecipientsRefused({}), False),
    (OSError("down"), False),
    (RuntimeError("x"), False),
])
def test_classifier(exc: BaseException, transient: bool):
    assert outbox.is_transient_mail_error(exc) is transient


def test_smtp_code_must_be_an_int():
    exc = smtplib.SMTPResponseException(450, b"x")
    exc.smtp_code = "450"  # type: ignore[assignment]
    assert outbox.is_transient_mail_error(exc) is False


@pytest.mark.parametrize("exc,transient", [
    (TimeoutError(), True),
    (socket.timeout(), True),  # noqa: UP041 - spec name; alias of TimeoutError on 3.10+
    (ConnectionError(), True),
    (smtplib.SMTPServerDisconnected(), True),
    (smtplib.SMTPResponseException(450, b"privacy@fakeb.example"), True),
    (smtplib.SMTPResponseException(550, b"privacy@fakeb.example"), False),
    (smtplib.SMTPAuthenticationError(535, b"privacy@fakeb.example"), False),
    (smtplib.SMTPAuthenticationError(454, b"privacy@fakeb.example"), False),
    (OSError("down"), False),
])
def test_send_request_classifies(store, exc: BaseException, transient: bool):
    p, req = _queued(store)
    before = req.status
    with pytest.raises(outbox.OutboxError) as caught:
        outbox.send_request(store, req, p, RaisingMailer(exc))
    assert str(caught.value) == f"send failed: {type(exc).__name__}"
    got = store.get_request(req.id)
    assert got is not None and got.attempt == 1
    ev = _failed(store, p.id, req.broker_id)[0]
    assert ev.detail["request_id"] == req.id
    assert ev.detail["error"] == type(exc).__name__
    if transient:
        assert got.status == before
        assert ev.detail["transient"] is True
        assert ev.detail["attempt"] == 1
    else:
        assert got.status == RequestStatus.FAILED
        assert ev.detail["transient"] is False
        assert "attempt" not in ev.detail
    _codes_only(store, p.id)


def test_third_transient_failure_marks_failed(store):
    p, req = _queued(store)
    mailer = RaisingMailer(ConnectionError("reset"), failures=3)
    for attempt in (1, 2):
        with pytest.raises(outbox.OutboxError, match="ConnectionError"):
            outbox.send_request(store, req, p, mailer)
        got = store.get_request(req.id)
        assert got is not None
        assert got.status == RequestStatus.QUEUED_FOR_APPROVAL
        assert got.attempt == 1
        assert _failed(store, p.id, req.broker_id)[0].detail["attempt"] == attempt
    with pytest.raises(outbox.OutboxError, match="ConnectionError"):
        outbox.send_request(store, req, p, mailer)
    got = store.get_request(req.id)
    assert got is not None and got.status == RequestStatus.FAILED
    rows = _failed(store, p.id, req.broker_id)
    assert [e.detail["attempt"] for e in rows] == [3, 2, 1]
    assert all(e.detail["transient"] is True for e in rows)
    assert mailer.calls == 3
    _codes_only(store, p.id)


def test_attempts_come_from_the_event_log_not_a_field(store):
    p, req = _queued(store)
    for attempt in (1, 2):
        store.log(Event(
            profile_id=p.id, broker_id=req.broker_id, actor=Actor.ENGINE,
            action="email_failed",
            detail={"request_id": req.id, "error": "TimeoutError", "transient": True,
                    "attempt": attempt}))
    store.log(Event(
        profile_id=p.id, broker_id=req.broker_id, actor=Actor.ENGINE,
        action="email_failed",
        detail={"request_id": req.id, "error": "OSError", "transient": False}))
    store.log(Event(
        profile_id=p.id, broker_id=req.broker_id, actor=Actor.ENGINE,
        action="email_failed",
        detail={"request_id": "a" * 32, "error": "TimeoutError", "transient": True,
                "attempt": 9}))
    mailer = RaisingMailer(TimeoutError())
    with pytest.raises(outbox.OutboxError, match="TimeoutError"):
        outbox.send_request(store, req, p, mailer)
    got = store.get_request(req.id)
    assert got is not None and got.status == RequestStatus.FAILED and got.attempt == 1
    assert mailer.calls == 1
    mine = [e.detail["attempt"] for e in _failed(store, p.id, req.broker_id)
            if e.detail.get("transient") is True and e.detail.get("request_id") == req.id]
    assert mine == [3, 2, 1]


def test_permanent_after_a_transient_fails_immediately(store):
    p, req = _queued(store)
    with pytest.raises(outbox.OutboxError):
        outbox.send_request(store, req, p, RaisingMailer(TimeoutError()))
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    with pytest.raises(outbox.OutboxError, match="SMTPResponseException"):
        outbox.send_request(store, req, p, RaisingMailer(smtplib.SMTPResponseException(550, b"x")))
    assert store.get_request(req.id).status == RequestStatus.FAILED


@pytest.mark.parametrize("inner,transient", [
    (TimeoutError(), True),
    (smtplib.SMTPResponseException(451, b"privacy@fakeb.example"), True),
    (smtplib.SMTPResponseException(552, b"privacy@fakeb.example"), False),
    (smtplib.SMTPAuthenticationError(454, b"privacy@fakeb.example"), False),
    (ConnectionResetError(), True),
])
def test_wrapped_mail_error_uses_the_chained_exception(store, inner: Exception,
                                                       transient: bool):
    p, req = _queued(store)
    with pytest.raises(outbox.OutboxError) as caught:
        outbox.send_request(store, req, p, RaisingMailer(_wrap(inner)))
    assert str(caught.value) == f"send failed: {type(inner).__name__}"
    got = store.get_request(req.id)
    assert got is not None
    ev = _failed(store, p.id, req.broker_id)[0]
    assert ev.detail["error"] == type(inner).__name__
    assert ev.detail["transient"] is transient
    if transient:
        assert got.status == RequestStatus.QUEUED_FOR_APPROVAL
        assert ev.detail["attempt"] == 1
    else:
        assert got.status == RequestStatus.FAILED
    _codes_only(store, p.id)


def test_bare_mail_error_is_permanent_and_stays_a_code(store, caplog):
    p, req = _queued(store)
    caplog.set_level(logging.DEBUG)
    exc = MailError("mailbox password not in keychain")
    with pytest.raises(outbox.OutboxError) as caught:
        outbox.send_request(store, req, p, RaisingMailer(exc))
    assert str(caught.value) == "send failed: MailError"
    assert "password" not in str(caught.value)
    assert "password" not in caplog.text
    assert "Jane" not in caplog.text
    got = store.get_request(req.id)
    assert got is not None and got.status == RequestStatus.FAILED
    ev = _failed(store, p.id, req.broker_id)[0]
    assert ev.detail == {"request_id": req.id, "error": "MailError", "transient": False}
    _codes_only(store, p.id)


def test_dry_run_is_never_sent(store):
    p = _profile()
    store.save_profile(p)
    mailer = RaisingMailer(TimeoutError())
    req = outbox.queue_email(store, p, _broker("fakedry"), [], dry_run=True, mailer=mailer)
    assert req.status == RequestStatus.DRAFT and req.dry_run is True
    assert mailer.calls == 0
    with pytest.raises(outbox.OutboxError, match="dry-run"):
        outbox.send_request(store, req, p, mailer)
    assert mailer.calls == 0
    got = store.get_request(req.id)
    assert got is not None and got.status == RequestStatus.DRAFT
    assert _failed(store, p.id) == []


def test_transient_first_send_keeps_the_approval_gate_closed(store):
    p = _profile()
    store.save_profile(p)
    b1, b2 = _broker("fakeone"), _broker("faketwo")
    reg = Registry(version="t", updated=date(2026, 11, 10), brokers=[b1, b2])
    first = outbox.queue_email(store, p, b1, [], dry_run=False, mailer=None)
    second = outbox.queue_email(store, p, b2, [], dry_run=False, mailer=None)
    with pytest.raises(outbox.OutboxError, match="TimeoutError"):
        outbox.approve_and_send(store, first.id, mailer=RaisingMailer(TimeoutError()),
                                registry=reg)
    assert store.get_request(first.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert store.get_request(second.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert outbox.needs_approval(p, RequestKind.OPT_OUT, store)
    assert outbox.release_held(store, p, mailer=RaisingMailer()) == {"sent": 0, "failed": 0}
    assert not any(e.action == outbox.RELEASE_ACTION for e in store.events(p.id))


def test_release_held_defers_inside_fifteen_minutes_then_sends(store):
    p, (waiting, going) = _held(store, "fakewait", "fakego")
    with pytest.raises(outbox.OutboxError):
        outbox.send_request(store, waiting, p, RaisingMailer(TimeoutError()))
    anchor = utcnow()
    first = RaisingMailer()
    got = outbox.release_held(store, p, mailer=first, now=anchor)
    assert got == {"sent": 1, "failed": 0, "deferred": 1}
    assert first.calls == 1
    assert store.get_request(waiting.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert store.get_request(going.id).status == RequestStatus.SENT
    rel = [e for e in store.events(p.id) if e.action == outbox.RELEASE_ACTION]
    assert rel[0].detail == {"sent": 1, "failed": 0, "deferred": 1}

    early = RaisingMailer()
    held = outbox.release_held(store, p, mailer=early, now=anchor + timedelta(minutes=14))
    assert early.calls == 0
    assert held == {"sent": 0, "failed": 0, "deferred": 1}
    assert store.get_request(waiting.id).status == RequestStatus.QUEUED_FOR_APPROVAL

    later = RaisingMailer()
    done = outbox.release_held(store, p, mailer=later, now=anchor + timedelta(minutes=16))
    assert later.calls == 1
    assert done == {"sent": 1, "failed": 0}
    assert store.get_request(waiting.id).status == RequestStatus.SENT
    _codes_only(store, p.id)


def test_second_transient_failure_waits_an_hour(store):
    p, (req,) = _held(store, "fakeb")
    mailer = RaisingMailer(smtplib.SMTPServerDisconnected(), failures=2)
    for _ in range(2):
        with pytest.raises(outbox.OutboxError):
            current = store.get_request(req.id)
            outbox.send_request(store, current, p, mailer)
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert [e.detail["attempt"] for e in _failed(store, p.id, req.broker_id)] == [2, 1]
    anchor = utcnow()

    early = RaisingMailer()
    held = outbox.release_held(store, p, mailer=early, now=anchor + timedelta(minutes=30))
    assert early.calls == 0
    assert held == {"sent": 0, "failed": 0, "deferred": 1}
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL

    # Backoff has elapsed, so this try is the third transient failure and stops.
    late = RaisingMailer(TimeoutError(), failures=1)
    got = outbox.release_held(store, p, mailer=late, now=anchor + timedelta(hours=1, minutes=1))
    assert late.calls == 1
    assert got == {"sent": 0, "failed": 1}
    assert "deferred" not in got
    got_req = store.get_request(req.id)
    assert got_req is not None and got_req.status == RequestStatus.FAILED
    assert _failed(store, p.id, req.broker_id)[0].detail["attempt"] == 3
    _codes_only(store, p.id)


def test_release_held_counts_a_retryable_failure_as_deferred_not_failed(store):
    """CodeRabbit #104 (PR #111): a 1st or 2nd transient failure leaves the request queued for
    a retry, so the release event must not report it as failed."""
    p, (req,) = _held(store, "fakeb")
    got = outbox.release_held(store, p, mailer=RaisingMailer(TimeoutError(), failures=1))
    assert got == {"sent": 0, "failed": 0, "deferred": 1}
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    rel = [e for e in store.events(p.id) if e.action == outbox.RELEASE_ACTION]
    assert rel[0].detail == {"sent": 0, "failed": 0, "deferred": 1}


def test_queue_email_reuse_respects_the_backoff(store):
    """PR #111 review: the next run's queue_email reuses the queued letter and must not send
    it again inside its backoff (only release_held checked it)."""
    p, (req,) = _held(store, "fakeb")
    with pytest.raises(outbox.OutboxError):
        outbox.send_request(store, req, p, RaisingMailer(TimeoutError(), failures=1))
    anchor = utcnow()
    early = RaisingMailer()
    got = outbox.queue_email(store, p, _broker("fakeb"), [], dry_run=False, mailer=early,
                             now=anchor + timedelta(minutes=5))
    assert early.calls == 0
    assert got.id == req.id and got.status == RequestStatus.QUEUED_FOR_APPROVAL
    late = RaisingMailer()
    sent = outbox.queue_email(store, p, _broker("fakeb"), [], dry_run=False, mailer=late,
                              now=anchor + timedelta(minutes=16))
    assert late.calls == 1 and sent.status == RequestStatus.SENT
