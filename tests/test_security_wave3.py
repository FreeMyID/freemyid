"""Post-v0.1.0 wave (SEC-46..): regressions for the reviewed fixes plus strict xfails for open
findings. When a fix lands the xfail XPASSes and fails the run: remove the marker then.
Fake people and *.example brokers only; FakeMailer only (SMTP is blocked)."""
from __future__ import annotations

import re
import smtplib
from datetime import date
from pathlib import Path

import keyring
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import outbox
from freemyid.engine.mail import FakeMailer
from freemyid.models import (
    Broker,
    Consent,
    ConsentBasis,
    EmailMode,
    MailboxConfig,
    Registry,
    RequestStatus,
    Todo,
    TodoKind,
)
from freemyid.storage import Store
from freemyid.wizard.server import _csrf_for, create_app
from tests.conftest import make_profile

TOKEN = "tok-wave3"
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")


def _broker(bid: str) -> Broker:
    return Broker.model_validate({
        "id": bid, "name": bid.title(), "url": f"https://{bid}.example/",
        "category": "data_broker", "domains": [f"{bid}.example"], "method": "email",
        "opt_out_email": f"privacy@{bid}.example"})


B1, B2 = _broker("fakeone"), _broker("faketwo")
REG = Registry(version="t", updated=date(2026, 11, 7), brokers=[B1, B2])


@pytest.fixture
def no_smtp(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("SMTP used")
    monkeypatch.setattr(smtplib, "SMTP", boom)
    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)


@pytest.fixture
def wiz(freemyid_env, monkeypatch, no_smtp):
    monkeypatch.setattr(keyring, "set_password", lambda *a: None)
    store = Store()
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: REG,
                     open_url=lambda u: True)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    c.headers["Origin"] = "http://testserver"
    p = make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                                     text_version=CURRENT_TEXT_VERSION),
                     mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(p)
    return c, store, p, {"csrf": _csrf_for(TOKEN)}


# --------------------------------------------------------------------------- SEC-38 (fixed)

def _assisted(store, p) -> Todo:
    t = Todo(profile_id=p.id, broker_id="fakeone", kind=TodoKind.ASSISTED_OPT_OUT,
             title="Remove your listing", body="1. Find it", links=["https://fakeone.example/x"])
    store.save_todo(t)
    return t


def test_sec38_confirm_page_needs_the_session(wiz):
    c, store, p, _ = wiz
    t = _assisted(store, p)
    anon = TestClient(c.app, follow_redirects=False)
    r = anon.get(f"/todo/{t.id}/fill/confirm")
    assert r.status_code in (401, 403) and "This sends a real request" not in r.text


def test_sec38_confirm_post_needs_csrf_and_writes_nothing(wiz):
    from freemyid import paths
    c, store, p, _ = wiz
    t = _assisted(store, p)
    r = c.post(f"/todo/{t.id}/fill", data={"confirm": "yes"})          # no CSRF
    assert r.status_code == 403
    assert not (paths.home() / ".fill-confirmed").exists()


def test_sec38_confirm_only_for_assisted_todos(wiz):
    c, store, p, f = wiz
    t = Todo(profile_id=p.id, broker_id="fakeone", kind=TodoKind.SEND_EMAIL_MANUALLY,
             title="Send this letter", body="x")
    store.save_todo(t)
    assert c.get(f"/todo/{t.id}/fill/confirm").headers["location"] == "/"
    assert c.post(f"/todo/{t.id}/fill", data={**f, "confirm": "yes"}).headers["location"] == "/"


# --------------------------------------------------------------------------- SEC-46 (fixed)

def test_sec46_wipe_removes_the_fill_confirmation_marker(store, memkeyring, monkeypatch,
                                                        freemyid_env):
    from freemyid import cli, paths, scheduler
    monkeypatch.setattr(scheduler, "remove", lambda: "removed")
    store.close()
    # the file name wizard/server.py `_fill_ack_path()` writes after the SEC-38 confirm
    (paths.home() / ".fill-confirmed").write_text("1", encoding="utf-8")
    res = CliRunner().invoke(cli.app, ["wipe", "--yes"])
    assert res.exit_code == 0, res.output
    assert not any(Path(freemyid_env).rglob("*"))


