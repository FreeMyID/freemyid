"""WO-341: classify one already-accepted broker reply into a code.

Fake broker wording only (example domains). No mailbox and no network.
"""
from __future__ import annotations

import logging
import socket
from dataclasses import fields

import pytest

from freemyid.engine import mail as mail_mod
from freemyid.engine.mail import (
    MAX_MESSAGE_BYTES,
    ReplyScan,
    asks_for_id,
    claims_extension,
    classify_reply,
)

_CODES = {"confirmed", "denied", "needs_id", "needs_more_time", "unknown"}

# phrase, code. Ambiguous rows must stay unknown (never confirmed).
_CASES = [
    ("we have removed", "confirmed"),
    ("We have removed your listing.", "confirmed"),
    ("We've removed your record.", "confirmed"),
    ("We have successfully removed your data.", "confirmed"),
    ("Your information has been deleted.", "confirmed"),
    ("The opt-out is complete.", "confirmed"),
    ("We have removed your listing from our site.", "confirmed"),
    ("unable to locate your record", "denied"),
    ("We were unable to locate your record in our database.", "denied"),
    ("We could not find your listing.", "denied"),
    ("No record was found.", "denied"),
    ("Your request was denied.", "denied"),
    ("We don't have your information.", "denied"),
    ("please verify your identity", "needs_id"),
    ("Please confirm your identity before we continue.", "needs_id"),
    ("Please reply with a copy of your government-issued photo ID.", "needs_id"),
    ("We need a scan of your driver's license.", "needs_id"),
    ("Provide the last four digits of your Social Security number.", "needs_id"),
    ("we need 45 more days", "needs_more_time"),
    ("We need 45 more days to finish your request.", "needs_more_time"),
    ("We need additional time.", "needs_more_time"),
    ("We are taking a 45-day extension.", "needs_more_time"),
    ("Thank you for your request.", "unknown"),
    ("Please confirm your email address.", "unknown"),
    ("We will remove your listing.", "unknown"),
    ("We have not removed your listing.", "unknown"),
    ("We may have removed your listing.", "unknown"),
    ("Have we removed your record?", "unknown"),
    ("If we have removed your record, you will see a note.", "unknown"),
    ("We have removed the fee.", "unknown"),
    ("We have removed nothing.", "unknown"),
    ("phone extension 12", "unknown"),
    ("install our browser extension", "unknown"),
    ("We have removed your listing. Please verify your identity.", "unknown"),
    ("We have removed your listing. We need 45 more days.", "unknown"),
    ("We have removed your listing. We were unable to locate your record.", "unknown"),
    ("We have removed your listing. We have not removed the copies.", "unknown"),
    ("   ", "unknown"),
    # CodeRabbit #103/#134 (PR #120): plain text the RFC822 parser would misread as headers.
    ("  We have removed your listing.", "confirmed"),
    ("Update: we have removed your listing.", "confirmed"),
    ("Update: We have not removed your listing.\n\nWe have removed your listing.", "unknown"),
    ("Note: we have removed your listing.\nStatus: we have not removed the copies.",
     "unknown"),
]


@pytest.fixture(autouse=True)
def _no_network(monkeypatch, freemyid_env):
    """socket.connect and create_connection raise, so a stray network call fails the test."""
    del freemyid_env

    def refuse(*_args, **_kwargs):
        raise AssertionError("network is disabled")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _mail(body: str, *, html: bool = False) -> bytes:
    kind = "text/html; charset=utf-8" if html else "text/plain; charset=utf-8"
    payload = f"<p>{body}</p>" if html else body
    text = (
        "From: Fake Broker <privacy@fakeb.example>\r\n"
        "To: removals@example.org\r\n"
        "Subject: Your request\r\n"
        f"Content-Type: {kind}\r\n"
        "\r\n"
        f"{payload}"
    )
    return text.encode()


