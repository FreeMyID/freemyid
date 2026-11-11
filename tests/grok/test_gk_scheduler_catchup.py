"""Cron receives the job environment, and a powered-off Mac catches up at next login.

Renders Linux, macOS, and Windows on whatever OS is running the tests. Nothing here
installs a real job or opens a socket.
"""
from __future__ import annotations

import plistlib
import shlex
import socket
import xml.etree.ElementTree as ET
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

import pytest

from freemyid import scheduler
from freemyid.scheduler import render

# Jane Q Testperson only. Space, both quotes, percent, dollar, and a backslash.
TRICKY = "Jane Q \"Testperson\" 100% $HOME's \\file"
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
CMD = ["/usr/bin/freemyid", "run", "--headless", "--scheduled"]


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    """socket.connect and create_connection always raise, including localhost.

    Depending on freemyid_env runs this after that fixture's own connect patch.
    """
    del freemyid_env

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_socket_helpers_raise() -> None:
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


def _cron_to_shell(line: str) -> str:
    """What cronie hands the shell: \\% becomes %, any other % ends the command."""
    out: list[str] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line):
            nxt = line[index + 1]
            out.append("%" if nxt == "%" else "\\" + nxt)
            index += 2
            continue
        if char == "%":
            break
        out.append(char)
        index += 1
    return "".join(out)


