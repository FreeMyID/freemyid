"""SEC-50, SEC-51 and SEC-53 regression tests (fakes only, no network)."""
from __future__ import annotations

import imaplib
from types import SimpleNamespace

import pytest

from freemyid.engine import mail as mail_mod
from freemyid.engine.mail import MailError, SmtpImapMailer
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
