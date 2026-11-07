"""Certificate pinning for local mail bridges (Proton Bridge): a fake self-signed
STARTTLS/implicit-TLS IMAP + SMTP server on 127.0.0.1. Never disables verification
for unpinned hosts; credentials are never sent on a mismatch."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import ipaddress
import socket
import ssl
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from pydantic import ValidationError

from freemyid.engine.mail import MailError, SmtpImapMailer
from freemyid.engine.mail_tls import (
    TlsPinError,
    check_peer,
    client_context,
    fetch_loopback_fingerprint,
    fingerprint,
    format_fingerprint,
    is_loopback,
    trust_on_first_use,
)
from freemyid.models import MailboxConfig
from freemyid.netpolicy import NetPolicy

PASSWORD = "bridge-test-pw-31337"
WRONG_PIN = "0" * 64


def _self_signed(tmp_path, cn="127.0.0.1"):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.now(UTC)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=30))
            .add_extension(x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                critical=False)
            .sign(key, hashes.SHA256()))
    cp, kp = tmp_path / "cert.pem", tmp_path / "key.pem"
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cp, kp)
    return ctx, fingerprint(cert.public_bytes(serialization.Encoding.DER))


class FakeServer:
    """One protocol ('imap'|'smtp'), STARTTLS or implicit TLS. Records every byte received
    and every credential command, so tests can prove nothing leaked before the pin check."""

    def __init__(self, ctx: ssl.SSLContext, proto: str, starttls: bool) -> None:
        self.ctx, self.proto, self.starttls = ctx, proto, starttls
        self.received = bytearray()
        self.logins = 0
        self.lsock = socket.socket()
        self.lsock.bind(("127.0.0.1", 0))
        self.lsock.listen(8)
        self.lsock.settimeout(10)
        self.port = self.lsock.getsockname()[1]
        self._stop = False
        self.done = threading.Event()   # set when a client connection has been closed
        self.t = threading.Thread(target=self._serve, daemon=True)
        self.t.start()

    def close(self) -> None:
        self._stop = True
        with contextlib.suppress(OSError):
            self.lsock.close()

    def _serve(self) -> None:
        while not self._stop:
            try:
                c, _ = self.lsock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(c,), daemon=True).start()

    def _handle(self, c: socket.socket) -> None:
        c.settimeout(10)
        try:
            if not self.starttls:
                c = self.ctx.wrap_socket(c, server_side=True)
            f = c.makefile("rwb")
            (self._imap if self.proto == "imap" else self._smtp)(c, f)
        except (OSError, ssl.SSLError, ValueError):
            pass
        finally:
            with contextlib.suppress(OSError):
                c.close()
            self.done.set()

    def _lines(self, f):
        while True:
            line = f.readline()
            if not line:
                return
            self.received += line
            yield line

    def _imap(self, c, f) -> None:
        tls = not self.starttls
        f.write(b"* OK fake bridge ready\r\n")
        f.flush()
        for line in self._lines(f):
            tag, _, rest = line.decode().strip().partition(" ")
            cmd = rest.split(" ")[0].upper()
            if cmd == "CAPABILITY":
                caps = "IMAP4rev1 AUTH=PLAIN" if tls else "IMAP4rev1 STARTTLS LOGINDISABLED"
                f.write(f"* CAPABILITY {caps}\r\n{tag} OK done\r\n".encode())
            elif cmd == "STARTTLS":
                f.write(f"{tag} OK begin TLS\r\n".encode())
                f.flush()
                c = self.ctx.wrap_socket(c, server_side=True)
                f = c.makefile("rwb")
                self._imap_tls(c, f)
                return
            else:
                self._imap_cmd(f, tag, cmd)
            f.flush()

    def _imap_tls(self, c, f) -> None:
        for line in self._lines(f):
            tag, _, rest = line.decode().strip().partition(" ")
            cmd = rest.split(" ")[0].upper()
            if cmd == "CAPABILITY":
                f.write(f"* CAPABILITY IMAP4rev1 AUTH=PLAIN\r\n{tag} OK done\r\n".encode())
            else:
                self._imap_cmd(f, tag, cmd)
            f.flush()
            if cmd == "LOGOUT":
                return

    def _imap_cmd(self, f, tag: str, cmd: str) -> None:
        if cmd == "LOGIN":
            self.logins += 1
            f.write(f"{tag} OK logged in\r\n".encode())
        elif cmd in ("SELECT", "EXAMINE"):
            f.write(f"* 0 EXISTS\r\n{tag} OK [READ-ONLY] done\r\n".encode())
        elif cmd == "SEARCH":
            f.write(f"* SEARCH\r\n{tag} OK done\r\n".encode())
        elif cmd == "LOGOUT":
            f.write(f"* BYE\r\n{tag} OK bye\r\n".encode())
        else:
            f.write(f"{tag} BAD unknown\r\n".encode())

    def _smtp(self, c, f) -> None:
        tls = not self.starttls
        f.write(b"220 fake bridge ESMTP\r\n")
        f.flush()
        in_data = False
        for line in self._lines(f):
            if in_data:
                if line in (b".\r\n", b".\n"):
                    in_data = False
                    f.write(b"250 queued\r\n")
                    f.flush()
                continue
            cmd = line.decode().strip().split(" ")[0].upper()
            if cmd in ("EHLO", "HELO"):
                extra = "" if tls else "250-STARTTLS\r\n"
                f.write(f"250-fake\r\n{extra}250 AUTH PLAIN LOGIN\r\n".encode())
            elif cmd == "STARTTLS" and not tls:
                f.write(b"220 go ahead\r\n")
                f.flush()
                c = self.ctx.wrap_socket(c, server_side=True)
                f = c.makefile("rwb")
                self._smtp_after(f)
                return
            else:
                in_data = self._smtp_cmd(f, cmd)
            f.flush()

    def _smtp_after(self, f) -> None:
        in_data = False
        for line in self._lines(f):
            if in_data:
                if line in (b".\r\n", b".\n"):
                    in_data = False
                    f.write(b"250 queued\r\n")
                    f.flush()
                continue
            cmd = line.decode().strip().split(" ")[0].upper()
            if cmd in ("EHLO", "HELO"):
                f.write(b"250-fake\r\n250 AUTH PLAIN LOGIN\r\n")
            else:
                in_data = self._smtp_cmd(f, cmd)
            f.flush()
            if cmd == "QUIT":
                return

    def _smtp_cmd(self, f, cmd: str) -> bool:
        if cmd == "AUTH":
            self.logins += 1
            f.write(b"235 ok\r\n")
        elif cmd in ("MAIL", "RCPT", "RSET", "NOOP"):
            f.write(b"250 ok\r\n")
        elif cmd == "DATA":
            f.write(b"354 go\r\n")
            return True
        elif cmd == "QUIT":
            f.write(b"221 bye\r\n")
        else:
            f.write(b"502 no\r\n")
        return False


@pytest.fixture
def server_ctx(tmp_path):
    return _self_signed(tmp_path)


@pytest.fixture
def servers(server_ctx):
    ctx, fp = server_ctx
    made: list[FakeServer] = []

    def make(proto: str, starttls: bool = True) -> FakeServer:
        s = FakeServer(ctx, proto, starttls)
        made.append(s)
        return s
    yield make, fp
    for s in made:
        s.close()


def _mailbox(imap: FakeServer | None = None, smtp: FakeServer | None = None,
             pin: str | None = None, host: str = "127.0.0.1") -> MailboxConfig:
    return MailboxConfig(
        address="removal@example.invalid", provider="proton_bridge",
        imap_host=host, imap_port=imap.port if imap else 1143,
        imap_ssl=not (imap.starttls if imap else True),
        imap_starttls=imap.starttls if imap else True,
        smtp_host=host, smtp_port=smtp.port if smtp else 1025,
        smtp_starttls=smtp.starttls if smtp else True,
        username="removal@example.invalid", tls_cert_sha256=pin)


def _mailer() -> SmtpImapMailer:
    return SmtpImapMailer(NetPolicy(None, allow_loopback=True),
                          password_getter=lambda pid, mb: PASSWORD, timeout_s=5)


def _profile(mb: MailboxConfig):
    return SimpleNamespace(id="p-test", mailbox=mb)


SINCE = datetime(2026, 1, 1, tzinfo=UTC)


# ------------------------------------------------------------------------------ model
def test_pin_validation_normalises_and_rejects():
    fp = "AB:" * 31 + "AB"
    assert _mailbox(pin=fp).tls_cert_sha256 == "ab" * 32
    for bad in ("abc", "g" * 64, "a" * 63, "a" * 65):
        with pytest.raises(ValidationError):
            _mailbox(pin=bad)


# ------------------------------------------------------------------------------ IMAP
@pytest.mark.parametrize("starttls", [True, False])
def test_imap_rejected_without_pin(servers, starttls):
    make, _fp = servers
    srv = make("imap", starttls)
    with pytest.raises(MailError, match="imap failed: SSLCertVerificationError"):
        _mailer().fetch_since(_profile(_mailbox(imap=srv)), SINCE)
    assert srv.logins == 0
    assert PASSWORD.encode() not in srv.received


@pytest.mark.parametrize("starttls", [True, False])
def test_imap_accepted_with_right_pin(servers, starttls):
    make, fp = servers
    srv = make("imap", starttls)
    assert _mailer().fetch_since(_profile(_mailbox(imap=srv, pin=fp)), SINCE) == []
    assert srv.logins == 1


@pytest.mark.parametrize("starttls", [True, False])
def test_imap_wrong_pin_sends_no_credentials(servers, starttls):
    make, _fp = servers
    srv = make("imap", starttls)
    with pytest.raises(MailError, match="certificate changed"):
        _mailer().fetch_since(_profile(_mailbox(imap=srv, pin=WRONG_PIN)), SINCE)
    assert srv.logins == 0
    assert PASSWORD.encode() not in srv.received
    assert b"LOGIN" not in srv.received.upper()


# ------------------------------------------------------------------------------ SMTP
@pytest.mark.parametrize("starttls", [True, False])
def test_smtp_rejected_without_pin(servers, starttls):
    make, _fp = servers
    srv = make("smtp", starttls)
    with pytest.raises(MailError, match="smtp failed: SSLCertVerificationError"):
        _mailer().send(_profile(_mailbox(smtp=srv)), "privacy@broker.example", "s", "b", "r1")
    assert srv.logins == 0


@pytest.mark.parametrize("starttls", [True, False])
def test_smtp_accepted_with_right_pin(servers, starttls):
    make, fp = servers
    srv = make("smtp", starttls)
    mid = _mailer().send(_profile(_mailbox(smtp=srv, pin=fp)),
                         "privacy@broker.example", "s", "b", "r1")
    assert "freemyid.r1" in mid
    assert srv.logins == 1


@pytest.mark.parametrize("starttls", [True, False])
def test_smtp_wrong_pin_sends_no_credentials(servers, starttls):
    make, _fp = servers
    srv = make("smtp", starttls)
    with pytest.raises(MailError, match="certificate changed"):
        _mailer().send(_profile(_mailbox(smtp=srv, pin=WRONG_PIN)),
                       "privacy@broker.example", "s", "b", "r1")
    assert srv.logins == 0
    assert b"AUTH" not in srv.received.upper()
    assert b"MAIL FROM" not in srv.received.upper()


# ------------------------------------------------------------------------------ host rules
def test_pin_on_non_loopback_host_refused(servers):
    _make, fp = servers
    with pytest.raises(TlsPinError, match="only allowed"):
        client_context("imap.mail.example", fp)
    mb = _mailbox(pin=fp, host="mail.example.invalid")
    policy = SimpleNamespace(is_allowed=lambda h: True)
    m = SmtpImapMailer(policy, password_getter=lambda pid, mb: PASSWORD)   # type: ignore[arg-type]
    with pytest.raises(MailError, match="only allowed"):
        m.fetch_since(_profile(mb), SINCE)
    with pytest.raises(MailError, match="only allowed"):
        m.send(_profile(mb), "privacy@broker.example", "s", "b", "r1")


def test_no_pin_keeps_default_verified_context():
    ctx = client_context("imap.gmail.com", None)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    ctx = client_context("127.0.0.1", None)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


# ------------------------------------------------------------------------------ TOFU
def test_trust_on_first_use_reads_fingerprint_without_credentials(servers):
    make, fp = servers
    imap, smtp = make("imap", True), make("smtp", True)
    res = trust_on_first_use(_mailbox(imap=imap, smtp=smtp), timeout_s=5)
    assert res.fingerprint == fp
    assert res.display == format_fingerprint(fp) and res.display in res.message
    assert imap.logins == 0 and smtp.logins == 0
    # the fingerprint it returns is exactly what makes a real connection succeed
    assert _mailer().fetch_since(_profile(_mailbox(imap=imap, pin=res.fingerprint)),
                                 SINCE) == []


def test_tofu_refuses_non_loopback():
    with pytest.raises(TlsPinError):
        fetch_loopback_fingerprint("mail.example.invalid", 993, "imap", starttls=False)


# =============================================================================== qa-security
# Negative tests added in the qa-security review of the pinning work (SEC-50..55).

def _ca_and_leaf(tmp_path):
    """Server context presenting leaf + CA chain; returns (ctx, leaf_fp, ca_fp, leaf_pem_sha)."""
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fake Bridge CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - dt.timedelta(days=1))
          .not_valid_after(now + dt.timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .sign(ca_key, hashes.SHA256()))
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
            .issuer_name(ca_name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=30))
            .sign(ca_key, hashes.SHA256()))
    pem = leaf.public_bytes(serialization.Encoding.PEM)
    cp, kp = tmp_path / "chain.pem", tmp_path / "leaf.key"
    cp.write_bytes(pem + ca.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cp, kp)
    return (ctx, fingerprint(leaf.public_bytes(serialization.Encoding.DER)),
            fingerprint(ca.public_bytes(serialization.Encoding.DER)),
            hashlib.sha256(pem).hexdigest())


@pytest.mark.parametrize("starttls", [True, False])
def test_qa_uppercase_colon_pin_is_accepted_end_to_end(servers, starttls):
    """The 'AB:CD:..' form Bridge/cert viewers show must work for IMAP and SMTP."""
    make, fp = servers
    imap, smtp = make("imap", starttls), make("smtp", starttls)
    shown = format_fingerprint(fp)
    assert ":" in shown and shown == shown.upper()
    assert _mailer().fetch_since(_profile(_mailbox(imap=imap, pin=shown)), SINCE) == []
    _mailer().send(_profile(_mailbox(smtp=smtp, pin=shown)), "privacy@broker.example",
                   "s", "b", "r1")
    assert imap.logins == 1 and smtp.logins == 1


def test_qa_unnormalised_pin_passed_directly_fails_closed():
    """Callers that bypass the model (e.g. the wizard) must not get a weaker check."""
    with pytest.raises(TlsPinError):
        client_context("127.0.0.1", "AB:" * 31 + "AB")
    with pytest.raises(TlsPinError):
        client_context("127.0.0.1", "")


@pytest.mark.parametrize("proto", ["imap", "smtp"])
@pytest.mark.parametrize("starttls", [True, False])
def test_qa_mismatch_closes_connection(servers, proto, starttls):
    make, _fp = servers
    srv = make(proto, starttls)
    mb = _mailbox(imap=srv, pin=WRONG_PIN) if proto == "imap" else _mailbox(smtp=srv,
                                                                             pin=WRONG_PIN)
    with pytest.raises(MailError, match="certificate changed"):
        if proto == "imap":
            _mailer().fetch_since(_profile(mb), SINCE)
        else:
            _mailer().send(_profile(mb), "privacy@broker.example", "s", "b", "r1")
    assert srv.done.wait(5), "client kept the connection open after a pin mismatch"
    assert srv.logins == 0 and PASSWORD.encode() not in srv.received


def test_qa_plain_imap_with_pin_never_sends_credentials(servers):
    """imap_ssl=False and imap_starttls=False with a pin: refuse, nothing in cleartext."""
    make, fp = servers
    srv = make("imap", starttls=True)        # plaintext greeting; would accept LOGIN
    mb = _mailbox(imap=srv, pin=fp).model_copy(update={"imap_ssl": False,
                                                       "imap_starttls": False})
    with pytest.raises(MailError, match="not encrypted"):
        _mailer().fetch_since(_profile(mb), SINCE)
    assert srv.logins == 0
    assert PASSWORD.encode() not in srv.received
    assert b"LOGIN" not in srv.received.upper()


def test_qa_sec53_plain_imap_without_pin_is_refused(servers):
    """SEC-53 (fixed in b631dfe): plaintext IMAP is refused before any socket opens.
    model_copy bypasses the MailboxConfig validator (f1167f5), so this tests _imap alone."""
    make, _fp = servers
    srv = make("imap", starttls=True)
    mb = _mailbox(imap=srv).model_copy(update={"imap_ssl": False, "imap_starttls": False})
    with pytest.raises(MailError, match="not encrypted"):
        _mailer().fetch_since(_profile(mb), SINCE)
    assert srv.logins == 0
    assert PASSWORD.encode() not in srv.received


def test_qa_check_peer_refuses_unencrypted_or_certless_socket():
    plain = socket.socket()
    try:
        with pytest.raises(TlsPinError, match="not encrypted"):
            check_peer(plain, "a" * 64)
    finally:
        plain.close()
    with pytest.raises(TlsPinError):
        check_peer(SimpleNamespace(getpeercert=lambda binary_form=False: None), "a" * 64)
    with pytest.raises(TlsPinError):
        check_peer(SimpleNamespace(getpeercert=lambda binary_form=False: b""), "a" * 64)


def test_qa_pin_is_over_der_leaf_only(tmp_path):
    """A pin of the CA cert, or of the leaf's PEM text, must not match."""
    ctx, leaf_fp, ca_fp, pem_sha = _ca_and_leaf(tmp_path)
    for bad in (ca_fp, pem_sha):
        srv = FakeServer(ctx, "imap", starttls=False)
        try:
            with pytest.raises(MailError, match="certificate changed"):
                _mailer().fetch_since(_profile(_mailbox(imap=srv, pin=bad)), SINCE)
            assert srv.logins == 0
        finally:
            srv.close()
    srv = FakeServer(ctx, "imap", starttls=False)
    try:
        assert _mailer().fetch_since(_profile(_mailbox(imap=srv, pin=leaf_fp)), SINCE) == []
    finally:
        srv.close()


