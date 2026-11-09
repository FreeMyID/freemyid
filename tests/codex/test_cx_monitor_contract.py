"""Offline contract tests for `freemyid monitor` and its monitor/1 comparison."""
from __future__ import annotations

import json
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

import pytest

from freemyid import monitor as mon
from freemyid.engine._dev import fixture_registry

ROOT = Path(__file__).resolve().parents[2]
OPT = "https://devauto.example/optout"
FORM = (b'<form><input id="email" type="email" name="email">'
        b'<input type="text" name="url"></form>')
NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
PREVIOUS_FIXTURE = Path(__file__).parent / "fixtures" / "monitor" / "previous_monitor_1.json"


class FakeRequester:
    """A route map that records requests and never accesses the network."""

    def __init__(self, routes: dict[str, tuple[int, str | None, bytes]]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method: str, url: str) -> tuple[int, str | None, bytes]:
        self.calls.append((method, url))
        return self.routes.get(url, (404, None, b""))


def _run(routes: dict[str, tuple[int, str | None, bytes]], *, previous=None,
         loader=None, ids=("devauto",)):
    requester = FakeRequester(routes)
    sleeps: list[float] = []
    result = mon.run_monitor(
        fixture_registry(), requester=requester, page_loader=loader,
        sleep=sleeps.append, now=NOW, previous=previous, broker_ids=list(ids),
    )
    return result, requester, sleeps


def _broker(doc: dict, broker_id: str = "devauto") -> dict:
    return next(item for item in doc["brokers"] if item["broker_id"] == broker_id)


def _previous_fixture() -> dict:
    return json.loads(PREVIOUS_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("case", "route", "loader", "expected"),
    [
        ("ok", (200, None, FORM), None, "ok"),
        ("moved", (301, "https://devauto.example/new", b""), None, "moved"),
        ("form_changed", (200, None, b'<form><input name="wrong"></form>'), None,
         "form_changed"),
        ("blocked", (429, None, b""), None, "blocked"),
        ("unreachable", (404, None, b""), None, "unreachable"),
        ("unknown", (200, None, b"<div id=app></div>"), None, "unknown"),
    ],
)
def test_documented_health_values_are_emitted_offline(case, route, loader, expected):
    """docs/MONITOR.md's six health values are exercised with only injected I/O."""
    routes = {OPT: route}
    if case == "moved":
        routes["https://devauto.example/new"] = (200, None, FORM)
    doc, requester, sleeps = _run(routes, loader=loader)

    assert _broker(doc)["health"] == expected, case
    assert set(doc["counts"]) == {
        "ok", "moved", "form_changed", "blocked", "unreachable", "unknown"
    }
    expected_calls = [("GET_BODY", OPT)]
    if case == "moved":
        expected_calls.append(("GET_BODY", "https://devauto.example/new"))
    assert requester.calls == expected_calls
    assert all(value >= 0 for value in sleeps)


def test_browser_path_injects_loader_and_sleep_without_real_browser_or_wait():
    seen: list[tuple[str, str]] = []

    def loader(broker, url):
        seen.append((broker.id, url))
        return 200, url, FORM.decode()

    doc, requester, sleeps = _run(
        {OPT: (200, None, b"<div id=app></div>")}, loader=loader
    )

    result = _broker(doc)
    assert result["health"] == "ok" and result["used_browser"] is True
    assert seen == [("devauto", OPT)]
    assert requester.calls == [("GET_BODY", OPT)]
    assert len(sleeps) == 1


def test_monitor_one_top_level_and_broker_fields_are_locked_to_emitted_contract():
    doc, _, _ = _run({OPT: (200, None, FORM)})

    assert set(doc) == {
        "schema", "generated_at", "previous_generated_at", "counts", "changed",
        "demote_suggested", "brokers",
    }
    assert doc["schema"] == "monitor/1"
    assert isinstance(doc["generated_at"], str)
    assert set(_broker(doc)) == {field.name for field in fields(mon.BrokerHealth)}


