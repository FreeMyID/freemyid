"""TLS for the removal mailbox, with certificate PINNING for local bridges.

Proton Mail Bridge runs on the user's own computer (127.0.0.1) and serves a self-signed
certificate, so normal CA verification always fails. We never switch verification off.
Instead the user confirms the certificate once (trust on first use) and its SHA-256
fingerprint is saved in `MailboxConfig.tls_cert_sha256`. On every connection:

* no pin           -> `ssl.create_default_context()` (full CA + hostname checks, unchanged);
* pin + loopback   -> handshake, then the peer's DER leaf certificate is hashed and compared
                      to the pin in constant time BEFORE any login/credential is sent;
                      a mismatch aborts the connection;
* pin + any other host -> refused with a clear error (pins are only for local bridges;
                      a real mail provider must pass normal verification).
"""
from __future__ import annotations

import contextlib
import hashlib
import hmac
import imaplib
import smtplib
import ssl
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..models import MailboxConfig

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class TlsPinError(RuntimeError):
    """Pin refused or mismatched. Message is short, plain-language and PII-free."""


def is_loopback(host: str) -> bool:
    return host.strip().lower().rstrip(".").strip("[]") in LOOPBACK_HOSTS


def fingerprint(der: bytes) -> str:
    """Lowercase hex SHA-256 of a DER certificate (the format stored as the pin)."""
    return hashlib.sha256(der).hexdigest()


def format_fingerprint(fp: str) -> str:
    """'ab12cd..' -> 'AB:12:CD:..' (how certificate viewers and Bridge show it)."""
    fp = fp.upper()
    return ":".join(fp[i:i + 2] for i in range(0, len(fp), 2))


def _unverified_context() -> ssl.SSLContext:
    """Handshake-only context. ONLY used where the peer certificate is checked against a
    pin before anything is sent (`client_context` with a pin) or where nothing but the
    certificate is read (`fetch_loopback_fingerprint`). Never returned for an unpinned
    connection that carries credentials."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE   # authenticity comes from the pin check instead
    return ctx


def client_context(host: str, pin: str | None) -> ssl.SSLContext:
    """TLS context for connecting to `host`. Callers MUST call `check_peer(sock, pin)`
    after the handshake when `pin` is set, before sending credentials."""
    if pin is None:
        return ssl.create_default_context()
    if not is_loopback(host):
        raise TlsPinError("a certificate pin is only allowed for a mail app on this "
                          "computer (127.0.0.1, ::1 or localhost); remove the pin or use "
                          "the provider's normal settings")
    if len(pin) != 64:
        raise TlsPinError("saved certificate fingerprint is malformed")
    return _unverified_context()


def check_peer(sock: object, pin: str | None) -> None:
    """Raise TlsPinError unless the TLS peer certificate's SHA-256 equals `pin`.
    No-op without a pin (the default context already verified the peer)."""
    if pin is None:
        return
    get = getattr(sock, "getpeercert", None)
    der = get(binary_form=True) if get else None
    if not der:
        raise TlsPinError("mail connection is not encrypted; refusing to sign in")
    if not hmac.compare_digest(fingerprint(der).encode(), pin.lower().encode()):
        raise TlsPinError("the mail app's security certificate changed and does not match "
                          "the one you approved; not signing in")


# ------------------------------------------------------------------ trust on first use
def fetch_loopback_fingerprint(host: str, port: int, protocol: Literal["imap", "smtp"],
                               *, starttls: bool, timeout_s: float = 10.0) -> str:
    """Connect to a LOCAL mail app (e.g. Proton Bridge), read its certificate and return the
    SHA-256 fingerprint for the user to confirm. Sends no username or password."""
    if not is_loopback(host):
        raise TlsPinError("only a mail app on this computer can be trusted this way")
    ctx = _unverified_context()
    sock: object
    try:
        if protocol == "imap":
            if starttls:
                conn = imaplib.IMAP4(host, port, timeout=timeout_s)
                conn.starttls(ssl_context=ctx)
            else:
                conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=timeout_s)
            sock = conn.sock
            der = sock.getpeercert(binary_form=True)  # type: ignore[attr-defined]
            with contextlib.suppress(Exception):
                conn.logout()
        else:
            if starttls:
                s = smtplib.SMTP(host, port, timeout=timeout_s)
                s.starttls(context=ctx)
            else:
                s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=timeout_s)
            der = s.sock.getpeercert(binary_form=True)  # type: ignore[union-attr]
            with contextlib.suppress(Exception):
                s.quit()
    except (OSError, imaplib.IMAP4.error, smtplib.SMTPException) as e:
        raise TlsPinError(f"could not reach the mail app ({type(e).__name__}); "
                          "is it running?") from None
    if not der:
        raise TlsPinError("the mail app did not offer a certificate")
    return fingerprint(der)


@dataclass
class TrustResult:
    fingerprint: str            # lowercase hex, ready for MailboxConfig.tls_cert_sha256
    display: str                # 'AB:12:..' for showing to the user
    message: str                # plain-language prompt for the confirm screen


def trust_on_first_use(mb: MailboxConfig, timeout_s: float = 10.0) -> TrustResult:
    """Read the certificate of a local mail app from both the IMAP and SMTP ports.
    The caller shows `message` and saves `fingerprint` only after the user says yes.
    Both ports must present the same certificate (Proton Bridge does)."""
    imap_fp = fetch_loopback_fingerprint(
        mb.imap_host, mb.imap_port, "imap",
        starttls=mb.imap_starttls or not mb.imap_ssl, timeout_s=timeout_s)
    smtp_fp = fetch_loopback_fingerprint(
        mb.smtp_host, mb.smtp_port, "smtp", starttls=mb.smtp_starttls, timeout_s=timeout_s)
    if not hmac.compare_digest(imap_fp, smtp_fp):
        raise TlsPinError("the mail app uses two different certificates; "
                          "this setup is not supported")
    shown = format_fingerprint(imap_fp)
    msg = ("Free My ID found the mail app on this computer (for example Proton Mail Bridge). "
           "Its security code is:\n\n" + shown + "\n\n"
           "If you just installed and started Proton Mail Bridge yourself, click Yes to "
           "trust it. Free My ID will remember this code and refuse to sign in if it "
           "ever changes.")
    return TrustResult(imap_fp, shown, msg)
