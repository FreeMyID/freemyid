"""Draft tests (CR-W2): the wizard's Test connection pins the local mail app's certificate
instead of switching verification off, and the trust prompt flow. Fake data only.

Reuses the fake self-signed Bridge from tests/test_mail_tls_pin.py.
"""
from __future__ import annotations

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.storage import Store
from freemyid.wizard import draft as dr
from freemyid.wizard.server import _csrf_for, create_app

from .test_mail_tls_pin import PASSWORD, WRONG_PIN, FakeServer, _self_signed

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
    assert not no["ok"] and not c.app.state.draft.tls_pin

    c.post("/wizard/test-connection", data={**_form(imap, smtp), **f})
    assert c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()["ok"]
    r = c.post("/wizard/test-connection", data={**_form(imap, smtp), **f}).json()
    assert r["ok"] and r["status"] == "ok" and imap.logins == 1

    # Certificate changes (pin differs): plain-language prompt, offer to trust the new one.
    c.app.state.draft.tls_pin = WRONG_PIN
    before = imap.logins
    r = c.post("/wizard/test-connection", data={**_form(imap, smtp), **f}).json()
    assert r["status"] == "trust" and r["changed"] and "changed" in r["message"]
    assert imap.logins == before
    assert c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()["ok"]
    assert c.app.state.draft.tls_pin == fp


def test_trust_yes_without_pending_is_refused(web):
    c, f = web
    c.get("/wizard/consent?new=1")
    r = c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()
    assert not r["ok"]


# --- SEC-53: the "other" provider must not allow plaintext IMAP -------------------------


def _other(**kw):
    f = {"provider": "other", "address": "removal@example.invalid", "password": PASSWORD,
         "imap_host": "mail.example.invalid", "smtp_host": "mail.example.invalid",
         "imap_port": "143", "smtp_port": "465"}
    f.update(kw)
    return f


def test_both_off_is_refused_with_plain_message():
    d = dr.Draft()
    errs = dr._apply_mailbox(d, _other())
    assert errs == [dr.UNENCRYPTED_MSG] and not d.mailbox
    assert "unprotected" in errs[0] and "SSL or STARTTLS" in errs[0]
    assert "Traceback" not in errs[0] and "ValueError" not in errs[0]


@pytest.mark.parametrize("flag", ["imap_ssl", "imap_starttls"])
def test_either_protection_is_accepted(flag):
    d = dr.Draft()
    assert dr._apply_mailbox(d, _other(**{flag: "1"})) == []
    assert d.mailbox and d.mailbox[flag] is True


def test_check_mailbox_refuses_both_off_without_connecting():
    mb = {"provider": "other", "address": "a@example.invalid", "username": "a",
          "imap_host": "mail.example.invalid", "imap_port": 143, "imap_ssl": False,
          "imap_starttls": False, "smtp_host": "mail.example.invalid", "smtp_port": 465,
          "smtp_starttls": False}
    ok, msg, status = dr.check_mailbox(mb, PASSWORD)
    assert (ok, status) == (False, "fail") and msg == dr.UNENCRYPTED_MSG


def test_web_test_connection_both_off_is_a_kind_message(web):
    c, f = web
    c.get("/wizard/consent?new=1")
    r = c.post("/wizard/test-connection", data={**_other(), **f},
               headers={"X-CSRF": f["csrf"]})
    assert r.status_code == 200
    j = r.json()
    assert not j["ok"] and j["status"] == "fail" and "unprotected" in j["message"]


def test_build_profile_with_bad_mailbox_raises_save_error_not_validation_error():
    d = dr.Draft()
    d.mailbox = {"provider": "other", "address": "a@example.invalid", "username": "a",
                 "imap_host": "mail.example.invalid", "imap_port": 143, "imap_ssl": False,
                 "imap_starttls": False, "smtp_host": "mail.example.invalid",
                 "smtp_port": 465, "smtp_starttls": False}
    d.consent_at = "x"
    with pytest.raises(dr.SaveError):
        dr.build_profile(d)


def test_require_trust_is_default_for_local_mail_app():
    d = dr.Draft()
    f = {"provider": "proton_bridge", "address": "removal@example.invalid",
         "password": PASSWORD}
    errs = dr._apply_mailbox(d, f)
    assert errs and "security code" in errs[0]
    assert dr._apply_mailbox(dr.Draft(), f, require_trust=False) == []


# ---- SEC-55: an approved pin belongs to one draft/profile, never to the whole app ----
PIN_A = "a" * 64
PIN_B = "b" * 64