@pytest.mark.parametrize("case", ["changed", "unchanged", "new", "removed"])
def test_previous_comparison_cases(case):
    prior = _previous_fixture()
    if case == "unchanged":
        current, _, _ = _run({OPT: (200, None, FORM)})
        prior["brokers"][0]["fingerprint"] = _broker(current)["fingerprint"]
    elif case == "new":
        prior["brokers"] = []
    elif case == "removed":
        prior["brokers"].append({"broker_id": "retired", "health": "ok"})

    result, _, _ = _run({OPT: (200, None, FORM)}, previous=prior)
    current = _broker(result)

    if case == "changed":
        assert current["health"] == "form_changed"
        assert current["previous_health"] == "ok" and current["changed"] is True
        assert result["changed"] == ["devauto"]
    elif case == "unchanged":
        assert current["health"] == "ok"
        assert current["previous_health"] == "ok" and current["changed"] is False
        assert result["changed"] == []
    elif case == "new":
        assert current["previous_health"] is None and current["changed"] is False
        assert result["changed"] == []
    else:
        # monitor/1 currently exposes no removed-broker field; this captures that gap.
        assert "retired" not in {item["broker_id"] for item in result["brokers"]}
        assert "removed" not in result


def test_two_bad_weeks_sets_first_seen_and_demotion_suggestion():
    prior = _previous_fixture()
    prior["brokers"][0].update({
        "health": "blocked", "fingerprint": None, "weeks_bad": 1,
        "first_seen_bad": "2026-11-01",
    })
    doc, _, _ = _run({OPT: (429, None, b"")}, previous=prior)

    broker = _broker(doc)
    assert broker["health"] == "blocked"
    assert broker["previous_health"] == "blocked" and broker["changed"] is False
    assert broker["weeks_bad"] == 2
    assert broker["first_seen_bad"] == "2026-11-01"
    assert broker["demote_suggested"] is True
    assert doc["demote_suggested"] == ["devauto"]


def _invoke_cli(monkeypatch, routes, *args):
    from typer.testing import CliRunner

    from freemyid import cli

    requester = FakeRequester(routes)
    monkeypatch.setattr(mon, "httpx_requester", lambda *a, **k: (requester, lambda: None))
    monkeypatch.setattr(mon, "_pauser", lambda delay, sleep: lambda: None)
    result = CliRunner().invoke(
        cli.app, ["monitor", "--registry", str(ROOT / "src/freemyid/engine/_dev/registry.yaml"),
                  "--broker", "devauto", *args],
    )
    return result, requester


def test_cli_json_is_one_object_and_uses_documented_monitor_schema(monkeypatch):
    result, requester = _invoke_cli(monkeypatch, {OPT: (200, None, FORM)}, "--json")

    assert result.exit_code == 0, result.output
    doc = json.loads(result.stdout)
    assert isinstance(doc, dict) and doc["schema"] == "monitor/1"
    assert result.stdout.count("\n") <= 1
    assert requester.calls == [("GET_BODY", OPT)]


@pytest.mark.parametrize("bad_previous", ["malformed", "oversized"])
def test_cli_ignores_invalid_or_oversized_previous_with_warning(
    monkeypatch, tmp_path, bad_previous
):
    previous = tmp_path / "previous.json"
    if bad_previous == "malformed":
        previous.write_text("{not json", encoding="utf-8")
    else:
        # More than the monitor's 2 MB page-body cap; previous files have no documented cap.
        previous.write_text('{"schema":"wrong/1","padding":"' + "x" * 2_000_001 + '"}',
                            encoding="utf-8")

    result, _ = _invoke_cli(
        monkeypatch, {OPT: (200, None, FORM)}, "--json", "--previous", str(previous)
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["schema"] == "monitor/1"
    assert "not a monitor/1 file; not compared" in result.stderr


def test_cli_registry_error_exit_code_and_json_error_envelope(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from freemyid import cli

    result = CliRunner().invoke(
        cli.app, ["monitor", "--json", "--registry", str(tmp_path / "missing.yaml")]
    )

    assert result.exit_code == 1
    assert json.loads(result.stdout)["schema"] == "error/1"
