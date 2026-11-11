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

`connection_failure_reason` maps a connection or login exception to a short code.
The code is a fixed word. Host names, user names and server banners are left out.
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

# Never announce this computer's hostname (often the owner's name) in EHLO; also avoids a
# slow reverse lookup on macOS.
_EHLO_NAME = "localhost"

if TYPE_CHECKING:
    from ..models import MailboxConfig
    from ..netpolicy import NetPolicy

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
# The connected peer must be one of these EXACT addresses (SEC-50). The name `localhost` is
# accepted in settings, but the resolver decides where it goes, so it is never trusted on
# its own: what counts is the address the socket actually reached.
LOOPBACK_PEER_IPS = frozenset({"127.0.0.1", "::1"})


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


def check_loopback_peer(sock: object) -> None:
    """Raise TlsPinError unless the socket is connected to exactly 127.0.0.1 or ::1.
    Fails closed: no `getpeername`, an error, or an unexpected shape all refuse."""
    try:
        peer = sock.getpeername()[0]  # type: ignore[attr-defined]
    except (OSError, AttributeError, TypeError, IndexError, KeyError, ValueError):
        peer = None
    if not isinstance(peer, str) or peer not in LOOPBACK_PEER_IPS:
        raise TlsPinError("the mail app is not on this computer; not trusting it")


def check_peer(sock: object, pin: str | None) -> None:
    """Raise TlsPinError unless the TLS peer certificate's SHA-256 equals `pin` and the
    peer is an exact loopback address (SEC-50). No-op without a pin (the default context
    already verified the peer)."""
    if pin is None:
        return
    get = getattr(sock, "getpeercert", None)
    der = get(binary_form=True) if get else None
    if not der:
        raise TlsPinError("mail connection is not encrypted; refusing to sign in")
    check_loopback_peer(sock)
    if not hmac.compare_digest(fingerprint(der).encode(), pin.lower().encode()):
        raise TlsPinError("the mail app's security certificate changed and does not match "
                          "the one you approved; not signing in")


# ------------------------------------------------------------------ trust on first use
def _loopback_policy() -> NetPolicy:
    """Fallback for callers that do not pass a policy yet: the global config allowlist
    plus loopback. Combined with `is_loopback` it still only ever admits this computer."""
    from ..netpolicy import NetPolicy
    return NetPolicy(None, allow_loopback=True)


def fetch_loopback_fingerprint(host: str, port: int, protocol: Literal["imap", "smtp"],
                               *, starttls: bool, timeout_s: float = 10.0,
                               netpolicy: NetPolicy | None = None) -> str:
    """Connect to a LOCAL mail app (e.g. Proton Bridge), read its certificate and return the
    SHA-256 fingerprint for the user to confirm. Sends no username or password.
    The host must pass `netpolicy.is_allowed` before any socket opens (SEC-51)."""
    if not is_loopback(host):
        raise TlsPinError("only a mail app on this computer can be trusted this way")
    pol = netpolicy if netpolicy is not None else _loopback_policy()
    if not pol.is_allowed(host):
        raise TlsPinError("mail host not on allowlist")
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
            try:
                check_loopback_peer(sock)
                der = sock.getpeercert(binary_form=True)  # type: ignore[attr-defined]
            finally:
                with contextlib.suppress(Exception):
                    conn.logout()
        else:
            if starttls:
                s = smtplib.SMTP(host, port, timeout=timeout_s, local_hostname=_EHLO_NAME)
                s.starttls(context=ctx)
            else:
                s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=timeout_s, local_hostname=_EHLO_NAME)
            try:
                check_loopback_peer(s.sock)
                der = s.sock.getpeercert(binary_form=True)  # type: ignore[union-attr]
            finally:
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


def trust_on_first_use(mb: MailboxConfig, timeout_s: float = 10.0, *,
                       netpolicy: NetPolicy | None = None) -> TrustResult:
    """Read the certificate of a local mail app from both the IMAP and SMTP ports.
    The caller shows `message` and saves `fingerprint` only after the user says yes.
    Both ports must present the same certificate (Proton Bridge does).
    Pass the caller's `netpolicy` (SEC-51); both hosts are checked before connecting."""
    pol = netpolicy if netpolicy is not None else _loopback_policy()
    for h in (mb.imap_host, mb.smtp_host):
        if not is_loopback(h):
            raise TlsPinError("only a mail app on this computer can be trusted this way")
        if not pol.is_allowed(h):
            raise TlsPinError("mail host not on allowlist")
    imap_fp = fetch_loopback_fingerprint(
        mb.imap_host, mb.imap_port, "imap",
        starttls=mb.imap_starttls or not mb.imap_ssl, timeout_s=timeout_s, netpolicy=pol)
    smtp_fp = fetch_loopback_fingerprint(
        mb.smtp_host, mb.smtp_port, "smtp", starttls=mb.smtp_starttls, timeout_s=timeout_s,
        netpolicy=pol)
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


