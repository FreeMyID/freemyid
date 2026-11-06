"""Draft tests for the 6-screen wizard (docs/PLAN_V1.md D6). Fake people only."""
from __future__ import annotations

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.storage import Store
from freemyid.wizard import draft as dr
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-test"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    saved, calls = {}, []
    monkeypatch.setattr(keyring, "set_password", lambda s, u, p: saved.__setitem__((s, u), p))
    store = Store()
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None,
                     on_finish=lambda p, on: calls.append(on))
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    return c, store, saved, calls, {"csrf": _csrf_for(TOKEN)}


def _until(c, f, last):
    """Complete the wizard up to (not including) `last`."""
    seq = [
        ("consent", {"basis": "self", "attested_by": "Jane Q Testperson", "ack": "1"}),
        ("name", {"first": "Jane", "last": "Testperson"}),
        ("address", {"city0": "Springfield", "state0": "IL"}),
        ("about", {"birth_year": "1975"}),
        ("mailbox", {"provider": "skip"}),
    ]
    for step, data in seq:
        if step == last:
            return
        assert c.post(f"/wizard/{step}", data={**data, **f}).status_code == 303, step


def test_six_screens_each_render_with_progress_and_back(env):
    c, _, _, _, f = env
    assert dr.STEPS == ["consent", "name", "address", "about", "mailbox", "finish"]
    c.get("/wizard/consent?new=1")
    _until(c, f, "finish")
    for i, step in enumerate(dr.STEPS):
        r = c.get(f"/wizard/{step}")
        assert r.status_code == 200
        assert f"Step {i + 1} of 6" in r.text and 'class="dots"' in r.text
        assert ("Back" in r.text) == (i > 0)
        assert "http://" not in r.text.replace("http://www.w3.org", "") or step == "consent"


def test_skip_mailbox_and_no_schedule(env):
    c, store, _, calls, f = env
    c.get("/wizard/consent?new=1")
    _until(c, f, "finish")
    assert c.post("/wizard/finish", data=f).status_code == 303   # box left unticked
    [p] = store.list_profiles()
    assert p.mailbox is None and calls == [False]
    assert p.age is not None            # birth year became an approximate age


def test_outlook_says_skip(env):
    c, _, _, _, f = env
    c.get("/wizard/consent?new=1")
    _until(c, f, "mailbox")
    r = c.post("/wizard/mailbox", data=dict(provider="outlook", **f))
    assert r.status_code == 400 and "by hand" in r.text


@pytest.mark.parametrize("prov,host", [("yahoo", "imap.mail.yahoo.com"),
                                       ("icloud", "imap.mail.me.com"),
                                       ("proton_bridge", "127.0.0.1")])
def test_provider_presets(env, prov, host):
    c, store, saved, _, f = env
    c.get("/wizard/consent?new=1")
    _until(c, f, "mailbox")
    r = c.post("/wizard/mailbox", data=dict(provider=prov, address="v@example.com",
                                            password="app-pw", **f))
    assert r.status_code == 303
    c.post("/wizard/finish", data={"weekly_recheck": "1", **f})
    [p] = store.list_profiles()
    assert p.mailbox.imap_host == host and "app-pw" in saved.values()


def test_mailbox_screen_lists_choices_and_help(env):
    c, _, _, _, f = env
    c.get("/wizard/consent?new=1")
    _until(c, f, "mailbox")
    t = c.get("/wizard/mailbox").text
    for word in ("Gmail", "Yahoo", "iCloud", "Proton", "Another email service",
                 "Skip, I&#x27;ll do these by hand", "App passwords"):
        assert word in t, word


def test_finish_default_checkbox_on(env):
    c, _, _, _, f = env
    c.get("/wizard/consent?new=1")
    _until(c, f, "finish")
    t = c.get("/wizard/finish").text
    assert 'name="weekly_recheck"' in t and "checked" in t


def test_settings_permissions_and_submissions(env):
    c, store, _, _, f = env
    c.get("/wizard/consent?new=1")
    _until(c, f, "finish")
    c.post("/wizard/finish", data=f)
    [p] = store.list_profiles()
    assert not p.permissions.allow_id_upload
    r = c.post(f"/settings/{p.id}/permissions", data={"allow_id_upload": "1", **f})
    assert r.status_code == 303
    assert store.get_profile(p.id).permissions.allow_id_upload
    assert "Practice mode" in c.get("/settings").text
    assert c.get(f"/settings/{p.id}/mailbox").status_code == 200
    r = c.post(f"/settings/{p.id}/mailbox", data=dict(provider="skip", **f))
    assert r.status_code == 303