def _two_profiles(c, imap, smtp):
    from .conftest import make_profile
    store = c.app.state.store if hasattr(c.app.state, "store") else Store()
    from freemyid.models import MailboxConfig
    out = []
    for label, pin in (("A", PIN_A), ("B", PIN_B)):
        mb = MailboxConfig(**_mb(imap, smtp, pin), keyring_service="freemyid-mailbox")
        p = make_profile(label=label, mailbox=mb)
        store.save_profile(p)
        out.append(p.id)
    return store, out


def _post_mailbox(c, f, pid, imap, smtp):
    form = {k: v for k, v in _form(imap, smtp).items() if k != "password"}
    return c.post(f"/settings/{pid}/mailbox", data={**form, **f})


def _approve_for(c, f, pid, imap, smtp, fp):
    """Open the settings page for pid, run test-connection, say yes."""
    assert c.get(f"/settings/{pid}/mailbox").status_code == 200
    c.app.state.draft.tls_pin = ""  # as if this profile had no pin yet
    r = c.post("/wizard/test-connection", data={**_form(imap, smtp), **f}).json()
    assert r["status"] == "trust"
    assert c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()["ok"]
    assert c.app.state.draft.tls_pin == fp


def test_pin_approved_for_a_does_not_change_b(web, bridge):
    c, f = web
    imap, smtp, fp = bridge
    store, (a, b) = _two_profiles(c, imap, smtp)
    _approve_for(c, f, a, imap, smtp, fp)
    assert not hasattr(c.app.state, "approved_pin")
    assert _post_mailbox(c, f, a, imap, smtp).status_code == 303
    assert store.get_profile(a).mailbox.tls_cert_sha256 == fp
    # Now edit B without approving anything: B keeps its own pin.
    c.get(f"/settings/{b}/mailbox")
    assert _post_mailbox(c, f, b, imap, smtp).status_code == 303
    assert store.get_profile(b).mailbox.tls_cert_sha256 == PIN_B


def test_pin_approved_for_a_is_not_applied_when_posting_b_directly(web, bridge):
    c, f = web
    imap, smtp, fp = bridge
    store, (a, b) = _two_profiles(c, imap, smtp)
    _approve_for(c, f, a, imap, smtp, fp)
    assert _post_mailbox(c, f, b, imap, smtp).status_code == 303  # no GET for B first
    assert store.get_profile(b).mailbox.tls_cert_sha256 == PIN_B
    assert store.get_profile(a).mailbox.tls_cert_sha256 == PIN_A


def test_pin_is_cleared_after_save(web, bridge):
    c, f = web
    imap, smtp, fp = bridge
    _store, (a, _b) = _two_profiles(c, imap, smtp)
    _approve_for(c, f, a, imap, smtp, fp)
    assert _post_mailbox(c, f, a, imap, smtp).status_code == 303
    assert c.app.state.draft is None and c.app.state.pending_pin is None


def test_new_draft_drops_pending_pin(web):
    c, _f = web
    c.app.state.pending_pin = PIN_A
    c.get("/wizard/consent?new=1")
    assert c.app.state.pending_pin is None


def test_edit_without_new_approval_keeps_saved_pin(web, bridge):
    c, f = web
    imap, smtp, _fp = bridge
    store, (a, _b) = _two_profiles(c, imap, smtp)
    c.get(f"/settings/{a}/mailbox")
    assert _post_mailbox(c, f, a, imap, smtp).status_code == 303
    assert store.get_profile(a).mailbox.tls_cert_sha256 == PIN_A


def test_import_drops_pending_pin_and_old_prompt_cannot_pin_imported_draft(web):
    """SEC-56: importing a bundle replaces the draft, so a stale pending pin must go too."""
    import json

    from freemyid.crypto import export_with_passphrase
    from freemyid.wizard.flows import BUNDLE_VERSION
    c, f = web
    c.get("/wizard/consent?new=1")
    c.app.state.pending_pin = PIN_A
    blob = export_with_passphrase(json.dumps({
        "freemyid_bundle": BUNDLE_VERSION,
        "profile": {"label": "Test", "name": {"first": "Test", "last": "Person"},
                    "addresses": [{"city": "Testville", "state": "NC", "current": True}]}}).encode(), "pw-test-1234")
    r = c.post("/wizard/import", data={"passphrase": "pw-test-1234", **f},
               files={"bundle": ("a.freemyid-profile", blob)})
    assert r.status_code == 303, r.text
    assert c.app.state.pending_pin is None
    r = c.post("/wizard/trust-certificate", data={"answer": "yes", **f}).json()
    assert not r["ok"] and not c.app.state.draft.tls_pin
