"""Tray / menu-bar icon (BL-IN-23). Off unless config `tray_enabled` is on AND the optional
`tray` extra (pystray + pillow) is installed. Everything that needs a display is behind
`start_tray`; the menu and the status text are plain functions so they test without one.

The status line is the dashboard's own sentence: no names, no site names.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

REFRESH_SECONDS = 60


@dataclass(frozen=True)
class MenuItem:
    label: str
    action: str | None      # None = a line of text, not clickable
    enabled: bool = True


def status_text(store: Any, running: bool = False) -> tuple[str, bool]:
    """(sentence, needs_you). Reads the database only; never the network."""
    from . import dashboard
    todos = store.list_todos()
    sentence, _good = dashboard.status_sentence(store.list_statuses(), len(todos), running,
                                                 has_people=bool(store.list_profiles()))
    return sentence, bool(todos)


def menu_items(sentence: str, checking: bool) -> list[MenuItem]:
    return [
        MenuItem("Open Free My ID", "open"),
        MenuItem(sentence, None, False),
        MenuItem("Checking now..." if checking else "Check now", "check", not checking),
        MenuItem("Quit Free My ID", "quit"),
    ]


def check_now_command(real: bool) -> list[str]:
    """Same program the scheduler runs, but without --scheduled (so it ignores 'not due yet')
    and always headless (never prompts or opens windows). Practice mode stays practice."""
    from ..scheduler import job_command
    cmd = [a for a in job_command() if a not in ("--scheduled", "--headless", "run")]
    return [*cmd, "run", "--headless", *([] if real else ["--dry-run"])]


class CheckNow:
    """Starts one background check at a time."""

    def __init__(self, popen: Callable[..., Any] = subprocess.Popen) -> None:
        self._popen = popen
        self._proc: Any = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        if self.running:
            return False
        from .. import config as cfgmod
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        kw: dict[str, Any] = {"creationflags": flags} if flags else {}
        self._proc = self._popen(check_now_command(cfgmod.load().real_submissions_enabled),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        return True


def available() -> bool:
    try:
        import PIL  # noqa: F401  # type: ignore[import-not-found,import-untyped,unused-ignore]
        import pystray  # noqa: F401  # type: ignore[import-not-found,import-untyped,unused-ignore]
    except Exception:  # noqa: BLE001  ImportError, or no display backend on import
        return False
    return True


def _icon_path() -> Path | None:
    here = Path(__file__).resolve().parent / "static"
    p = here / "freemyid.png"
    return p if p.is_file() else None


def start_tray(store: Any, *, on_open: Callable[[], None], on_quit: Callable[[], None],
               checker: CheckNow | None = None) -> Any | None:
    """Start the tray icon in a background thread. Returns the icon, or None when the setting is
    off, the extra is missing or the desktop has no tray. Never raises."""
    try:
        from .. import config as cfgmod
        if not cfgmod.load().tray_enabled or not available():
            return None
        import pystray  # type: ignore[import-not-found,import-untyped,unused-ignore]
        from PIL import Image
        checker = checker or CheckNow()
        path = _icon_path()
        if path is None:
            return None
        image = Image.open(path)
        actions: dict[str, Callable[[], Any]] = {
            "open": on_open, "check": lambda: checker.start(), "quit": on_quit}

        def build() -> Any:
            sentence, _ = status_text(store, checker.running)
            return pystray.Menu(*[
                pystray.MenuItem(i.label, (lambda _ic, _it, a=i.action: actions[a]())
                                 if i.action else None, enabled=i.enabled,
                                 default=i.action == "open")
                for i in menu_items(sentence, checker.running)])

        icon = pystray.Icon("freemyid", image, "Free My ID", build())

        def refresh() -> None:
            import threading
            ev = threading.Event()
            while not ev.wait(REFRESH_SECONDS):
                try:
                    icon.title = "Free My ID"
                    icon.menu = build()
                    icon.update_menu()
                except Exception as e:  # noqa: BLE001
                    log.debug("tray refresh failed: %s", type(e).__name__)
        import threading
        icon.run_detached()
        threading.Thread(target=refresh, name="freemyid-tray-refresh", daemon=True).start()
        return icon
    except Exception as e:  # noqa: BLE001
        log.info("tray icon not started: %s", type(e).__name__)
        return None
