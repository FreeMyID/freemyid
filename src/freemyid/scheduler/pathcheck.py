"""Check a scheduled program path and its arguments.

Pure: no file system, no process, no look at the machine this runs on. The
caller passes the OS name (``linux``, ``macos``, or ``windows``).

``problems`` is empty only when that command is safe to schedule on that OS.
``quoted`` is the command text, or None when this OS has no quoted command
line (macOS launchd stores an argument array) or the text cannot be formed.
On Linux, ``quoted`` is the systemd ``ExecStart`` text and ``cron_quoted`` is
the crontab command. Both are set when the command is safe, because install
may use either scheduler. Neither is set when ``problems`` is not empty.
"""
from __future__ import annotations

import re
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

OS_LINUX = "linux"
OS_MACOS = "macos"
OS_WINDOWS = "windows"
OS_NAMES = frozenset({OS_LINUX, OS_MACOS, OS_WINDOWS})

Code = Literal[
    "unknown_os",
    "empty_command",
    "empty_program",
    "not_text",
    "nul",
    "newline",
    "control",
    "invalid_char",
    "cron_backslash_percent",
    "windows_env_ref",
]

CODE_UNKNOWN_OS: Code = "unknown_os"
CODE_EMPTY_COMMAND: Code = "empty_command"
CODE_EMPTY_PROGRAM: Code = "empty_program"
CODE_NOT_TEXT: Code = "not_text"
CODE_NUL: Code = "nul"
CODE_NEWLINE: Code = "newline"
CODE_CONTROL: Code = "control"
CODE_INVALID_CHAR: Code = "invalid_char"
# Crontab turns \% into % before the shell runs, and a backslash always
# consumes the next character. An odd run of backslashes immediately before
# % cannot be written so the shell still sees that same run. Linux install
# may fall back to cron, so the command is not safe to schedule.
CODE_CRON_BACKSLASH_PERCENT: Code = "cron_backslash_percent"
# Task Scheduler expands %NAME% in the Exec Command and Arguments; % has no escape.
CODE_WINDOWS_ENV_REF: Code = "windows_env_ref"
_ENV_REF = re.compile(r"%[^%]+%")


@dataclass(frozen=True)
class Problem:
    """One reason a command is not safe to schedule. ``code`` is safe to log."""

    code: Code
    index: int


@dataclass(frozen=True)
class PathCheck:
    """``problems`` empty means safe to schedule. See the module docstring."""

    problems: list[Problem]
    quoted: str | None
    cron_quoted: str | None


def check_path(argv: Sequence[object], os_name: str) -> PathCheck:
    """Validate ``argv`` for ``os_name`` and return the quoted form, if one exists."""
    if os_name not in OS_NAMES:
        return _refuse(CODE_UNKNOWN_OS, -1)
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence):
        return _refuse(CODE_NOT_TEXT, -1)
    if len(argv) == 0:
        return _refuse(CODE_EMPTY_COMMAND, -1)

    problems: list[Problem] = []
    text_args: list[str] = []
    for index, arg in enumerate(argv):
        if not isinstance(arg, str):
            problems.append(Problem(CODE_NOT_TEXT, index))
            continue
        if index == 0 and arg == "":
            problems.append(Problem(CODE_EMPTY_PROGRAM, index))
            continue
        problems.extend(_char_problems(arg, index))
        if os_name == OS_LINUX and _odd_backslash_before_percent(arg):
            problems.append(Problem(CODE_CRON_BACKSLASH_PERCENT, index))
        text_args.append(arg)
    if problems:
        return PathCheck(problems, None, None)
    if os_name == OS_MACOS:
        return PathCheck([], None, None)
    if os_name == OS_WINDOWS:
        env_ref = _windows_env_ref(text_args)
        if env_ref is not None:
            return _refuse(CODE_WINDOWS_ENV_REF, env_ref)
        return PathCheck([], _windows_cmdline(text_args), None)
    systemd = " ".join(_systemd_quote(arg, program=index == 0)
                       for index, arg in enumerate(text_args))
    cron = " ".join(_cron_quote(arg) for arg in text_args)
    return PathCheck([], systemd, cron)


def _refuse(code: Code, index: int) -> PathCheck:
    return PathCheck([Problem(code, index)], None, None)


