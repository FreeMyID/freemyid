"""Guard the human-readable registry source summary and warning lines."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from typer.testing import CliRunner


def _app():
    from freemyid.cli import app

    return app


def _stub_registry(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    warnings: list[str],
) -> None:
    """Keep the CLI invocation away from the filesystem, store, keyring and network."""
    from freemyid import cli, registry

    synthetic_registry = SimpleNamespace(
        brokers=(object(), object()),
        version="fixture-v1",
    )
    monkeypatch.setattr(cli, "_harden_home", lambda: None)
    monkeypatch.setattr(cli.logging_setup, "setup", lambda verbose=False: None)
    monkeypatch.setattr(registry, "load_registry", lambda path=None: synthetic_registry)
    monkeypatch.setattr(registry, "registry_source", lambda: source)
    monkeypatch.setattr(registry, "load_warnings", warnings)


@pytest.mark.parametrize("source", ["update", "family", "full", "sample"])
def test_registry_source_prints_summary_for_selected_source(
    source: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The source command names the source, broker count and registry version."""
    _stub_registry(monkeypatch, source, [])

    result = CliRunner().invoke(_app(), ["registry", "source"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.splitlines() == [
        f"{source}: 2 brokers (version fixture-v1)",
    ]


def test_registry_source_prints_exact_warning_lines_after_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warnings = [
        "family registry invalid: synthetic fixture",
        "full registry unreadable: synthetic fixture",
    ]
    _stub_registry(monkeypatch, "sample", warnings)

    result = CliRunner().invoke(_app(), ["registry", "source"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.splitlines() == [
        "sample: 2 brokers (version fixture-v1)",
        *(f"warning: {warning}" for warning in warnings),
    ]
