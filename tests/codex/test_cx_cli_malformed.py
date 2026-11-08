"""Malformed command-line invocations fail cleanly before doing work."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from freemyid.cli import app


@pytest.mark.parametrize(
    ("arguments", "case"),
    [
        (("not-a-freemyid-command",), "unknown command"),
        (("fill",), "missing required broker argument"),
        (("fill", "fake-broker", "--timeout", "not-an-integer"), "bad integer value"),
    ],
)
def test_malformed_invocations_exit_cleanly_without_sensitive_output(
    arguments: tuple[str, ...],
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parser errors stay short, nonzero, and free of traceback or profile content."""
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    result = CliRunner().invoke(app, list(arguments))
    output = f"{result.stdout}\n{result.stderr}"

    assert result.exit_code != 0, f"{case} unexpectedly succeeded: {output}"
    assert output.strip(), f"{case} did not explain the usage failure"
    assert "Traceback (most recent call last)" not in output
    assert re.search(r"\b(usage|error|invalid|missing|required)\b", output, re.IGNORECASE)
    assert len(output) <= 1000, f"{case} message is unexpectedly long: {output}"
    assert "Jane Q Testperson" not in output
