"""`freemyid search-engines` and the exposure footer (docs/CLI.md, search_engines/1).
Fake people only; the checklist entries are public data. Nothing is fetched or opened."""
from __future__ import annotations

import json
import webbrowser
from datetime import date

import pytest
from typer.testing import CliRunner

from freemyid import checklist_state as cs
from freemyid.models import Checklist, ChecklistFile
from tests.conftest import make_profile


def _c(cid: str, url: str) -> Checklist:
    return Checklist(id=cid, title=f"{cid} title", why="why", url=url, cost="Free.",
                     time_needed="10 minutes", steps=["Open the page.", "Do the steps."],
                     how_to_undo="undo", source_urls=[url], date_checked=date(2026, 11, 7),
                     verification="partial")


GOOGLE_ID, BING_ID = "google_results_about_you", "bing_content_removal"
CF = ChecklistFile(version="t", updated=date(2026, 11, 7), checklists=[
    _c(GOOGLE_ID, "https://goo.gle/resultsaboutyou"),
    _c(BING_ID, "https://www.bing.com/webmaster/tools/contentremovalform"),
    _c("freeze_equifax", "https://www.equifax.com/x")])


@pytest.fixture
def opened(monkeypatch) -> list[str]:
    urls: list[str] = []
    monkeypatch.setattr(cs, "load_checklists", lambda: CF)
    monkeypatch.setattr(webbrowser, "open", lambda url, *a, **k: urls.append(url) or True)
    return urls


@pytest.fixture
def person(store):
    p = make_profile()
    store.save_profile(p)
    return p


def _app():
    from freemyid.cli import app
    return app


def _run(*args: str):
    return CliRunner().invoke(_app(), ["search-engines", *args])


def _json(res) -> dict:
    assert res.exit_code == 0, res.output
    return json.loads(res.stdout)


def test_list_text(opened, person):
    res = _run()
    assert res.exit_code == 0, res.output
    assert "does not search Google or Bing" in res.stdout
    assert GOOGLE_ID in res.stdout and BING_ID in res.stdout
    assert "freeze_equifax" not in res.stdout
    assert "2 of 2 to do" in res.stdout
    assert opened == []


def test_list_json_schema(opened, person):
    doc = _json(_run("--json"))
    assert doc["schema"] == "search_engines/1" and doc["profile_id"] == person.id
    assert doc["pending"] == 2
    assert [s["id"] for s in doc["steps"]] == [GOOGLE_ID, BING_ID]
    s = doc["steps"][0]
    assert s["engine"] == "Google" and s["status"] == "not_started"
    assert s["opened_at"] is None and s["done_at"] is None
    assert s["url"] == "https://goo.gle/resultsaboutyou"


def test_open_records_and_opens_only_the_official_page(opened, person):
    res = _run("open", GOOGLE_ID)
    assert res.exit_code == 0, res.output
    assert opened == ["https://goo.gle/resultsaboutyou"]
    doc = _json(_run("--json"))
    assert doc["steps"][0]["status"] == "opened" and doc["steps"][0]["opened_at"]


def test_open_json_and_engine_alias(opened, person):
    doc = _json(_run("open", "bing", "--json"))
    assert opened == ["https://www.bing.com/webmaster/tools/contentremovalform"]
    assert doc["schema"] == "search_engines/1"
    assert doc["steps"][1]["status"] == "opened"


def test_done_and_undo(opened, person):
    res = _run("done", GOOGLE_ID)
    assert res.exit_code == 0 and "Done:" in res.stdout
    doc = _json(_run("--json"))
    assert doc["steps"][0]["status"] == "done" and doc["steps"][0]["done_at"]
    assert doc["pending"] == 1
    doc = _json(_run("undo", GOOGLE_ID, "--json"))
    assert doc["steps"][0]["status"] == "not_started" and doc["pending"] == 2
    assert opened == []


def test_done_json(opened, person):
    doc = _json(_run("done", "goo", "--json"))
    assert doc["steps"][0]["status"] == "done"


def test_done_is_shared_with_checklist(opened, store, person):
    _run("done", BING_ID)
    tick = cs.ticks(store, person.id).get(BING_ID)
    assert tick is not None and tick.done


def test_unknown_id_is_usage_error_and_writes_nothing(opened, store, person):
    for action in ("open", "done", "undo"):
        res = _run(action, "zz_nope")
        assert res.exit_code == 2, res.output
    res = _run("done", "freeze_equifax")          # a checklist, but not a search step
    assert res.exit_code == 2
    assert opened == [] and cs.ticks(store, person.id) == {}


def test_unknown_action_and_missing_id(opened, person):
    assert _run("search", GOOGLE_ID).exit_code == 2
    assert _run("open").exit_code == 2
    res = _run("frobnicate", "--json")
    assert res.exit_code == 2
    assert json.loads(res.stdout)["schema"] == "error/1"


def test_unknown_profile(opened, person):
    res = _run("-p", "Nobody")
    assert res.exit_code == 2
    assert _run("done", GOOGLE_ID, "-p", "Nobody").exit_code == 2


def test_needs_profile_when_several(opened, store, person):
    store.save_profile(make_profile(label="Other"))
    assert _run().exit_code == 2
    res = _run("done", GOOGLE_ID, "-p", "Other", "--json")
    assert _json(res)["pending"] == 1


def test_nobody_set_up(opened, store):
    res = _run("--json")
    assert res.exit_code == 4
    assert json.loads(res.stdout)["schema"] == "error/1"


def test_missing_checklist_file(monkeypatch, person):
    monkeypatch.setattr(cs, "load_checklists", lambda: None)
    assert _run().exit_code == 1


def test_exposure_footer(opened, store, monkeypatch):
    from freemyid import cli
    from freemyid.engine._dev import fixture_registry
    p = make_profile()
    store.save_profile(p)
    monkeypatch.setattr(cli, "_registry", fixture_registry)
    r = CliRunner()
    res = r.invoke(cli.app, ["exposure", "--offline", "--profile", p.id])
    assert res.exit_code == 0, res.output
    text = " ".join(res.stdout.split())
    assert "Google and Bing: 2 steps to do. Run freemyid search-engines." in text
    res = r.invoke(cli.app, ["exposure", "--offline", "--json", "--profile", p.id])
    assert "Google and Bing" not in res.stdout
    json.loads(res.stdout)
    r.invoke(cli.app, ["search-engines", "done", GOOGLE_ID])
    r.invoke(cli.app, ["search-engines", "done", BING_ID])
    res = r.invoke(cli.app, ["exposure", "--offline", "--profile", p.id])
    assert res.exit_code == 0 and "Google and Bing" not in res.stdout
