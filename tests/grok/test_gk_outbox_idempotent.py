"""WO-342: a crash between send and record does not send the same message twice."""
from __future__ import annotations

import logging
import socket
from datetime import timedelta

import pytest

from freemyid.engine import outbox
from freemyid.models import (
    Broker,
    EmailMode,
    EvidenceKind,
    MailboxConfig,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    utcnow,
)
from tests.conftest import make_profile

MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")

# Words that would mean a letter, address, or link leaked into a log or event.
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


class CountingMailer:
    """Records request ids. Sends nothing and opens no socket."""

    def __init__(self) -> None:
        self.ids: list[str] = []

    def send(self, _profile, _to, _subject, _body, request_id: str) -> str:
        self.ids.append(request_id)
        return "mid"


class _CrashStore:
    """Delegates to the real store. The first SENT row, or the first sent blob, raises."""

    def __init__(self, inner, on: str) -> None:
        self._inner = inner
        self._on = on
        self.raised = False

    def save_request(self, req):
        if self._on == "sent" and req.status == RequestStatus.SENT and not self.raised:
            self.raised = True
            raise RuntimeError("crash between send and record")
        return self._inner.save_request(req)

    def save_evidence(self, evidence, plaintext: bytes):
        if (self._on == "evidence" and evidence.kind == EvidenceKind.EMAIL_SENT
                and not self.raised):
            self.raised = True
            raise RuntimeError("crash between send and record")
        return self._inner.save_evidence(evidence, plaintext)

    def __getattr__(self, name: str):
        return getattr(self._inner, name)


def _broker(bid: str) -> Broker:
    return Broker.model_validate({
        "id": bid, "name": bid.title(), "url": f"https://{bid}.example/",
        "category": "data_broker", "domains": [f"{bid}.example"], "method": "email",
        "opt_out_email": f"privacy@{bid}.example"})


def _profile():
    return make_profile(mailbox=MB, email_mode=EmailMode.AUTO)


def _open_gate(store, profile) -> None:
    store.save_request(Request(
        profile_id=profile.id, broker_id="gateopen", kind=RequestKind.OPT_OUT,
        method=Method.EMAIL, status=RequestStatus.SENT))


def _ready(store, *bids: str):
    """AUTO profile whose first email is already sent, plus queued letters."""
    profile = _profile()
    store.save_profile(profile)
    _open_gate(store, profile)
    reqs = [outbox.queue_email(store, profile, _broker(bid), [], dry_run=False, mailer=None)
            for bid in bids]
    assert all(req.status == RequestStatus.QUEUED_FOR_APPROVAL for req in reqs)
    return profile, reqs


def _rows(store, profile_id: str, broker_id: str, action: str) -> list:
    return [ev for ev in store.events(profile_id, broker_id)
            if ev.action == action]


def _sent_blobs(store, profile_id: str, broker_id: str, request_id: str) -> list:
    return [ev for ev in store.list_evidence(profile_id, broker_id)
            if ev.kind == EvidenceKind.EMAIL_SENT and ev.request_id == request_id]


def _codes_only(store, profile_id: str, caplog) -> None:
    text = caplog.text
    for ev in store.events(profile_id):
        blob = repr(ev.detail)
        for word in _PII:
            assert word not in blob, (ev.action, word)
            assert word not in text, word
        if ev.action == outbox.HANDOFF_ACTION:
            assert set(ev.detail) == {"request_id", "has_message_id"}
            assert ev.detail["has_message_id"] is True
        if ev.action == "email_sent":
            assert set(ev.detail) == {"request_id", "kind", "has_message_id"}
            assert ev.detail["kind"] == "opt_out"
        if ev.action == "email_failed":
            assert set(ev.detail) <= {"request_id", "error", "transient", "attempt"}
            assert ev.detail["error"].isidentifier()


def test_sockets_cannot_connect():
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


