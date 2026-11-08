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


# --------------------------------------------------------------------------- monthly update

PROGRESS_MARKER = ".last-progress-summary"
PROGRESS_DAYS = 30


def progress_counts(store, since) -> dict[str, int]:
    """Counts only (no names, no site names). Practice-mode requests are never counted."""
    from .models import ListingState, RequestStatus
    sent = sum(1 for r in store.list_requests(status=RequestStatus.SENT)
               if not r.dry_run and (r.sent_at or r.created_at) >= since)
    done = sum(1 for s in store.list_statuses()
               if s.state in (ListingState.CONFIRMED, ListingState.REMOVED)
               and not s.broker_id.startswith("_"))
    return {"sent": sent, "confirmed": done, "need_you": len(store.list_todos())}


def progress_body(c: dict[str, int]) -> str:
    def n(k: int, one: str, many: str) -> str:
        return f"{k} {one if k == 1 else many}"
    return (f"In the last month: {n(c['sent'], 'request', 'requests')} sent, "
            f"{n(c['confirmed'], 'site', 'sites')} confirmed or no longer listing you, "
            f"{c['need_you']} {'needs' if c['need_you'] == 1 else 'need'} you. "
            "Open Free My ID to see the details.")


def maybe_monthly_progress(store, notifier=None, now=None, home: Path | None = None) -> bool:
    """Send one PII-free summary toast at most every 30 days. Returns True if sent.

    The first call only starts the clock (nothing to report yet). Nothing is sent when no real
    request went out and nothing was confirmed, so practice mode stays quiet.
    """
    from datetime import datetime, timedelta

    from . import paths
    from .models import utcnow
    now = now or utcnow()
    marker = (home or paths.home()) / PROGRESS_MARKER
    try:
        last = datetime.fromisoformat(marker.read_text().strip())
    except (OSError, ValueError):
        marker.write_text(now.isoformat())
        return False
    if now - last < timedelta(days=PROGRESS_DAYS):
        return False
    c = progress_counts(store, last)
    marker.write_text(now.isoformat())
    if not (c["sent"] or c["confirmed"]):
        return False
    (notifier or get_notifier()).notify("Free My ID: your monthly update", progress_body(c))
    return True
