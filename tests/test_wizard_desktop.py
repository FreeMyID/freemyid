"""Draft tests for the desktop launcher (no window is ever opened)."""
from __future__ import annotations

import urllib.request

import pytest

from vanish.wizard import desktop
from vanish.wizard.server import start_background


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("VANISH_HOME", str(tmp_path))
    monkeypatch.setenv("VANISH_TEST_KEY", "dev")
    return tmp_path


def test_instance_file_roundtrip_and_stale(home):
    assert desktop.read_instance() is None
    desktop.write_instance(1, "tok")          # nothing listens on port 1 -> stale
    assert desktop.read_instance() is None
    desktop.clear_instance(1)
    assert not (home / desktop.INSTANCE_FILE).exists()


def test_second_launch_focuses_first(home, monkeypatch):
    running = start_background(0)
    try:
        hits = []
        running.app.state.on_focus = lambda: hits.append(1)
        desktop.write_instance(running.port, running.token)
        info = desktop.read_instance()
        assert info == {"port": running.port, "token": running.token}
        opened = []
        monkeypatch.setattr(desktop.webbrowser, "open", lambda u: opened.append(u))
        assert desktop.main() == 0           # second launch: no new server, no window
        assert hits == [1] and opened == []
        assert desktop.ask_running_instance_to_focus({"port": running.port, "token": "wrong"}) is False
    finally:
        running.stop()


def test_server_only_on_loopback_and_needs_token(home):
    running = start_background(0)
    try:
        assert running.url.startswith("http://127.0.0.1:")
        req = urllib.request.Request(f"http://127.0.0.1:{running.port}/")
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=3)
        assert e.value.code == 403
    finally:
        running.stop()


def test_browser_fallback_when_no_pywebview(home, monkeypatch):
    opened = []
    monkeypatch.setattr(desktop, "_show_window", lambda url, cb: False)
    monkeypatch.setattr(desktop.webbrowser, "open", lambda u: opened.append(u))
    monkeypatch.setattr(desktop, "_wait_forever", lambda stop: None)
    assert desktop.main() == 0
    assert opened and opened[0].startswith("http://127.0.0.1:")
    assert not (home / desktop.INSTANCE_FILE).exists()
