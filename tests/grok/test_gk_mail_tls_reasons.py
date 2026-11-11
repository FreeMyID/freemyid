"""Reason codes for a mail connection that failed.

Jane Q Testperson, Springfield IL. The socket fixture blocks every connect,
including loopback. No mailbox and no subprocess.
"""
from __future__ import annotations

import errno
import imaplib
import smtplib
import socket
import ssl
from pathlib import Path

import pytest

from freemyid.engine.mail_tls import (
    REASON_AUTH_FAILED,
    REASON_CERT_EXPIRED,
    REASON_CERT_UNTRUSTED,
    REASON_HOSTNAME_MISMATCH,
    REASON_REFUSED,
    REASON_STARTTLS_NOT_OFFERED,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
    client_context,
    connection_failure_reason,
)

# Distinctive tokens. A reason that copies a banner will contain one of them.
HOST = "mail.jane-q-testperson.example"
USER = "jane.q.testperson"
PASSWORD = "springfield-il-not-a-secret"

_CODES = {
    REASON_CERT_EXPIRED: "cert_expired",
    REASON_CERT_UNTRUSTED: "cert_untrusted",
    REASON_HOSTNAME_MISMATCH: "hostname_mismatch",
    REASON_TIMEOUT: "timeout",
    REASON_REFUSED: "refused",
    REASON_AUTH_FAILED: "auth_failed",
    REASON_STARTTLS_NOT_OFFERED: "starttls_not_offered",
    REASON_UNKNOWN: "unknown",
}


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    """socket.connect and create_connection always raise, including localhost.

    Depending on freemyid_env runs this after that fixture's own connect patch.
    """
    del freemyid_env

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise OSError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_socket_helpers_raise() -> None:
    sock = socket.socket()
    try:
        with pytest.raises(OSError, match="network blocked"):
            sock.connect(("127.0.0.1", 9))
    finally:
        sock.close()
    with pytest.raises(OSError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


def _banner(body: str) -> str:
    return f"{body} {HOST} {USER} {PASSWORD}".strip()


def _cert(body: str, code: int | None = None) -> ssl.SSLCertVerificationError:
    message = _banner(body)
    exc = ssl.SSLCertVerificationError(message)
    if code is not None:
        exc.verify_code = code
        exc.verify_message = message
    return exc


def test_reason_codes_are_fixed_words() -> None:
    assert _CODES == {
        "cert_expired": "cert_expired",
        "cert_untrusted": "cert_untrusted",
        "hostname_mismatch": "hostname_mismatch",
        "timeout": "timeout",
        "refused": "refused",
        "auth_failed": "auth_failed",
        "starttls_not_offered": "starttls_not_offered",
        "unknown": "unknown",
    }
    assert len(set(_CODES.values())) == 8


def test_default_context_still_verifies_certificates() -> None:
    """No pin keeps full CA and hostname checks. Verification is not switched off."""
    for host in (HOST, "127.0.0.1"):
        ctx = client_context(host, None)
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True
        assert ctx.verify_mode != ssl.CERT_NONE
    fresh = ssl.create_default_context()
    made = client_context(HOST, None)
    assert made.verify_mode == fresh.verify_mode
    assert made.check_hostname is fresh.check_hostname


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        pytest.param(_cert("certificate has expired", 10), "cert_expired", id="expired-code"),
        pytest.param(
            _cert("certificate verify failed: certificate has expired"),
            "cert_expired", id="expired-text"),
        pytest.param(
            ssl.SSLError(_banner("certificate verify failed: certificate has expired")),
            "cert_expired", id="expired-sslerror"),
        pytest.param(_cert("self-signed certificate", 18), "cert_untrusted", id="self-signed"),
        pytest.param(
            _cert("unable to get local issuer certificate", 20),
            "cert_untrusted", id="untrusted-issuer"),
        pytest.param(
            _cert("certificate is not yet valid", 9), "cert_untrusted", id="not-yet-valid"),
        pytest.param(
            _cert("certificate verify failed: self-signed certificate"),
            "cert_untrusted", id="self-signed-text"),
        pytest.param(
            ssl.SSLError(_banner(
                "certificate verify failed: unable to get local issuer certificate")),
            "cert_untrusted", id="issuer-sslerror"),
        pytest.param(
            ssl.SSLCertVerificationError(_banner("unspecified")),
            "cert_untrusted", id="cert-unspecified"),
        pytest.param(_cert("Hostname mismatch", 62), "hostname_mismatch", id="hostname-code"),
        pytest.param(_cert("IP address mismatch", 64), "hostname_mismatch", id="ip-code"),
        pytest.param(
            _cert("Hostname mismatch, certificate is not valid for the server"),
            "hostname_mismatch", id="hostname-text"),
        pytest.param(
            ssl.SSLError(_banner("certificate verify failed: Hostname mismatch")),
            "hostname_mismatch", id="hostname-sslerror"),
        pytest.param(
            _cert("certificate has expired", 62), "hostname_mismatch", id="code-beats-text"),
        pytest.param(TimeoutError(_banner("timed out")), "timeout", id="timeout"),
        pytest.param(
            OSError(errno.ETIMEDOUT, _banner("connection timed out")), "timeout", id="etimedout"),
        pytest.param(
            ssl.SSLError(_banner("The handshake operation timed out")), "timeout", id="handshake"),
        pytest.param(
            ConnectionRefusedError(_banner("connection refused")), "refused", id="refused"),
        pytest.param(
            OSError(errno.ECONNREFUSED, _banner("connection refused")),
            "refused", id="econnrefused"),
        pytest.param(
            smtplib.SMTPAuthenticationError(
                535, _banner("535 5.7.8 authentication failed").encode()),
            "auth_failed", id="smtp-auth"),
        pytest.param(
            imaplib.IMAP4.error(_banner("AUTHENTICATIONFAILED Invalid credentials").encode()),
            "auth_failed", id="imap-auth"),
        pytest.param(
            imaplib.IMAP4.error(_banner("NO Login failed.")),
            "auth_failed", id="imap-login-failed"),
        pytest.param(
            smtplib.SMTPNotSupportedError(
                _banner("STARTTLS extension not supported by server.")),
            "starttls_not_offered", id="smtp-starttls"),
        pytest.param(
            imaplib.IMAP4.error(_banner("STARTTLS extension not supported by server.").encode()),
            "starttls_not_offered", id="imap-starttls"),
        pytest.param(
            smtplib.SMTPNotSupportedError(_banner("SMTPUTF8 not supported by server.")),
            "unknown", id="other-extension"),
        pytest.param(imaplib.IMAP4.error(_banner("STARTTLS")), "unknown", id="starttls-word-only"),
        pytest.param(
            imaplib.IMAP4.error(_banner("LOGIN command incomplete")), "unknown", id="login-word"),
        pytest.param(ssl.SSLError(_banner("WRONG_VERSION_NUMBER")), "unknown", id="protocol"),
        pytest.param(
            smtplib.SMTPServerDisconnected(_banner("Connection unexpectedly closed")),
            "unknown", id="smtp-disconnected"),
        pytest.param(ConnectionResetError(_banner("connection reset")), "unknown", id="reset"),
        pytest.param(RuntimeError(_banner("")), "unknown", id="runtime"),
    ],
)
def test_failure_reason_table(exc: BaseException, code: str) -> None:
    reason = connection_failure_reason(exc)
    assert reason == code
    assert reason in _CODES.values()
    assert HOST not in reason
    assert USER not in reason
    assert PASSWORD not in reason
    assert HOST not in str(reason) and USER not in str(reason) and PASSWORD not in str(reason)
