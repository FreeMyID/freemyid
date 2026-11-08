"""Cross-cutting contract checks for commands exposing the documented --json option."""
from __future__ import annotations

import json

import pytest
from typer.main import get_command
from typer.testing import CliRunner


def _json_command_paths() -> list[tuple[str, ...]]:
    """Discover JSON-enabled leaves from Click metadata, including nested commands."""
    from freemyid.cli import app

    root = get_command(app)
    found: list[tuple[str, ...]] = []

    def visit(command, prefix: tuple[str, ...]) -> None:
        if hasattr(command, "commands"):
            for name, child in command.commands.items():
                visit(child, (*prefix, name))
            return
        if any(parameter.name == "as_json" for parameter in command.params):
            found.append(prefix)

    visit(root, ())
    return found


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _app():
    from freemyid.cli import app

    return app


def test_json_capability_is_discovered_from_click_tree() -> None:
    paths = _json_command_paths()

    assert paths
    assert len(paths) == len(set(paths))
    # Each discovered path must resolve to a leaf command with the JSON parameter.
    root = get_command(_app())
    for path in paths:
        command = root
        for part in path:
            assert hasattr(command, "commands")
            command = command.commands[part]
        assert any(parameter.name == "as_json" for parameter in command.params)


@pytest.mark.parametrize("command_path", _json_command_paths())
def test_json_read_commands_keep_usage_errors_off_stdout(
    runner: CliRunner, command_path: tuple[str, ...]
) -> None:
    """Unknown options are documented usage failures (2), never partial JSON output."""
    result = runner.invoke(_app(), [*command_path, "--json", "--not-a-real-option"])

    assert result.exit_code == 2, result.output
    assert result.stdout == ""
    assert result.stderr.strip()


@pytest.mark.parametrize(
    ("command_path", "arguments"),
    [
        (("schedule", "status"), ()),
        (("registry", "show"), ()),
        (("registry", "source"), ()),
        (("secrets", "status"), ()),
    ],
)
def test_read_only_json_success_is_one_object(
    runner: CliRunner,
    command_path: tuple[str, ...],
    arguments: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if command_path == ("schedule", "status"):
        from freemyid import scheduler

        monkeypatch.setattr(scheduler, "status", lambda: "not installed")
    result = runner.invoke(_app(), [*command_path, *arguments, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert payload["schema"]
    assert result.stdout.count("\n") <= 1
