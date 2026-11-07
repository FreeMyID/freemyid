"""v0.3 app pages: Today, broker detail, Protect yourself, summary, theme. Fake people only."""
from __future__ import annotations

import filecmp
from pathlib import Path

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.models import (
    Address,
    BrokerStatus,
    Consent,
    ConsentBasis,
    Listing,
    ListingState,
    MatchLevel,
    PersonName,
    Profile,
    Request,
    RequestKind,
    RequestStatus,
    Todo,
    TodoKind,
)
from freemyid.models import Method as M
from freemyid.storage import Store
from freemyid.wizard import protect
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-v03"


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
    p = Profile(label="Jane", name=PersonName(first="Jane", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                                text_version="t"))
    store.save_profile(p)
    return c, store, p, opened, {"csrf": _csrf_for(TOKEN)}


def _todo(p):
    return Todo(profile_id=p.id, broker_id="examplebroker", kind=TodoKind.ASSISTED_OPT_OUT,
                title="Remove your listing", body="1. Find it\n2. Click Remove",
                links=["https://example.com/optout"])


def test_today_one_big_card_then_progress_line(env):
    c, store, p, _, _ = env
    store.save_todo(_todo(p))
    store.save_todo(_todo(p).model_copy(update={"id": "b" * 32, "title": "Second one"}))
    store.save_request(Request(profile_id=p.id, broker_id="examplebroker", kind=RequestKind.OPT_OUT,
                               method=M.EMAIL, status=RequestStatus.SENT))
    store.save_request(Request(profile_id=p.id, broker_id="x", kind=RequestKind.OPT_OUT,
                               method=M.EMAIL, status=RequestStatus.SENT, dry_run=True))
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.CONFIRMED))
    t = c.get("/").text
    assert t.count('class="card hero-card"') == 1 and "Next for you" in t
    assert "1 request sent, 1 confirmed, 2 need you" in t     # practice request not counted
    assert t.index("hero-card") < t.index("1 request sent") < t.index("Also waiting (1)")
    assert t.count("<h1") == 1                                # one h1 per page
    assert "Coming soon" in t or "Where you are listed" in t


def test_today_calm_when_nothing_to_do(env):
    c, *_ = env
    t = c.get("/").text
    assert "Nothing needs you today" in t and "0 requests sent, 0 confirmed, 0 need you" in t
    assert "/static/img/safety-local.svg" in t


def test_layout_a11y_basics(env):
    c, *_ = env
    t = c.get("/").text
    assert 'class="skip" href="#main"' in t and '<main id="main"' in t
    assert 'aria-current="page">Today' in t and "theme-toggle" in t
    assert "/static/tokens.css" in t and "<style" not in t and 'style="' not in t
    assert "http://" not in t and "https://" not in t          # nothing external, no inline URLs


def test_tokens_css_matches_site_copy():
    here = Path(__file__).resolve().parents[1]
    site = here / "web" / "src" / "styles" / "tokens.css"
    if site.exists():
        assert filecmp.cmp(site, here / "src/freemyid/wizard/static/tokens.css", shallow=False), \
            "static/tokens.css drifted from web/src/styles/tokens.css: copy it again"


def test_broker_page(env):
    c, store, p, _, _ = env
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.SUBMITTED))
    store.save_listing(Listing(profile_id=p.id, broker_id="examplebroker", url="https://e.example/x",
                               name_shown="Jane Testperson", age_shown=60,
                               locations_shown=["Springfield, IL"], match_score=90,
                               match_level=MatchLevel.CONFIRMED))
    store.save_request(Request(profile_id=p.id, broker_id="examplebroker", kind=RequestKind.OPT_OUT,
                               method=M.EMAIL, status=RequestStatus.SENT))
    r = c.get(f"/profile/{p.id}/site/examplebroker")
    assert r.status_code == 200
    t = r.text
    for want in ("What this site shows about you", "Springfield, IL", "Deletion request",
                 "What came back", "Next check", "Receipts"):
        assert want in t
    assert c.get(f"/profile/{p.id}/site/../x").status_code in (404, 307, 308)
    assert c.get(f"/profile/{p.id}/site/Bad%20Id").status_code == 404
    assert c.get("/profile/nope/site/examplebroker").status_code == 404
    assert f"/profile/{p.id}/site/examplebroker" in c.get(f"/profile/{p.id}").text


