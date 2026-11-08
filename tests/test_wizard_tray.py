"""BL-IN-23: tray icon. Nothing here needs a display or pystray."""
from __future__ import annotations

import sys

from freemyid import config as cfgmod
from freemyid.wizard import tray


class FakeStore:
    def __init__(self, todos=0):
        self._t = [object()] * todos

    def list_todos(self):
        return self._t

    def list_statuses(self):
        return []

    def list_profiles(self):
        return [object()]


def test_menu_items_and_checking_state():
    m = tray.menu_items("All quiet.", checking=False)
    assert [i.action for i in m] == ["open", None, "check", "quit"]
    assert m[1].label == "All quiet." and not m[1].enabled
    c = tray.menu_items("x", checking=True)
    assert c[2].label == "Checking now..." and not c[2].enabled


def test_status_text_has_no_names_and_flags_todos():
    s, needs = tray.status_text(FakeStore(todos=2))
    assert needs and isinstance(s, str) and s
    assert not tray.status_text(FakeStore())[1]


def test_check_now_command_is_headless_and_practice_stays_practice():
    cmd = tray.check_now_command(real=False)
    assert cmd[-3:] == ["run", "--headless", "--dry-run"] and "--scheduled" not in cmd
    assert tray.check_now_command(real=True)[-2:] == ["run", "--headless"]


def test_check_now_runs_one_at_a_time(freemyid_env):
    class P:
        def poll(self):
            return None
    calls = []
    c = tray.CheckNow(lambda cmd, **kw: calls.append(cmd) or P())
    assert c.start() is True and c.start() is False and len(calls) == 1


def test_off_by_default_and_missing_extra_is_quiet(freemyid_env, monkeypatch):
    assert cfgmod.load().tray_enabled is False
    assert tray.start_tray(FakeStore(), on_open=lambda: None, on_quit=lambda: None) is None
    monkeypatch.setattr(cfgmod, "load", lambda: cfgmod.Config(tray_enabled=True))
    monkeypatch.setitem(sys.modules, "pystray", None)       # simulate the extra not installed
    assert tray.available() is False
    assert tray.start_tray(FakeStore(), on_open=lambda: None, on_quit=lambda: None) is None
