"""SEC-16/18/21/27/28/29 engine fixes (automation-engineer, wave 2). Fake people only."""
from __future__ import annotations

import asyncio
from email.message import EmailMessage

from freemyid.engine import outbox
from freemyid.engine.browser import host_resolver_rules
from freemyid.engine.handoff import GENERIC_HELP, QueuedHandoff
from freemyid.engine.letters import letter_vars
from freemyid.engine.mail import FakeMailer, extract_links
from freemyid.models import (
    Broker,
    EmailMode,
    Listing,
    MailboxConfig,
    MatchLevel,
    ProfileField,
    RequestKind,
    RequestStatus,
    Todo,
    TodoKind,
)
from tests.conftest import make_profile

B = Broker(id="fakeb", name="Fake B", url="https://fakeb.example/", category="data_broker",
           domains=["fakeb.example"], method="email", opt_out_email="privacy@fakeb.example",
           confirmation_domains=["mail.fakeb.example"])
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")


def _mail(html: str) -> bytes:
    m = EmailMessage()
    m["From"] = "Fake B <no-reply@fakeb.example>"
    m["To"] = MB.address
    m["Subject"] = "Please confirm"
    m.set_content("see html")
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


# ---------------------------------------------------------------- SEC-16 resolver floor
def test_resolver_rules_map_everything_but_allowlist():
    r = host_resolver_rules({"fakeb.example", "127.0.0.1", "::1"})
    assert r.startswith("MAP * ~NOTFOUND")
    assert "EXCLUDE fakeb.example" in r and "EXCLUDE *.fakeb.example" in r
    assert "EXCLUDE 127.0.0.1" in r and "EXCLUDE *.127.0.0.1" not in r
    assert "EXCLUDE [::1]" in r


def test_resolver_rules_fixture_mode_only_loopback():
    r = host_resolver_rules({"fakeb.example"}, fixture_mode=True)
    assert "fakeb.example" not in r
    assert "EXCLUDE localhost" in r and "EXCLUDE 127.0.0.1" in r


# ---------------------------------------------------------------- SEC-18 link ranking
def test_confirm_link_ranked_first_and_cancel_dropped():
    html = ('<a href="https://mail.fakeb.example/x?t=9">Privacy policy</a>'
            '<a href="https://mail.fakeb.example/a?t=1">Not you? Click here</a>'
            '<a href="https://mail.fakeb.example/go?t=2">Open</a>'
            '<a href="https://mail.fakeb.example/b?t=3"><b>Verify</b> my request</a>'
            '<a href="https://mail.fakeb.example/preferences">Settings</a>')
    assert extract_links(_mail(html), ["mail.fakeb.example"]) == [
        "https://mail.fakeb.example/b?t=3", "https://mail.fakeb.example/go?t=2"]


def test_host_named_privacy_is_not_a_reason_to_drop():
    html = '<a href="https://privacy.mail.fakeb.example/confirm?t=1">Confirm</a>'
    assert extract_links(_mail(html), ["mail.fakeb.example"]) == [
        "https://privacy.mail.fakeb.example/confirm?t=1"]


# ---------------------------------------------------------------- SEC-21
def test_dev_fixture_base_loopback_http_only(monkeypatch):
    import sys
    for bad in ("https://127.0.0.1:8000", "http://127.0.0.1.evil.example/",
                "http://evil.example\\@127.0.0.1/", "file:///tmp"):
        monkeypatch.setenv(outbox.DEV_FIXTURES_ENV, bad)
        assert outbox.dev_fixture_base() is None, bad
    monkeypatch.setenv(outbox.DEV_FIXTURES_ENV, "http://127.0.0.1:8123")
    assert outbox.dev_fixture_base() == "http://127.0.0.1:8123"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert outbox.dev_fixture_base() is None


# ---------------------------------------------------------------- SEC-27
def test_first_auto_email_per_profile_waits_for_approval(store):
    p = make_profile(mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    m = FakeMailer()
    first = outbox.queue_email(store, p, B, [], dry_run=False, mailer=m)
    assert first.status == RequestStatus.QUEUED_FOR_APPROVAL and m.sent == []
    outbox.send_request(store, first, p, m)          # the person approved it
    b2 = B.model_copy(update={"id": "fakec", "opt_out_email": "privacy@fakec.example"})
    second = outbox.queue_email(store, p, b2, [], dry_run=False, mailer=m)
    assert second.status == RequestStatus.SENT
    assert outbox.needs_approval(p, RequestKind.LEGAL_DEMAND, store)


# ---------------------------------------------------------------- SEC-28
def test_queued_handoff_notification_is_generic(store):
    calls = []

    class Rec:
        def notify(self, title, body, url=None):
            calls.append((title, body, url))

    p = make_profile(label="Jane Q Testperson")
    t = Todo(profile_id=p.id, broker_id="fakeb", kind=TodoKind.ASSISTED_OPT_OUT, title="t",
             body="b")
    asyncio.run(QueuedHandoff(store, Rec(), p.label).request(t, None))
    assert calls == [("Free My ID needs you", GENERIC_HELP, None)]


# ---------------------------------------------------------------- SEC-29
def _li(p, shown):
    return Listing(profile_id=p.id, broker_id="fakeb", url="https://fakeb.example/p/1",
                   match_level=MatchLevel.CONFIRMED, match_score=95.0,
                   shown_fields=shown)


def test_letter_name_drops_middle_unless_shown():
    p = make_profile()
    v = letter_vars(p, B, [_li(p, [ProfileField.FULL_NAME, ProfileField.CITY])])
    assert v["name"] == "Jane Testperson"
    v = letter_vars(p, B, [_li(p, [ProfileField.FULL_NAME, ProfileField.MIDDLE_NAME])])
    assert v["name"] == p.name.full
