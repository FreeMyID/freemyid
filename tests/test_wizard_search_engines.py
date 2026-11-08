"""Protect page 'Google and Bing' group, Today line and the POST routes (fake data only)."""
from __future__ import annotations

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid import checklist_state as cs
from freemyid.engine import search_engines as se
from freemyid.models import (
    Address,
    Consent,
    ConsentBasis,
    PersonName,
    Profile,
)
from freemyid.storage import Store
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-search-engines"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    monkeypatch.setattr(keyring, "set_password", lambda *a: None)
    store = Store()
    opened: list[str] = []
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None,
                     open_url=lambda u: opened.append(u) or True)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    p = Profile(label="Pat", name=PersonName(first="Pat", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                text_version="t"))
    store.save_profile(p)
    # the real opener is webbrowser.open; route it to our recorder
    monkeypatch.setattr(se.webbrowser, "open", lambda u: opened.append(u) or True)
    return c, store, p, opened, {"csrf": _csrf_for(TOKEN)}


def test_group_is_first_and_complete(env):
    c, store, p, _, _ = env
    html = c.get(f"/protect?p={p.id}").text
    assert 'id="engines-h"' in html
    assert html.index("Google and Bing") < html.index("Protect yourself</h1>") + 4000
    assert html.index('id="engines-h"') < html.index('class="progress" role="status">0 of')
    assert se.INTRO.split(".")[0][:40] in html.replace("&#x27;", "'")
    for g in se.guided_steps(store, p.id):
        assert "Open the page for me" in html
        assert "I did this" in html
        assert g.step.engine in html
    assert "Not done yet." in html


def test_open_requires_csrf(env):
    c, _, p, opened, _ = env
    r = c.post(f"/protect/{p.id}/search/google_results_about_you/open")
    assert r.status_code in (400, 403)
    assert opened == []


def test_open_opens_official_page_and_records(env):
    c, store, p, opened, csrf = env
    r = c.post(f"/protect/{p.id}/search/bing_content_removal/open", data=csrf)
    assert r.status_code == 303
    assert len(opened) == 1 and opened[0].startswith("https://")
    g = {x.checklist.id: x for x in se.guided_steps(store, p.id)}["bing_content_removal"]
    assert g.status == "opened" and g.opened_at is not None
    assert "You opened the page" in c.get(f"/protect?p={p.id}").text


def test_done_and_undo(env):
    c, store, p, _, csrf = env
    cid = "google_results_about_you"
    assert c.post(f"/protect/{p.id}/search/{cid}/done", data={}).status_code in (400, 403)
    assert c.post(f"/protect/{p.id}/search/{cid}/done", data=csrf).status_code == 303
    assert cs.ticks(store, p.id)[cid].done
    assert se.pending(se.guided_steps(store, p.id)) == 1
    assert "Done on" in c.get(f"/protect?p={p.id}").text
    c.post(f"/protect/{p.id}/search/{cid}/undo", data=csrf)
    assert se.pending(se.guided_steps(store, p.id)) == 2


def test_unknown_ids_rejected(env):
    c, store, p, opened, csrf = env
    for url in (f"/protect/{p.id}/search/freeze_equifax/open",
                f"/protect/{p.id}/search/nope/done",
                "/protect/nobody/search/bing_content_removal/open",
                f"/protect/{p.id}/search/bing_content_removal/explode"):
        r = c.post(url, data=csrf)
        assert r.status_code == 303 and r.headers["location"] == "/protect"
    assert opened == []
    assert cs.ticks(store, p.id) == {} or not any(t.done for t in cs.ticks(store, p.id).values())


def test_off_host_url_never_opened(env, monkeypatch):
    c, store, p, opened, csrf = env
    cf = cs.load_checklists()
    assert cf is not None
    bad = [x.model_copy(update={"url": "https://evil.example.com/x"}) if x.id.startswith(
        "bing") else x for x in cf.checklists]
    monkeypatch.setattr(cs, "load_checklists", lambda: cf.model_copy(update={"checklists": bad}))
    c.post(f"/protect/{p.id}/search/bing_content_removal/open", data=csrf)
    assert opened == []
    assert all(g.checklist.id != "bing_content_removal" for g in se.guided_steps(store, p.id))


def test_today_line_per_person(env):
    c, _store, p, _, csrf = env
    assert "Google and Bing: 2 steps to do" in c.get("/more").text
    c.post(f"/protect/{p.id}/search/google_results_about_you/done", data=csrf)
    assert "Google and Bing: 1 step to do" in c.get("/more").text
    c.post(f"/protect/{p.id}/search/bing_content_removal/done", data=csrf)
    assert "Google and Bing:" not in c.get("/more").text