def test_crash_between_send_and_record_sends_no_duplicate(store, caplog):
    """The mailer accepted the first letter; the SENT row did not land. Next pass records
    it and sends only the letter that never reached the mailer."""
    caplog.set_level(logging.INFO)
    profile, (first, second) = _ready(store, "fakea", "fakeb")
    stamp = utcnow()
    mailer = CountingMailer()
    crashing = _CrashStore(store, "sent")
    with pytest.raises(RuntimeError, match="crash between send and record"):
        outbox.drain(crashing, profile, mailer, now=stamp)
    assert crashing.raised is True
    assert mailer.ids == [first.id]
    saved = store.get_request(first.id)
    assert saved is not None and saved.status == RequestStatus.QUEUED_FOR_APPROVAL
    assert len(_rows(store, profile.id, first.broker_id, outbox.HANDOFF_ACTION)) == 1
    assert _rows(store, profile.id, first.broker_id, "email_sent") == []
    assert len(_sent_blobs(store, profile.id, first.broker_id, first.id)) == 1
    untouched = store.get_request(second.id)
    assert untouched is not None and untouched.status == RequestStatus.QUEUED_FOR_APPROVAL
    assert _rows(store, profile.id, second.broker_id, outbox.HANDOFF_ACTION) == []

    # The runner's next queue_email is the same recovery: record, do not send.
    fresh = CountingMailer()
    recorded = outbox.queue_email(store, profile, _broker("fakea"), [], dry_run=False,
                                  mailer=fresh, now=stamp + timedelta(hours=5))
    assert fresh.ids == []
    assert recorded.id == first.id and recorded.status == RequestStatus.SENT
    assert recorded.sent_at == stamp
    assert len(_sent_blobs(store, profile.id, first.broker_id, first.id)) == 1
    assert len(_rows(store, profile.id, first.broker_id, "email_sent")) == 1

    # The letter that never reached the mailer goes out once on the next drain.
    nxt = CountingMailer()
    got = outbox.drain(store, profile, nxt)
    assert nxt.ids == [second.id]
    assert got == {"sent": 1, "recorded": 0, "failed": 0, "deferred": 0}
    assert store.get_request(second.id).status == RequestStatus.SENT
    assert len(_sent_blobs(store, profile.id, second.broker_id, second.id)) == 1
    assert len(_rows(store, profile.id, second.broker_id, outbox.HANDOFF_ACTION)) == 1
    assert len(_rows(store, profile.id, second.broker_id, "email_sent")) == 1

    again = CountingMailer()
    quiet = outbox.drain(store, profile, again)
    assert again.ids == []
    assert quiet == {"sent": 0, "recorded": 0, "failed": 0, "deferred": 0}
    assert len(_sent_blobs(store, profile.id, first.broker_id, first.id)) == 1
    assert "outbox code=already_handed count=1" in caplog.text
    assert "outbox code=email_sent count=1" in caplog.text
    assert "outbox drain sent=1 recorded=0 failed=0 deferred=0" in caplog.text
    _codes_only(store, profile.id, caplog)


def test_crash_before_the_sent_blob_still_records_once(store, caplog):
    """Raising on the sent-mail blob, after the mailer returned, still does not resend."""
    caplog.set_level(logging.INFO)
    profile, (req,) = _ready(store, "fakec")
    mailer = CountingMailer()
    crashing = _CrashStore(store, "evidence")
    with pytest.raises(RuntimeError, match="crash between send and record"):
        outbox.drain(crashing, profile, mailer)
    assert mailer.ids == [req.id]
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert _sent_blobs(store, profile.id, req.broker_id, req.id) == []
    assert len(_rows(store, profile.id, req.broker_id, outbox.HANDOFF_ACTION)) == 1

    nxt = CountingMailer()
    got = outbox.drain(store, profile, nxt)
    assert nxt.ids == []
    assert got == {"sent": 0, "recorded": 1, "failed": 0, "deferred": 0}
    assert store.get_request(req.id).status == RequestStatus.SENT
    assert len(_sent_blobs(store, profile.id, req.broker_id, req.id)) == 1
    assert len(_rows(store, profile.id, req.broker_id, "email_sent")) == 1
    assert len(_rows(store, profile.id, req.broker_id, outbox.HANDOFF_ACTION)) == 1

    quiet = outbox.drain(store, profile, CountingMailer())
    assert quiet["sent"] == 0 and quiet["recorded"] == 0
    assert len(_sent_blobs(store, profile.id, req.broker_id, req.id)) == 1
    _codes_only(store, profile.id, caplog)


def test_message_that_never_reached_the_mailer_is_sent_next_run(store, caplog):
    """A send that raises never counts as handed off. Backoff still applies, then it goes."""
    caplog.set_level(logging.INFO)
    profile, (req,) = _ready(store, "faked")

    class Boom:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, _profile, _to, _subject, _body, _request_id: str) -> str:
            self.calls += 1
            raise TimeoutError("down")

    boom = Boom()
    failed = outbox.drain(store, profile, boom)
    assert boom.calls == 1
    # A 1st transient failure stays queued for a retry: deferred, not failed (CodeRabbit #104).
    assert failed == {"sent": 0, "recorded": 0, "failed": 0, "deferred": 1}
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    assert _rows(store, profile.id, req.broker_id, outbox.HANDOFF_ACTION) == []
    anchor = utcnow()
    early = CountingMailer()
    held = outbox.drain(store, profile, early, now=anchor + timedelta(minutes=14))
    assert early.ids == []
    assert held["deferred"] == 1 and held["sent"] == 0 and held["recorded"] == 0
    later = CountingMailer()
    done = outbox.drain(store, profile, later, now=anchor + timedelta(minutes=16))
    assert later.ids == [req.id]
    assert done["sent"] == 1 and done["recorded"] == 0
    assert store.get_request(req.id).status == RequestStatus.SENT
    assert len(_sent_blobs(store, profile.id, req.broker_id, req.id)) == 1
    _codes_only(store, profile.id, caplog)


def test_drain_leaves_unapproved_mail_queued(store):
    profile = make_profile(mailbox=MB)
    store.save_profile(profile)
    req = outbox.queue_email(store, profile, _broker("fakeap"), [], dry_run=False, mailer=None)
    mailer = CountingMailer()
    got = outbox.drain(store, profile, mailer)
    assert mailer.ids == []
    assert got == {"sent": 0, "recorded": 0, "failed": 0, "deferred": 0}
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
