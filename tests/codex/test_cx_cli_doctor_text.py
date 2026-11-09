"""Guard the human-readable doctor diagnostic output using stubbed checks only."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from typer.testing import CliRunner

from freemyid import cli, doctor
from freemyid.cli import app
from freemyid.doctor import Check


@pytest.fixture
def doctor_checks(monkeypatch: pytest.MonkeyPatch) -> Callable[[tuple[Check, ...]], list[str]]:
    """Install stubs for every diagnostic and return the invocation recorder."""
    calls: list[str] = []
    monkeypatch.setattr(cli, "_harden_home", lambda: None)
    monkeypatch.setattr(cli.logging_setup, "setup", lambda verbose=False: None)

    def install(checks: tuple[Check, ...]) -> list[str]:
        assert len(checks) == 8

        def simple(name: str, result: Check) -> Callable[[], Check]:
            def run() -> Check:
                calls.append(name)
                return result

            return run

        monkeypatch.setattr(doctor, "check_python", simple("python", checks[0]))
        monkeypatch.setattr(doctor, "check_home", simple("home", checks[1]))
        monkeypatch.setattr(doctor, "check_secrets", simple("secrets", checks[2]))

        def check_store(out: dict[str, Any]) -> Check:
            calls.append("store")
            return checks[3]

        monkeypatch.setattr(doctor, "check_store", check_store)
        monkeypatch.setattr(doctor, "check_browser", simple("browser", checks[4]))
        monkeypatch.setattr(doctor, "check_scheduler", simple("scheduler", checks[5]))

        def check_mailboxes(
            profiles: list[Any] | None,
            network: bool = True,
            prober: Callable[[str, int, bool], str | None] | None = None,
        ) -> Check:
            calls.append("mailbox")
            assert network is False
            return checks[6]

        monkeypatch.setattr(doctor, "check_mailboxes", check_mailboxes)
        monkeypatch.setattr(doctor, "check_registry", simple("registry", checks[7]))
        return calls

    return install


def _checks(*statuses: str) -> tuple[Check, ...]:
    ids_and_titles = (
        ("python", "Python"),
        ("home", "Data folder"),
        ("secrets", "Secrets backend"),
        ("store", "Saved people"),
        ("browser", "Browser for automatic removals"),
        ("scheduler", "Background checks"),
        ("mailbox", "Removal mailbox"),
        ("registry", "Broker list"),
    )
    assert len(statuses) == len(ids_and_titles)
    return tuple(Check(check_id, title, status, f"{check_id} detail", f"{check_id} fix")
                 for (check_id, title), status in zip(ids_and_titles, statuses))


def test_mixed_results_stay_ordered_and_show_fixes_only_when_needed(
    monkeypatch: pytest.MonkeyPatch,
    doctor_checks: Callable[[tuple[Check, ...]], list[str]],
) -> None:
    checks = _checks(
        "ok", "warn", "ok", "fail", "warn", "ok", "fail", "ok",
    )
    calls = doctor_checks(checks)
    result = CliRunner().invoke(app, ["doctor", "--offline"])
    lines = result.stdout.splitlines()

    assert result.exit_code == 1
    assert calls == ["python", "home", "secrets", "store", "browser", "scheduler",
                     "mailbox", "registry"]
    summary_lines = [
        next(line for line in lines if line.endswith(f"{check.title}: {check.detail}"))
        for check in checks
    ]
    positions = [lines.index(line) for line in summary_lines]
    assert positions == sorted(positions)
    for check, line in zip(checks, summary_lines):
        assert line.lstrip().startswith(check.status.upper())

    for check in checks:
        if check.status == "ok":
            assert check.fix not in result.stdout
        else:
            assert f"fix: {check.fix}" in result.stdout


def test_warn_only_results_keep_success_exit_code(
    doctor_checks: Callable[[tuple[Check, ...]], list[str]],
) -> None:
    checks = _checks(
        "ok", "ok", "warn", "ok", "ok", "ok", "ok", "ok",
    )
    calls = doctor_checks(checks)
    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "WARN" in result.stdout
    assert calls == ["python", "home", "secrets", "store", "browser", "scheduler",
                     "mailbox", "registry"]


def test_empty_fix_is_not_rendered(
    doctor_checks: Callable[[tuple[Check, ...]], list[str]],
) -> None:
    checks = list(_checks(
        "ok", "warn", "ok", "ok", "ok", "ok", "ok", "ok",
    ))
    checks[1] = Check("home", "Data folder", "warn", "home is shared", "")
    doctor_checks(tuple(checks))
    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "WARN" in result.stdout
    assert "fix:" not in result.stdout
