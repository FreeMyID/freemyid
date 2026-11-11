"""Scheduler text escapes &, <, >, quotes, and non-ASCII. Nothing is installed.

The caller passes the path. Windows and plist text are parsed with the standard
library. Cron uses cronie's \\% rule, then shlex. Jane Q Testperson only.
"""
from __future__ import annotations

import hashlib
import plistlib
import re
import shlex
import socket
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from subprocess import list2cmdline

import pytest

from freemyid.scheduler import render

# The path is the caller's. é is one accented character (U+00E9).
ACCENT = "\u00e9"
SPECIAL = f"data & <files> Jane's \"Q\" 100% caf{ACCENT}"
POSIX_PATH = str(PurePosixPath("/home/Jane Q Testperson", SPECIAL, "freemyid"))
WIN_PATH = f"C:\\Users\\Jane Q Testperson\\{SPECIAL}\\FreeMyID.exe"
LOG_PATH = str(PurePosixPath("/home/Jane Q Testperson", SPECIAL, "scheduler.log"))
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}

PLAIN_CMD = ["/home/Jane Q Testperson/FreeMyID/freemyid", "run", "--scheduled"]
PLAIN_LOG = "/home/Jane Q Testperson/Library/Logs/scheduler.log"
PLAIN_WIN = [
    r"C:\Users\Jane Q Testperson\AppData\Local\FreeMyID\FreeMyID.exe",
    "run",
    "--scheduled",
]
PLAIN_ENV = {"FREEMYID_HOME": "/home/Jane Q Testperson/data"}
META = "/home/Jane Q Testperson/data & <files>/freemyid"
META_WIN = [r"C:\Users\Jane Q Testperson\data & <files>\FreeMyID.exe", "run", "--scheduled"]
PCT = "/home/Jane Q Testperson/100%/freemyid"
PCT_WIN = [r"C:\Users\Jane Q Testperson\100%\FreeMyID.exe", "run", "--scheduled"]

