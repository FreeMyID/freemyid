"""Friendly error pages, window sizing, D9 'Fill it in for me' routes, installer/icon files."""
from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

from freemyid.engine import fill_for_me as ffm
from freemyid.models import TodoKind
from freemyid.wizard import desktop
from tests.test_wizard_dashboard import TOKEN, _assisted, env  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def test_bad_origin_is_friendly_403(env):  # noqa: F811
    c, _s, _p, _, f = env
    r = c.post("/todo/x/done", data=f, headers={"origin": "http://evil.example"})
    assert r.status_code == 403 and "Go back and try again" in r.text
    assert "Bad origin" not in r.text


def test_bad_csrf_and_no_cookie_friendly_403(env):  # noqa: F811
    c, *_ = env
    r = c.post("/todo/x/done", data={"csrf": "nope"})
    assert r.status_code == 403 and "Go back and try again" in r.text
    c.cookies.clear()
    r = c.get("/")
    assert r.status_code == 403 and "<html" in r.text


def test_window_geometry_fits_small_screen():
    w, h, x, y = desktop.window_geometry(1024, 768)
    assert w <= 922 and h <= 692 and x >= 0 and y >= 0 and x + w <= 1024
    assert desktop.window_geometry(None, None) == (1100, 820, None, None)
    w, h, *_ = desktop.window_geometry(3840, 2160)
    assert (w, h) == (1100, 820)


def test_consent_text_mailbox_optional():
    from freemyid.wizard.draft import CONSENT_TEXT
    assert "you set up" not in " ".join(CONSENT_TEXT).replace("if you set one up", "")


def test_icon_and_installer_settings():
    assert (ROOT / "packaging/windows/freemyid.ico").stat().st_size > 1000
    iss = (ROOT / "packaging/windows/freemyid.iss").read_text()
    for k in ("DisableDirPage=yes", "SetupIconFile=freemyid.ico"):
    assert "DisableReadyPage" not in iss  # Ready page stays on purpose (v0.1.3)
        assert k in iss
    assert "ArchitecturesAllowed=x64compatible" in iss
    assert "NextButton.OnClick" not in iss  # never auto-press Install for the person
    assert "icon=ICON" in (ROOT / "packaging/windows/freemyid.spec").read_text()


def _fill_env(env, monkeypatch, result, gate=None, ack=True):  # noqa: F811
    c, store, p, _, f = env
    if ack:
        from freemyid import paths
        (paths.home() / ".fill-confirmed").write_text("1")
    t = _assisted(p)
    store.save_todo(t)
    calls = []

    def stub(st, pid, bid, **kw):
        calls.append((pid, bid))
        if gate:
            gate.wait(5)
        return result
    monkeypatch.setattr(ffm, "fill_for_me_sync", stub)
    return c, store, t, f, calls


def _settle(c):
    for _ in range(100):
        r = c.get("/fill")
        if "Your turn" not in r.text:
            return r
        threading.Event().wait(0.05)
    raise AssertionError("fill never finished")


def test_fill_button_only_on_assisted_cards(env):  # noqa: F811
    c, store, p, _, _ = env
    store.save_todo(_assisted(p))
    assert "Fill it in for me" in c.get("/").text
    assert "Fill it in for me" in c.get(f"/profile/{p.id}").text


def test_fill_submitted(env, monkeypatch):  # noqa: F811
    res = SimpleNamespace(status="submitted", reason="success_text", submit_seen=True,
                          todo_id=None)
    c, _s, t, f, calls = _fill_env(env, monkeypatch, res)
    r = c.post(f"/todo/{t.id}/fill", data=f)
    assert r.status_code == 303 and r.headers["location"] == "/fill"
    r = _settle(c)
    assert r.status_code == 303 and "msg=fill_done" in r.headers["location"]
    assert calls and calls[0][1] == "examplebroker"


def test_fill_waiting_page_and_one_at_a_time(env, monkeypatch):  # noqa: F811
    gate = threading.Event()
    res = SimpleNamespace(status="fallback", reason="timeout", submit_seen=False, todo_id=None)
    c, store, t, f, calls = _fill_env(env, monkeypatch, res, gate)
    c.post(f"/todo/{t.id}/fill", data=f)
    page = c.get("/fill").text
    assert "Tick the" in page and "not a robot" in page and 'http-equiv="refresh"' in page
    r = c.post(f"/todo/{t.id}/fill", data=f)
    assert "msg=fill_busy" in r.headers["location"] and len(calls) <= 1
    gate.set()
    r = _settle(c)
    assert "msg=fill_none" in r.headers["location"]
    assert any(x.id == t.id for x in store.list_todos())   # card unchanged


def test_fill_fallback_submit_seen_offers_i_did_it(env, monkeypatch):  # noqa: F811
    res = SimpleNamespace(status="fallback", reason="unverified", submit_seen=True, todo_id=None)
    c, _s, t, f, _ = _fill_env(env, monkeypatch, res)
    c.post(f"/todo/{t.id}/fill", data=f)
    r = _settle(c)
    assert r.status_code == 200 and "I did it" in r.text and f"/todo/{t.id}/done" in r.text


def test_fill_requires_csrf_and_assisted(env, monkeypatch):  # noqa: F811
    res = SimpleNamespace(status="submitted", reason="", submit_seen=True, todo_id=None)
    c, store, t, f, calls = _fill_env(env, monkeypatch, res)
    assert c.post(f"/todo/{t.id}/fill", data={"csrf": "bad"}).status_code == 403
    mail = t.model_copy(update={"id": "ab" * 16, "kind": TodoKind.SEND_EMAIL_MANUALLY})
    store.save_todo(mail)
    r = c.post(f"/todo/{mail.id}/fill", data=f)
    assert r.headers["location"] == "/" and not calls




def test_fill_first_time_needs_confirm_page(env, monkeypatch):  # noqa: F811
    from freemyid import paths
    c, _s, t, f, calls = _fill_env(env, monkeypatch, SimpleNamespace(
        status="submitted", reason="x", submit_seen=True, todo_id=None), ack=False)
    r = c.post(f"/todo/{t.id}/fill", data=f)
    assert r.status_code == 303 and r.headers["location"] == f"/todo/{t.id}/fill/confirm"
    assert not calls
    page = c.get(f"/todo/{t.id}/fill/confirm").text
    assert "This sends a real request to the site." in page and 'name="confirm"' in page
    assert "alert(" not in page
    r = c.post(f"/todo/{t.id}/fill", data={**f, "confirm": "yes"})
    assert r.headers["location"] == "/fill"
    assert (paths.home() / ".fill-confirmed").exists()
    # one-time: next press goes straight through
    for _ in range(100):
        if not c.app.state.fill["running"]:
            break
        import time
        time.sleep(0.05)
    r = c.post(f"/todo/{t.id}/fill", data=f)
    assert r.headers["location"] == "/fill"


def test_about_step_copy_is_not_an_absolute_never_sent():
    from freemyid.wizard import ui
    from freemyid.wizard.draft import Draft

    body = ui._screen_body("about", Draft())
    assert "never sent to anyone" not in body
    assert "only sent what its own listing already shows" in body
