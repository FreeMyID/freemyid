"""Recovery guarantees of the existing event-backed checklist state.

WO-281 describes JSON state files, but this module stores encrypted audit Events.
These tests exercise its current interface; they do not claim file recovery or
atomic replace behavior in the in-house storage implementation.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from freemyid import checklist_state as cs
from freemyid.models import Actor, Event, utcnow
from tests.conftest import make_profile


@pytest.mark.parametrize("bad_id", [None, False, 0, 1, [], {}, ["synthetic_tick"], ""])
def test_malformed_tick_id_keeps_all_readable_ticks(store, bad_id: Any) -> None:
    profile = make_profile()
    store.save_profile(profile)
    start = utcnow()
    for offset, cid in enumerate(("synthetic_first", "synthetic_second")):
        store.log(Event(profile_id=profile.id, broker_id=cs.TAG, actor=Actor.USER,
                        action=cs.DONE, detail={"checklist": cid},
                        ts=start + timedelta(seconds=offset)))
    store.log(Event(profile_id=profile.id, broker_id=cs.TAG, actor=Actor.USER,
                    action=cs.UNDONE, detail={"checklist": bad_id},
                    ts=start + timedelta(seconds=2)))

    assert cs.progress(store, profile.id) == {
        "synthetic_first": True, "synthetic_second": True,
    }


@pytest.mark.parametrize("detail", [{}, {"unknown": "synthetic_marker"},
                                    {"checklist": "synthetic_tick", "unknown": [1, None]}])
def test_unknown_detail_fields_do_not_replace_readable_tick(store, detail: dict[str, Any]) -> None:
    profile = make_profile()
    store.save_profile(profile)
    start = utcnow()
    store.log(Event(profile_id=profile.id, broker_id=cs.TAG, actor=Actor.USER,
                    action=cs.DONE, detail={"checklist": "synthetic_tick"}, ts=start))
    store.log(Event(profile_id=profile.id, broker_id=cs.TAG, actor=Actor.USER,
                    action=cs.DONE, detail=detail, ts=start + timedelta(seconds=1)))

    assert cs.progress(store, profile.id) == {"synthetic_tick": True}
    assert set(cs.ticks(store, profile.id)) == {"synthetic_tick"}


def test_removed_checklist_tick_survives_without_inflating_current_counts(store) -> None:
    profile = make_profile()
    store.save_profile(profile)
    cf = cs.load_checklists()
    assert cf is not None
    cid = cf.checklists[0].id
    assert cs.set_done(store, profile.id, cid, True, checklists=cf)
    store.log(Event(profile_id=profile.id, broker_id=cs.TAG, actor=Actor.USER,
                    action=cs.DONE, detail={"checklist": "synthetic_removed_item"}))

    assert cs.progress(store, profile.id) == {cid: True, "synthetic_removed_item": True}
    assert cs.counts(store, profile.id, cf) == (1, len(cf.checklists))
    assert {item["id"] for item in cs.list_doc(cf, cs.ticks(store, profile.id), profile.id)[
        "checklists"]} == {item.id for item in cf.checklists}


def test_failed_tick_append_keeps_previous_tick(store, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = make_profile()
    store.save_profile(profile)
    cf = cs.load_checklists()
    assert cf is not None
    cid = cf.checklists[0].id
    assert cs.set_done(store, profile.id, cid, True, checklists=cf)
    previous = cs.ticks(store, profile.id)
    previous_events = store.events(profile.id, cs.TAG)

    def fail_append(event: Event) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(store, "log", fail_append)
    with pytest.raises(OSError, match="synthetic write failure"):
        cs.set_done(store, profile.id, cid, False, checklists=cf)

    assert cs.ticks(store, profile.id) == previous
    assert store.events(profile.id, cs.TAG) == previous_events
