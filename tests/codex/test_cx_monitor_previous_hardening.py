"""CLI hardening checks for untrusted monitor/1 comparison files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from freemyid import cli
from freemyid import monitor as mon

ROOT = Path(__file__).resolve().parents[2]
DEV_REGISTRY = ROOT / "src" / "freemyid" / "engine" / "_dev" / "registry.yaml"
OPT = "https://devauto.example/optout"
FORM = b'<form><input id="email" type="email" name="email"></form>'


class FakeRequester:
    """Return a fixed broker response; this helper never opens a network connection."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method: str, url: str) -> tuple[int, None, bytes]:
        self.calls.append((method, url))
        return (429, None, b"") if url == OPT else (404, None, b"")


def _invoke_with_previous(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, contents: str
) -> tuple[Any, FakeRequester]:
    previous = tmp_path / "previous.json"
    previous.write_text(contents, encoding="utf-8")
    requester = FakeRequester()
    monkeypatch.setattr(mon, "httpx_requester", lambda: (requester, lambda: None))
    monkeypatch.setattr(mon, "_pauser", lambda _delay, _sleep: lambda: None)
    result = CliRunner().invoke(
        cli.app,
        ["monitor", "--registry", str(DEV_REGISTRY), "--broker", "devauto",
         "--previous", str(previous), "--json"],
    )
    return result, requester


def test_cli_drops_malformed_previous_entry_values_from_new_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nested bad values and non-object rows do not crash or leak into monitor/1 output."""
    contents = (
        '{"schema":"monitor/1","generated_at":"2026-11-08T12:00:00+00:00",'
        '"brokers":["NON_OBJECT_ROW_MARKER",'
        '{"broker_id":["LIST_BROKER_ID_MARKER"],"health":"blocked",'
        '"fingerprint":["LIST_FINGERPRINT_MARKER"],"weeks_bad":1e400,'
        '"first_seen_bad":{"marker":"BAD_DATE_MARKER"}},'
        '{"broker_id":"devauto","health":"BAD_HEALTH_MARKER",'
        '"fingerprint":["BAD_FINGERPRINT_MARKER"],"weeks_bad":1e400,'
        '"first_seen_bad":"2026-99-99"}]}'
    )

    result, requester = _invoke_with_previous(monkeypatch, tmp_path, contents)

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    broker = report["brokers"][0]
    assert report["previous_generated_at"] == "2026-11-08T12:00:00+00:00"
    assert report["removed_brokers"] == []
    assert broker["broker_id"] == "devauto"
    assert broker["previous_health"] is None
    assert broker["weeks_bad"] == 1
    assert broker["first_seen_bad"] != "2026-99-99"
    for marker in (
        "NON_OBJECT_ROW_MARKER", "LIST_BROKER_ID_MARKER", "LIST_FINGERPRINT_MARKER",
        "BAD_DATE_MARKER", "BAD_HEALTH_MARKER", "BAD_FINGERPRINT_MARKER",
    ):
        assert marker not in result.stdout
    assert requester.calls == [("GET_BODY", OPT)]


def test_cli_drops_huge_previous_generated_at_instead_of_copying_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A JSON number too large for a finite float is not valid prior timestamp data."""
    contents = (
        '{"schema":"monitor/1","generated_at":1e400,'
        '"brokers":[{"broker_id":"devauto","health":"blocked"}]}'
    )

    result, _requester = _invoke_with_previous(monkeypatch, tmp_path, contents)

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["previous_generated_at"] is None


@pytest.mark.parametrize(
    "generated_at",
    [
        pytest.param(None, id="null"),
        pytest.param(True, id="boolean"),
        pytest.param(42, id="number"),
        pytest.param(["TIMESTAMP_LIST_MARKER"], id="list"),
        pytest.param({"marker": "TIMESTAMP_OBJECT_MARKER"}, id="object"),
        pytest.param("", id="empty"),
        pytest.param("TIMESTAMP_TEXT_MARKER", id="not-a-date"),
        pytest.param("2026-11-08", id="date-only"),
        pytest.param("2026-02-30T12:00:00+00:00", id="impossible-calendar-date"),
        pytest.param("2026-11-08T25:00:00+00:00", id="impossible-time"),
        pytest.param("2026-11-08T12:00:00+25:00", id="impossible-offset"),
        pytest.param("2026-11-08X12:00:00", id="arbitrary-separator"),
        pytest.param("2026-11-08\n12:00:00", id="newline-separator"),
        pytest.param("2026-11-08T12:00:00+00:00\n", id="trailing-newline"),
        pytest.param(" 2026-11-08T12:00:00+00:00", id="leading-space"),
        pytest.param("2026-11-08T12:00:00.123456789012345+05:30", id="41-characters"),
        pytest.param("TIMESTAMP_PADDING_MARKER" + "x" * 1_000_000, id="one-megabyte"),
    ],
)
def test_cli_drops_invalid_previous_timestamp_but_keeps_broker_comparison(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, generated_at: Any
) -> None:
    contents = json.dumps({
        "schema": "monitor/1",
        "generated_at": generated_at,
        "unused": "UNUSED_TOP_LEVEL_MARKER",
        "brokers": [{"broker_id": "devauto", "health": "blocked", "weeks_bad": 3}],
    })

    result, requester = _invoke_with_previous(monkeypatch, tmp_path, contents)

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["previous_generated_at"] is None
    assert report["brokers"][0]["previous_health"] == "blocked"
    assert report["brokers"][0]["weeks_bad"] == 4
    assert "TIMESTAMP_" not in result.stdout
    assert "UNUSED_TOP_LEVEL_MARKER" not in result.stdout
    assert set(report) == {
        "schema", "generated_at", "previous_generated_at", "counts", "changed",
        "demote_suggested", "new_brokers", "removed_brokers", "brokers",
    }
    assert requester.calls == [("GET_BODY", OPT)]


@pytest.mark.parametrize(
    "generated_at",
    [
        "2026-11-08T12:00:00+00:00",
        "2026-11-08T12:00:00Z",
        "2026-11-08T12:00:00+05:30",
        "2026-11-08T12:00:00-03:30",
        "2026-11-08T12:00:00.123456+00:00",
        "2026-11-08T12:00:00.12345678901234+05:30",
        "2026-11-08T12:00:00",
        "2026-11-08T12:00",
        "2026-11-08t12:00:00",
        "2026-11-08 12:00:00",
    ],
)
def test_cli_preserves_valid_previous_date_time_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, generated_at: str
) -> None:
    contents = json.dumps({"schema": "monitor/1", "generated_at": generated_at,
                           "brokers": []})

    result, _requester = _invoke_with_previous(monkeypatch, tmp_path, contents)

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["previous_generated_at"] == generated_at
