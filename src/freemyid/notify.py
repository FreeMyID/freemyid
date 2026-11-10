"""Desktop notifications. Bodies must be PII-free (counts and first names at most)."""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar, Protocol

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


def get_notifier() -> LogNotifier | DesktopNotifier:
    try:
        return DesktopNotifier()
    except Exception as e:  # noqa: BLE001
        log.info("desktop-notifier not usable (%s); logging instead", type(e).__name__)
        return LogNotifier()


class _SupportsNotify(Protocol):
    def notify(self, title: str, body: str, url: str | None = None) -> None: ...


def _wall_clock() -> datetime:
    return datetime.now(UTC)


def _things_need_you(count: int) -> str:
    if count == 1:
        return "1 thing needs you"
    return f"{count} things need you"


class ThrottledNotifier:
    """Deliver the first notice in a run; count the rest until flush().

    Later notices are counted while this run is still open, and any notice
    within 10 minutes of the first one that went out (every wrapper in this
    process shares that window). The summary is counts only: no site names.
    """

    window: ClassVar[timedelta] = timedelta(minutes=10)
    _shared_started_at: ClassVar[datetime | None] = None

    def __init__(self, inner: _SupportsNotify, *,
                 now: Callable[[], datetime] | None = None) -> None:
        self._inner = inner
        self._now = now or _wall_clock
        self._held = 0
        self._run_open = False

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        now = self._now()
        if self._counting(now):
            self._held += 1
            self._run_open = True
            return
        self._inner.notify(title, body, url)
        ThrottledNotifier._shared_started_at = now
        self._run_open = True

    def flush(self) -> None:
        """Send one closing summary when notices were held back. Safe to repeat."""
        held = self._held
        if held <= 0:
            self._run_open = False
            return
        phrase = _things_need_you(held)
        seen = "it" if held == 1 else "them"
        self._inner.notify(f"Free My ID: {phrase}",
                           f"{phrase}. Open Free My ID to see {seen}.", None)
        self._held = 0
        self._run_open = False

    def _counting(self, now: datetime) -> bool:
        if self._run_open:
            return True
        started = ThrottledNotifier._shared_started_at
        return started is not None and now - started < ThrottledNotifier.window


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


def _write_marker(marker: Path, text: str) -> None:
    """Replace the marker atomically: a temp file in the same folder, then replace."""
    parent = marker.parent
    if not parent.is_dir():
        raise OSError("home folder missing")
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=f".{marker.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    wrote = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, marker)
        wrote = True
    finally:
        if not wrote:
            tmp.unlink(missing_ok=True)


def _restart_clock(marker: Path, now: datetime) -> bool:
    try:
        _write_marker(marker, now.isoformat())
    except OSError as exc:
        log.info("monthly progress skipped; marker not written (%s)", type(exc).__name__)
    return False


def maybe_monthly_progress(store: Any, notifier: Any = None, now: datetime | None = None,
                           home: Path | None = None) -> bool:
    """Send one PII-free summary toast at most every 30 days. Returns True if sent.

    The first call only starts the clock (nothing to report yet). Nothing is sent when no real
    request went out and nothing was confirmed, so practice mode stays quiet.
    A missing or unwritable home folder is logged and returns False; it never raises.
    """
    from . import paths
    from .models import utcnow
    now = now or utcnow()
    try:
        root = home if home is not None else paths.home()
    except OSError as exc:
        log.info("monthly progress skipped; home unavailable (%s)", type(exc).__name__)
        return False
    marker = root / PROGRESS_MARKER
    try:
        raw = marker.read_text(encoding="utf-8")
    except OSError:
        return _restart_clock(marker, now)
    try:
        last = datetime.fromisoformat(raw.strip())
    except ValueError:
        return _restart_clock(marker, now)
    if now - last < timedelta(days=PROGRESS_DAYS):
        return False
    counts = progress_counts(store, last)
    try:
        _write_marker(marker, now.isoformat())
    except OSError as exc:
        log.info("monthly progress skipped; marker not written (%s)", type(exc).__name__)
        return False
    if not (counts["sent"] or counts["confirmed"]):
        return False
    (notifier or get_notifier()).notify("Free My ID: your monthly update", progress_body(counts))
    return True
