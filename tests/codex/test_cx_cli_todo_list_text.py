"""Guard the privacy-safe human-readable ``todo list`` rows."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from typer import Typer
from typer.testing import CliRunner

from freemyid.models import Todo, TodoKind

PROFILE_ID = "f0e1d2c3b4a5968778695a4b3c2d1e0f"


@dataclass(frozen=True)
class FakeStore:
    rows: list[Todo]

    def list_todos(self, profile_id: str) -> list[Todo]:
        assert profile_id == PROFILE_ID
        return self.rows


def _app() -> Typer:
    from freemyid.cli import app

    return app


def _install_stubs(monkeypatch: pytest.MonkeyPatch, rows: list[Todo]) -> FakeStore:
    from freemyid import cli

    profile = SimpleNamespace(id=PROFILE_ID, label="Pat Testperson")
    store = FakeStore(rows)
    monkeypatch.setattr(cli, "_harden_home", lambda: None)
    monkeypatch.setattr(cli.logging_setup, "setup", lambda _verbose: None)
    monkeypatch.setattr(cli, "_open_store_or_fail", lambda: store)
    monkeypatch.setattr(cli, "_select", lambda _store, _key, _skipped: [profile])
    return store


def test_todo_list_prints_short_id_label_kind_and_title_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_id = "a1b2c3d4deadbeef0123456789abcdef"
    todo = Todo(
        id=full_id,
        profile_id=PROFILE_ID,
        kind=TodoKind.ASSISTED_OPT_OUT,
        title="Check the sample listing",
        body="BODY_DO_NOT_PRINT_9c73",
        copy_fields={"Name": "COPY_DO_NOT_PRINT_3a1d"},
    )
    _install_stubs(monkeypatch, [todo])

    result = CliRunner().invoke(_app(), ["todo", "list"])

    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        "[a1b2c3d4] Pat Testperson · assisted_opt_out · Check the sample listing"
    ]
    assert full_id[8:] not in result.stdout
    assert "BODY_DO_NOT_PRINT_9c73" not in result.stdout
    assert "COPY_DO_NOT_PRINT_3a1d" not in result.stdout


def test_todo_list_prints_nothing_for_an_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_stubs(monkeypatch, [])

    result = CliRunner().invoke(_app(), ["todo", "list"])

    assert result.exit_code == 0, result.output
    assert result.stdout == ""