# SHA-256 of the copied WO-334 renderer, before quote and non-ASCII escaping.
_WO334 = {
    "cron_plain": "cc9e2ff2ece692f699592da72cb5fc3990eccb27167376341c41275e2b69669b",
    "plist_plain": "0232aaa09e752f7bc2ecdfd10193af25f25c8897368d794dab88ef4d307c842d",
    "plist_plain_env": "4e345a0a9078bef0e8c66a2a4f2dd035c731036c99c2311379fb4573c38a1acc",
    "win_plain": "0debfb44d2580924b695050011d8f2c30d7f028d2e2dfb06adc208a86f82fae0",
    "systemd_plain": "e385379b2a83f246ab05301de8cf622fa8e2b495e8ed5fa9964871513ea774f7",
    "plist_meta": "8290ef64fdecf62ef246de9f025001ca7491e9fedea93efa93e3fc2101848aec",
    "win_meta": "619470fb8fb6e4d5795a4d2ea2268d77fee1418659fe80e2673c0cf27414737a",
    "plist_pct": "9a65f6199f4efe99ff579b454acb6f28ab4c77452a62c8fecddf7bbb562dc776",
    "win_pct": "b48d184fd944c9dd963c26646fafc9babb741161f71e1e371366628b2769bbf6",
    "cron_pct": "0a3425dfd70b7bd488fd4ad0c2277dc95bffad4c962ec8b4ad6d3fd32ca8e2f6",
    "cron_special": "568b434831c1046b852be6957253b53535e99a91ad09b355fdc1cfecc858e53b",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


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
    """What cronie hands the shell: \\% becomes %, and any other % ends the command."""
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


def _cron_command(line: str) -> list[str]:
    words = shlex.split(_cron_to_shell(line), comments=False, posix=True)
    mark = render.CRON_MARK.split()
    assert words[-len(mark):] == mark
    body = words[:-len(mark)]
    if body[:1] == ["@reboot"]:
        assert body[1:4] == ["sleep", "120", "&&"]
        return body[4:]
    assert body[:5] == ["0", str(render.DAILY_HOUR), "*", "*", "*"]
    return body[5:]


def _task_text(root: ET.Element, path: str) -> str:
    node = root.find(path, NS)
    assert node is not None and node.text is not None
    return node.text


def test_output_without_specials_matches_wo334_bytes() -> None:
    cron = render.cron_lines(PLAIN_CMD)
    assert cron == render.cron_lines(PLAIN_CMD, None)
    assert cron == render.cron_lines(PLAIN_CMD, {})
    assert _sha(cron) == _WO334["cron_plain"]
    plist = render.launchd_plist(PLAIN_CMD, PLAIN_LOG)
    assert f"<string>{PLAIN_CMD[0]}</string>" in plist
    assert _sha(plist) == _WO334["plist_plain"]
    assert _sha(render.launchd_plist(PLAIN_CMD, PLAIN_LOG, PLAIN_ENV)) == _WO334["plist_plain_env"]
    xml = render.windows_task_xml(PLAIN_WIN)
    assert f"<Command>{PLAIN_WIN[0]}</Command>" in xml
    assert "&quot;" not in xml and "&apos;" not in xml and "&#" not in xml
    assert _sha(xml) == _WO334["win_plain"]
    assert _sha(render.systemd_service(PLAIN_CMD, PLAIN_ENV)) == _WO334["systemd_plain"]


def test_wo334_amp_lt_gt_and_cron_percent_stay() -> None:
    """& < > were already &amp; &lt; &gt;. A bare % in cron was already \\%."""
    win = render.windows_task_xml(META_WIN)
    assert "&amp;" in win and "&lt;" in win and "&gt;" in win
    assert _sha(win) == _WO334["win_meta"]
    assert _sha(render.launchd_plist([META, "run", "--scheduled"], META)) == _WO334["plist_meta"]
    assert _sha(render.windows_task_xml(PCT_WIN)) == _WO334["win_pct"]
    assert _sha(render.launchd_plist([PCT, "run", "--scheduled"], PCT)) == _WO334["plist_pct"]
    cron = render.cron_lines([PCT, "run", "--scheduled"])
    assert "100\\%" in cron and _sha(cron) == _WO334["cron_pct"]
    assert _cron_command(cron.splitlines()[0]) == [PCT, "run", "--scheduled"]


def test_special_path_parses_back_to_the_input() -> None:
    cmd = [POSIX_PATH, "run", "--scheduled"]
    plist = render.launchd_plist(cmd, LOG_PATH, {"FREEMYID_HOME": POSIX_PATH})
    assert ACCENT not in plist
    assert f"&#{ord(ACCENT)};" in plist
    assert "&quot;" in plist and "&apos;" in plist
    assert "&amp;" in plist and "&lt;" in plist and "&gt;" in plist
    for body in re.findall(r"<string>(.*?)</string>", plist):
        assert "<" not in body and ">" not in body
        assert '"' not in body and "'" not in body
    data = plistlib.loads(plist.encode())
    assert data["ProgramArguments"] == cmd
    assert data["StandardOutPath"] == LOG_PATH
    assert data["StandardErrorPath"] == LOG_PATH
    assert data["EnvironmentVariables"] == {"FREEMYID_HOME": POSIX_PATH}

    win_args = ["run", "--scheduled", WIN_PATH]
    xml = render.windows_task_xml([WIN_PATH, *win_args])
    command = xml.split("<Command>", 1)[1].split("</Command>", 1)[0]
    arguments = xml.split("<Arguments>", 1)[1].split("</Arguments>", 1)[0]
    for chunk in (command, arguments):
        assert "<" not in chunk and ">" not in chunk
        assert '"' not in chunk and "'" not in chunk
        assert ACCENT not in chunk
        assert "&amp;" in chunk and "&lt;" in chunk and "&gt;" in chunk
        assert "&quot;" in chunk and "&apos;" in chunk
        assert f"&#{ord(ACCENT)};" in chunk
        assert "%" in chunk and "&#37;" not in chunk
    for parsed in (ET.fromstring(xml), ET.fromstring(xml.encode("utf-16"))):
        assert _task_text(parsed, "t:Actions/t:Exec/t:Command") == WIN_PATH
        assert _task_text(parsed, "t:Actions/t:Exec/t:Arguments") == list2cmdline(win_args)

    cron = render.cron_lines(cmd)
    assert _sha(cron) == _WO334["cron_special"]
    lines = cron.splitlines()
    assert len(lines) == 2
    assert _cron_command(lines[0]) == cmd
    assert _cron_command(lines[1]) == cmd
