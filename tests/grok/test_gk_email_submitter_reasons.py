"""WO-348: a failed email submit returns a plain reason and does not raise.

Fake people only (Jane Q Testperson, Springfield IL). No network and no real mailbox.
"""
from __future__ import annotations

import smtplib
import socket
from datetime import UTC, datetime

import pytest

from freemyid.engine.mail import FakeMailer, MailError
from freemyid.interfaces import RunContext
from freemyid.models import (
    Broker,
    EmailMode,
    ListingState,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    SubmitOutcome,
    TodoKind,
)
from freemyid.netpolicy import NetPolicy
from freemyid.submitters.email import (
    REASON_CONNECTION,
    REASON_FIRST,
    REASON_MAILER,
    REASON_REFUSED,
    EmailSubmitter,
)
from tests.conftest import make_profile

RECIPIENT = "privacy@wo348.example"
NOW = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
MB_ADDRESS = "removals@example.org"


class _Quiet:
    def notify(self, title: str, body: str, url: str | None = None) -> None:
        return None

    async def request(self, todo: object, page: object, timeout_s: int = 900) -> bool:
        return False


class RaisingMailer:
    """Fake mailer: records the attempt, then fails. Never opens a socket."""

    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.calls = 0
        self.last_to = ""

    def send(self, profile: object, to: str, subject: str, body: str, request_id: str) -> str:
        self.calls += 1
        self.last_to = to
        raise self.exc


@pytest.fixture(autouse=True)
def _block_sockets(monkeypatch: pytest.MonkeyPatch, freemyid_env: object) -> None:
    """After the shared guard, both socket entry points raise. Loopback included."""
    def _raise(*_a: object, **_k: object) -> None:
        raise AssertionError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", _raise)
    monkeypatch.setattr(socket, "create_connection", _raise)


def _mailbox():
    from freemyid.models import MailboxConfig
    return MailboxConfig(address=MB_ADDRESS, imap_host="imap.example.org",
                         smtp_host="smtp.example.org", username=MB_ADDRESS)


def _person(store, *, mode: EmailMode = EmailMode.AUTO):
    profile = make_profile(label="Jane Q Testperson", mailbox=_mailbox(), email_mode=mode)
    store.save_profile(profile)
    return profile


def _broker() -> Broker:
    return Broker.model_validate({
        "id": "wo348", "name": "Example Broker", "url": "https://wo348.example/",
        "category": "data_broker", "domains": ["wo348.example"], "method": "email",
        "opt_out_email": RECIPIENT,
    })


def _open_gate(store, profile, broker) -> None:
    store.save_request(Request(
        profile_id=profile.id, broker_id=broker.id, kind=RequestKind.OPT_OUT,
        method=Method.EMAIL, status=RequestStatus.SENT, created_at=NOW, sent_at=NOW,
    ))


def _ctx(store, profile, broker, mailer, *, dry_run: bool = False) -> RunContext:
    return RunContext(
        profile=profile, broker=broker, store=store, netpolicy=NetPolicy(None),
        handoff=_Quiet(), notifier=_Quiet(), mailer=mailer, dry_run=dry_run,
        interactive=False, now=NOW,
    )


def _reason_text(out: SubmitOutcome) -> str:
    parts = [out.message]
    if out.request is not None and out.request.reference:
        parts.append(out.request.reference)
    for todo in out.todos:
        parts.extend([todo.title, todo.body, todo.resume_token or ""])
        parts.extend(todo.links)
        parts.extend(todo.copy_fields.values())
    return "\n".join(parts)


def _assert_not_sent(out: SubmitOutcome, reason: str) -> None:
    assert out.message == f"not sent: {reason}"
    assert "not sent" in out.message
    assert reason in out.message
    assert out.new_state != ListingState.SUBMITTED
    assert out.request is None or out.request.status != RequestStatus.SENT
    assert out.todos
    text = _reason_text(out)
    assert RECIPIENT not in text
    assert "@" not in out.message
    assert MB_ADDRESS not in text


async def _submit(store, mailer, *, mode: EmailMode = EmailMode.AUTO, opened: bool = False,
                  dry_run: bool = False):
    profile = _person(store, mode=mode)
    broker = _broker()
    if opened:
        _open_gate(store, profile, broker)
    out = await EmailSubmitter().submit(
        _ctx(store, profile, broker, mailer, dry_run=dry_run), [])
    return out, profile, broker


