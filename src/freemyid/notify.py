"""Desktop notifications. Bodies must be PII-free (counts and first names at most).

A missing OS notifier, or one that exits non-zero, does nothing visible and does not raise.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar, Protocol

log = logging.getLogger(__name__)

_NOTICE_TIMEOUT_S = 10


class _OsGate:
    """One bad exit disables OS notices until the process ends."""

    unavailable: ClassVar[bool] = False
    logged: ClassVar[bool] = False


def _which(name: str) -> str | None:
    return shutil.which(name)


_finder: Callable[[str], str | None] = _which
_runner: Callable[[Sequence[str]], object] | None = None


class LogNotifier:
    """Fallback: write to the log only."""

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        log.info("notification: %s - %s", title, body)


def _app_icon() -> Path | None:
    """The Free My ID icon, found next to the package (installed exe) or in the repo."""
    here = Path(__file__).resolve().parent
    for p in (here / "wizard" / "static" / "freemyid.png",
              here / "wizard" / "static" / "freemyid.ico",
              here.parents[1] / "packaging" / "windows" / "freemyid.ico"):
        if p.is_file():
            return p
    return None


def _tool_name(platform: str) -> str | None:
    system = platform.lower()
    if system.startswith("linux"):
        return "notify-send"
    if system == "darwin":
        return "osascript"
    if system == "win32":
        return "powershell"
    return None


def _rejected(text: str) -> bool:
    """Lock-screen text stays free of links and email addresses."""
    if "\x00" in text:
        return True
    lowered = text.casefold()
    return "://" in lowered or "www." in lowered or "@" in text


def _mark_down(reason: str) -> bool:
    _OsGate.unavailable = True
    if not _OsGate.logged:
        _OsGate.logged = True
        log.info("desktop notification unavailable (%s)", reason)
    return False


def _exit_code(result: object) -> int | None:
    if isinstance(result, int) and not isinstance(result, bool):
        return result
    code = getattr(result, "returncode", None)
    if isinstance(code, int) and not isinstance(code, bool):
        return code
    return None


def _subprocess_runner(argv: Sequence[str]) -> int:
    """Run the OS tool. Output is captured so a failure cannot print a traceback."""
    args = list(argv)
    try:
        if sys.platform == "win32":
            flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
            done = subprocess.run(
                args, check=False, capture_output=True, stdin=subprocess.DEVNULL,
                timeout=_NOTICE_TIMEOUT_S, creationflags=flags)
        else:
            done = subprocess.run(
                args, check=False, capture_output=True, stdin=subprocess.DEVNULL,
                timeout=_NOTICE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 127
    return int(done.returncode)


def _active_runner(
    runner: Callable[[Sequence[str]], object] | None,
) -> Callable[[Sequence[str]], object]:
    if runner is not None:
        return runner
    if _runner is not None:
        return _runner
    return _subprocess_runner


_OSASCRIPT = (
    "on run argv\n"
    "display notification (item 2 of argv) with title (item 1 of argv)\n"
    "end run"
)


def _xml_escape(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _powershell_script(title: str, body: str) -> str:
    """WinRT toast. A failed load exits non-zero; disabled toasts show nothing."""
    safe_title = _ps_quote(_xml_escape(title))
    safe_body = _ps_quote(_xml_escape(body))
    load_toast = (
        "  $null = [Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime]"
    )
    load_xml = (
        "  $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
        "ContentType = WindowsRuntime]"
    )
    new_doc = (
        "$doc = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
        "ContentType = WindowsRuntime]::new()"
    )
    new_toast = (
        "$toast = [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, "
        "ContentType = WindowsRuntime]::new($doc)"
    )
    show = ("[Windows.UI.Notifications.ToastNotificationManager]::"
            "CreateToastNotifier($app).Show($toast)")
    app_id = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$title = {safe_title}",
        f"$body = {safe_body}",
        "try {",
        load_toast,
        load_xml,
        "} catch { exit 1 }",
        "$xml = '<toast><visual><binding template=\"ToastText02\">' +",
        "'<text id=\"1\">' + $title + '</text><text id=\"2\">' + $body + '</text>' +",
        "'</binding></visual></toast>'",
        new_doc,
        "$doc.LoadXml($xml)",
        f"$app = '{app_id}'",
        new_toast,
        show,
        "exit 0",
    ]
    return "\n".join(lines)


def _argv(platform: str, tool_path: str, title: str, body: str, icon: Path | None) -> list[str]:
    kind = _tool_name(platform)
    if kind == "notify-send":
        cmd = [tool_path, "-a", "Free My ID"]
        if icon is not None:
            cmd.extend(["-i", str(icon)])
        cmd.extend(["--", title, body])
        return cmd
    if kind == "osascript":
        return [tool_path, "-e", _OSASCRIPT, title, body]
    return [tool_path, "-NoProfile", "-NonInteractive", "-Command",
            _powershell_script(title, body)]


def _send_os_notice(
    title: str,
    body: str,
    *,
    platform: str | None,
    finder: Callable[[str], str | None] | None,
    runner: Callable[[Sequence[str]], object] | None,
    icon: Path | None,
) -> bool:
    if _OsGate.unavailable:
        return False
    if _rejected(title) or _rejected(body):
        return False
    system = sys.platform if platform is None else platform
    tool = _tool_name(system)
    if tool is None:
        return False
    find = _finder if finder is None else finder
    try:
        path = find(tool)
    except OSError as exc:
        return _mark_down(type(exc).__name__)
    if not path:
        return False
    argv = _argv(system, path, title, body, icon)
    try:
        result = _active_runner(runner)(argv)
    except OSError as exc:
        return _mark_down(type(exc).__name__)
    code = _exit_code(result)
    if code is None or code != 0:
        reason = "bad exit" if code is None else f"exit {code}"
        return _mark_down(reason)
    return True


def _deliver_os_notice(
    title: str,
    body: str,
    *,
    platform: str | None = None,
    finder: Callable[[str], str | None] | None = None,
    runner: Callable[[Sequence[str]], object] | None = None,
    icon: Path | None = None,
) -> bool:
    """Show one notice. False means nothing was shown. Never raises.

    The library used to log a traceback when no notifier was there. A missing executable is a
    no-op. One non-zero exit disables the tool for the rest of this process.
    """
    try:
        return _send_os_notice(title, body, platform=platform, finder=finder, runner=runner,
                               icon=icon)
    except Exception as exc:
        # A toast must not surface a traceback. Keep AssertionError so a test can block subprocess.
        if isinstance(exc, AssertionError):
            raise
        return _mark_down(type(exc).__name__)


class DesktopNotifier:
    def __init__(self) -> None:
        self._fallback = LogNotifier()
        self._icon = _app_icon()

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self._fallback.notify(title, body, url)
        # url is a link. It stays off the lock screen.
        _deliver_os_notice(title, body, icon=self._icon)


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