# ------------------------------------------------------------------ failure reasons
# X509_V_ERR_* from OpenSSL. The ssl module does not export them. Only the number is
# used: on a hostname mismatch, verify_message includes the server name.
_X509_HAS_EXPIRED = 10
_X509_NAME_MISMATCH = frozenset({62, 63, 64})  # hostname, email, IP

MailConnectReason = Literal[
    "cert_expired",
    "cert_untrusted",
    "hostname_mismatch",
    "timeout",
    "refused",
    "auth_failed",
    "starttls_not_offered",
    "unknown",
]

REASON_CERT_EXPIRED: MailConnectReason = "cert_expired"
REASON_CERT_UNTRUSTED: MailConnectReason = "cert_untrusted"
REASON_HOSTNAME_MISMATCH: MailConnectReason = "hostname_mismatch"
REASON_TIMEOUT: MailConnectReason = "timeout"
REASON_REFUSED: MailConnectReason = "refused"
REASON_AUTH_FAILED: MailConnectReason = "auth_failed"
REASON_STARTTLS_NOT_OFFERED: MailConnectReason = "starttls_not_offered"
REASON_UNKNOWN: MailConnectReason = "unknown"

_AUTH_MARKERS = (
    "authenticationfailed",
    "invalidcredentials",
    "loginfailed",
    "badcredentials",
    "passwordnotaccepted",
)
_STARTTLS_ABSENT = ("not supported", "not offered", "not available", "unknown command")


def _text(exc: BaseException) -> str:
    """Lowercased text of an exception. Never returned to a caller."""
    parts: list[str] = []
    for arg in exc.args:
        values: list[object] = list(arg) if isinstance(arg, (tuple, list)) else [arg]
        for value in values:
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, bytes):
                parts.append(value.decode("utf-8", "replace"))
            elif isinstance(value, (tuple, list)):
                for inner in value:
                    if isinstance(inner, str):
                        parts.append(inner)
                    elif isinstance(inner, bytes):
                        parts.append(inner.decode("utf-8", "replace"))
    message = getattr(exc, "verify_message", None)
    if isinstance(message, str):
        parts.append(message)
    return " ".join(parts).casefold()


def _reason_for_verify_code(exc: ssl.SSLCertVerificationError) -> MailConnectReason | None:
    code = getattr(exc, "verify_code", None)
    if not isinstance(code, int):
        return None
    if code in _X509_NAME_MISMATCH:
        return REASON_HOSTNAME_MISMATCH
    if code == _X509_HAS_EXPIRED:
        return REASON_CERT_EXPIRED
    return REASON_CERT_UNTRUSTED


def _reason_for_cert_text(text: str) -> MailConnectReason | None:
    if ("hostname mismatch" in text or "ip address mismatch" in text
            or "email address mismatch" in text):
        return REASON_HOSTNAME_MISMATCH
    if "certificate has expired" in text:
        return REASON_CERT_EXPIRED
    if ("self-signed" in text or "self signed" in text
            or "unable to get local issuer" in text
            or "unable to get issuer certificate" in text
            or "certificate untrusted" in text or "unknown ca" in text
            or "certificate verify failed" in text or "not yet valid" in text):
        return REASON_CERT_UNTRUSTED
    return None


def _auth_failed(text: str) -> bool:
    compact = "".join(ch for ch in text if ch.isalnum())
    return any(marker in compact for marker in _AUTH_MARKERS)


def _starttls_missing(text: str) -> bool:
    return "starttls" in text and any(phrase in text for phrase in _STARTTLS_ABSENT)


def _ssl_reason(exc: ssl.SSLError) -> MailConnectReason:
    if isinstance(exc, ssl.SSLCertVerificationError):
        coded = _reason_for_verify_code(exc)
        if coded is not None:
            return coded
    text = _text(exc)
    named = _reason_for_cert_text(text)
    if named is not None:
        return named
    if isinstance(exc, ssl.SSLCertVerificationError):
        return REASON_CERT_UNTRUSTED
    if "timed out" in text:
        return REASON_TIMEOUT
    return REASON_UNKNOWN


def connection_failure_reason(exc: BaseException) -> MailConnectReason:
    """Map one mail-connection exception to a short reason code.

    Codes: cert_expired, cert_untrusted, hostname_mismatch, timeout, refused,
    auth_failed, starttls_not_offered. Anything else is unknown.

    The return value is only that word. Exception text is not copied, because a
    server banner can include the mailbox name or the server name.
    """
    if isinstance(exc, ssl.SSLError):
        return _ssl_reason(exc)
    if isinstance(exc, TimeoutError):
        return REASON_TIMEOUT
    if isinstance(exc, ConnectionRefusedError):
        return REASON_REFUSED
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return REASON_AUTH_FAILED
    text = _text(exc)
    if isinstance(exc, smtplib.SMTPNotSupportedError):
        if _starttls_missing(text):
            return REASON_STARTTLS_NOT_OFFERED
        return REASON_UNKNOWN
    if isinstance(exc, imaplib.IMAP4.error):
        if _starttls_missing(text):
            return REASON_STARTTLS_NOT_OFFERED
        if _auth_failed(text):
            return REASON_AUTH_FAILED
        return REASON_UNKNOWN
    return REASON_UNKNOWN
