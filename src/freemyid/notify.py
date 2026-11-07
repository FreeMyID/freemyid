"""Desktop notifications. Bodies must be PII-free (counts and first names at most)."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class LogNotifier:
    """Fallback: write to the log only."""

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        log.info("notification: %s - %s", title, body)


def _app_icon() -> Path | None:
    """The Free My ID icon, found next to the package (installed exe) or in the repo."""
    here = Path(__file__).resolve().parent
    for p in (here / "wizard" / "static" / "freemyid.png", here / "wizard" / "static" / "freemyid.ico",
              here.parents[1] / "packaging" / "windows" / "freemyid.ico"):
        if p.is_file():
            return p
    return None


class DesktopNotifier:
    def __init__(self) -> None:
        from desktop_notifier import DesktopNotifier as _DN
        icon = _app_icon()
        if icon is not None:
            from desktop_notifier import Icon
            self._dn = _DN(app_name="Free My ID", app_icon=Icon(path=icon))
        else:
            self._dn = _DN(app_name="Free My ID")
        self._fallback = LogNotifier()

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self._fallback.notify(title, body, url)
        try:
            coro = self._dn.send(title=title, message=body)
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:   # called from async code: fire and forget on the running loop
                asyncio.ensure_future(coro)
        except Exception as e:  # noqa: BLE001  headless boxes have no notification daemon
            log.info("desktop notification unavailable: %s", type(e).__name__)


def get_notifier():
    try:
        return DesktopNotifier()
    except Exception as e:  # noqa: BLE001
        log.info("desktop-notifier not usable (%s); logging instead", type(e).__name__)
        return LogNotifier()
