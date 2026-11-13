"""WO-633 (field report F4): pressing Finish twice, or while the scheduled job was still
being installed, showed "Consent has not been given" although the person was already saved.

Finish is answered at once, a repeat goes to the home page with the same "all set" message,
and the consent gate still refuses a draft nobody agreed to. Fake people only."""
from __future__ import annotations

import threading

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid import scheduler
from freemyid.consent import CURRENT_TEXT_VERSION, consent_ok
from freemyid.models import Consent, ConsentBasis
from freemyid.storage import Store
from freemyid.wizard import draft as dr
from freemyid.wizard import server
from freemyid.wizard.server import MSGS, STATIC_DIR, _csrf_for, create_app

TOKEN = "tok-wo633"
OLD_MESSAGE = "Consent has not been given"
STEPS = [
    ("consent", {"basis": "self", "attested_by": "Jane Q Testperson", "ack": "1"}),
    ("name", {"first": "Jane", "middle": "Q", "last": "Testperson", "label": "Jane"}),
    ("address", {"city0": "Springfield", "state0": "il", "current": "0"}),
    ("about", {"birth_year": "1980", "phones": "555-0100"}),
    ("mailbox", {"provider": "gmail", "address": "jane.freemyid@example.com",
                 "password": "pw"}),
]
FINISH = {"weekly_recheck": "1"}


@pytest.fixture
def store(tmp_path, monkeypatch) -> Store:
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    monkeypatch.setattr(keyring, "set_password", lambda s, u, p: None)
    return Store()


def client(store: Store, **kw) -> tuple[TestClient, dict[str, str]]:
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None, **kw)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    return c, {"csrf": _csrf_for(TOKEN)}


def fill_in(c: TestClient, f: dict[str, str]) -> None:
    assert c.get("/wizard/consent?new=1").status_code == 200
    for step, data in STEPS:
        r = c.post(f"/wizard/{step}", data={**data, **f})
        assert r.status_code == 303, (step, r.text[:300])


def join_background() -> None:
    for t in threading.enumerate():
        if t.name == "freemyid-first-run":
            t.join(10)
            assert not t.is_alive()


# ------------------------------------------------------------------ finish pressed twice

def test_second_finish_post_goes_to_the_dashboard_not_an_error(store):
    calls: list[str] = []
    c, f = client(store, on_finish=lambda p, on: calls.append(p.id))
    fill_in(c, f)
    first = c.post("/wizard/finish", data={**FINISH, **f})
    assert (first.status_code, first.headers["location"]) == (303, "/?msg=created")
    for _ in range(3):   # double click, page re-post, Back then Finish
        again = c.post("/wizard/finish", data={**FINISH, **f})
        assert OLD_MESSAGE not in again.text
        assert (again.status_code, again.headers["location"]) == (303, "/?msg=created")
    [p] = store.list_profiles()
    assert calls == [p.id]                      # saved once, first check started once
    assert len([e for e in store.events(p.id) if e.action == "profile_created"]) == 1
    assert MSGS["created"] in c.get(again.headers["location"]).text


def test_back_to_a_wizard_page_after_finish_goes_to_the_dashboard(store):
    c, f = client(store, on_finish=lambda p, on: None)
    fill_in(c, f)
    assert c.post("/wizard/finish", data={**FINISH, **f}).status_code == 303
    r = c.get("/wizard/finish")
    assert (r.status_code, r.headers["location"]) == (303, "/?msg=created")
    r = c.post("/wizard/mailbox", data={"skip_mailbox": "1", **f})
    assert (r.status_code, r.headers["location"]) == (303, "/?msg=created")
    assert len(store.list_profiles()) == 1


def test_second_save_after_editing_goes_to_the_dashboard(store):
    c, f = client(store, on_finish=lambda p, on: None)
    fill_in(c, f)
    c.post("/wizard/finish", data={**FINISH, **f})
    [p] = store.list_profiles()
    assert c.get(f"/profile/{p.id}/edit").status_code == 303
    for _ in range(2):
        r = c.post("/wizard/finish", data={**FINISH, **f})
        assert (r.status_code, r.headers["location"]) == (303, "/?msg=updated")
    assert len(store.list_profiles()) == 1


# ------------------------------------------------------------------ slow scheduler install

