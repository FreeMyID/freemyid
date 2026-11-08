"""WO-001: Checklist tips ('Good to know') and durable ticks in the app.

Tests acceptance criteria:
- Tips appear under a 'Good to know' heading after steps; checklists without tips have no heading.
- Research `notes` never appear on any rendered page.
- Ticking and unticking in the app agree with checklist_state;
  old untagged ticks still read as done.
- Visiting site pages for reserved internal ids (_checklist, _consent) 404s (no broker shown).
- Fake data only (Pat Testperson, Springfield IL).
"""
from __future__ import annotations

from datetime import date

import keyring
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from freemyid import checklist_state as cs
from freemyid.models import (
    Actor,
    Address,
    BrokerStatus,
    Checklist,
    ChecklistFile,
    Consent,
    ConsentBasis,
    Event,
    ListingState,
    PersonName,
    Profile,
)
from freemyid.storage import Store
from freemyid.wizard import protect, views
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-protect-tips"


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
    return c, store, p, opened, {"csrf": _csrf_for(TOKEN)}


def _make_fake_checklists(distinctive_notes: str = "") -> ChecklistFile:
    c1 = Checklist(
        id="freeze_pat",
        title="Freeze your credit at Bureau A",
        why="A freeze stops a thief from opening new credit in your name.",
        url="https://example.com/freeze",
        cost="Free to place, lift and remove.",
        time_needed="About 10 minutes online.",
        need_on_hand=["Your Social Security number", "Date of birth"],
        steps=["Open the web address.", "Choose Place a Security Freeze."],
        how_to_undo="Sign in to lift the freeze.",
        tips=[
            "A freeze at one bureau does not freeze the others. Freeze all of them.",
            "Never pay anyone to freeze your credit. It is free.",
        ],
        source_urls=["https://example.com/freeze"],
        date_checked=date(2026, 11, 7),
        verification="official_page",
        notes=distinctive_notes or "Research note: checked official site on 2026-11-07.",
    )
    c2 = Checklist(
        id="optout_pat",
        title="Stop junk mail offers",
        why="Stops pre-approved offers in the mail.",
        url="https://example.com/optout",
        cost="Free.",
        time_needed="5 minutes online.",
        need_on_hand=[],
        steps=["Open the website.", "Type your name and address."],
        how_to_undo="Use the same website to opt back in.",
        tips=[],
        source_urls=["https://example.com/optout"],
        date_checked=date(2026, 11, 7),
        verification="official_page",
        notes=distinctive_notes or "Research note: unverified phone number removed.",
    )
    return ChecklistFile(version="2026.11.07", updated=date(2026, 11, 7), checklists=[c1, c2])


def test_checklist_with_tips_shows_good_to_know():
    cf = _make_fake_checklists()
    c_tips, c_notips = cf.checklists[0], cf.checklists[1]
    p = Profile(label="Pat", name=PersonName(first="Pat", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                text_version="t"))

    html = views.protect_page(cf, [p], p, {}, "csrf-token")

    # Item with tips shows heading and every tip
    assert "<h2 class=\"sub\">Good to know</h2>" in html
    for tip in c_tips.tips:
        assert f"<li>{tip}</li>" in html

    # Heading placement: after steps and before undo
    steps_idx = html.index("<h2 class=\"sub\">Steps</h2>")
    tips_idx = html.index("<h2 class=\"sub\">Good to know</h2>")
    undo_idx = html.index("<b>To undo it:</b>")
    assert steps_idx < tips_idx < undo_idx

    # Item without tips has no "Good to know" heading
    assert html.count("<h2 class=\"sub\">Good to know</h2>") == 1  # only on c_tips, never on c_notips
    body_no_tips = views._checklist_item(c_notips, False, p.id, "csrf-token")
    assert "Good to know" not in body_no_tips
    assert "<h2 class=\"sub\">Good to know</h2>" not in body_no_tips


def test_notes_text_never_appears_in_rendered_page():
    secret = "DISTINCTIVE_RESEARCH_NOTE_XYZ_987654_DO_NOT_LEAK"
    cf = _make_fake_checklists(distinctive_notes=secret)
    p = Profile(label="Pat", name=PersonName(first="Pat", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                text_version="t"))

    html = views.protect_page(cf, [p], p, {}, "csrf-token")
    assert secret not in html

    for c in cf.checklists:
        item_html = views._checklist_item(c, False, p.id, "csrf-token")
        assert secret not in item_html


