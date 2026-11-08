"""Search-engine exposure guided step (engine/search_engines.py). Never fetches anything."""
from __future__ import annotations

from datetime import date, timedelta

from freemyid import checklist_state as cs
from freemyid.engine import search_engines as se
from freemyid.models import (
    BrokerStatus,
    Checklist,
    ChecklistFile,
    ListingState,
    utcnow,
)
from tests.conftest import make_profile


def _c(cid: str, url: str) -> Checklist:
    return Checklist(id=cid, title=f"{cid} title", why="why", url=url, cost="Free.",
                     time_needed="10 minutes", steps=["Open the page.", "Do the steps."],
                     how_to_undo="undo", source_urls=[url], date_checked=date(2026, 11, 7),
                     verification="partial")


def _cf(*items: Checklist) -> ChecklistFile:
    return ChecklistFile(version="t", updated=date(2026, 11, 7), checklists=list(items))


GOOGLE = _c("google_results_about_you", "https://goo.gle/resultsaboutyou")
BING = _c("bing_content_removal", "https://www.bing.com/webmaster/tools/contentremovalform")
CF = _cf(GOOGLE, BING, _c("freeze_equifax", "https://www.equifax.com/x"))


def _p(store):
    p = make_profile()
    store.save_profile(p)
    return p


def test_real_checklist_file_has_the_google_step_on_an_official_host():
    cf = cs.load_checklists()
    assert cf is not None
    ids = [c.id for c in cf.checklists if se.is_search_step(c.id)]
    assert "google_results_about_you" in ids
    for c in cf.checklists:
        if se.is_search_step(c.id):
            step = next(s for s in se.STEPS if s.checklist_id == c.id)
            assert se.official_url(step, c), c.id
            assert c.source_urls


def test_steps_in_order_and_open_records_when(store):
    p = _p(store)
    steps = se.guided_steps(store, p.id, CF)
    assert [g.checklist.id for g in steps] == ["google_results_about_you",
                                               "bing_content_removal"]
    assert {g.status for g in steps} == {"not_started"} and se.pending(steps) == 2
    opened: list[str] = []
    assert se.open_step(store, p.id, "bing_content_removal", opener=opened.append, cf=CF)
    assert opened == [str(BING.url)]
    [_, bing] = se.guided_steps(store, p.id, CF)
    assert bing.status == "opened" and bing.opened_at is not None and bing.done_at is None
    assert se.mark_done(store, p.id, "bing_content_removal", cf=CF)
    [_, bing] = se.guided_steps(store, p.id, CF)
    assert bing.status == "done" and bing.done_at is not None
    # the same tick the Protect page reads
    assert cs.progress(store, p.id)["bing_content_removal"] is True


def test_events_hold_only_the_public_id(store):
    p = _p(store)
    se.open_step(store, p.id, "google_results_about_you", opener=lambda u: None, cf=CF)
    se.mark_done(store, p.id, "google_results_about_you", cf=CF)
    evs = store.events(p.id, cs.TAG)
    assert evs and all(ev.detail == {"checklist": "google_results_about_you"} for ev in evs)
    assert {ev.action for ev in evs} == {se.OPENED, cs.DONE}


def test_refuses_unknown_non_search_and_off_host_urls(store):
    p = _p(store)
    calls: list[str] = []
    assert not se.open_step(store, p.id, "nope", opener=calls.append, cf=CF)
    assert not se.open_step(store, p.id, "freeze_equifax", opener=calls.append, cf=CF)
    assert not se.mark_done(store, p.id, "freeze_equifax", cf=CF)
    for bad in ("https://goo.gle.evil.example/x", "http://goo.gle/resultsaboutyou",
                "https://evil.example/goo.gle"):
        cf = _cf(_c("google_results_about_you", bad))
        assert not se.open_step(store, p.id, "google_results_about_you",
                                opener=calls.append, cf=cf)
        assert se.guided_steps(store, p.id, cf) == []
    assert calls == [] and store.events(p.id, cs.TAG) == []


def test_bing_do_again_after_a_listing_is_removed(store):
    p = _p(store)
    se.mark_done(store, p.id, "bing_content_removal", cf=CF)
    se.mark_done(store, p.id, "google_results_about_you", cf=CF)
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="devauto",
                                   state=ListingState.REMOVED,
                                   updated_at=utcnow() + timedelta(minutes=1)))
    g, b = se.guided_steps(store, p.id, CF)
    assert g.status == "done"            # Google's tool keeps watching by itself
    assert b.status == "do_again" and se.pending([g, b]) == 1


def test_missing_bing_entry_is_skipped_and_doc_is_plain(store):
    p = _p(store)
    steps = se.guided_steps(store, p.id, _cf(GOOGLE))
    d = se.doc(steps, p.id)
    assert d["schema"] == "search_engines/1" and [s["engine"] for s in d["steps"]] == ["Google"]
    assert "do not" in d["intro"] and "automatic" in d["intro"]
    assert d["steps"][0]["status_text"] == "Not done yet."
    assert se.guided_steps(store, p.id, _cf()) == []