@pytest.mark.parametrize("exc", [
    MailError("mailbox password not in keychain"),
    MailError("smtp failed: SMTPAuthenticationError"),
])
async def test_mailer_not_set_up(store, exc: BaseException) -> None:
    mailer = RaisingMailer(exc)
    out, profile, broker = await _submit(store, mailer, opened=True)
    _assert_not_sent(out, REASON_MAILER)
    assert mailer.calls == 1
    assert out.request is None
    assert out.new_state == ListingState.NEEDS_HUMAN
    assert "mailbox" in out.todos[0].body and "password" in out.todos[0].body
    failed = [r for r in store.list_requests(profile.id, broker.id)
              if r.status == RequestStatus.FAILED]
    assert len(failed) == 1
    assert mailer.last_to == RECIPIENT


async def test_missing_mailer_when_a_send_is_due(store) -> None:
    out, _profile, _broker = await _submit(store, None, opened=True)
    _assert_not_sent(out, REASON_MAILER)
    assert out.request is None


@pytest.mark.parametrize("exc", [
    smtplib.SMTPRecipientsRefused({RECIPIENT: (550, b"5.1.1 refused")}),
    MailError("smtp failed: SMTPRecipientsRefused"),
])
async def test_refused_address(store, exc: BaseException) -> None:
    mailer = RaisingMailer(exc)
    out, profile, broker = await _submit(store, mailer, opened=True)
    _assert_not_sent(out, REASON_REFUSED)
    assert mailer.calls == 1
    assert "refused" in out.todos[0].body
    assert RECIPIENT in str(exc) or "SMTPRecipientsRefused" in str(exc)
    failed = store.list_requests(profile.id, broker.id, status=RequestStatus.FAILED)
    assert len(failed) == 1


@pytest.mark.parametrize("exc", [
    ConnectionError(f"timed out while contacting {RECIPIENT}"),
    MailError("smtp failed: TimeoutError"),
    OSError("down"),
])
async def test_connection_error(store, exc: BaseException) -> None:
    mailer = RaisingMailer(exc)
    out, _profile, _broker = await _submit(store, mailer, opened=True)
    _assert_not_sent(out, REASON_CONNECTION)
    assert mailer.calls == 1
    assert "connection" in out.todos[0].body
    assert out.message != f"not sent: {REASON_FIRST}"


async def test_first_email_approval_missing(store) -> None:
    mailer = RaisingMailer(ConnectionError(f"down {RECIPIENT}"))
    out, profile, broker = await _submit(store, mailer, opened=False)
    _assert_not_sent(out, REASON_FIRST)
    assert mailer.calls == 0
    assert out.request is not None
    assert out.request.status == RequestStatus.QUEUED_FOR_APPROVAL
    assert out.todos[0].kind == TodoKind.APPROVE_EMAIL
    assert "approve" in out.todos[0].body.lower()
    queued = store.list_requests(profile.id, broker.id,
                                 status=RequestStatus.QUEUED_FOR_APPROVAL)
    assert len(queued) == 1
    assert not store.list_requests(profile.id, broker.id, status=RequestStatus.FAILED)


async def test_approval_gate_is_distinct_from_a_connection_error(store) -> None:
    approval, _, _ = await _submit(
        store, RaisingMailer(ConnectionError(f"down {RECIPIENT}")), opened=False)
    connection, _, _ = await _submit(
        store, RaisingMailer(ConnectionError(f"down {RECIPIENT}")), opened=True)
    assert approval.message == f"not sent: {REASON_FIRST}"
    assert connection.message == f"not sent: {REASON_CONNECTION}"
    assert approval.message != connection.message
    assert REASON_CONNECTION not in approval.message
    assert REASON_FIRST not in connection.message
    assert RECIPIENT not in _reason_text(approval)
    assert RECIPIENT not in _reason_text(connection)


async def test_sent_queued_and_dry_run_are_unchanged(store) -> None:
    sent, profile, broker = await _submit(store, FakeMailer(), opened=True)
    assert sent.message == "email_sent"
    assert sent.todos == []
    assert sent.request is not None and sent.request.status == RequestStatus.SENT
    assert sent.new_state == ListingState.SUBMITTED
    assert RECIPIENT not in sent.message

    queued, _, _ = await _submit(store, FakeMailer(), mode=EmailMode.APPROVE_EACH)
    assert queued.message == "email_queued"
    assert queued.todos == []
    assert queued.request is not None
    assert queued.request.status == RequestStatus.QUEUED_FOR_APPROVAL
    assert queued.new_state == ListingState.FOUND

    draft, _, _ = await _submit(store, FakeMailer(), dry_run=True)
    assert draft.message == "email_draft"
    assert draft.todos == []
    assert draft.request is not None and draft.request.dry_run
    assert draft.request.status == RequestStatus.DRAFT
    assert store.list_requests(profile.id, broker.id, status=RequestStatus.SENT)
