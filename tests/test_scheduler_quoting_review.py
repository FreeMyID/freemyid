"""qa-security review of the engine-sched group (PR #114, #127): scheduler quoting.

Pure renderers only: nothing here installs a job or starts a process.
Fake paths only (Jane Q Testperson, Springfield IL).
"""
from __future__ import annotations

import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

from freemyid import scheduler
from freemyid.scheduler import pathcheck, render

_LIN = "/home/Jane Q Testperson/Springfield IL"
_WIN = "C:\\Users\\Jane Q Testperson\\Springfield IL"


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    del freemyid_env

    def refuse(*_a: object, **_k: object) -> None:
        raise RuntimeError("network blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _exec_words(service: str) -> str:
    return next(line for line in service.splitlines()
                if line.startswith("ExecStart=")).removeprefix("ExecStart=")


# --- systemd: ExecStart expands $NAME and ${NAME} in arguments (systemd.service(5),
# "Command lines"); a literal dollar is written $$. Environment= does no expansion. ---

def test_systemd_execstart_doubles_dollar_in_arguments() -> None:
    svc = render.systemd_service(["/usr/bin/freemyid", "run", "$HOME", "a${USER}b"])
    assert _exec_words(svc) == '"/usr/bin/freemyid" "run" "$$HOME" "a$${USER}b"'


def test_systemd_execstart_program_path_keeps_dollar() -> None:
    # The program word is not variable-substituted, so its $ stays literal.
    svc = render.systemd_service([f"{_LIN}/$bin/freemyid", "run"])
    assert _exec_words(svc) == f'"{_LIN}/$bin/freemyid" "run"'


def test_systemd_environment_line_keeps_single_dollar() -> None:
    svc = render.systemd_service(["/usr/bin/freemyid"], {"FREEMYID_HOME": f"{_LIN}/$data"})
    assert f'Environment="FREEMYID_HOME={_LIN}/$data"' in svc


def test_pathcheck_systemd_doubles_dollar_in_arguments() -> None:
    result = pathcheck.check_path([f"{_LIN}/$bin/freemyid", "$HOME"], "linux")
    assert result.problems == []
    assert result.quoted == f'"{_LIN}/$bin/freemyid" "$$HOME"'


def test_pathcheck_and_render_agree_on_systemd_words() -> None:
    argv = [f"{_LIN}/free my id", "run", "100% $HOME", 'say "hi"', "back\\slash"]
    result = pathcheck.check_path(argv, "linux")
    assert result.quoted == _exec_words(render.systemd_service(argv))


# --- Windows: Task Scheduler expands %NAME% in the Exec Command and Arguments. ---

@pytest.mark.parametrize("argv", [
    [f"{_WIN}\\%USERNAME%\\FreeMyID.exe", "run"],
    [f"{_WIN}\\FreeMyID.exe", "run", "%APPDATA%"],
    [f"{_WIN}\\FreeMyID.exe", "100%", "and 50%"],   # pairs across two arguments
])
def test_pathcheck_windows_refuses_env_reference(argv: list[str]) -> None:
    result = pathcheck.check_path(argv, "windows")
    assert [p.code for p in result.problems] == ["windows_env_ref"]
    assert result.quoted is None
    # Codes and indexes only: never the path.
    assert all(_WIN not in repr(p) for p in result.problems)


def test_pathcheck_windows_single_percent_is_safe() -> None:
    result = pathcheck.check_path([f"{_WIN}\\100%\\FreeMyID.exe", "run"], "windows")
    assert result.problems == []


def test_pathcheck_env_ref_only_on_windows() -> None:
    argv = [f"{_LIN}/%USERNAME%/freemyid", "run"]
    assert pathcheck.check_path(argv, "macos").problems == []
    assert pathcheck.check_path(argv, "linux").problems == []


# --- cron: the program word gets the same odd-backslash-before-% handling as env values. ---

def _cron_to_shell(line: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append("%" if line[i + 1] == "%" else "\\" + line[i + 1])
            i += 2
            continue
        assert c != "%", "a bare % ends the cron command"
        out.append(c)
        i += 1
    return "".join(out)


def test_cron_command_with_backslash_percent_stays_one_command() -> None:
    text = render.cron_lines([f"{_LIN}/share\\%file/freemyid", "run"])
    for line in text.splitlines():
        _cron_to_shell(line)    # no bare % anywhere on the line
        assert line.endswith(render.CRON_MARK)


# --- macOS: RunAtLoad also runs at install and at each login; say so. ---

def test_macos_install_message_says_it_runs_now_and_at_login(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler, "platform_name", lambda: "macos")
    monkeypatch.setattr(scheduler, "_uid", lambda: 501)
    monkeypatch.setattr(scheduler.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(scheduler, "job_command", lambda *_a, **_k: ["/usr/bin/freemyid"])
    monkeypatch.setattr(
        scheduler, "_run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout=""))
    message = scheduler.install()
    assert "now" in message and "log in" in message
    assert "only checks sites that are due" in message
