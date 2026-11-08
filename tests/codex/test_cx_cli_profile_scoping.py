"""Selected-profile read commands stay within that profile's records."""
from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from freemyid.models import ListingState, Todo, TodoKind
from tests.conftest import make_profile


def _app():
    from freemyid.cli import app

    return app


def _json(result: Any) -> dict[str, Any]:
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


@pytest.fixture
def profiles_with_records(store, fake_registry):
    selected = make_profile(label="Pat Testperson")
    other = make_profile(label="Riley Sampleperson")
    store.save_profile(selected)
    store.save_profile(other)

    broker = fake_registry.brokers[0]
    selected_status = store.get_status(selected.id, broker.id).model_copy(
        update={"state": ListingState.FOUND}
    )
    other_status = store.get_status(other.id, broker.id).model_copy(
        update={"state": ListingState.REMOVED}
    )
    store.save_status(selected_status)
    store.save_status(other_status)
    store.save_todo(Todo(profile_id=selected.id, broker_id=broker.id,
                         kind=TodoKind.OTHER, title="Selected fake follow-up"))
    store.save_todo(Todo(profile_id=other.id, broker_id=broker.id,
                         kind=TodoKind.OTHER, title="Other fake follow-up"))
    return selected, other, broker


def test_status_profile_scopes_human_output(profiles_with_records, fake_registry,
                                           monkeypatch) -> None:
    from freemyid import cli

    selected, other, _broker = profiles_with_records
    monkeypatch.setattr(cli, "_registry", lambda: fake_registry)
    result = CliRunner().invoke(_app(), ["status", "--profile", selected.id])

    assert result.exit_code == 0, result.output
    assert selected.label in result.stdout
    assert other.label not in result.stdout
    assert "found" in result.stdout.lower()


def test_status_profile_json_excludes_other_profile(profiles_with_records, fake_registry,
                                                    monkeypatch) -> None:
    from freemyid import cli

    selected, other, broker = profiles_with_records
    monkeypatch.setattr(cli, "_registry", lambda: fake_registry)
    result = CliRunner().invoke(_app(), ["status", "--profile", selected.id, "--json"])
    payload = _json(result)

    assert [profile["label"] for profile in payload["profiles"]] == [selected.label]
    serialized = json.dumps(payload)
    assert other.label not in serialized
    assert "Other fake follow-up" not in serialized
    assert "removed" not in serialized
    assert payload["profiles"][0]["brokers"][0]["state"] == "found"
    assert payload["profiles"][0]["brokers"][0]["broker_id"] == broker.id


def test_todo_list_profile_json_shows_only_selected_todos(profiles_with_records) -> None:
    selected, other, _broker = profiles_with_records
    result = CliRunner().invoke(
        _app(), ["todo", "list", "--profile", selected.id, "--json"]
    )
    payload = _json(result)

    assert [todo["label"] for todo in payload["todos"]] == [selected.label]
    assert [todo["title"] for todo in payload["todos"]] == ["Selected fake follow-up"]
    serialized = json.dumps(payload)
    assert other.label not in serialized
    assert "Other fake follow-up" not in serialized


def test_report_profile_json_builds_only_selected_profile(
    profiles_with_records, fake_registry, monkeypatch, tmp_path
) -> None:
    from freemyid import cli
    from freemyid.wizard import report as report_module

    selected, other, _broker = profiles_with_records
    calls: list[str] = []
    output = tmp_path / "report.html"

    def build_report(_store, _registry, profile_id: str, _fmt: str):
        calls.append(profile_id)
        return output

    monkeypatch.setattr(cli, "_registry", lambda: fake_registry)
    monkeypatch.setattr(report_module, "build_report", build_report)
    result = CliRunner().invoke(_app(), ["report", "--profile", selected.id, "--json"])
    payload = _json(result)

    assert calls == [selected.id]
    assert [row["profile_id"] for row in payload["reports"]] == [selected.id]
    assert [row["label"] for row in payload["reports"]] == [selected.label]
    assert other.label not in json.dumps(payload)
    assert not output.exists()
