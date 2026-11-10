"""Odd install paths for a scheduled command. Nothing is installed.

The person in every path is Jane Q Testperson of Springfield IL. The OS name
is an argument: these tests run on whatever machine collected them.
"""
from __future__ import annotations

import builtins
import shlex
import socket
import sys
from collections.abc import Sequence

import pytest

from freemyid.scheduler.pathcheck import (
    CODE_CONTROL,
    CODE_CRON_BACKSLASH_PERCENT,
    CODE_EMPTY_COMMAND,
    CODE_EMPTY_PROGRAM,
    CODE_INVALID_CHAR,
    CODE_NEWLINE,
    CODE_NOT_TEXT,
    CODE_NUL,
    CODE_UNKNOWN_OS,
    PathCheck,
    check_path,
)

# Possessive of Jane Q Testperson, not another person. café is a folder name.
_WIN = "C:\\Users\\Jane Q Testperson\\Springfield IL"
_MAC = "/Users/Jane Q Testperson/Springfield IL"
_LIN = "/home/Jane Q Testperson/Springfield IL"


def _win(*parts: str) -> str:
    return "\\".join((_WIN, *parts))


def _mac(*parts: str) -> str:
    return "/".join((_MAC, *parts))


def _lin(*parts: str) -> str:
    return "/".join((_LIN, *parts))


# One row per OS per hazard. The hazard is in the program and in an argument.
_TABLE: list[tuple[str, str, list[str]]] = [
    ("windows", "space", [_win("Free My ID", "FreeMyID.exe"), "run scheduled"]),
    ("windows", "apostrophe", [_win("Jane's files", "FreeMyID.exe"), "Jane's"]),
    ("windows", "non_ascii", [_win("café", "FreeMyID.exe"), "café"]),
    ("windows", "trailing_backslash", [_win("FreeMyID") + "\\", "run\\"]),
    ("windows", "percent", [_win("100%", "FreeMyID.exe"), "100%"]),
    ("windows", "dollar", [_win("$HOME", "FreeMyID.exe"), "$HOME"]),
    ("windows", "quote", [_win('Free"My"ID', "FreeMyID.exe"), 'say "hi"']),
    ("macos", "space", [_mac("Free My ID", "FreeMyID"), "run scheduled"]),
    ("macos", "apostrophe", [_mac("Jane's files", "FreeMyID"), "Jane's"]),
    ("macos", "non_ascii", [_mac("café", "FreeMyID"), "café"]),
    ("macos", "trailing_backslash", [_mac("FreeMyID") + "\\", "run\\"]),
    ("macos", "percent", [_mac("100%", "FreeMyID"), "100%"]),
    ("macos", "dollar", [_mac("$HOME", "FreeMyID"), "$HOME"]),
    ("macos", "quote", [_mac('Free"My"ID', "FreeMyID"), 'say "hi"']),
    ("linux", "space", [_lin("Free My ID", "freemyid"), "run scheduled"]),
    ("linux", "apostrophe", [_lin("Jane's files", "freemyid"), "Jane's"]),
    ("linux", "non_ascii", [_lin("café", "freemyid"), "café"]),
    ("linux", "trailing_backslash", [_lin("freemyid") + "\\", "run\\"]),
    ("linux", "percent", [_lin("100%", "freemyid"), "100%"]),
    ("linux", "dollar", [_lin("$HOME", "freemyid"), "$HOME"]),
    ("linux", "quote", [_lin('Free"My"ID', "freemyid"), 'say "hi"']),
]


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: object) -> None:
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


def _codes(result: PathCheck) -> list[str]:
    return [problem.code for problem in result.problems]