def test_protect_page_and_ticks_persist(env):
    c, store, p, opened, f = env
    r = c.get("/protect")
    assert r.status_code == 200 and "Protect yourself" in r.text
    cf = protect.load_checklists()
    assert cf is not None
    first = cf.checklists[0]
    assert protect.progress(store, p.id) == {}
    assert c.post(f"/protect/{p.id}/{first.id}/done", data=f).status_code == 303
    assert protect.progress(store, p.id) == {first.id: True}
    assert protect.counts(store, p.id) == (1, len(cf.checklists))
    assert f"1 of {len(cf.checklists)} done" in c.get("/protect").text
    c.post(f"/protect/{p.id}/{first.id}/undo", data=f)
    assert protect.progress(store, p.id) == {first.id: False}
    # unknown ids are ignored and nothing is written
    n = len(store.events(p.id))
    c.post(f"/protect/{p.id}/nope_id/done", data=f)
    c.post(f"/protect/{p.id}/BAD..id/done", data=f)
    assert len(store.events(p.id)) == n
    # open uses the checklist's own URL only
    c.post(f"/protect/{p.id}/{first.id}/open", data=f)
    assert opened == [str(first.url)]
    # ticks hold no free text
    assert all(ev.detail == {"checklist": first.id} for ev in store.events(p.id)
               if ev.action.startswith("checklist"))


def test_protect_requires_csrf(env):
    c, store, p, *_ = env
    r = c.post(f"/protect/{p.id}/{protect.load_checklists().checklists[0].id}/done", data={})
    assert r.status_code == 403 and protect.progress(store, p.id) == {}


def test_partial_checklist_shows_calm_note(env):
    c, *_ = env
    cf = protect.load_checklists()
    partial = [x for x in cf.checklists if x.verification == "partial"]
    t = c.get("/protect").text
    if partial:
        assert t.count("could not read this company") == len(partial)
        assert "HTTP 403" not in t           # editor notes never reach the user
        assert "Do not publish" not in t


def test_summary_is_printable_and_pii_light(env):
    c, store, p, _, _ = env
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.REMOVED))
    r = c.get(f"/profile/{p.id}/summary")
    t = r.text
    assert r.status_code == 200 and "What Free My ID did for Jane" in t and "examplebroker" in t
    assert "Springfield" not in t and "Testperson" not in t and 'data-print="1"' in t
    assert c.get("/profile/nope/summary").status_code == 404
    css = (Path(__file__).resolve().parents[1] / "src/freemyid/wizard/static/style.css").read_text()
    assert "@media print" in css


def test_exposure_card_with_and_without_engine(env, monkeypatch):
    import sys
    import types

    from freemyid.exposure_models import ExposureEntry, ExposureResult
    from freemyid.wizard import views
    _, store, p, *_ = env
    monkeypatch.setitem(sys.modules, "freemyid.engine.exposure", None)   # forces ImportError
    assert "Coming soon" in views.exposure_card(store, p)
    mod = types.ModuleType("freemyid.engine.exposure")
    res = ExposureResult(profile_id=p.id, score=40, entries=[
        ExposureEntry(broker_id="a", broker_name="A", status="found"),
        ExposureEntry(broker_id="b", broker_name="B", status="check_by_hand")])
    mod.latest_exposure = lambda s, pr: res                              # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "freemyid.engine.exposure", mod)
    t = views.exposure_card(store, p)
    assert "<b>40</b> out of 100" in t and "1 site list you, 1 to look at by hand" in t
    mod.latest_exposure = lambda s, pr: None                             # type: ignore[attr-defined]
    assert "No picture yet" in views.exposure_card(store, p)

    def boom(s, pr):
        raise RuntimeError("x")
    mod.latest_exposure = boom                                           # type: ignore[attr-defined]
    assert "not available" in views.exposure_card(store, p)
