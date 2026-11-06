"""Scheduler tests: render only, nothing is ever installed."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from vanish import scheduler
from vanish.scheduler import render

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
WIN = [r"C:\Users\Test User\AppData\Local\Vanish\Vanish.exe", "run", "--scheduled"]


def test_windows_xml_is_valid_and_windowless_and_catches_up():
    x = render.windows_task_xml(WIN)
    root = ET.fromstring(x.replace('encoding="UTF-16"', ""))
    g = lambda p: root.find(p, NS)
    assert g("t:Settings/t:StartWhenAvailable").text == "true"
    assert g("t:Settings/t:Hidden").text == "false"
    assert g("t:Settings/t:MultipleInstancesPolicy").text == "IgnoreNew"
    assert g("t:Principals/t:Principal/t:RunLevel").text == "LeastPrivilege"
    assert g("t:Triggers/t:CalendarTrigger/t:ScheduleByDay/t:DaysInterval").text == "1"
    assert g("t:Actions/t:Exec/t:Command").text.endswith("Vanish.exe")
    assert g("t:Actions/t:Exec/t:Arguments").text == "run --scheduled"


def test_windows_xml_escapes():
    x = render.windows_task_xml([r"C:\A & B\Vanish.exe", "run", "--scheduled"])
    assert "A &amp; B" in x and "<Command>C:" in x


def test_windows_commands_per_user_no_admin():
    assert scheduler.windows_create_args("x.xml") == [
        "schtasks", "/Create", "/TN", render.TASK, "/XML", "x.xml", "/F"]   # /F = idempotent
    for a in (scheduler.windows_create_args("x"), scheduler.windows_delete_args(),
              scheduler.windows_query_args()):
        assert "/RU" not in a and "/RP" not in a and "SYSTEM" not in " ".join(a)


def test_job_command_variants():
    c = scheduler.job_command(frozen=False, platform="windows")
    assert c[-2:] == ["run", "--scheduled"] and "from vanish.cli import app" in c[2]
    assert scheduler.job_command(frozen=True, platform="linux")[1:] == ["run", "--scheduled"]


def test_linux_and_mac_render_unchanged():
    cmd = ["/usr/bin/vanish", "run", "--scheduled"]
    assert "OnCalendar=daily" in render.systemd_timer() and "Persistent=true" in render.systemd_timer()
    assert "@reboot" in render.cron_lines(cmd)
    assert "StartCalendarInterval" in render.launchd_plist(cmd, "/tmp/x.log")