def _windows_argv(cmdline: str) -> list[str]:
    """CommandLineToArgvW, independent of the quoter."""
    args: list[str] = []
    index = 0
    length = len(cmdline)
    while index < length:
        if cmdline[index] in " \t":
            index += 1
            continue
        current: list[str] = []
        in_quotes = False
        while index < length:
            char = cmdline[index]
            if not in_quotes and char in " \t":
                break
            if char == "\\":
                start = index
                while index < length and cmdline[index] == "\\":
                    index += 1
                slashes = index - start
                if index < length and cmdline[index] == '"':
                    current.append("\\" * (slashes // 2))
                    index += 1
                    if slashes % 2 == 1:
                        current.append('"')
                    else:
                        in_quotes = not in_quotes
                else:
                    current.append("\\" * slashes)
                continue
            if char == '"':
                in_quotes = not in_quotes
                index += 1
                continue
            current.append(char)
            index += 1
        args.append("".join(current))
    return args


def _systemd_argv(text: str) -> list[str]:
    """Undo specifier doubling, then systemd word splits. Independent of the quoter."""
    expanded: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == "%" and index + 1 < len(text) and text[index + 1] == "%":
            expanded.append("%")
            index += 2
            continue
        expanded.append(text[index])
        index += 1
    raw = "".join(expanded)
    args: list[str] = []
    index = 0
    length = len(raw)
    while index < length:
        if raw[index] == " ":
            index += 1
            continue
        assert raw[index] == '"'
        index += 1
        current: list[str] = []
        while index < length and raw[index] != '"':
            if raw[index] == "\\":
                current.append(raw[index + 1])
                index += 2
                continue
            current.append(raw[index])
            index += 1
        assert index < length and raw[index] == '"'
        index += 1
        args.append("".join(current))
    return args


def _cron_to_shell(line: str) -> str:
    """What cron hands the shell: \\% becomes %, and any other % would end the command."""
    out: list[str] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line):
            nxt = line[index + 1]
            out.append("%" if nxt == "%" else "\\" + nxt)
            index += 2
            continue
        assert char != "%"
        out.append(char)
        index += 1
    return "".join(out)


def _assert_round_trip(os_name: str, result: PathCheck, argv: Sequence[str]) -> None:
    assert result.problems == []
    if os_name == "windows":
        assert result.quoted is not None
        assert result.cron_quoted is None
        assert _windows_argv(result.quoted) == list(argv)
        return
    if os_name == "linux":
        assert result.quoted is not None
        assert result.cron_quoted is not None
        assert _systemd_argv(result.quoted) == list(argv)
        assert shlex.split(_cron_to_shell(result.cron_quoted)) == list(argv)
        assert "$(" not in result.cron_quoted
        return
    assert os_name == "macos"
    assert result.quoted is None
    assert result.cron_quoted is None


@pytest.mark.parametrize(
    ("os_name", "hazard", "argv"),
    _TABLE,
    ids=[f"{os_name}-{hazard}" for os_name, hazard, _argv in _TABLE],
)
def test_odd_paths_round_trip(os_name: str, hazard: str, argv: list[str]) -> None:
    assert "Jane Q Testperson" in argv[0]
    assert "Springfield IL" in argv[0]
    assert hazard
    result = check_path(argv, os_name)
    _assert_round_trip(os_name, result, argv)


def test_os_name_is_not_taken_from_this_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    program = _lin("freemyid")
    monkeypatch.setattr(sys, "platform", "win32")
    linux = check_path([program, "run"], "linux")
    monkeypatch.setattr(sys, "platform", "linux")
    windows = check_path([_win("FreeMyID.exe"), "run"], "windows")
    assert linux.quoted is not None and linux.quoted.startswith('"/home/')
    assert windows.quoted is not None and "C:\\Users\\" in windows.quoted
    assert linux.cron_quoted is not None
    assert windows.cron_quoted is None


def test_even_backslashes_before_percent_round_trip_on_linux() -> None:
    argv = [_lin("share\\\\%file"), "a\\\\%b"]
    result = check_path(argv, "linux")
    _assert_round_trip("linux", result, argv)


def test_odd_backslashes_before_percent_are_refused_on_linux_only() -> None:
    program = _lin("share\\%file")
    argument = "tail\\%"
    for os_name in ("linux", "macos", "windows"):
        argv = [program if os_name == "linux" else _win("share\\%file"), argument]
        if os_name == "macos":
            argv[0] = _mac("share\\%file")
        result = check_path(argv, os_name)
        if os_name == "linux":
            assert _codes(result) == [CODE_CRON_BACKSLASH_PERCENT, CODE_CRON_BACKSLASH_PERCENT]
            assert [problem.index for problem in result.problems] == [0, 1]
            assert result.quoted is None and result.cron_quoted is None
        else:
            _assert_round_trip(os_name, result, argv)


def test_empty_tab_and_metacharacters_round_trip() -> None:
    argv = [_lin("freemyid"), "", "tab\there", "a & b", "pipe|or", "semi;colon"]
    for os_name in ("linux", "macos", "windows"):
        _assert_round_trip(os_name, check_path(argv, os_name), argv)


def test_refuses_what_cannot_be_quoted() -> None:
    program = _lin("freemyid")
    assert _codes(check_path([], "linux")) == [CODE_EMPTY_COMMAND]
    assert check_path([], "linux").problems[0].index == -1
    empty = check_path([""], "windows")
    assert _codes(empty) == [CODE_EMPTY_PROGRAM] and empty.quoted is None
    nul = check_path([program, "a\0b"], "macos")
    assert _codes(nul) == [CODE_NUL] and nul.problems[0].index == 1
    newline = check_path([program + "\n"], "linux")
    assert _codes(newline) == [CODE_NEWLINE]
    cr = check_path(["line\r"], "windows")
    assert _codes(cr) == [CODE_NEWLINE]
    control = check_path([program, "bell\x07"], "macos")
    assert _codes(control) == [CODE_CONTROL] and control.problems[0].index == 1
    invalid = check_path([program + "\ufffe"], "linux")
    assert _codes(invalid) == [CODE_INVALID_CHAR]
    surrogate = check_path(["\ud800"], "windows")
    assert _codes(surrogate) == [CODE_INVALID_CHAR]
    unknown = check_path([program], "win32")
    assert _codes(unknown) == [CODE_UNKNOWN_OS] and unknown.quoted is None
    not_text = check_path("not-a-list", "linux")  # type: ignore[arg-type]
    assert _codes(not_text) == [CODE_NOT_TEXT]
    mixed = check_path([program, 3], "macos")  # type: ignore[list-item]
    assert _codes(mixed) == [CODE_NOT_TEXT] and mixed.problems[0].index == 1


def test_one_argument_can_carry_several_codes() -> None:
    result = check_path([_mac("FreeMyID") + "\0\n\x07\ufffe"], "macos")
    assert _codes(result) == [CODE_NUL, CODE_NEWLINE, CODE_CONTROL, CODE_INVALID_CHAR]
    assert {problem.index for problem in result.problems} == {0}
    blob = " ".join(_codes(result))
    assert "Jane" not in blob and "Springfield" not in blob and "café" not in blob


def test_check_does_not_open_a_file_or_start_a_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse_open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("file access")

    monkeypatch.setattr(builtins, "open", refuse_open)
    argv = [_lin("100%", "café", "Jane's files", "freemyid") + "\\", "$HOME", 'say "hi"']
    result = check_path(argv, "linux")
    _assert_round_trip("linux", result, argv)
