"""WO-331: real From address, a time word near "extension", one parse per message.

Fake broker mail only (example domains). No mailbox and no network.
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
    claims_extension,
    scan_replies,
    sender_domain,
)
from freemyid.models import Broker

_BROKER = Broker.model_validate({
    "id": "fake_broker",
    "name": "Fake Broker",
    "url": "https://fakeb.example/",
    "category": "data_broker",
    "domains": ["fakeb.example"],
    "method": "email",
    "opt_out_email": "privacy@fakeb.example",
    "confirmation_domains": ["mail.fakeb.example"],
})

_LINK = "https://mail.fakeb.example/confirm?t=1"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch, freemyid_env):
    """socket.connect and create_connection raise, so a stray network call fails the test."""
    del freemyid_env

    def refuse(*_args, **_kwargs):
        raise AssertionError("network is disabled")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _raw(body: str, *, sender: str = "Fake Broker <privacy@fakeb.example>",
         mid: str | None = None) -> bytes:
    lines = [
        f"From: {sender}",
        "To: removals@example.org",
        "Subject: Your request",
        "Content-Type: text/plain; charset=utf-8",
    ]
    if mid is not None:
        lines.append(f"Message-ID: {mid}")
    return ("\r\n".join(lines) + "\r\n\r\n" + body).encode()


def _count_parses(monkeypatch):
    seen: list[bytes] = []
    real = mail_mod.email.message_from_bytes

    def counting(data, *args, **kwargs):
        seen.append(data if isinstance(data, bytes) else bytes(data))
        return real(data, *args, **kwargs)

    monkeypatch.setattr(mail_mod.email, "message_from_bytes", counting)
    return seen


def test_sockets_cannot_connect():
    with pytest.raises(AssertionError, match="network is disabled"):
        socket.create_connection(("example.invalid", 9))
    sock = socket.socket()
    try:
        with pytest.raises(AssertionError, match="network is disabled"):
            sock.connect(("example.invalid", 9))
    finally:
        sock.close()


def test_reply_scan_fields_stay_in_order():
    assert [item.name for item in fields(ReplyScan)] == [
        "links", "id_requested", "extension_claimed", "messages",
        "duplicates", "stale", "replies",
    ]


def test_sender_domain_uses_the_angle_address_not_the_display_name(caplog):
    caplog.set_level(logging.DEBUG)
    sender = '"privacy@broker.example" <x@attacker.example>'
    raw = _raw(f"Confirm {_LINK}", sender=sender)
    assert sender_domain(raw) == "attacker.example"
    scan = scan_replies([raw], _BROKER)
    assert scan.messages == 0
    assert scan.links == []
    for secret in ("attacker.example", "privacy@broker.example", "confirm?t=1"):
        assert secret not in caplog.text


def test_display_name_at_sign_does_not_hide_the_real_broker():
    raw = _raw(
        f"Confirm {_LINK}",
        sender='"privacy@other.example" <Privacy@FakeB.Example>',
    )
    assert sender_domain(raw) == "fakeb.example"
    assert scan_replies([raw], _BROKER).links == [_LINK]


@pytest.mark.parametrize(("text", "claimed"), [
    ("we are taking a 45-day extension", True),
    ("we need additional time", True),
    ("call us at ext. 204", False),
    ("phone extension 12", False),
    ("install our browser extension", False),
])
def test_extension_needs_a_nearby_time_word(text, claimed):
    raw = _raw(text)
    assert claims_extension(raw) is claimed
    assert scan_replies([raw], _BROKER).extension_claimed is claimed


def test_claims_extension_uses_the_same_size_cap(monkeypatch):
    base = _raw("we are taking a 45-day extension")
    # A newline keeps "extension" a whole word; the pad must not glue onto it.
    pad = b"\n" + b"z" * (MAX_MESSAGE_BYTES - len(base) - 1)
    exact = base + pad
    over = exact + b"z"
    assert len(exact) == MAX_MESSAGE_BYTES
    assert claims_extension(exact) is True

    seen = _count_parses(monkeypatch)
    assert claims_extension(over) is False
    assert seen == []
    scan = scan_replies([over], _BROKER)
    assert scan.extension_claimed is False
    assert scan.links == []
    assert scan.messages == 1
    assert seen == [over[:65536]]


def test_scan_replies_parses_each_message_once(monkeypatch):
    small = _raw(f"Confirm {_LINK}", mid="<small@fakeb.example>")
    big = _raw(
        ("y" * 70_000) + " we are taking a 45-day extension",
        mid="<big@fakeb.example>",
    )
    spoof = _raw(
        f"Confirm {_LINK.replace('t=1', 't=spoof')}",
        sender='"privacy@broker.example" <x@attacker.example>',
    )
    assert len(small) < 65536 < len(big) <= MAX_MESSAGE_BYTES
    raws = [small, big, small, spoof]
    seen = _count_parses(monkeypatch)

    scan = scan_replies(raws, _BROKER)
    assert seen == raws
    scan_replies(raws, _BROKER)
    assert seen == raws + raws

    assert scan.links == [_LINK]
    assert scan.extension_claimed is True
    assert scan.duplicates == 1
    assert scan.messages == 2
    assert scan.id_requested is False
