"""WO-612 CLI wiring: `scan --attended` and the background session before scheduled runs.
Fake people only; the engine session is replaced, so no browser ever opens."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from freemyid import cli_json as cj
from freemyid.engine import search_session as ss

from .conftest import make_profile
from .test_cli_json_headless import _app, fake_run  # noqa: F401  (fixture re-export)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_session(monkeypatch):
    box: dict = {"calls": [], "result": None}

    def run_for_profiles(store, ids, **kw):
        box["calls"].append({"ids": list(ids), **kw})
        if box["result"] is not None:
            return {pid: box["result"] for pid in ids}
        rep = ss.SessionReport(mode=kw["mode"], outcomes={
            "a": ss.Outcome.READ, "b": ss.Outcome.SELF_CLEARED, "c": ss.Outcome.SKIPPED})
        return {pid: rep for pid in ids}

    monkeypatch.setattr(ss, "run_for_profiles", run_for_profiles)
    return box


def test_scan_attended_runs_visible_session_and_prints_counts(store, runner, fake_session,
                                                             fake_run):  # noqa: F811
    p = make_profile()
    store.save_profile(p)
    res = runner.invoke(_app(), ["scan", "--attended"])
    assert res.exit_code == 0, res.output
    call = fake_session["calls"][0]
    assert call["mode"] == "attended" and call["ids"] == [p.id]
    assert "checked 2 sites" in res.output and "1 to check yourself" in res.output
    assert fake_run["calls"] == []          # the headless runner is not used for --attended


@pytest.mark.parametrize("reason,text", [("no_display", "no screen"),
                                         ("busy", "already open"),
                                         ("no_consent", "permission")])
def test_scan_attended_reports_reason_plainly(store, runner, fake_session, reason, text):
    store.save_profile(make_profile())
    fake_session["result"] = reason
    res = runner.invoke(_app(), ["scan", "--attended"])
    assert res.exit_code == 0, res.output
    assert text in res.output


@pytest.mark.parametrize("extra", [["--headless"], ["--json"], ["--broker", "spokeo"]])
def test_scan_attended_rejects_conflicting_flags(store, runner, fake_session, extra):
    store.save_profile(make_profile())
    res = runner.invoke(_app(), ["scan", "--attended", *extra])
    assert res.exit_code == cj.EXIT_USAGE
    assert fake_session["calls"] == []


def test_scheduled_run_does_background_session_before_runner(store, runner, fake_session,
                                                             fake_run):  # noqa: F811
    p = make_profile()
    store.save_profile(p)
    res = runner.invoke(_app(), ["run", "--headless", "--scheduled"])
    assert res.exit_code == 0, res.output
    assert [c["mode"] for c in fake_session["calls"]] == ["background"]
    assert fake_session["calls"][0]["ids"] == [p.id]
    assert fake_run["calls"] and fake_run["calls"][0]["only_due"] is True


def test_unscheduled_run_and_scan_never_open_session(store, runner, fake_session,
                                                     fake_run):  # noqa: F811
    store.save_profile(make_profile())
    assert runner.invoke(_app(), ["run", "--headless", "--dry-run"]).exit_code == 0
    assert runner.invoke(_app(), ["scan", "--headless"]).exit_code == 0
    assert fake_session["calls"] == []


def test_scheduled_run_survives_session_failure_reason(store, runner, fake_session,
                                                       fake_run):  # noqa: F811
    store.save_profile(make_profile())
    fake_session["result"] = "error"
    res = runner.invoke(_app(), ["run", "--headless", "--scheduled"])
    assert res.exit_code == 0, res.output
    assert fake_run["calls"]


def test_conftest_stub_means_no_real_window(store) -> None:
    assert ss.has_display() is False      # tests never launch a real browser
