"""Draft tests for the desktop launcher (no window is ever opened)."""
from __future__ import annotations

import urllib.request

import pytest

from freemyid.wizard import desktop
from freemyid.wizard.server import start_background


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
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


class _Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, fn):
        self.handlers.append(fn)
        return self

    def fire(self, *args):
        for fn in self.handlers:
            fn(*args)


class _FakeWin:
    def __init__(self):
        self.events = type("E", (), {})()
        self.events.loaded = _Event()


def test_splash_stays_until_page_loaded(home, monkeypatch):
    """v0.3.0 bug: the splash closed when the window was created, 10-30 s before the page drew.
    It must only close on the webview's 'loaded' event."""
    calls = []

    def fake_window(url, cb):
        win = _FakeWin()
        cb(win)
        assert calls == []       # window created, page not loaded: splash still up
        win.events.loaded.fire(win)
        assert calls == [1]      # page loaded: splash closed
        return True

    monkeypatch.setattr(desktop, "_show_window", fake_window)
    assert desktop.main(on_started=lambda: calls.append(1)) == 0
    assert calls[0] == 1


def test_splash_closes_on_window_ready_with_old_pywebview(home, monkeypatch):
    """No loaded event (old pywebview): fall back to closing when the window is created."""
    calls = []

    def fake_window(url, cb):
        cb(object())
        assert calls == [1]
        return True

    monkeypatch.setattr(desktop, "_show_window", fake_window)
    assert desktop.main(on_started=lambda: calls.append(1)) == 0


def test_splash_closes_if_window_never_loads(home, monkeypatch):
    """Window closed or crashed before loading: the splash still goes away on exit."""
    calls = []
    monkeypatch.setattr(desktop, "_show_window", lambda url, cb: (cb(_FakeWin()), True)[1])
    assert desktop.main(on_started=lambda: calls.append(1)) == 0
    assert calls


def _splash():
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "packaging" / "windows" / "splash_win.py"
    spec = importlib.util.spec_from_file_location("splash_win_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_splash_text_does_not_promise_15_seconds():
    s = _splash()
    assert "15 seconds" not in s.TEXT and "up to a minute" in s.TEXT
    assert "still starting" in s.SLOW_TEXT and s.TIMEOUT_S >= 60


def test_splash_pump_waits_for_close_and_shows_slow_state_on_timeout():
    import threading
    s = _splash()
    now = [0.0]
    slow, ticks = [], []
    done = threading.Event()

    def tick():
        ticks.append(1)
        now[0] += 10.0
        if now[0] >= 200:
            done.set()           # the page finally loaded at 200 s

    assert s.pump(done, lambda: slow.append(now[0]), tick, clock=lambda: now[0],
                  timeout=120, step=0) is True
    assert slow == [120.0]       # switched once, at the timeout, and did not vanish
    assert len(ticks) == 20      # kept running until close()


def test_splash_pump_fast_start_never_shows_slow_state():
    import threading
    s = _splash()
    done = threading.Event()
    now = [0.0]

    def tick():
        now[0] += 1.0
        if now[0] >= 5:
            done.set()

    assert s.pump(done, lambda: None, tick, clock=lambda: now[0], timeout=120, step=0) is False


def test_on_started_called_in_browser_fallback(home, monkeypatch):
    calls = []
    monkeypatch.setattr(desktop, "_show_window", lambda url, cb: False)
    monkeypatch.setattr(desktop.webbrowser, "open", lambda u: None)
    monkeypatch.setattr(desktop, "_wait_forever", lambda stop: None)
    assert desktop.main(on_started=lambda: calls.append(1)) == 0
    assert calls