def test_ticks_app_and_checklist_state_agree(env):
    c, store, p, _, f = env
    cf = protect.load_checklists()
    assert cf is not None
    cid = cf.checklists[0].id

    # Start: not done
    assert cs.progress(store, p.id) == {}
    assert protect.progress(store, p.id) == {}
    assert protect.counts(store, p.id) == (0, len(cf.checklists))

    # Tick in the app
    res = c.post(f"/protect/{p.id}/{cid}/done", data=f)
    assert res.status_code == 303

    # checklist_state and protect agree it is done
    assert cs.progress(store, p.id) == {cid: True}
    assert protect.progress(store, p.id) == {cid: True}
    assert cs.ticks(store, p.id)[cid].done is True
    assert protect.counts(store, p.id) == (1, len(cf.checklists))

    # Event logged has reserved TAG broker_id '_checklist' and no PII
    events = store.events(p.id)
    assert len(events) == 1
    ev = events[0]
    assert ev.broker_id == cs.TAG == "_checklist"
    assert ev.actor == Actor.USER
    assert ev.action == cs.DONE
    assert ev.detail == {"checklist": cid}

    # UI displays done state
    page_text = c.get("/protect").text
    assert f"1 of {len(cf.checklists)} done" in page_text
    assert f'class="card cl done" id="c-{cid}"' in page_text

    # Untick in the app
    res = c.post(f"/protect/{p.id}/{cid}/undo", data=f)
    assert res.status_code == 303

    # checklist_state and protect agree it is undone
    assert cs.progress(store, p.id) == {cid: False}
    assert protect.progress(store, p.id) == {cid: False}
    assert cs.ticks(store, p.id)[cid].done is False
    assert protect.counts(store, p.id) == (0, len(cf.checklists))


def test_old_untagged_tick_reads_as_done(env):
    c, store, p, _, f = env
    cf = protect.load_checklists()
    assert cf is not None
    cid = cf.checklists[1].id

    # Simulate legacy tick event written by v1 (broker_id None, untagged)
    store.log(Event(profile_id=p.id, broker_id=None, actor=Actor.USER,
                    action=cs.DONE, detail={"checklist": cid}))

    # Reads as done via checklist_state and protect
    assert cs.progress(store, p.id) == {cid: True}
    assert protect.progress(store, p.id) == {cid: True}
    assert protect.counts(store, p.id) == (1, len(cf.checklists))

    # App page renders it as ticked
    page_text = c.get("/protect").text
    assert f'class="card cl done" id="c-{cid}"' in page_text

    # App untick writes a tagged event and overrides legacy tick
    c.post(f"/protect/{p.id}/{cid}/undo", data=f)
    assert cs.progress(store, p.id) == {cid: False}
    assert protect.progress(store, p.id) == {cid: False}


def test_site_page_ignores_internal_ids_checklist_and_consent(env):
    c, store, p, _, _ = env

    # Visiting site page for _checklist returns 404 (never shows as a broker)
    r_chk = c.get(f"/profile/{p.id}/site/_checklist")
    assert r_chk.status_code == 404

    # Visiting site page for _consent returns 404 (matching _consent)
    r_con = c.get(f"/profile/{p.id}/site/_consent")
    assert r_con.status_code == 404

    # Direct call to broker_page with reserved internal ids raises HTTPException 404
    with pytest.raises(HTTPException) as exc_chk:
        views.broker_page(p, None, "_checklist", store.get_status(p.id, "_checklist"),
                          [], [], [], [], [])
    assert exc_chk.value.status_code == 404

    with pytest.raises(HTTPException) as exc_con:
        views.broker_page(p, None, "_consent", store.get_status(p.id, "_consent"),
                          [], [], [], [], [])
    assert exc_con.value.status_code == 404


def test_summary_page_skips_internal_ids():
    p = Profile(label="Pat", name=PersonName(first="Pat", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                text_version="t"))
    statuses = [
        BrokerStatus(profile_id=p.id, broker_id="_checklist", state=ListingState.CONFIRMED),
        BrokerStatus(profile_id=p.id, broker_id="_consent", state=ListingState.CONFIRMED),
        BrokerStatus(profile_id=p.id, broker_id="realbroker", state=ListingState.CONFIRMED),
    ]
    names = {"realbroker": "Real Broker Inc"}

    html = views.summary_page(p, statuses, names, 0, 1)

    assert "Real Broker" in html
    assert "_checklist" not in html
    assert "_consent" not in html
    assert "1 site has confirmed" in html  # only realbroker counted, not 3