def test_finish_answers_while_the_scheduler_install_is_still_running(store, monkeypatch):
    started, release, installs = threading.Event(), threading.Event(), []

    def slow_install() -> str:
        installs.append(1)
        started.set()
        assert release.wait(10)
        return "installed"

    monkeypatch.setattr(server, "_background_disabled", lambda: False)
    monkeypatch.setattr(scheduler, "install", slow_install)
    c, f = client(store)
    fill_in(c, f)
    try:
        first = c.post("/wizard/finish", data={**FINISH, **f})
        assert (first.status_code, first.headers["location"]) == (303, "/?msg=created")
        assert started.wait(10) and not release.is_set()     # install is still running
        again = c.post("/wizard/finish", data={**FINISH, **f})
        assert (again.status_code, again.headers["location"]) == (303, "/?msg=created")
        home = c.get("/?msg=created")
        assert home.status_code == 200 and MSGS["created"] in home.text
        assert server.SCHED_PROBLEM not in home.text
    finally:
        release.set()
        join_background()
    assert installs == [1]
    assert len(store.list_profiles()) == 1
    assert server.SCHED_PROBLEM not in c.get("/").text


def test_scheduler_failure_is_reported_on_the_dashboard(store, monkeypatch):
    def broken_install() -> str:
        raise OSError("synthetic schtasks failure for Jane Q Testperson")

    monkeypatch.setattr(server, "_background_disabled", lambda: False)
    monkeypatch.setattr(scheduler, "install", broken_install)
    c, f = client(store)
    fill_in(c, f)
    r = c.post("/wizard/finish", data={**FINISH, **f})
    assert (r.status_code, r.headers["location"]) == (303, "/?msg=created")
    join_background()
    home = c.get("/")
    assert home.status_code == 200 and server.SCHED_PROBLEM in home.text
    assert 'href="/settings"' in home.text and "synthetic" not in home.text
    # turning it on by hand in Settings clears the note
    monkeypatch.setattr(scheduler, "install", lambda: "installed")
    assert c.post("/schedule/install", data=f).headers["location"] == "/settings?msg=sched_on"
    assert server.SCHED_PROBLEM not in c.get("/").text


def test_no_scheduler_install_when_the_person_did_not_ask_for_it(store, monkeypatch):
    installs: list[int] = []
    monkeypatch.setattr(server, "_background_disabled", lambda: False)
    monkeypatch.setattr(scheduler, "install", lambda: installs.append(1))
    c, f = client(store)
    fill_in(c, f)
    assert c.post("/wizard/finish", data=f).status_code == 303     # box not ticked
    join_background()
    assert installs == [] and server.SCHED_PROBLEM not in c.get("/").text


# ------------------------------------------------------------------ the gate stays closed

def test_finish_without_consent_is_still_refused_and_says_what_to_do(store):
    c, f = client(store, on_finish=lambda p, on: pytest.fail("nothing was saved"))
    r = c.post("/wizard/finish", data={**FINISH, **f})
    assert r.status_code == 400 and store.list_profiles() == []
    assert OLD_MESSAGE not in r.text
    assert "go back to the first step" in r.text


def test_a_new_person_after_finish_is_not_waved_through(store):
    """The repeat-finish answer only covers the person just saved, never a new draft."""
    c, f = client(store, on_finish=lambda p, on: None)
    fill_in(c, f)
    c.post("/wizard/finish", data={**FINISH, **f})
    assert c.get("/wizard/consent?new=1").status_code == 200
    c.post("/wizard/name", data={"first": "John", "last": "Testperson", **f})
    r = c.post("/wizard/finish", data={**FINISH, **f})
    assert r.status_code == 400 and "go back to the first step" in r.text
    assert [p.name.first for p in store.list_profiles()] == ["Jane"]


def test_build_profile_refuses_a_draft_without_consent():
    with pytest.raises(dr.SaveError):
        dr.build_profile(dr.Draft(first="Jane", last="Testperson"))


# ------------------------------------------------------------------ the Finish button

def test_finish_button_is_marked_to_show_saving(store):
    c, f = client(store)
    fill_in(c, f)
    page = c.get("/wizard/finish").text
    assert 'data-busy="Saving..."' in page
    assert 'data-busy' not in c.get("/wizard/name").text
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "data-busy" in js and "disabled = true" in js


# ------------------------------------------------------------------ authorized agent

def test_home_page_accepts_an_authorized_agent_with_a_stored_document(store):
    from freemyid.models import Address, PersonName, Profile
    p = Profile(label="Jane", name=PersonName(first="Jane", middle="Q", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)], age=46,
                consent=Consent(basis=ConsentBasis.AUTHORIZED_AGENT,
                                attested_by="John Testperson",
                                text_version=CURRENT_TEXT_VERSION))
    store.save_profile(p)
    c, _ = client(store)
    assert "Not running yet for Jane" in c.get("/").text          # no document yet: refused
    doc = dr.save_authorization(store, p.id, "synthetic-authorization.pdf",
                                b"%PDF-1.4 synthetic signed form")
    p = p.model_copy(update={"consent": p.consent.model_copy(
        update={"authorization_doc": doc})})
    store.save_profile(p)
    assert consent_ok(p, store) == (True, "")
    for url in ("/", f"/profile/{p.id}"):
        r = c.get(url)
        assert r.status_code == 200 and "Not running yet" not in r.text
