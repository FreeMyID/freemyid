"""Linux/macOS scheduler install/remove/status against a fake subprocess layer."""
from __future__ import annotations

import subprocess

import pytest

from freemyid import scheduler
from freemyid.scheduler import render

CMD = ["/usr/bin/freemyid", "run", "--headless", "--scheduled"]


class Fake:
    def __init__(self, fail: tuple[str, ...] = ()):
        self.calls: list[list[str]] = []
        self.fail = fail

    def __call__(self, args, input=None):
        self.calls.append(list(args))
        rc = 1 if any(f in " ".join(args) for f in self.fail) else 0
        return subprocess.CompletedProcess(args, rc, stdout="enabled\n", stderr="")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path / "fm"))
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.setattr(scheduler.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(scheduler, "job_command", lambda *a, **k: list(CMD))
    monkeypatch.setattr(scheduler.shutil, "which", lambda n: f"/usr/bin/{n}")
    fake = Fake()
    monkeypatch.setattr(scheduler, "_run", fake)
    return tmp_path, fake, monkeypatch


def test_linux_install_remove_status(env):
    tmp, fake, mp = env
    mp.setattr(scheduler, "platform_name", lambda: "linux")
    msg = scheduler.install()
    d = tmp / "cfg" / "systemd" / "user"
    svc = (d / f"{render.UNIT}.service").read_text()
    assert "--headless" in svc and "Environment=" in svc and "FREEMYID_HOME" in svc
    assert "OnCalendar=daily" in (d / f"{render.UNIT}.timer").read_text()
    assert "enable-linger" in msg
    assert ["systemctl", "--user", "daemon-reload"] in fake.calls
    assert ["systemctl", "--user", "enable", "--now", f"{render.UNIT}.timer"] in fake.calls
    assert all(c[0] != "sudo" and "--system" not in c for c in fake.calls)
    assert "enabled" in scheduler.status()
    scheduler.remove()
    assert not list(d.glob("freemyid-recheck.*"))
    assert ["systemctl", "--user", "disable", "--now", f"{render.UNIT}.timer"] in fake.calls


def test_linux_enable_failure_raises(env):
    _tmp, _fake, mp = env
    mp.setattr(scheduler, "platform_name", lambda: "linux")
    mp.setattr(scheduler, "_run", Fake(fail=("enable",)))
    with pytest.raises(RuntimeError):
        scheduler.install()


def test_linux_cron_fallback(env):
    _tmp, fake, mp = env
    mp.setattr(scheduler, "platform_name", lambda: "linux")
    mp.setattr(scheduler, "_has_systemd_user", lambda: False)
    scheduler.install()
    assert ["crontab", "-"] in fake.calls


def test_macos_install_remove_status(env):
    tmp, fake, mp = env
    mp.setattr(scheduler, "platform_name", lambda: "macos")
    mp.setattr(scheduler, "_uid", lambda: 501)
    scheduler.install()
    plist = tmp / "Library" / "LaunchAgents" / f"{render.LABEL}.plist"
    text = plist.read_text()
    assert "--headless" in text and "EnvironmentVariables" in text
    assert ["launchctl", "bootstrap", "gui/501", str(plist)] in fake.calls
    assert scheduler.status() == "launchd agent loaded"
    scheduler.remove()
    assert not plist.exists()
    assert ["launchctl", "bootout", f"gui/501/{render.LABEL}"] in fake.calls


def test_macos_status_not_installed(env):
    _tmp, _fake, mp = env
    mp.setattr(scheduler, "platform_name", lambda: "macos")
    assert scheduler.status() == "not installed"


def test_render_snapshots():
    svc = render.systemd_service(CMD, {"FREEMYID_HOME": "/data"})
    assert svc.splitlines()[-1] == 'ExecStart="/usr/bin/freemyid" "run" "--headless" "--scheduled"'
    assert 'Environment="FREEMYID_HOME=/data"' in svc
    p = render.launchd_plist(CMD, "/tmp/x.log", {"FREEMYID_HOME": "/data"})
    assert "<string>--headless</string>" in p and "<key>FREEMYID_HOME</key>" in p
