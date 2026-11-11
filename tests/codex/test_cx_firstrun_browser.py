"""Offline guards for first-run browser detection and the download question."""
from __future__ import annotations

import re
from pathlib import Path
from typing import NoReturn

import pytest

from freemyid.wizard import firstrun


def _unexpected_call(*args: object, **kwargs: object) -> NoReturn:
    pytest.fail("Unexpected browser detection, question, or subprocess call")


@pytest.fixture(autouse=True)
def _block_real_subprocesses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(firstrun.subprocess, "Popen", _unexpected_call)


@pytest.mark.parametrize("browser_path", [p for p in firstrun._PATHS if p.endswith(".exe")])
def test_system_browser_finds_each_windows_install_path(
    monkeypatch: pytest.MonkeyPatch, browser_path: str
) -> None:
    monkeypatch.setattr(firstrun.shutil, "which", lambda name: None)
    expected = Path(browser_path)
    monkeypatch.setattr(Path, "exists", lambda path: path == expected)

    assert firstrun.system_browser() == browser_path


def test_system_browser_prefers_search_path_over_known_locations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = str(tmp_path / "synthetic-browser.exe")
    monkeypatch.setattr(firstrun.shutil, "which", lambda name: executable)
    monkeypatch.setattr(Path, "exists", _unexpected_call)

    assert firstrun.system_browser() == executable


def test_system_browser_checks_later_search_path_candidates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = str(tmp_path / "synthetic-edge.exe")
    monkeypatch.setattr(
        firstrun.shutil, "which", lambda name: executable if name == "msedge" else None
    )
    monkeypatch.setattr(Path, "exists", _unexpected_call)

    assert firstrun.system_browser() == executable


def test_system_browser_returns_none_when_no_browser_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(firstrun.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "exists", lambda path: False)

    assert firstrun.system_browser() is None


def test_ensure_browser_uses_existing_browser_without_asking_or_installing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        firstrun, "system_browser", lambda: str(tmp_path / "synthetic-browser.exe")
    )

    assert firstrun.ensure_browser(ask=_unexpected_call, run=_unexpected_call) == "system"


@pytest.mark.parametrize("answer", ["", "n", "no", "N", "   ", "true", "ok", "1"])
def test_ensure_browser_declines_without_an_answer_starting_with_y(
    monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    monkeypatch.setattr(firstrun, "system_browser", lambda: None)
    questions: list[str] = []

    def ask(question: str) -> str:
        questions.append(question)
        return answer

    assert firstrun.ensure_browser(ask=ask, run=_unexpected_call) == "declined"
    assert len(questions) == 1


@pytest.mark.parametrize("answer", ["y", "Y", " yes "])
def test_ensure_browser_installs_chromium_once_after_yes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str
) -> None:
    monkeypatch.setattr(firstrun, "system_browser", lambda: None)
    executable = str(tmp_path / "synthetic-python.exe")
    monkeypatch.setattr(firstrun.sys, "executable", executable)
    commands: list[tuple[list[str], bool]] = []
    questions: list[str] = []

    def ask(question: str) -> str:
        questions.append(question)
        return answer

    def run(command: list[str], *, check: bool) -> None:
        commands.append((command, check))

    assert firstrun.ensure_browser(ask=ask, run=run) == "installed"
    assert len(questions) == 1
    assert commands == [([executable, "-m", "playwright", "install", "chromium"], True)]


def test_browser_install_command_uses_current_python_and_chromium_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = str(tmp_path / "synthetic-python.exe")
    monkeypatch.setattr(firstrun.sys, "executable", executable)

    assert firstrun.browser_install_command() == [
        executable, "-m", "playwright", "install", "chromium"
    ]


def test_browser_question_explains_download_size_without_banned_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(firstrun, "system_browser", lambda: None)
    questions: list[str] = []

    def ask(question: str) -> str:
        questions.append(question)
        return "n"

    assert firstrun.ensure_browser(ask=ask, run=_unexpected_call) == "declined"
    assert len(questions) == 1
    question = questions[0]
    assert "download" in question.casefold()
    assert re.search(r"\b\d+(?:\.\d+)?\s*(?:MB|GB)\b", question, flags=re.IGNORECASE)
    assert not re.search(
        r"\bguarantee(?:d|s)?\b|\berase(?:d|s)?\b|100%|nothing is sent|"
        r"hackers have your data",
        question,
        flags=re.IGNORECASE,
    )
