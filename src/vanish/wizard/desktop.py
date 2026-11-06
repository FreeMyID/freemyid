"""Desktop launcher: the app window users double-click (Start Menu / Desktop shortcut).

Starts the local server on a free 127.0.0.1 port in a background thread and shows it in a
native window (pywebview, which uses Edge WebView2 on Windows). If pywebview or its browser
engine is missing, falls back to the default web browser. The user never sees "localhost".

First launch with no profile lands in the wizard, otherwise the dashboard (the "/" route
already decides). A second launch finds the first through an instance file in VANISH_HOME,
asks it to come to the front, and exits.
"""
from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .. import paths

log = logging.getLogger(__name__)
INSTANCE_FILE = "app-instance.json"
TITLE = "Vanish"


def _instance_path() -> Path:
    return paths.home() / INSTANCE_FILE


def _alive(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def read_instance() -> dict[str, Any] | None:
    """The running instance's {port, token}, or None (missing file or stale after a crash)."""
    try:
        info = json.loads(_instance_path().read_text())
        port, token = int(info["port"]), str(info["token"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {"port": port, "token": token} if _alive(port) else None


def write_instance(port: int, token: str) -> None:
    p = _instance_path()
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"port": port, "token": token}))
    os.replace(tmp, p)


def clear_instance(port: int) -> None:
    try:
        if json.loads(_instance_path().read_text()).get("port") == port:
            _instance_path().unlink()
    except (OSError, ValueError):
        pass


def ask_running_instance_to_focus(info: dict[str, Any]) -> bool:
    """POST /_focus to the first instance (same token + CSRF scheme as the browser)."""
    csrf = hmac.new(info["token"].encode(), b"vanish-csrf", hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}/_focus", data=b"", method="POST",
        headers={"Cookie": f"vanish_session={info['token']}", "X-CSRF": csrf})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except OSError:
        return False


def _wait_forever(stop: threading.Event) -> None:
    try:
        while not stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass


def _show_window(url: str, on_ready: Callable[[Any], None]) -> bool:
    """Open a pywebview window and block until it closes. False if pywebview is unusable."""
    try:
        import webview
    except ImportError:
        return False
    try:
        with contextlib.suppress(Exception):
            webview.settings["ALLOW_DOWNLOADS"] = True
        win = webview.create_window(TITLE, url, width=1100, height=820, min_size=(760, 560))
        on_ready(win)
        webview.start()
        return True
    except Exception as e:  # noqa: BLE001  no WebView2 / no GUI toolkit
        log.warning("native window unavailable (%s); using the web browser", type(e).__name__)
        return False


def main(window: bool = True) -> int:
    """Run the app. Returns a process exit code."""
    from .server import start_background

    paths.home()
    if (info := read_instance()) is not None:
        if not ask_running_instance_to_focus(info):
            webbrowser.open(f"http://127.0.0.1:{info['port']}/?t={info['token']}")
        return 0

    running = start_background(0)
    write_instance(running.port, running.token)
    stop = threading.Event()
    try:
        shown = False
        if window and os.environ.get("VANISH_NO_WINDOW") != "1":
            def on_ready(win: Any) -> None:
                def focus() -> None:
                    for fn in ("restore", "show"):
                        with contextlib.suppress(Exception):
                            getattr(win, fn)()
                    with contextlib.suppress(Exception):   # nudge to front
                        win.on_top = True
                        win.on_top = False
                running.app.state.on_focus = focus
            shown = _show_window(running.url, on_ready)
        if not shown:
            # Browser fallback: the program keeps running until "Close Vanish" in Settings.
            running.app.state.on_focus = lambda: webbrowser.open(running.url)
            running.app.state.on_quit = stop.set
            webbrowser.open(running.url)
            _wait_forever(stop)
    finally:
        clear_instance(running.port)
        running.stop()
    return 0


if __name__ == "__main__":      # python -m vanish.wizard.desktop
    sys.exit(main())