def _cron_assignments(line: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for word in shlex.split(_cron_to_shell(line)):
        key, sep, value = word.partition("=")
        if sep and key.startswith("FREEMYID_"):
            found[key] = value
    return found


def _xml_text(root: ET.Element, path: str) -> str:
    node = root.find(path, NS)
    assert node is not None and node.text is not None
    return node.text


def _systemd_unquote(token: str) -> str:
    assert token.startswith('"') and token.endswith('"')
    body = token[1:-1]
    out: list[str] = []
    index = 0
    while index < len(body):
        if body[index] == "\\":
            out.append(body[index + 1])
            index += 2
            continue
        if body[index] == "%":
            assert body[index + 1] == "%"
            out.append("%")
            index += 2
            continue
        out.append(body[index])
        index += 1
    return "".join(out)


def test_cron_without_env_is_unchanged() -> None:
    command = " ".join(shlex.quote(part) for part in CMD)
    mark = render.CRON_MARK
    expected = (
        f"0 {render.DAILY_HOUR} * * * {command} {mark}\n"
        f"@reboot sleep 120 && {command} {mark}\n"
    )
    assert render.cron_lines(CMD) == expected
    assert render.cron_lines(CMD, None) == expected
    assert render.cron_lines(CMD, {}) == expected


def test_cron_env_is_on_both_lines_and_round_trips(tmp_path: Path) -> None:
    env = {
        "FREEMYID_HOME": str(tmp_path / "Jane Q Testperson"),
        "FREEMYID_PASSPHRASE_FILE": TRICKY,
    }
    lines = render.cron_lines(CMD, env).splitlines()
    assert len(lines) == 2
    assert lines[0].startswith(f"0 {render.DAILY_HOUR} * * * FREEMYID_HOME=")
    assert lines[1].startswith("@reboot sleep 120 && FREEMYID_HOME=")
    for line in lines:
        shell = _cron_to_shell(line)
        assert shell.index("FREEMYID_HOME=") < shell.index("FREEMYID_PASSPHRASE_FILE=")
        assert shell.index("FREEMYID_PASSPHRASE_FILE=") < shell.index("/usr/bin/freemyid")
        assert _cron_assignments(line) == env
        assert "$(printf" not in line
        if line.startswith("@reboot"):
            assert shell.index("sleep") < shell.index("&&") < shell.index("FREEMYID_HOME=")

    percent = render.cron_lines(["/usr/bin/freemyid", "100% done"])
    assert "100\\% done" in percent
    words = shlex.split(_cron_to_shell(percent.splitlines()[0]))
    assert words[5:7] == ["/usr/bin/freemyid", "100% done"]


def test_cron_percent_after_backslash_stays_one_field() -> None:
    value = "share\\%file $HOME"
    text = render.cron_lines(["/usr/bin/freemyid", "run"], {"FREEMYID_HOME": value})
    for line in text.splitlines():
        assert "%" not in line
        assert line.count("$(printf '") == 1
        octets = line.split("$(printf '", 1)[1].split("')", 1)[0]
        decoded = octets.encode("ascii").decode("unicode_escape").encode("latin1").decode()
        assert decoded == value
        assert "/usr/bin/freemyid" in line and line.endswith(render.CRON_MARK)


def test_install_passes_job_env_to_cron(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "Jane Q Testperson"
    monkeypatch.setenv("FREEMYID_HOME", str(custom))
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", TRICKY)
    monkeypatch.setattr(scheduler, "platform_name", lambda: "linux")
    monkeypatch.setattr(scheduler, "_has_systemd_user", lambda: False)
    monkeypatch.setattr(scheduler, "job_command", lambda *_a, **_k: list(CMD))

    def which(name: str) -> str | None:
        return "crontab" if name == "crontab" else None

    monkeypatch.setattr(scheduler.shutil, "which", which)
    calls: list[tuple[list[str], str | None]] = []

    def fake_run(args: list[str], input: str | None = None) -> SimpleNamespace:
        calls.append((list(args), input))
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(scheduler, "_run", fake_run)
    assert scheduler.install() == "Installed a daily cron job plus a run at startup."
    written = [text for args, text in calls if args == ["crontab", "-"]]
    env = {"FREEMYID_HOME": str(custom), "FREEMYID_PASSPHRASE_FILE": TRICKY}
    assert len(written) == 1
    crontab = written[0]
    assert crontab is not None
    assert crontab == render.cron_lines(CMD, env)
    for line in crontab.splitlines():
        assert _cron_assignments(line) == env


def test_systemd_and_launchd_quote_tricky_values(tmp_path: Path) -> None:
    env = {"FREEMYID_HOME": TRICKY, "FREEMYID_PASSPHRASE_FILE": str(tmp_path / "pass phrase")}
    service = render.systemd_service(CMD, env)
    quoted = [line.removeprefix("Environment=") for line in service.splitlines()
              if line.startswith("Environment=")]
    assert [_systemd_unquote(item) for item in quoted] == [
        f"{key}={value}" for key, value in env.items()]

    log = tmp_path / "scheduler.log"
    plist = render.launchd_plist(CMD, str(log), env)
    data = plistlib.loads(plist.encode())
    assert data["RunAtLoad"] is True
    assert data["EnvironmentVariables"] == env
    assert data["ProgramArguments"] == CMD
    assert data["StandardOutPath"] == str(log)
    assert data["StandardErrorPath"] == str(log)
    assert "<key>RunAtLoad</key>\n  <true/>" in plist


def test_macos_install_says_switched_off_runs_at_next_login(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "Jane Q Testperson"
    monkeypatch.setenv("FREEMYID_HOME", str(home))
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.setattr(scheduler, "platform_name", lambda: "macos")
    monkeypatch.setattr(scheduler, "_uid", lambda: 501)
    monkeypatch.setattr(scheduler.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(scheduler, "job_command", lambda *_a, **_k: list(CMD))
    monkeypatch.setattr(
        scheduler, "_run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout=""))
    message = scheduler.install()
    assert message == (
        "Installed a daily launchd agent. It also runs now and each time you log in, "
        "but only checks sites that are due, so a check missed while the Mac was "
        "switched off still happens."
    )
    plist_path = tmp_path / "Library" / "LaunchAgents" / f"{render.LABEL}.plist"
    data = plistlib.loads(plist_path.read_bytes())
    assert data["RunAtLoad"] is True
    assert data["EnvironmentVariables"]["FREEMYID_HOME"] == str(home)
    assert "FREEMYID_PASSPHRASE_FILE" not in data["EnvironmentVariables"]


def test_windows_pins_catchup_and_battery_and_has_no_env(tmp_path: Path) -> None:
    folder = tmp_path.name
    exe = str(PureWindowsPath(r"C:\Users") / f"Jane Q \"Testperson\" {folder}" / "100% $HOME"
              / "FreeMyID.exe")
    args = ["run", "--scheduled", "say \"hi\" 100% $HOME"]
    xml = render.windows_task_xml([exe, *args])
    root = ET.fromstring(xml.replace('encoding="UTF-16"', ""))
    assert _xml_text(root, "t:Settings/t:StartWhenAvailable") == "true"
    assert _xml_text(root, "t:Settings/t:DisallowStartIfOnBatteries") == "false"
    assert _xml_text(root, "t:Settings/t:StopIfGoingOnBatteries") == "false"
    assert _xml_text(root, "t:Actions/t:Exec/t:Command") == exe
    # list2cmdline quoting, checked here without spawning a process.
    assert _xml_text(root, "t:Actions/t:Exec/t:Arguments") == (
        'run --scheduled "say \\"hi\\" 100% $HOME"')
    assert "FREEMYID_HOME" not in xml
    assert "Environment" not in xml


def test_windows_install_does_not_embed_custom_home(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "Jane Q Testperson"
    monkeypatch.setenv("FREEMYID_HOME", str(custom))
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", TRICKY)
    monkeypatch.setattr(scheduler, "platform_name", lambda: "windows")
    monkeypatch.setattr(
        scheduler, "job_command",
        lambda *_a, **_k: [r"C:\Program Files\FreeMyID\FreeMyID.exe", "run", "--scheduled"])
    seen: dict[str, str] = {}

    def fake_run(args: list[str], input: str | None = None) -> SimpleNamespace:
        xml_path = Path(args[args.index("/XML") + 1])
        seen["xml"] = xml_path.read_text(encoding="utf-16")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(scheduler, "_run", fake_run)
    message = scheduler.install()
    assert message == "Installed a daily scheduled task that also runs after a missed start."
    xml = seen["xml"]
    root = ET.fromstring(xml.replace('encoding="UTF-16"', ""))
    assert _xml_text(root, "t:Settings/t:StartWhenAvailable") == "true"
    assert _xml_text(root, "t:Settings/t:DisallowStartIfOnBatteries") == "false"
    assert str(custom) not in xml
    assert "FREEMYID_HOME" not in xml
    assert TRICKY not in xml
    assert not (custom / "freemyid-task.xml").exists()
