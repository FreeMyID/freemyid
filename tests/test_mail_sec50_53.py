"""SEC-50, SEC-51 and SEC-53 regression tests (fakes only, no network)."""
from __future__ import annotations

import imaplib
from types import SimpleNamespace

import pytest

from freemyid.engine import mail as mail_mod
from freemyid.engine import mail_tls
from freemyid.engine.mail import MailError, SmtpImapMailer
from freemyid.engine.mail_tls import (
    TlsPinError,
    check_loopback_peer,
    check_peer,
    fingerprint,
    trust_on_first_use,
)
from freemyid.models import MailboxConfig
from freemyid.netpolicy import NetPolicy

PASSWORD = "fake-pw-not-real"


def _mb(host: str = "127.0.0.1", **upd) -> MailboxConfig:
    mb = MailboxConfig(
        address="removal@example.invalid", provider="proton_bridge",
        imap_host=host, imap_port=1143, imap_ssl=False, imap_starttls=True,
        smtp_host=host, smtp_port=1025, smtp_starttls=True,
        username="jane.testperson", keyring_service="freemyid-test")
    return mb.model_copy(update=upd) if upd else mb


def _mailer() -> SmtpImapMailer:
    return SmtpImapMailer(NetPolicy(None, allow_loopback=True),
                          password_getter=lambda pid, mb: PASSWORD, timeout_s=1)


class _Boom:
    """Stands in for imaplib classes: any construction means a socket would open."""
    calls = 0
    error = imaplib.IMAP4.error
    abort = imaplib.IMAP4.abort

    def __init__(self, *a, **k):
        type(self).calls += 1
        raise AssertionError("a connection was attempted")


# ------------------------------------------------------------------------- SEC-53
@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "imap.example.org"])
def test_sec53_plain_imap_refused_before_connecting(monkeypatch, host):
    _Boom.calls = 0
    monkeypatch.setattr(mail_mod.imaplib, "IMAP4", _Boom)
    monkeypatch.setattr(mail_mod.imaplib, "IMAP4_SSL", _Boom)
    mb = _mb(host, imap_ssl=False, imap_starttls=False)   # bypasses the model validator
    pol = NetPolicy(None, allow_loopback=True)
    pol.allowed.add("imap.example.org")
    m = SmtpImapMailer(pol, password_getter=lambda pid, mb: PASSWORD, timeout_s=1)
    with pytest.raises(MailError, match="not encrypted") as ei:
        m.fetch_since(SimpleNamespace(id="p-test", mailbox=mb), mail_mod.now())
    assert _Boom.calls == 0
    assert PASSWORD not in str(ei.value) and "jane" not in str(ei.value)


def test_sec53_encrypted_imap_still_connects(monkeypatch):
    _Boom.calls = 0
    monkeypatch.setattr(mail_mod.imaplib, "IMAP4", _Boom)
    with pytest.raises(AssertionError, match="attempted"):
        _mailer()._imap(_mb())
    assert _Boom.calls == 1


# ------------------------------------------------------------------------- SEC-50
class _Sock:
    def __init__(self, peer, der=b"fake-der"):
        self._peer, self._der = peer, der

    def getpeername(self):
        if isinstance(self._peer, Exception):
            raise self._peer
        return self._peer

    def getpeercert(self, binary_form=False):
        return self._der


def _pin() -> str:
    return fingerprint(b"fake-der")


@pytest.mark.parametrize("peer", [("127.0.0.1", 1143), ("::1", 1143, 0, 0)])
def test_sec50_exact_loopback_peer_accepted(peer):
    check_peer(_Sock(peer), _pin())
    check_loopback_peer(_Sock(peer))


@pytest.mark.parametrize("peer", [
    ("10.0.0.5", 1143), ("192.168.1.20", 1143), ("127.0.0.2", 1143),
    ("::ffff:127.0.0.1", 1143, 0, 0), ("localhost", 1143), ("", 0), (None, 0), (),
    OSError("not connected")])
