"""Pure renderers for scheduler files. Nothing here touches the system."""
from __future__ import annotations

import re
import shlex
import subprocess
from xml.sax.saxutils import escape as xesc

LABEL = "org.freemyid.recheck"
UNIT = "freemyid-recheck"
TASK = "Free My ID Recheck"
DAILY_HOUR = 10


ENV_PASSTHROUGH = ("FREEMYID_HOME", "FREEMYID_PASSPHRASE_FILE")


def systemd_service(cmd: list[str], env: dict[str, str] | None = None) -> str:
    envs = "".join(f"Environment={_sd_quote(f'{k}={v}')}\n" for k, v in (env or {}).items())
    return ("[Unit]\nDescription=Free My ID scheduled re-check (no UI, no email without approval)\n\n"
            f"[Service]\nType=oneshot\nNice=10\n{envs}"
            f"ExecStart={_sd_exec(cmd)}\n"
            # exit 3 = "something needs you" (docs/CLI.md): a normal outcome, not a unit failure
            "SuccessExitStatus=3\n")


def _sd_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def _sd_exec(cmd: list[str]) -> str:
    """ExecStart words. Arguments also get $ doubled: systemd substitutes $NAME and
    ${NAME} in ExecStart arguments (systemd.service(5), "Command lines") and $$ is a
    literal dollar. The program word is not substituted, so it keeps its $.
    Environment= does no substitution, so _sd_quote alone is right there.
    """
    return " ".join(_sd_quote(c) if i == 0 else _sd_quote(c).replace("$", "$$")
                    for i, c in enumerate(cmd))


def systemd_timer() -> str:
    # Persistent=true: a run missed while the machine was off/asleep fires at next boot/wake.
    return ("[Unit]\nDescription=Run Free My ID re-check daily\n\n[Timer]\nOnCalendar=daily\n"
            "Persistent=true\nRandomizedDelaySec=15min\n\n[Install]\nWantedBy=timers.target\n")


CRON_MARK = "# freemyid-recheck"
# Cronie keeps a backslash, unless the next character is %. \% becomes %
# before the shell runs, and a bare % ends the command. An odd run of
# backslashes immediately before % cannot be written with that escape.
_CRON_NAME = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")


def cron_lines(cmd: list[str], env: dict[str, str] | None = None) -> str:
    """Daily line and @reboot line. env is the same dict systemd and launchd get.

    Quoted NAME=value assignments go on both lines, in front of the command
    (and after ``sleep`` on @reboot, so the shell applies them to the command
    rather than only to sleep).
    """
    command = " ".join(_cron_word(part) for part in cmd)
    prefix = _cron_env_prefix(env)
    return (f"0 {DAILY_HOUR} * * * {prefix}{command} {CRON_MARK}\n"
            f"@reboot sleep 120 && {prefix}{command} {CRON_MARK}\n")


def _cron_word(part: str) -> str:
    """One command word: shell-quoted with % escaped for cron, or printf when an odd
    run of backslashes sits right before a % (see _cron_quote)."""
    if _cron_percent_needs_printf(part):
        return _cron_printf(part)
    return shlex.quote(part).replace("%", "\\%")


def _cron_env_prefix(env: dict[str, str] | None) -> str:
    if not env:
        return ""
    parts = [f"{_cron_name(key)}={_cron_quote(value)}" for key, value in env.items()]
    return " ".join(parts) + " "


def _cron_name(name: str) -> str:
    if _CRON_NAME.fullmatch(name) is None:
        raise ValueError("cron environment name must be a shell identifier")
    return name


def _cron_quote(value: str) -> str:
    """One POSIX shell word, still one crontab field after cronie handles %."""
    if "\n" in value or "\r" in value or "\0" in value:
        raise ValueError("cron environment values must be a single line")
    if _cron_percent_needs_printf(value):
        return _cron_printf(value)
    quoted = "'" + value.replace("'", "'\"'\"'") + "'"
    return quoted.replace("%", "\\%")


def _cron_percent_needs_printf(value: str) -> bool:
    for index, char in enumerate(value):
        if char != "%":
            continue
        count = 0
        before = index
        while before > 0 and value[before - 1] == "\\":
            count += 1
            before -= 1
        if count % 2 == 1:
            return True
    return False


def _cron_printf(value: str) -> str:
    # Octal of the UTF-8 bytes: no bare % for cron, and no quote/space/$ for the shell.
    octets = "".join(f"\\{byte:03o}" for byte in value.encode())
    return f"\"$(printf '{octets}')\""


def launchd_plist(cmd: list[str], log_path: str, env: dict[str, str] | None = None) -> str:
    envx = ""
    if env:
        items = "".join(f"    <key>{xesc(k)}</key>\n    <string>{xesc(v)}</string>\n"
                        for k, v in env.items())
        envx = f"  <key>EnvironmentVariables</key>\n  <dict>\n{items}  </dict>\n"
    args = "".join(f"    <string>{xesc(c)}</string>\n" for c in cmd)
    # RunAtLoad: runs when loaded (at install and at each login), so a check missed
    # while the Mac was switched off still happens.
    # The job uses --scheduled, so that login run only checks sites that are due.
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{LABEL}</string>\n{envx}"
            f"  <key>ProgramArguments</key>\n  <array>\n{args}  </array>\n"
            "  <key>StartCalendarInterval</key>\n  <dict>\n"
            f"    <key>Hour</key>\n    <integer>{DAILY_HOUR}</integer>\n"
            "    <key>Minute</key>\n    <integer>0</integer>\n  </dict>\n"
            "  <key>RunAtLoad</key>\n  <true/>\n"
            "  <key>ProcessType</key>\n  <string>Background</string>\n"
            f"  <key>StandardErrorPath</key>\n  <string>{xesc(log_path)}</string>\n"
            f"  <key>StandardOutPath</key>\n  <string>{xesc(log_path)}</string>\n"
            "</dict>\n</plist>\n")


def windows_task_xml(cmd: list[str], hour: int = DAILY_HOUR) -> str:
    """Per-user Task Scheduler XML (no admin needed).

    Daily trigger; StartWhenAvailable = run as soon as possible after a missed start;
    A windowed executable (FreeMyID.exe / pythonw.exe) = no console window flashes.
    """
    exe, args = cmd[0], subprocess.list2cmdline(cmd[1:])
    return ('<?xml version="1.0" encoding="UTF-16"?>\n'
            '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
            "  <RegistrationInfo><Description>Free My ID: quiet daily check for data-broker "
            "listings. Only bothers you when it needs help.</Description></RegistrationInfo>\n"
            "  <Triggers>\n    <CalendarTrigger>\n"
            f"      <StartBoundary>2000-01-01T{hour:02d}:00:00</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n      <ScheduleByDay><DaysInterval>1</DaysInterval>"
            "</ScheduleByDay>\n    </CalendarTrigger>\n  </Triggers>\n"
            "  <Principals><Principal id=\"Author\"><LogonType>InteractiveToken</LogonType>"
            "<RunLevel>LeastPrivilege</RunLevel></Principal></Principals>\n"
            "  <Settings>\n    <StartWhenAvailable>true</StartWhenAvailable>\n"
            "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
            "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
            "    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>\n"
            "    <WakeToRun>false</WakeToRun>\n    <Hidden>false</Hidden>\n"
            "    <Enabled>true</Enabled>\n"
            "    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>\n"
            "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n  </Settings>\n"
            f"  <Actions Context=\"Author\">\n    <Exec>\n      <Command>{xesc(exe)}</Command>\n"
            f"      <Arguments>{xesc(args)}</Arguments>\n    </Exec>\n  </Actions>\n</Task>\n")
