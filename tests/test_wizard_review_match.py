"""'Is this you?' buttons on REVIEW_MATCH to-dos: routes, engine effect, guards."""
from __future__ import annotations

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.models import (
    Address,
    Consent,
    ConsentBasis,
    Listing,
    MatchLevel,
    PersonName,
    Profile,
    Todo,
    TodoKind,
)
from freemyid.storage import Store
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-test"


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

    def person(label):
        p = Profile(label=label, name=PersonName(first="Jane", last="Testperson"),
                    addresses=[Address(city="Springfield", state="IL", current=True)],
                    consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                                    text_version="t"))
        store.save_profile(p)
        return p
    p = person("Jane")
    li = Listing(profile_id=p.id, broker_id="examplebroker", url="https://example.com/p/1",
                 match_score=60, match_level=MatchLevel.POSSIBLE, match_reasons=["city"])
    store.save_listing(li)
    t = Todo(profile_id=p.id, broker_id="examplebroker", kind=TodoKind.REVIEW_MATCH,
             title="Is this Jane? (Example)", body="b", links=[li.url],
             resume_token=f"review:{li.id}")
    store.save_todo(t)
    return c, store, p, li, t, {"csrf": _csrf_for(TOKEN), "listing_id": li.id}, person


def _level(store, p, li):
    return next(x for x in store.list_listings(p.id) if x.id == li.id)


def test_card_shows_buttons_and_plain_promises(env):
    c = env[0]
    h = c.get("/").text
    for s in ("Yes, this is me", "No, this is not me", "Open the page",
              "ask this site to take the listing down", "nothing will be sent for this listing",
              "the name is the same, and so is the city"):
        assert s in h
    assert "I finished it" not in h and "https://example.com/p/1" not in h


def test_yes_confirms_and_closes(env):
    c, store, p, li, t, f, _ = env
    r = c.post(f"/todo/{t.id}/review/yes", data=f)
    assert r.status_code == 303 and "review_yes" in r.headers["location"]
    got = _level(store, p, li)
    assert got.match_level == MatchLevel.CONFIRMED and "user_confirmed" in got.match_reasons
    assert store.list_todos(p.id) == []


def test_no_rejects_and_closes(env):
    c, store, p, li, t, f, _ = env
    r = c.post(f"/todo/{t.id}/review/no", data=f)
    assert r.status_code == 303 and "review_no" in r.headers["location"]
    got = _level(store, p, li)
    assert got.match_level == MatchLevel.NO_MATCH and got.match_reasons == ["user_rejected"]
    assert store.list_todos(p.id) == []


def test_double_submit_is_harmless_and_cannot_flip_the_answer(env):
    c, store, p, li, t, f, _ = env
    c.post(f"/todo/{t.id}/review/yes", data=f)
    r = c.post(f"/todo/{t.id}/review/no", data=f)
    assert r.status_code == 303 and "review_gone" in r.headers["location"]
    assert _level(store, p, li).match_level == MatchLevel.CONFIRMED


def test_mismatched_ids_rejected(env):
    c, store, p, li, t, f, person = env
    r = c.post(f"/todo/{t.id}/review/yes", data={**f, "listing_id": "0" * 32})
    assert r.status_code == 400
    # a listing of another person, with its own id forged into the form
    q = person("Other")
    other = Listing(profile_id=q.id, broker_id="examplebroker", url="https://example.com/p/2",
                    match_score=60, match_level=MatchLevel.POSSIBLE)
    store.save_listing(other)
    r = c.post(f"/todo/{t.id}/review/yes", data={**f, "listing_id": other.id})
    assert r.status_code == 400
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE
    assert len(store.list_todos(p.id)) == 1
    # a non-review to-do can't be answered this way
    a = Todo(profile_id=p.id, broker_id="b", kind=TodoKind.ASSISTED_OPT_OUT, title="x", body="y")
    store.save_todo(a)
    assert c.post(f"/todo/{a.id}/review/yes", data=f).status_code == 400
    assert c.post(f"/todo/{t.id}/review/maybe", data=f).status_code == 303
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE


@pytest.mark.parametrize("origin", ["http://evil.example", "null"])
def test_forged_origin_and_missing_csrf_rejected(env, origin):
    c, store, p, li, t, f, _ = env
    assert c.post(f"/todo/{t.id}/review/yes", data=f,
                  headers={"Origin": origin}).status_code == 403
    assert c.post(f"/todo/{t.id}/review/yes",
                  data={"listing_id": li.id}).status_code == 403
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE
    assert len(store.list_todos(p.id)) == 1


@pytest.mark.parametrize("answer,level", [("yes", MatchLevel.CONFIRMED),
                                          ("no", MatchLevel.NO_MATCH)])
def test_engine_answer_survives_a_rescan(env, answer, level):
    """The route's answer is what the runner's next scan keeps (yes -> submit, no -> never)."""
    from freemyid.engine.runner import merge_listings
    from freemyid.models import Broker
    c, store, p, li, t, f, _ = env
    c.post(f"/todo/{t.id}/review/{answer}", data=f)
    assert store.list_todos(p.id) == []
    fresh = li.model_copy(update={"id": "f" * 32, "match_level": MatchLevel.POSSIBLE,
                                  "match_reasons": ["city"]})
    from datetime import UTC, datetime
    broker = Broker.model_construct(id="examplebroker", name="Example")
    merge_listings(store, p, broker, [fresh], datetime.now(UTC))
    assert _level(store, p, li).match_level == level
