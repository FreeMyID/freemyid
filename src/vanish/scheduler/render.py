"""Pure renderers for scheduler files. Nothing here touches the system."""
from __future__ import annotations

import shlex
import subprocess
from xml.sax.saxutils import escape as xesc

LABEL = "org.vanish.recheck"
UNIT = "vanish-recheck"
TASK = "Vanish Recheck"
DAILY_HOUR = 10


def systemd_service(cmd: list[str]) -> str:
    return ("[Unit]\nDescription=Vanish scheduled re-check (no UI, no email without approval)\n\n"
            "[Service]\nType=oneshot\nNice=10\n"
            f"ExecStart={' '.join(_sd_quote(c) for c in cmd)}\n")


def _sd_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def systemd_timer() -> str:
    # Persistent=true: a run missed while the machine was off/asleep fires at next boot/wake.
    return ("[Unit]\nDescription=Run Vanish re-check daily\n\n[Timer]\nOnCalendar=daily\n"
            "Persistent=true\nRandomizedDelaySec=15min\n\n[Install]\nWantedBy=timers.target\n")


CRON_MARK = "# vanish-recheck"


def cron_lines(cmd: list[str]) -> str:
    c = " ".join(shlex.quote(x) for x in cmd)
    return (f"0 {DAILY_HOUR} * * * {c} {CRON_MARK}\n"
            f"@reboot sleep 120 && {c} {CRON_MARK}\n")


def launchd_plist(cmd: list[str], log_path: str) -> str:
    args = "".join(f"    <string>{xesc(c)}</string>\n" for c in cmd)
    # launchd runs a job missed during sleep when the Mac wakes.
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{LABEL}</string>\n"
            f"  <key>ProgramArguments</key>\n  <array>\n{args}  </array>\n"
            "  <key>StartCalendarInterval</key>\n  <dict>\n"
            f"    <key>Hour</key>\n    <integer>{DAILY_HOUR}</integer>\n"
            "    <key>Minute</key>\n    <integer>0</integer>\n  </dict>\n"
            "  <key>RunAtLoad</key>\n  <false/>\n  <key>ProcessType</key>\n  <string>Background</string>\n"
            f"  <key>StandardErrorPath</key>\n  <string>{xesc(log_path)}</string>\n"
            f"  <key>StandardOutPath</key>\n  <string>{xesc(log_path)}</string>\n"
            "</dict>\n</plist>\n")


def windows_task_xml(cmd: list[str], hour: int = DAILY_HOUR) -> str:
    """Per-user Task Scheduler XML (no admin needed).

    Daily trigger; StartWhenAvailable = run as soon as possible after a missed start;
    A windowed executable (Vanish.exe / pythonw.exe) = no console window flashes.
    """
    exe, args = cmd[0], subprocess.list2cmdline(cmd[1:])
    return ('<?xml version="1.0" encoding="UTF-16"?>\n'
            '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
            "  <RegistrationInfo><Description>Vanish: quiet daily check for data-broker "
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
