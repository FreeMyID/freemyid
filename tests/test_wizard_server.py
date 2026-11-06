"""Draft tests for the wizard server (qa to adopt). Fake people only."""
from __future__ import annotations

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.storage import Store
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-test"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    saved = {}
    monkeypatch.setattr(keyring, "set_password", lambda s, u, p: saved.__setitem__((s, u), p))
    store = Store()
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None)
    c = TestClient(app, follow_redirects=False)
    return c, store, saved


def authed(c):
    c.cookies.set("freemyid_session", TOKEN)
    return {"csrf": _csrf_for(TOKEN)}


def test_requires_token(env):
    c, _, _ = env
    assert c.get("/").status_code == 403
    r = c.get(f"/?t={TOKEN}")
    assert r.status_code == 303 and "freemyid_session" in r.cookies


def test_bad_host_and_csrf(env):
    c, _, _ = env
    f = authed(c)
    assert c.get("/", headers={"host": "evil.example"}).status_code == 403
    assert c.post("/wizard/names", data={"first": "A"}).status_code == 403
    assert f["csrf"]


def finish_hook(calls):
    return lambda prof, sched: calls.append((prof.id, sched))


def test_full_wizard_creates_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    saved, calls = {}, []
    monkeypatch.setattr(keyring, "set_password", lambda s, u, p: saved.__setitem__((s, u), p))
    store = Store()
    c = TestClient(create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None,
                              on_finish=finish_hook(calls)), follow_redirects=False)
    f = authed(c)
    assert c.get("/wizard/consent?new=1").status_code == 200
    steps = [
        ("consent", {"basis": "self", "attested_by": "Jane Q Testperson", "ack": "1"}),
        ("name", {"first": "Jane", "middle": "Q", "last": "Testperson", "label": "Jane"}),
        ("address", {"city0": "Springfield", "state0": "il", "current": "0"}),
        ("about", {"birth_year": "1980", "phones": "555-0100"}),
        ("mailbox", {"provider": "gmail", "address": "jane.freemyid@example.com",
                     "password": "pw"}),
        ("finish", {"weekly_recheck": "1"}),
    ]
    for step, data in steps:
        r = c.post(f"/wizard/{step}", data={**data, **f})
        assert r.status_code == 303, (step, r.text[:300])
    [p] = store.list_profiles()
    assert p.name.last == "Testperson" and p.addresses[0].state == "IL"
    assert p.mailbox and p.mailbox.imap_host == "imap.gmail.com"
    assert "pw" in saved.values() and "pw" not in p.model_dump_json()
    assert calls == [(p.id, True)]
    assert c.get("/").status_code == 200
    assert c.get(f"/profile/{p.id}").status_code == 200
    assert c.get("/outbox").status_code == 200
    assert c.get("/settings").status_code == 200


def test_minor_requires_guardian(env):
    c, _, _ = env
    f = authed(c)
    c.post("/wizard/consent", data=dict(basis="self", attested_by="Kid T", ack="1", **f))
    r = c.post("/wizard/about", data=dict(birth_year="2015", **f))
    assert r.status_code == 400


def test_outlook_rejected(env):
    c, _, _ = env
    f = authed(c)
    c.post("/wizard/consent", data=dict(basis="self", attested_by="J T", ack="1", **f))
    r = c.post("/wizard/mailbox", data=dict(provider="outlook", address="a@b.co",
                                            password="x", **f))
    assert r.status_code == 400