def test_sec50_non_loopback_peer_refused_even_with_matching_pin(peer):
    with pytest.raises(TlsPinError, match="not on this computer"):
        check_peer(_Sock(peer), _pin())


def test_sec50_socket_without_getpeername_fails_closed():
    s = SimpleNamespace(getpeercert=lambda binary_form=False: b"fake-der")
    with pytest.raises(TlsPinError):
        check_peer(s, _pin())


def test_sec50_no_pin_is_still_a_noop():
    check_peer(_Sock(("203.0.113.9", 993)), None)   # CA-verified path, unchanged


class _FakeImap:
    """imaplib.IMAP4 stand-in that 'connects' to a chosen peer address."""
    error = imaplib.IMAP4.error
    abort = imaplib.IMAP4.abort
    peer: tuple = ("127.0.0.1", 1143)
    logged_out = 0

    def __init__(self, host, port, timeout=None):
        self.sock = _Sock(type(self).peer)

    def starttls(self, ssl_context=None):
        return "OK", [b""]

    def logout(self):
        type(self).logged_out += 1


class _FakeSmtp:
    peer: tuple = ("127.0.0.1", 1025)

    def __init__(self, host, port, timeout=None):
        self.sock = _Sock(type(self).peer)

    def starttls(self, context=None):
        return 220, b""

    def quit(self):
        pass


def _patch_tofu(monkeypatch, imap_peer, smtp_peer):
    _FakeImap.peer, _FakeSmtp.peer, _FakeImap.logged_out = imap_peer, smtp_peer, 0
    monkeypatch.setattr(mail_tls.imaplib, "IMAP4", _FakeImap)
    monkeypatch.setattr(mail_tls.smtplib, "SMTP", _FakeSmtp)


def test_sec50_tofu_on_redirected_localhost_is_refused(monkeypatch):
    _patch_tofu(monkeypatch, ("198.51.100.7", 1143), ("198.51.100.7", 1025))
    with pytest.raises(TlsPinError, match="not on this computer"):
        trust_on_first_use(_mb("localhost"))
    assert _FakeImap.logged_out == 1      # connection still closed


def test_sec50_tofu_on_real_loopback_returns_code(monkeypatch):
    _patch_tofu(monkeypatch, ("127.0.0.1", 1143), ("127.0.0.1", 1025))
    res = trust_on_first_use(_mb("localhost"))
    assert res.fingerprint == _pin()


# ------------------------------------------------------------------------- SEC-51
def test_sec51_policy_without_loopback_blocks_before_connecting(monkeypatch):
    _Boom.calls = 0
    monkeypatch.setattr(mail_tls.imaplib, "IMAP4", _Boom)
    monkeypatch.setattr(mail_tls.smtplib, "SMTP", _Boom)
    strict = NetPolicy(None)                       # loopback NOT allowed
    with pytest.raises(TlsPinError, match="allowlist"):
        trust_on_first_use(_mb(), netpolicy=strict)
    with pytest.raises(TlsPinError, match="allowlist"):
        mail_tls.fetch_loopback_fingerprint("127.0.0.1", 1143, "imap", starttls=True,
                                            netpolicy=strict)
    assert _Boom.calls == 0


def test_sec51_policy_is_consulted_for_both_hosts(monkeypatch):
    _patch_tofu(monkeypatch, ("127.0.0.1", 1143), ("127.0.0.1", 1025))
    seen: list[str] = []

    class Spy:
        def is_allowed(self, h):
            seen.append(h)
            return True

    trust_on_first_use(_mb(), netpolicy=Spy())     # type: ignore[arg-type]
    assert seen.count("127.0.0.1") >= 2


def test_sec51_default_policy_still_allows_loopback(monkeypatch):
    _patch_tofu(monkeypatch, ("::1", 1143, 0, 0), ("::1", 1025, 0, 0))
    assert trust_on_first_use(_mb("::1")).fingerprint == _pin()
