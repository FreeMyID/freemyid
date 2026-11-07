"""Checklist done-state (src/freemyid/checklist_state.py) and `freemyid checklist ...`.
Fake people only; the checklist file is public data."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from freemyid import checklist_state as cs
from freemyid.models import Actor, Event, utcnow
from tests.conftest import make_profile

CF = cs.load_checklists()
assert CF is not None
FIRST, SECOND = CF.checklists[0].id, CF.checklists[1].id


@pytest.fixture
def person(store):
    p = make_profile()
    store.save_profile(p)
    return p


def _app():
    from freemyid.cli import app
    return app


def _json(res) -> dict:
    assert res.exit_code == 0, res.output
    return json.loads(res.stdout)


# --------------------------------------------------------------------------- state helper

def test_done_undo_and_counts(store, person):
    assert cs.progress(store, person.id) == {}
    assert cs.set_done(store, person.id, FIRST, True)
    assert cs.progress(store, person.id) == {FIRST: True}
    assert cs.counts(store, person.id) == (1, len(CF.checklists))
    assert cs.set_done(store, person.id, FIRST, False)
    assert cs.progress(store, person.id) == {FIRST: False}
    assert cs.counts(store, person.id)[0] == 0


def test_unknown_id_writes_nothing(store, person):
    assert not cs.set_done(store, person.id, "not_a_checklist", True)
    assert store.events(person.id) == []


def test_ticks_are_per_person(store, person):
    other = make_profile(label="Other")
    store.save_profile(other)
    cs.set_done(store, person.id, FIRST, True)
    assert cs.progress(store, other.id) == {}


def test_ticks_survive_a_busy_event_log(store, person, monkeypatch):
    monkeypatch.setattr(cs, "_LEGACY_SCAN", 10)
    cs.set_done(store, person.id, FIRST, True)
    for _ in range(50):         # a long run's worth of engine events after the tick
        store.log(Event(profile_id=person.id, broker_id="fakeb", actor=Actor.ENGINE,
                        action="scan_done"))
    assert cs.progress(store, person.id) == {FIRST: True}


def test_reads_ticks_from_the_first_dashboard_version(store, person):
    # wizard/protect.py v1 wrote untagged events; the newest tick still wins
    t0 = utcnow()
    store.log(Event(profile_id=person.id, actor=Actor.USER, action=cs.DONE,
                    detail={"checklist": SECOND}, ts=t0 - timedelta(minutes=5)))
    assert cs.progress(store, person.id) == {SECOND: True}
    cs.set_done(store, person.id, SECOND, False)
    assert cs.progress(store, person.id) == {SECOND: False}


def test_tick_event_has_no_pii(store, person):
    cs.set_done(store, person.id, FIRST, True)
    [ev] = store.events(person.id)
    assert ev.broker_id == cs.TAG and ev.actor == Actor.USER
    assert ev.detail == {"checklist": FIRST}


# --------------------------------------------------------------------------- CLI

def test_cli_list_show_done_undo(store, person):
    r = CliRunner()
    res = r.invoke(_app(), ["checklist", "list"])
    assert res.exit_code == 0, res.output
    assert f"[ ] {FIRST}" in res.stdout and f"0 of {len(CF.checklists)} done" in res.stdout

    res = r.invoke(_app(), ["checklist", "done", FIRST])
    assert res.exit_code == 0 and "Done:" in res.stdout
    assert f"[x] {FIRST}" in r.invoke(_app(), ["checklist", "list"]).stdout

    res = r.invoke(_app(), ["checklist", "show", FIRST])
    assert res.exit_code == 0 and "Steps:" in res.stdout and "Status: done on" in res.stdout

    res = r.invoke(_app(), ["checklist", "undo", FIRST])
    assert res.exit_code == 0 and "Not done:" in res.stdout
    assert cs.progress(store, person.id) == {FIRST: False}


def test_cli_json_documents(store, person):
    r = CliRunner()
    doc = _json(r.invoke(_app(), ["checklist", "done", FIRST, "--json"]))
    assert doc["schema"] == "checklist/1" and doc["id"] == FIRST and doc["done"] is True
    assert doc["steps"] and doc["done_at"]
    doc = _json(r.invoke(_app(), ["checklist", "list", "--json"]))
    assert doc["schema"] == "checklists/1" and doc["done"] == 1
    assert doc["total"] == len(CF.checklists) == len(doc["checklists"])
    assert {c["id"]: c["done"] for c in doc["checklists"]}[FIRST] is True
    raw = json.dumps(doc)
    assert "Jane" not in raw and "Testperson" not in raw
    doc = _json(r.invoke(_app(), ["checklist", "show", SECOND, "--json"]))
    assert doc["done"] is False and doc["done_at"] is None


def test_cli_unknown_checklist_is_usage_error(store, person):
    res = CliRunner().invoke(_app(), ["checklist", "done", "zz_nope"])
    assert res.exit_code == 2
    assert store.events(person.id) == []


def test_cli_needs_profile_when_several(store, person):
    other = make_profile(label="Other")
    store.save_profile(other)
    r = CliRunner()
    assert r.invoke(_app(), ["checklist", "list"]).exit_code == 2
    res = r.invoke(_app(), ["checklist", "done", FIRST, "-p", "Other"])
    assert res.exit_code == 0, res.output
    assert cs.progress(store, other.id) == {FIRST: True}
    assert cs.progress(store, person.id) == {}


def test_cli_no_profile_yet(store):
    res = CliRunner().invoke(_app(), ["checklist", "list", "--json"])
    assert res.exit_code == 4
    assert json.loads(res.stdout)["schema"] == "error/1"
