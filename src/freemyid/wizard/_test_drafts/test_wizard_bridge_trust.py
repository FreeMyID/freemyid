"""Draft tests (CR-W2): the wizard's Test connection pins the local mail app's certificate
instead of switching verification off, and the trust prompt flow. Fake data only.

Reuses the fake self-signed Bridge from tests/test_mail_tls_pin.py. Adopting into tests/:
change the import below to `from .test_mail_tls_pin import ...` (or drop the sys.path line).
"""
from __future__ import annotations

import sys
from pathlib import Path

import keyring
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from freemyid.storage import Store
from freemyid.wizard import draft as dr
from freemyid.wizard.server import _csrf_for, create_app
from tests.test_mail_tls_pin import PASSWORD, WRONG_PIN, FakeServer, _self_signed

TOKEN = "tok-test"


@pytest.fixture
def bridge(tmp_path):
    ctx, fp = _self_signed(tmp_path)
    made: list[FakeServer] = []

    def make(proto: str) -> FakeServer:
        s = FakeServer(ctx, proto, True)
        made.append(s)
        return s
    yield make("imap"), make("smtp"), fp
    for s in made:
        s.close()


def _mb(imap, smtp, pin=None):
    mb = {"provider": "proton_bridge", "address": "removal@example.invalid",
          "username": "removal@example.invalid", "imap_host": "127.0.0.1",
          "imap_port": imap.port, "imap_ssl": False, "imap_starttls": True,
          "smtp_host": "127.0.0.1", "smtp_port": smtp.port, "smtp_starttls": True}
    if pin:
        mb["tls_cert_sha256"] = pin
    return mb


def test_no_pin_never_sends_password(bridge):
    imap, smtp, _fp = bridge
    ok, _msg, status = dr.check_mailbox(_mb(imap, smtp), PASSWORD)
    assert (ok, status) == (False, "needs_trust")
    assert imap.logins == smtp.logins == 0
    assert PASSWORD.encode() not in imap.received + smtp.received


def test_wrong_pin_sends_no_password(bridge):
    imap, smtp, _fp = bridge
    ok, msg, status = dr.check_mailbox(_mb(imap, smtp, WRONG_PIN), PASSWORD)
    assert (ok, status) == (False, "cert_changed")
    assert PASSWORD not in msg
    assert imap.logins == smtp.logins == 0
    assert PASSWORD.encode() not in imap.received + smtp.received


def test_right_pin_passes(bridge):
    imap, smtp, fp = bridge
    assert dr.check_mailbox(_mb(imap, smtp, fp), PASSWORD)[::2] == (True, "ok")
    assert imap.logins == 1 and smtp.logins == 1


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    monkeypatch.setattr(keyring, "set_password", lambda s, u, p: None)
    app = create_app(Store(), TOKEN, {"testserver"}, registry_loader=lambda: None,
                     on_finish=lambda p, on: None)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    return c, {"csrf": _csrf_for(TOKEN)}


def _form(imap, smtp):
    return {"provider": "other", "address": "removal@example.invalid", "password": PASSWORD,
            "username": "removal@example.invalid", "imap_host": "127.0.0.1",
            "imap_port": str(imap.port), "smtp_host": "127.0.0.1",
            "smtp_port": str(smtp.port), "imap_starttls": "1", "smtp_starttls": "1"}


def test_trust_flow_yes_then_connects_and_changed_then_retrust(web, bridge):
    c, f = web
    imap, smtp, fp = bridge
    c.get("/wizard/consent?new=1")
    r = c.post("/wizard/test-connection", data={**_form(imap, smtp), **f},
               headers={"X-CSRF": f["csrf"]}).json()
    assert r["status"] == "trust" and not r["changed"]
    assert r["display"].upper().replace(":", "").lower() == fp
    assert imap.logins == smtp.logins == 0 and PASSWORD.encode() not in imap.received

    # No: nothing saved, still no password sent.
    no = c.post("/wizard/trust-certificate", data={"answer": "no", **f}).json()
    assert not no["ok"] and not getattr(c.app.state, "approved_pin", None)

    c.post("/wizard/test-connection", data={**_form(imap, smtp), **f})
    assert c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()["ok"]
    r = c.post("/wizard/test-connection", data={**_form(imap, smtp), **f}).json()
    assert r["ok"] and r["status"] == "ok" and imap.logins == 1

    # Certificate changes (pin differs): plain-language prompt, offer to trust the new one.
    c.app.state.approved_pin = WRONG_PIN
    before = imap.logins
    r = c.post("/wizard/test-connection", data={**_form(imap, smtp), **f}).json()
    assert r["status"] == "trust" and r["changed"] and "changed" in r["message"]
    assert imap.logins == before
    assert c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()["ok"]
    assert c.app.state.approved_pin == fp


def test_trust_yes_without_pending_is_refused(web):
    c, f = web
    c.get("/wizard/consent?new=1")
    r = c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()
    assert not r["ok"]