# --------------------------------------------------------------------------- SEC-47 (fixed)

def _card(page: str, rid: str) -> str:
    return next(c for c in page.split('<div class="card">') if f"/outbox/{rid}/approve" in c)


def test_sec47_approve_card_discloses_every_email_it_sends(wiz, monkeypatch):
    c, store, p, f = wiz
    m = FakeMailer()
    first = outbox.queue_email(store, p, B1, [], dry_run=False, mailer=m)
    second = outbox.queue_email(store, p, B2, [], dry_run=False, mailer=m)
    assert {first.status, second.status} == {RequestStatus.QUEUED_FOR_APPROVAL}
    monkeypatch.setattr(outbox, "_default_mailer", lambda *a, **k: m)
    card = _card(c.get("/outbox").text, first.id)
    r = c.post(f"/outbox/{first.id}/approve", data=f)
    assert r.status_code == 303
    others = {s.to for s in m.sent} - {"privacy@fakeone.example"}
    if others:   # the click sent more than the card it was on: the card must have said so
        assert "faketwo" in card.lower() or re.search(r"\b(1|one) other\b", card, re.IGNORECASE)


def test_sec47_guard_held_emails_never_leave_before_an_approval(wiz):
    _c, store, p, _ = wiz
    m = FakeMailer()
    for b in (B1, B2):
        outbox.queue_email(store, p, b, [], dry_run=False, mailer=m)
    assert m.sent == []
    assert outbox.release_held(store, p, mailer=m, registry=REG) == {"sent": 0, "failed": 0}
    assert m.sent == []


# --------------------------------------------------------------------------- SEC-48 (fixed)

def test_sec48_approve_does_not_send_on_the_event_loop(wiz, monkeypatch):
    import asyncio
    c, store, p, f = wiz
    req = outbox.queue_email(store, p, B1, [], dry_run=False, mailer=FakeMailer())
    seen: list[bool] = []

    def fake_approve(store, rid, **k):
        try:
            asyncio.get_running_loop()
            seen.append(True)        # called on the server's event loop thread
        except RuntimeError:
            seen.append(False)       # called in a worker thread (threadpool / sync route)
    monkeypatch.setattr(outbox, "approve_and_send", fake_approve)
    assert c.post(f"/outbox/{req.id}/approve", data=f).status_code == 303
    assert seen == [False]


# --------------------------------------------------------------------------- SEC-49 (open)

@pytest.mark.xfail(strict=True, reason="SEC-49: /safety/ says the printable report holds "
                   "'only site names, statuses and dates', but it is headed with the person's label")
def test_sec49_safety_report_claim_mentions_the_persons_name():
    from tests.conftest import ROOT
    tpl = (ROOT / "site_src/templates/pages/safety.html").read_text(encoding="utf-8")
    item = next(li for li in tpl.split("<li>") if "printable progress report" in li)
    rest = re.sub(r"\{#.*?#\}", "", item, flags=re.DOTALL).replace("site names", "")
    assert re.search(r"\b(name|label)\b", rest, re.IGNORECASE)


def test_sec49_guard_report_has_label_but_no_address_or_mailbox(wiz):
    from freemyid.models import Address, BrokerStatus, ListingState
    from freemyid.wizard.report import build_report
    _c, store, p, _ = wiz
    p = p.model_copy(update={"label": "Jane", "addresses": [
        Address(street="742 Evergreen Terrace", city="Springfield", state="IL", zip="62701",
                current=True)]})
    store.save_profile(p)
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="fakeone",
                                   state=ListingState.SUBMITTED))
    text = build_report(store, REG, p.id, "html").read_text(encoding="utf-8")
    assert "Jane" in text and "Fakeone" in text
    for leak in ("Evergreen", "62701", "removals@example.org", p.name.last):
        assert leak not in text
