"""Draft tests for engine/runner.py + dev fixtures (qa to adopt). Fake people/brokers only.

Uses CURRENT_TEXT_VERSION consent: tests/conftest.make_profile's "v1" is refused by the
consent gate, so the runner (correctly) skips that profile.
"""
from __future__ import annotations

import smtplib
from datetime import timedelta

import pytest

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import _dev
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import run
from freemyid.models import (
    Consent,
    ConsentBasis,
    ListingState,
    MailboxConfig,
    RequestStatus,
    Tier,
    TodoKind,
    utcnow,
)
from tests.conftest import make_profile

MB = MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                   smtp_host="smtp.example.com", username="removals.testperson@example.com")


def person(**over):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    return make_profile(consent=c, **over)


class Rec:
    def __init__(self):
        self.calls = []

    def notify(self, title, body, url=None):
        self.calls.append((title, body, url))


@pytest.fixture
def no_smtp(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("SMTP used")
    monkeypatch.setattr(smtplib, "SMTP", boom)
    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)


def _run(store, profiles, **kw):
    reg = _dev.fixture_registry()
    kw.setdefault("notifier", Rec())
    with _dev.fixture_server():
        return reg, run(store, reg, profiles, scan_only=False, interactive=False, **kw)


@pytest.mark.parametrize("with_mb", [True, False])
def test_dry_run_end_to_end(store, no_smtp, with_mb):
    p = person(mailbox=MB if with_mb else None)
    store.save_profile(p)
    _reg, rep = _run(store, [p], dry_run=True)
    assert rep.errors == 0, rep.summary_lines()
    st = {s.broker_id: s for s in store.list_statuses(p.id)}
    assert st["devauto"].tier == Tier.AUTOMATIC
    assert st["devmail"].tier == (Tier.EMAIL if with_mb else Tier.ASSISTED)
    assert st["devweb"].tier == Tier.ASSISTED
    assert st["devchild"].tier == Tier.ASSISTED
    assert all(s.last_submitted_at is None for s in st.values())
    assert not any(s.state == ListingState.SUBMITTED for s in st.values())
    for r in store.list_requests(p.id):
        assert r.dry_run and r.status == RequestStatus.DRAFT
    kinds = {(t.broker_id, t.kind) for t in store.list_todos(p.id)}
    assert ("devweb", TodoKind.ASSISTED_OPT_OUT) in kinds
    assert ("devchild", TodoKind.ASSISTED_OPT_OUT) not in kinds     # covered by devweb
    if not with_mb:
        assert ("devmail", TodoKind.SEND_EMAIL_MANUALLY) in kinds
    for t in store.list_todos(p.id):
        joined = " ".join(t.copy_fields.values())
        for bad in ("742 Evergreen", "62704", "217-555-0142", "jane.testperson@example.com",
                    "John Testperson", "1980"):
            assert bad not in joined, (t.broker_id, bad)


def test_scan_finds_confirmed_listing_and_saves_evidence(store, no_smtp):
    p = person(mailbox=MB)
    store.save_profile(p)
    _run(store, [p], dry_run=True)
    lis = store.list_listings(p.id, "devauto")
    assert any(li.match_level == "confirmed" for li in lis)
    assert all(li.url.startswith("https://devauto.example/") for li in lis)
    assert any(e.kind == "screenshot" for e in store.list_evidence(p.id, "devauto"))


def test_consent_gate_skips_profile(store):
    from freemyid.models import Consent, ConsentBasis
    p = make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                                     text_version="v1"))   # outdated consent text: refused
    store.save_profile(p)
    _, rep = _run(store, [p], dry_run=True)
    assert rep.skipped_profiles == 1
    assert store.list_statuses(p.id) == []


def test_one_notification_when_todos(store):
    p = person()
    store.save_profile(p)
    rec = Rec()
    _run(store, [p], dry_run=True, notifier=rec)
    assert len(rec.calls) == 1
    assert "Jane" not in rec.calls[0][1] and "Testperson" not in rec.calls[0][1]


def test_scheduled_skips_not_due(store):
    p = person()
    store.save_profile(p)
    _run(store, [p], dry_run=True)
    _, rep = _run(store, [p], dry_run=True, scheduled=True)
    assert rep.skipped_not_due == len(_dev.fixture_registry().brokers)


def test_ca_resident_gets_drop_todo_first_once(store):
    from freemyid.models import Address
    p = person(addresses=[Address(city="Fresno", state="CA", current=True)])
    store.save_profile(p)
    _run(store, [p], dry_run=True)
    _run(store, [p], dry_run=True)
    gov = [t for t in store.list_todos(p.id) if t.kind == TodoKind.GOVERNMENT_PORTAL]
    assert len(gov) == 1
    assert store.list_todos(p.id)[0].kind == TodoKind.GOVERNMENT_PORTAL


def test_fixture_submit_loop_and_escalation(store, no_smtp, monkeypatch):
    """Non-dry run against fixtures only (FakeMailer + local server)."""
    from freemyid import config as cfgmod
    cfg = cfgmod.Config(min_delay_s=0, max_delay_s=0, max_retries=1)
    p = person(mailbox=MB)
    store.save_profile(p)
    mailer = FakeMailer(inbox=_dev.fixture_inbox())
    _run(store, [p], dry_run=False, mailer=mailer, cfg=cfg)
    st = store.get_status(p.id, "devauto")
    if st.state == ListingState.NEEDS_HUMAN:
        pytest.skip("no headless browser available; automatic dropped to assisted")
    assert st.state == ListingState.CONFIRMED          # form + confirmation link via fixtures
    assert mailer.sent == []                           # approve_each: nothing auto-sent
    q = store.list_requests(p.id, "devmail", status=RequestStatus.QUEUED_FOR_APPROVAL)
    assert len(q) == 1
    # approve -> FakeMailer send, EMAIL_SENT evidence, broker SUBMITTED
    from freemyid.engine.outbox import approve_and_send
    approve_and_send(store, q[0].id, mailer=mailer, registry=_dev.fixture_registry())
    assert len(mailer.sent) == 1 and mailer.sent[0].to == "privacy@devmail.example"
    assert store.get_status(p.id, "devmail").state == ListingState.SUBMITTED
    assert any(e.kind == "email_sent" for e in store.list_evidence(p.id, "devmail"))
    # 61 days later the email broker escalates: resubmit queued for approval
    later = utcnow() + timedelta(days=61)
    _run(store, [p], dry_run=False, mailer=mailer, cfg=cfg, now=later)
    s2 = store.get_status(p.id, "devmail")
    assert s2.escalation_level == 1
    assert store.list_requests(p.id, "devmail", status=RequestStatus.QUEUED_FOR_APPROVAL)
