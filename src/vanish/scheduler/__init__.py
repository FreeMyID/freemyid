"""Background re-check job: install / remove / status. Runs `vanish run --scheduled`.

Rendering lives in render.py (pure, testable). The functions here are the only code that
touches the system, and only when the user explicitly asks (`vanish schedule install`).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .. import paths
from . import render

__all__ = ["install", "job_command", "platform_name", "remove", "status", "windows_create_args",
           "windows_delete_args", "windows_query_args"]


def platform_name() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    raise RuntimeError("Scheduling is not supported on this system.")


def _windowless_python() -> str:
    """pythonw.exe next to python.exe (no console window); falls back to python.exe."""
    exe = Path(sys.executable)
    pw = exe.with_name("pythonw.exe")
    return str(pw) if pw.exists() else str(exe)


def job_command(frozen: bool | None = None, platform: str | None = None) -> list[str]:
    """The command the scheduler runs. Arguments let tests render it for any OS."""
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    win = (sys.platform == "win32") if platform is None else platform == "windows"
    if frozen:
        exe = Path(sys.executable)
        if win:   # the windowed Vanish.exe, so no console window flashes
            gui = exe.with_name("Vanish.exe")
            return [str(gui if gui.exists() else exe), "run", "--scheduled"]
        return [str(exe), "run", "--scheduled"]
    if win:
        return [_windowless_python(), "-c", "from vanish.cli import app; app()",
                "run", "--scheduled"]
    exe_path = shutil.which("vanish")
    if exe_path:
        return [exe_path, "run", "--scheduled"]
    return [sys.executable, "-c", "from vanish.cli import app; app()", "run", "--scheduled"]


def _run(args: list[str], input: str | None = None) -> subprocess.CompletedProcess:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    return subprocess.run(args, input=input, check=False, capture_output=True, text=True,
                          timeout=60, creationflags=flags)


def _systemd_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd" / "user"


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{render.LABEL}.plist"


def _has_systemd_user() -> bool:
    if not shutil.which("systemctl"):
        return False
    try:
        return _run(["systemctl", "--user", "show-environment"]).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _crontab_get() -> str:
    r = _run(["crontab", "-l"])
    return r.stdout if r.returncode == 0 else ""


def _strip_cron(text: str) -> str:
    return "".join(ln + "\n" for ln in text.splitlines() if render.CRON_MARK not in ln)


def windows_create_args(xml_path: str) -> list[str]:
    # No /RU or /RP: the task belongs to the current user and needs no admin rights.
    return ["schtasks", "/Create", "/TN", render.TASK, "/XML", xml_path, "/F"]


def windows_delete_args() -> list[str]:
    return ["schtasks", "/Delete", "/TN", render.TASK, "/F"]


def windows_query_args() -> list[str]:
    return ["schtasks", "/Query", "/TN", render.TASK]


def install() -> str:
    cmd = job_command()
    plat = platform_name()
    if plat == "linux":
        if _has_systemd_user():
            d = _systemd_dir()
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{render.UNIT}.service").write_text(render.systemd_service(cmd))
            (d / f"{render.UNIT}.timer").write_text(render.systemd_timer())
            _run(["systemctl", "--user", "daemon-reload"])
            r = _run(["systemctl", "--user", "enable", "--now", f"{render.UNIT}.timer"])
            if r.returncode != 0:
                raise RuntimeError("Could not start the systemd timer.")
            return ("Installed a daily systemd user timer. If the computer was off, the check "
                    "runs when it next starts.")
        if shutil.which("crontab"):
            new = _strip_cron(_crontab_get()) + render.cron_lines(cmd)
            if _run(["crontab", "-"], input=new).returncode != 0:
                raise RuntimeError("Could not update crontab.")
            return "Installed a daily cron job plus a run at startup."
        raise RuntimeError("Neither systemd nor cron is available.")
    if plat == "macos":
        p = _plist_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render.launchd_plist(cmd, str(paths.logs_dir() / "scheduler.log")))
        _run(["launchctl", "unload", str(p)])
        if _run(["launchctl", "load", "-w", str(p)]).returncode != 0:
            raise RuntimeError("Could not load the launchd agent.")
        return "Installed a daily launchd agent. Missed runs happen when the Mac wakes."
    xml = paths.home() / "vanish-task.xml"
    xml.write_text(render.windows_task_xml(cmd), encoding="utf-16")
    try:   # /F replaces an existing task, so installing twice is harmless
        r = _run(windows_create_args(str(xml)))
    finally:
        xml.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError("Could not create the scheduled task.")
    return "Installed a daily scheduled task that also runs after a missed start."


def remove() -> str:
    plat = platform_name()
    if plat == "linux":
        if shutil.which("systemctl"):
            _run(["systemctl", "--user", "disable", "--now", f"{render.UNIT}.timer"])
        d = _systemd_dir()
        for ext in ("service", "timer"):
            (d / f"{render.UNIT}.{ext}").unlink(missing_ok=True)
        if shutil.which("crontab"):
            cur = _crontab_get()
            if render.CRON_MARK in cur:
                _run(["crontab", "-"], input=_strip_cron(cur))
        return "Background checks removed."
    if plat == "macos":
        p = _plist_path()
        _run(["launchctl", "unload", str(p)])
        p.unlink(missing_ok=True)
        return "Background checks removed."
    _run(windows_delete_args())    # fails harmlessly if it was never installed
    return "Background checks removed."


def status() -> str:
    try:
        plat = platform_name()
    except RuntimeError as e:
        return str(e)
    if plat == "linux":
        if (_systemd_dir() / f"{render.UNIT}.timer").exists():
            r = _run(["systemctl", "--user", "is-active", f"{render.UNIT}.timer"])
            return f"systemd timer: {r.stdout.strip() or 'unknown'}"
        if shutil.which("crontab") and render.CRON_MARK in _crontab_get():
            return "cron job installed"
        return "not installed"
    if plat == "macos":
        return "launchd agent installed" if _plist_path().exists() else "not installed"
    r = _run(windows_query_args())
    return "scheduled task installed" if r.returncode == 0 else "not installed"