def test_sockets_cannot_connect():
    with pytest.raises(AssertionError, match="network is disabled"):
        socket.create_connection(("example.invalid", 9))
    sock = socket.socket()
    try:
        with pytest.raises(AssertionError, match="network is disabled"):
            sock.connect(("example.invalid", 9))
    finally:
        sock.close()


def test_reply_scan_is_unchanged():
    assert [item.name for item in fields(ReplyScan)] == [
        "links", "id_requested", "extension_claimed", "messages",
        "duplicates", "stale", "replies",
    ]
    assert fields(ReplyScan)[-1].repr is False


@pytest.mark.parametrize(("text", "code"), _CASES)
@pytest.mark.parametrize("kind", ["str", "bytes", "mail"])
def test_classify_reply_table(text, code, kind):
    if kind == "str":
        got = classify_reply(text)
    elif kind == "bytes":
        got = classify_reply(text.encode())
    else:
        got = classify_reply(_mail(text))
    assert got == code
    assert got in _CODES
    assert "Jane" not in got
    assert "@" not in got


def test_html_removal_is_confirmed():
    raw = _mail("We have removed your listing.", html=True)
    assert classify_reply(raw) == "confirmed"


def test_identity_phrase_is_not_the_document_helper():
    raw = _mail("please verify your identity")
    assert asks_for_id(raw) is False
    assert classify_reply(raw) == "needs_id"


def test_forty_five_more_days_is_not_the_extension_helper():
    raw = _mail("we need 45 more days")
    assert claims_extension(raw) is False
    assert classify_reply(raw) == "needs_more_time"


def test_extension_helper_still_counts_as_more_time():
    raw = _mail("We need additional time.")
    assert claims_extension(raw) is True
    assert classify_reply(raw) == "needs_more_time"


def test_result_and_logs_carry_no_message_text(caplog):
    caplog.set_level(logging.DEBUG)
    text = (
        "Jane Q Testperson in Springfield IL: we have removed your listing. "
        "Reply to removals@example.org."
    )
    got = classify_reply(text)
    assert got == "confirmed"
    for secret in ("Jane", "Testperson", "Springfield", "example.org", "removed", "listing"):
        assert secret not in got
        assert secret not in caplog.text


@pytest.mark.parametrize("text", ["", "   ", "\n\n", b"", b"   ", b"\r\n"])
def test_empty_is_unknown(text):
    assert classify_reply(text) == "unknown"


def test_huge_binary_and_empty_are_unknown_and_not_parsed(monkeypatch):
    seen: list[bytes] = []
    real = mail_mod.email.message_from_bytes

    def counting(data, *args, **kwargs):
        seen.append(data if isinstance(data, bytes) else bytes(data))
        return real(data, *args, **kwargs)

    monkeypatch.setattr(mail_mod.email, "message_from_bytes", counting)
    huge = b"we have removed\n" + b"x" * MAX_MESSAGE_BYTES
    assert len(huge) > MAX_MESSAGE_BYTES
    assert classify_reply(huge) == "unknown"
    assert classify_reply(huge.decode()) == "unknown"
    assert classify_reply(b"\xff\xfewe have removed") == "unknown"
    assert classify_reply(b"we have removed\x00tail") == "unknown"
    assert classify_reply(b"") == "unknown"
    assert classify_reply("we have removed\x01") == "unknown"
    assert seen == []


def test_exact_cap_can_still_confirm():
    # The period keeps the padding in a later sentence, so the cap still classifies.
    prefix = b"we have removed.\n"
    raw = prefix + b"y" * (MAX_MESSAGE_BYTES - len(prefix))
    assert len(raw) == MAX_MESSAGE_BYTES
    assert classify_reply(raw) == "confirmed"
    assert classify_reply(raw.decode()) == "confirmed"


def test_unreadable_message_is_unknown(monkeypatch):
    def boom(*_args, **_kwargs):
        raise ValueError("header")

    monkeypatch.setattr(mail_mod.email, "message_from_bytes", boom)
    assert classify_reply(b"we have removed") == "unknown"