def _char_problems(text: str, index: int) -> list[Problem]:
    saw_nul = False
    saw_newline = False
    saw_control = False
    saw_invalid = False
    for char in text:
        codepoint = ord(char)
        if char == "\0":
            saw_nul = True
        elif char in "\n\r":
            saw_newline = True
        elif codepoint < 32 and char != "\t":
            saw_control = True
        elif not _xml_char(codepoint):
            saw_invalid = True
    found: list[Problem] = []
    if saw_nul:
        found.append(Problem(CODE_NUL, index))
    if saw_newline:
        found.append(Problem(CODE_NEWLINE, index))
    if saw_control:
        found.append(Problem(CODE_CONTROL, index))
    if saw_invalid:
        found.append(Problem(CODE_INVALID_CHAR, index))
    return found


def _xml_char(codepoint: int) -> bool:
    """True for an XML 1.0 Char. Scheduler files are XML or line-oriented text."""
    if codepoint in (0x9, 0xA, 0xD):
        return True
    if 0x20 <= codepoint <= 0xD7FF:
        return True
    if 0xE000 <= codepoint <= 0xFFFD:
        return True
    return 0x10000 <= codepoint <= 0x10FFFF


def _odd_backslash_before_percent(text: str) -> bool:
    start = 0
    while True:
        found = text.find("%", start)
        if found < 0:
            return False
        count = 0
        before = found
        while before > 0 and text[before - 1] == "\\":
            count += 1
            before -= 1
        if count % 2 == 1:
            return True
        start = found + 1


def _systemd_quote(text: str, program: bool = False) -> str:
    """One systemd word. Backslash first, so a quote's escape is not doubled again.

    ``%`` is doubled because unit specifiers expand ``%`` even inside quotes.
    In arguments ``$`` is doubled too: ExecStart substitutes ``$NAME`` and
    ``${NAME}`` (systemd.service(5), "Command lines") and ``$$`` is a literal
    dollar. The program word is not substituted, so it keeps its ``$``.
    Matches ``render.systemd_service``.
    """
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    if not program:
        escaped = escaped.replace("$", "$$")
    return f'"{escaped}"'


def _windows_env_ref(argv: Sequence[str]) -> int | None:
    """Index of the first word in a ``%NAME%`` pair, or None.

    Task Scheduler expands ``%NAME%`` in the Exec Command and in the Arguments
    line, and there is no escape for ``%``. Arguments are one line, so a pair
    can span two words. A single ``%`` is safe.
    """
    if _ENV_REF.search(argv[0]):
        return 0
    line = _windows_cmdline(argv[1:])
    found = _ENV_REF.search(line)
    if found is None:
        return None
    offset = 0
    for index, arg in enumerate(argv[1:], start=1):
        offset += len(_windows_cmdline([arg])) + 1
        if found.start() < offset:
            return index
    return len(argv) - 1


def _cron_quote(text: str) -> str:
    """One crontab field that the shell reads back as ``text``.

    Cron replaces ``\\%`` with ``%`` before the shell, and quotes do not stop
    that. ``%`` is escaped after shell quoting. ``$`` stays inside single
    quotes, so it is not expanded.
    """
    return shlex.quote(text).replace("%", "\\%")


def _windows_cmdline(argv: Sequence[str]) -> str:
    """CommandLineToArgvW quoting (the MS C runtime rules). No process is started.

    A trailing backslash inside quotes is doubled so it does not escape the
    closing quote. ``$`` and a single ``%`` are kept: a Task Scheduler Exec
    action does not run the command through cmd.exe. A ``%NAME%`` pair is
    refused before this (``windows_env_ref``), because Task Scheduler expands it.
    """
    result: list[str] = []
    for arg in argv:
        bs_buf: list[str] = []
        if result:
            result.append(" ")
        needquote = (" " in arg) or ("\t" in arg) or arg == ""
        if needquote:
            result.append('"')
        for char in arg:
            if char == "\\":
                bs_buf.append(char)
            elif char == '"':
                result.append("\\" * (len(bs_buf) * 2))
                bs_buf = []
                result.append('\\"')
            else:
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(char)
        if bs_buf:
            result.extend(bs_buf)
        if needquote:
            result.extend(bs_buf)
            result.append('"')
    return "".join(result)
