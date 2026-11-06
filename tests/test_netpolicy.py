"""netpolicy.NetPolicy: allowlist built from registry, mailboxes, config."""
from __future__ import annotations

import pytest

from freemyid import config
from freemyid.models import MailboxConfig
from freemyid.netpolicy import NetPolicy
from tests.conftest import make_profile


@pytest.fixture
def policy(fake_registry):
    mb = MailboxConfig(address="removals@example.com", imap_host="IMAP.mail.example",
                       smtp_host="smtp.mail.example", username="removals@example.com")
    config.save(config.Config(registry_url="https://raw.example.org/u/r/main/registry.yaml",
                              extra_allowed_hosts=["Extra.example"]))
    return NetPolicy(fake_registry, [make_profile(mailbox=mb)])


@pytest.mark.parametrize("target", [
    "https://fakepeople.example/optout", "https://www.fakepeople.example/x",
    "https://mail.fakepeople.example/confirm?t=1", "https://FAKEPEOPLE.EXAMPLE./",
    "fakemail.example", "imap.mail.example", "smtp.mail.example", "raw.example.org",
    "https://extra.example/",
])
def test_allowed(policy, target):
    assert policy.is_allowed(target)


@pytest.mark.parametrize("target", [
    "https://evilfakepeople.example/", "https://fakepeople.example.evil.test/",
    "https://google.com/", "", "file:///etc/passwd", "https://", "mail.example",
    "https://user@evil.test/@fakepeople.example",
])
def test_denied(policy, target):
    assert not policy.is_allowed(target)


def test_userinfo_does_not_confuse_host(policy):
    assert not policy.is_allowed("https://fakepeople.example@evil.test/")


def test_no_config_no_registry_host(fake_registry):
    assert not NetPolicy(fake_registry).is_allowed("raw.example.org")


# ---- SEC-09 (fixed) ----

@pytest.mark.parametrize("target", ["http://127.0.0.1:8765/", "http://localhost:8765/api"])
def test_loopback_not_default(fake_registry, target):
    assert not NetPolicy(fake_registry).is_allowed(target)


def test_backslash_url_rejected(policy):
    assert not policy.is_allowed("https://evil.test\\@fakepeople.example/")


def test_for_broker_intersects(policy):
    assert "attacker.test" not in policy.for_broker(["fakepeople.example"], ["attacker.test"])


def test_loopback_opt_in(fake_registry):
    assert NetPolicy(fake_registry, allow_loopback=True).is_allowed("http://127.0.0.1:8765/")
    base = NetPolicy(fake_registry)
    assert base.with_loopback().is_allowed("http://localhost:8765/")
    assert not base.is_allowed("http://localhost:8765/")


def test_for_broker_drops_loopback_without_opt_in(fake_registry):
    mb = MailboxConfig(address="r@example.com", imap_host="127.0.0.1", smtp_host="127.0.0.1",
                       username="r@example.com")
    pol = NetPolicy(fake_registry, [make_profile(mailbox=mb)])
    assert pol.is_allowed("127.0.0.1")          # mail to Proton Bridge is fine
    assert "127.0.0.1" not in pol.for_broker(["fakepeople.example"], ["127.0.0.1"])
    assert pol.for_broker(["fakepeople.example"]) == {"fakepeople.example"}


@pytest.mark.parametrize("target", ["https://fake people.example/", "https://fakepeople.example\n",
                                    "https://fakepeople.example/\x00"])
def test_control_chars_rejected(policy, target):
    assert not policy.is_allowed(target.encode().decode("unicode_escape"))