@pytest.mark.parametrize("host", [
    "127.0.0.2", "127.1", "0.0.0.0", "::ffff:127.0.0.1", "[::ffff:127.0.0.1]",
    "0:0:0:0:0:0:0:1", "localhost.example", "evil.localhost", "localhost.evil.example",
    "127.0.0.1.nip.io", "mail.example.invalid", "", "10.0.0.1"])
def test_qa_pin_refused_on_non_exact_loopback(host):
    assert not is_loopback(host)
    with pytest.raises(TlsPinError, match="only allowed"):
        client_context(host, "a" * 64)
    with pytest.raises(TlsPinError):
        fetch_loopback_fingerprint(host, 993, "imap", starttls=False)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "[::1]", "localhost", "LOCALHOST",
                                  "localhost.", " 127.0.0.1 "])
def test_qa_exact_loopback_set(host):
    assert is_loopback(host)
    assert client_context(host, "a" * 64).verify_mode == ssl.CERT_NONE


@pytest.mark.parametrize("host", ["imap.gmail.com", "127.0.0.1", "localhost", "::1",
                                  "mail.example.invalid"])
def test_qa_no_pin_never_returns_unverified_context(host):
    ctx = client_context(host, None)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


def test_qa_pinned_context_floor_is_tls12():
    assert client_context("127.0.0.1", "a" * 64).minimum_version >= ssl.TLSVersion.TLSv1_2


def test_qa_different_certs_on_imap_and_smtp_fail_safe(tmp_path, servers):
    """One pin covers both ports. If Bridge ever serves two certs, TOFU refuses and the
    pinned connection to the other port refuses before AUTH."""
    make, imap_fp = servers
    imap = make("imap", True)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other_ctx, other_fp = _self_signed(other_dir)
    assert other_fp != imap_fp
    smtp = FakeServer(other_ctx, "smtp", True)
    try:
        with pytest.raises(TlsPinError, match="two different certificates"):
            trust_on_first_use(_mailbox(imap=imap, smtp=smtp), timeout_s=5)
        with pytest.raises(MailError, match="certificate changed"):
            _mailer().send(_profile(_mailbox(smtp=smtp, pin=imap_fp)),
                           "privacy@broker.example", "s", "b", "r1")
        assert smtp.logins == 0 and b"AUTH" not in smtp.received.upper()
        assert imap.logins == 0
    finally:
        smtp.close()
