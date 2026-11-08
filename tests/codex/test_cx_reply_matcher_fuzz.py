"""Bounded adversarial inputs for the pure broker-reply matcher.

All senders and links use reserved example domains. No mailbox or network is used.
"""
from __future__ import annotations

from random import Random
from urllib.parse import urlsplit

from freemyid.engine.mail import MAX_MESSAGE_BYTES, asks_for_id, scan_replies
from freemyid.models import Broker

_BROKER = Broker.model_validate(
    {
        "id": "fake_broker",
        "name": "Fake Broker",
        "url": "https://fakeb.example/",
        "category": "data_broker",
        "domains": ["fakeb.example"],
        "method": "email",
        "opt_out_email": "privacy@fakeb.example",
        "confirmation_domains": ["mail.fakeb.example"],
    }
)


def _raw(body: bytes, *, sender: bytes | None = b"no-reply@fakeb.example",
         content_type: bytes = b"text/plain; charset=utf-8",
         transfer_encoding: bytes | None = None, extra: tuple[bytes, ...] = ()) -> bytes:
    headers = list(extra)
    if sender is not None:
        headers.insert(0, b"From: " + sender)
    headers.extend((b"Content-Type: " + content_type,))
    if transfer_encoding is not None:
        headers.append(b"Content-Transfer-Encoding: " + transfer_encoding)
    return b"\r\n".join((*headers, b"", body))


def _assert_only_broker_hosts(links: list[str]) -> None:
    for link in links:
        host = urlsplit(link).hostname
        assert host is not None
        assert host == "fakeb.example" or host.endswith(".fakeb.example")


def test_bounded_fixed_seed_malformed_corpus_never_crashes_or_returns_other_hosts() -> None:
    """Keep the corpus deterministic and small enough for a normal unit-test run."""
    rng = Random(127)
    alphabet = b"abcXYZ012 <>.=\r\n\t"
    corpus = [
        _raw(b"", sender=None),
        _raw(b"Content-Type: text/html\r\n\r\n<a href=\"https://mail.fakeb.example/confirm?t=bad\">Go"),
        _raw(b"bad=QZ quoted-printable=\xff", transfer_encoding=b"quoted-printable"),
        _raw(b"\xff\xfe\x80opaque bytes", content_type=b"text/plain; charset=x-unknown-127"),
        _raw(
            b"--broken\r\nContent-Type: text/plain\r\n\r\nquoted body\r\n"
            b"-----Original Message-----\r\nFrom: fake sender\r\n"
            b"Please confirm https://mail.fakeb.example/confirm?t=quoted\r\n"
            b"--broken\r\nContent-Type: text/html\r\n<a href=\"https://fakeb.example/confirm?t=html\">Confirm</a>",
            content_type=b"multipart/alternative; boundary=broken",
        ),
    ]
    for index in range(48):
        body = bytes(rng.choice(alphabet) for _ in range(rng.randrange(1, 1025)))
        corpus.append(_raw(body, extra=(b"X-Fuzz-Case: " + str(index).encode("ascii"),)))

    for raw in corpus:
        result = scan_replies([raw], _BROKER)
        _assert_only_broker_hosts(result.links)
        assert result.messages in (0, 1)


def test_quoted_printable_confirmation_is_decoded_and_nested_quotes_are_bounded() -> None:
    raw = _raw(
        b"Please=20confirm=20this=20request:=20"
        b"https://mail.fakeb.example/confirm?t=qp\r\n"
        b"> On yesterday, a quoted message included https://mail.fakeb.example/cancel?t=old",
        transfer_encoding=b"quoted-printable",
    )

    result = scan_replies([raw], _BROKER)

    assert result.links == ["https://mail.fakeb.example/confirm?t=qp"]


def test_html_only_message_can_yield_only_an_allowed_confirmation_link() -> None:
    raw = _raw(
        b'<html><body><a href="https://mail.fakeb.example/confirm?t=html">Confirm</a>'
        b'<a href="https://mail.fakeb.example.attacker.invalid/confirm?t=bad">Confirm</a>'
        b"</body></html>",
        content_type=b"text/html; charset=utf-8",
    )

    result = scan_replies([raw], _BROKER)

    assert result.links == ["https://mail.fakeb.example/confirm?t=html"]


def test_lookalike_sender_domains_do_not_contribute_links() -> None:
    link = b"https://mail.fakeb.example/confirm?t=trusted-link-host"
    for sender in (b"no-reply@fakeb.example.attacker.invalid", b"no-reply@notfakeb.example"):
        result = scan_replies([_raw(link, sender=sender)], _BROKER)
        assert result.links == []


def test_oversized_message_is_ignored_for_id_requests_and_links() -> None:
    raw = _raw(
        b"Please send a copy of your photo ID. "
        b"https://mail.fakeb.example/confirm?t=oversized "
        + b"x" * (MAX_MESSAGE_BYTES + 1),
    )

    result = scan_replies([raw], _BROKER)

    assert len(raw) > MAX_MESSAGE_BYTES
    assert not asks_for_id(raw)
    assert result.links == []
    assert not result.id_requested
