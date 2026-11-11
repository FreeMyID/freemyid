"""Home-browser search session (WO-612): search people-search sites from the person's own PC.

The app runs on the person's computer with their home connection, so it searches there the
way the person would: ONE window of their installed browser (Edge on Windows, through
`BrowserManager`), on a dedicated Free My ID profile folder (`paths.home()/browser_profile`,
never their everyday profile), one site at a time at human pacing, honest user agent, every
request through NetPolicy. Pages are read with the registry `search:` spec
(`exposure.parse_candidates` via `exposure.scan_exposure(site_fetch=...)`), and matches go
to the matcher / review flow as in any exposure scan.

Two modes:

* "background" (default, scheduled runs): the window is HEADED but placed off-screen, never
  brought to the front. A site's own "checking your browser" interstitial gets a short grace
  period to clear by itself (the site's check running in a real browser, untouched). A site
  that still shows a challenge is retried on a later run; after that one retry it is QUEUED
  for the person (a CAPTCHA to-do). ONE notification once 3 sites are queued or the oldest
  has waited 14 days. Nothing ever pops up.
* "attended" (the person pressed "Look for me now" / `freemyid scan --attended`): the window
  is visible. On a challenge it stays on that site and the hooks show the banner
  (`BANNER_TEXT`); the PERSON ticks the box. Free My ID only watches the page (reads its
  HTML and frame URLs) until the challenge is gone, then carries on by itself. Timeout or
  "Skip this site" -> a hand-check to-do.

Hard limits (shared rule 5): Free My ID never clicks, types into, scripts or otherwise
touches a challenge or its frames, never uses a solver, stealth plugin, fingerprint or UA
trick, proxy or IP rotation. Cookies the person earned by passing a check stay in the app's
own profile (that is a person passing the check, not a bypass).

Events (`action="search_session"`): broker id, the `Outcome` value, the mode and timings only.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol
from urllib.parse import urlsplit

from ..models import Actor, Event, Todo, TodoKind, utcnow
from .exposure import Fetched, FetchFailed, has_parser, scan_brokers

if TYPE_CHECKING:
    from ..config import Config
    from ..exposure_models import ExposureResult
    from ..interfaces import Notifier
    from ..models import Broker, Registry
    from ..storage import Store
    from .browser import BrowserManager

log = logging.getLogger(__name__)

Mode = Literal["background", "attended"]

EVENT_ACTION = "search_session"
NOTICE_ACTION = "search_session_notice"
QUEUE_TOKEN = "search_session:"      # + broker id: queued for the person's next batch
HAND_TOKEN = "hand_check:"           # + broker id: open the page yourself
BANNER_TEXT = "This site wants a person to tick a box. Tick it, then Free My ID carries on."
NOTICE_MIN_SITES = 3
NOTICE_MAX_WAIT = timedelta(days=14)
CHALLENGE_TIMEOUT_S = 600            # attended: how long the window waits for the person
BACKGROUND_GRACE_S = 20              # background: a site's own interstitial may clear itself
POLL_S = 1.0


class Outcome(StrEnum):
    READ = "read"                              # page read, no challenge
    SELF_CLEARED = "self_cleared"              # interstitial went away by itself, then read
    READ_AFTER_CHALLENGE = "read_after_challenge"  # the person cleared it, then read
    CACHED = "cached"                          # answered by today's earlier check, no visit
    CHALLENGE_RETRY = "challenge_retry"        # background: challenged, try again next run
    QUEUED = "queued"                          # background: challenged twice, needs a person
    TIMED_OUT = "timed_out"                    # attended: nobody cleared it in time
    SKIPPED = "skipped"                        # attended: "Skip this site"
    HAND_CHECK = "hand_check"                  # blocked / unreadable: check it yourself
    BLOCKED_BY_POLICY = "blocked_by_policy"    # tried to leave the allowlist
    ERROR = "error"                            # network trouble; next run tries again
    NO_BROWSER = "no_browser"                  # the window could not be opened
    NOT_TRIED = "not_tried"                    # missing details etc.: nothing to visit


_READ_OK = {Outcome.READ, Outcome.SELF_CLEARED, Outcome.READ_AFTER_CHALLENGE, Outcome.CACHED}
_HAND = {Outcome.TIMED_OUT, Outcome.SKIPPED, Outcome.HAND_CHECK, Outcome.BLOCKED_BY_POLICY}
_CHALLENGED = "challenged"           # internal: background challenge before settling


class SessionUnavailable(Exception):
    """The window cannot be opened here (`reason`: "no_display" or "busy"). PII-free."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- the window


@dataclass
class View:
    """What the window shows: final URL, HTTP status (None when only looked at), HTML and
    the challenge label from `browser.detect_challenge` (markup / frames / text only)."""
    url: str
    status: int | None
    html: str
    challenge: str | None


class SiteWindow(Protocol):
    async def load(self, broker: Broker, url: str) -> View: ...
    async def look(self) -> View: ...
    async def show(self) -> None: ...
    async def close(self) -> None: ...


class WindowUnavailable(Exception):
    pass


class PlaywrightWindow:
    """The real window: `BrowserManager.persistent_context`. Reads pages, never acts on them."""

    def __init__(self, bm: BrowserManager, profile_dir: Path, mode: Mode,
                 test_headless: bool = False) -> None:
        self.bm, self.profile_dir, self.mode = bm, profile_dir, mode
        self.test_headless = test_headless
        self._ctx: Any = None
        self._page: Any = None
        self._failed = False

    async def _ensure(self) -> Any:
        if self._page is not None:
            return self._page
        if self._failed:
            raise WindowUnavailable
        try:
            self.profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            window = "background" if self.mode == "background" else "visible"
            self._ctx = await self.bm.persistent_context(
                str(self.profile_dir), window=window, test_headless=self.test_headless)
            self._page = self._ctx.pages[0] if self._ctx.pages else await self._ctx.new_page()
        except Exception as e:
            self._failed = True
            log.warning("search window unavailable (%s)", type(e).__name__)
            raise WindowUnavailable from e
        return self._page

    async def _view(self, status: int | None) -> View:
        from .browser import detect_challenge
        page = self._page
        html = await page.content()
        frames = [f.url for f in page.frames]
        return View(page.url, status, html, detect_challenge(html, frames))

    async def load(self, broker: Broker, url: str) -> View:
        page = await self._ensure()
        self.bm.retarget(self._ctx, list(broker.domains))
        resp = await self.bm.goto(page, url, check_challenge=False)
        return await self._view(resp.status if resp is not None else None)

    async def look(self) -> View:
        page = await self._ensure()
        self.bm.check_escaped(page)
        try:
            return await self._view(None)
        except Exception:  # noqa: BLE001 - mid-navigation: not cleared yet
            return View(page.url, None, "", "loading")

    async def show(self) -> None:
        if self.mode != "attended":       # background windows never take focus
            return
        page = await self._ensure()
        await page.bring_to_front()

    async def close(self) -> None:
        await self.bm.close()


# --------------------------------------------------------------------------- hooks (UI)


class SessionHooks:
    """UI hooks (the wizard's window/banner subclasses this; Nina). Defaults print to the
    console for `freemyid scan --attended`. Everything passed in is PII-free."""

    def on_site(self, broker_id: str, broker_name: str, index: int, total: int) -> None:
        log.info("search session: site %d of %d", index, total)

    def on_challenge(self, broker_id: str, broker_name: str) -> None:
        print(f"\n[Free My ID] {broker_name}: {BANNER_TEXT}", flush=True)

    def on_cleared(self, broker_id: str) -> None:
        print("[Free My ID] Thank you, carrying on.", flush=True)

    def skip_requested(self, broker_id: str) -> bool:
        return False


# --------------------------------------------------------------------------- the fetcher


@dataclass
class SiteRun:
    outcome: str
    elapsed_ms: int = 0
    waited_ms: int = 0


def _same_page(a: str, b: str) -> bool:
    def norm(u: str) -> tuple[str, str, str]:
        s = urlsplit(u)
        return ((s.hostname or "").lower(), s.path.rstrip("/") or "/", s.query)
    return norm(a) == norm(b)


class SessionFetcher:
    """An `exposure.Fetcher` backed by the window. Records one `SiteRun` per broker (its
    main page). Raises `exposure.FetchFailed` for anything that is not a readable page."""

    def __init__(self, window: SiteWindow, mode: Mode, hooks: SessionHooks | None = None, *,
                 timeout_s: float = CHALLENGE_TIMEOUT_S, grace_s: float = BACKGROUND_GRACE_S,
                 poll_s: float = POLL_S, clock: Callable[[], float] = time.monotonic) -> None:
        self.window, self.mode = window, mode
        self.hooks = hooks or SessionHooks()
        self.timeout_s, self.grace_s, self.poll_s, self.clock = timeout_s, grace_s, poll_s, clock
        self.runs: dict[str, SiteRun] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def __call__(self, broker: Broker, url: str) -> Fetched:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(self._fetch(broker, url))

    def close(self) -> None:
        if self._loop is None:
            return
        try:
            self._loop.run_until_complete(self.window.close())
        except Exception as e:  # noqa: BLE001 - closing never fails a run
            log.debug("search window close failed (%s)", type(e).__name__)
        self._loop.close()
        self._loop = None

    def _rec(self, broker: Broker, outcome: str, t0: float, waited: float = 0.0) -> None:
        if broker.id not in self.runs:       # the main page decides; extra pages don't
            self.runs[broker.id] = SiteRun(outcome, int((self.clock() - t0) * 1000),
                                           int(waited * 1000))

    async def _fetch(self, broker: Broker, url: str) -> Fetched:
        from .browser import BlockedByPolicy
        t0 = self.clock()
        try:
            view = await self.window.load(broker, url)
            outcome, waited = Outcome.READ, 0.0
            if view.challenge:
                view, outcome, waited = await self._wait(broker, url, t0)
        except FetchFailed:
            raise
        except BlockedByPolicy as e:
            self._rec(broker, Outcome.BLOCKED_BY_POLICY, t0)
            raise FetchFailed("blocked_by_policy") from e
        except WindowUnavailable as e:
            self._rec(broker, Outcome.NO_BROWSER, t0)
            raise FetchFailed("needs_browser") from e
        except Exception as e:
            self._rec(broker, Outcome.ERROR, t0)
            raise FetchFailed("network") from e
        if view.status is not None and view.status >= 400:
            self._rec(broker, Outcome.HAND_CHECK, t0)
            raise FetchFailed("http_error")
        self._rec(broker, outcome, t0, waited)
        page_url = view.url if view.url.startswith("https://") else url
        return Fetched(page_url, view.status or 200, view.html)

    async def _wait(self, broker: Broker, url: str, t0: float) -> tuple[View, Outcome, float]:
        """Watch (read-only) until the challenge is gone. Attended: show the window and the
        banner and wait for the person. Background: a short grace period, never shown."""
        attended = self.mode == "attended"
        limit = self.timeout_s if attended else self.grace_s
        if attended:
            await self.window.show()
            self.hooks.on_challenge(broker.id, broker.name)
        start = self.clock()
        while self.clock() - start < limit:
            if attended and self.hooks.skip_requested(broker.id):
                self._rec(broker, Outcome.SKIPPED, t0, self.clock() - start)
                raise FetchFailed("challenge")
            await asyncio.sleep(self.poll_s)
            cur = await self.window.look()
            if cur.challenge:
                continue
            waited = self.clock() - start
            if not _same_page(cur.url, url):     # cleared onto another page: load ours
                cur = await self.window.load(broker, url)
                if cur.challenge:
                    continue
            else:
                cur.status = cur.status or 200
            if attended:
                self.hooks.on_cleared(broker.id)
            return cur, (Outcome.READ_AFTER_CHALLENGE if attended else
                         Outcome.SELF_CLEARED), waited
        self._rec(broker, Outcome.TIMED_OUT if attended else _CHALLENGED, t0,
                  self.clock() - start)
        raise FetchFailed("challenge")


# --------------------------------------------------------------------------- queue + to-dos


def _open_by_token(store: Store, profile_id: str, token: str) -> list[Todo]:
    return [t for t in store.list_todos(profile_id) if t.resume_token == token]


def queued_todos(store: Store, profile_id: str) -> list[Todo]:
    """Open "needs one click from you" to-dos (the next attended batch). Wizard hook."""
    return [t for t in store.list_todos(profile_id)
            if (t.resume_token or "").startswith(QUEUE_TOKEN)]


def pending_sites(store: Store, profile_id: str) -> int:
    """How many sites wait for the person (the wizard's "Look for me now" badge)."""
    return len(queued_todos(store, profile_id))


def _close(store: Store, profile_id: str, token: str) -> None:
    for t in _open_by_token(store, profile_id, token):
        store.complete_todo(t.id)


def _save_once(store: Store, todo: Todo) -> None:
    if not _open_by_token(store, todo.profile_id, str(todo.resume_token)):
        store.save_todo(todo)


def _queue(store: Store, profile_id: str, broker: Broker) -> None:
    _save_once(store, Todo(
        profile_id=profile_id, broker_id=broker.id, kind=TodoKind.CAPTCHA,
        title=f"{broker.name} wants a person to tick a box",
        body=("Press \"Look for me now\" in Free My ID. It opens the site; you tick the box "
              "and Free My ID carries on by itself."),
        resume_token=QUEUE_TOKEN + broker.id))


def _hand_check(store: Store, profile_id: str, broker: Broker, reason: str | None,
                check_url: str | None) -> None:
    from ..exposure_models import HAND_REASONS
    why = HAND_REASONS.get(reason or "", "")
    _save_once(store, Todo(
        profile_id=profile_id, broker_id=broker.id, kind=TodoKind.OTHER,
        title=f"Check {broker.name} yourself",
        body=f"{why} Open the link and look for your name.".strip(),
        links=[check_url] if check_url else [], resume_token=HAND_TOKEN + broker.id))


def _previous_outcome(store: Store, profile_id: str, broker_id: str) -> str | None:
    """The last decisive session outcome for this site (errors and cache hits skipped)."""
    skip = {Outcome.ERROR, Outcome.NO_BROWSER, Outcome.CACHED, Outcome.NOT_TRIED}
    for ev in store.events(profile_id, broker_id, limit=50):
        if ev.action == EVENT_ACTION and ev.detail.get("outcome") not in skip:
            return str(ev.detail.get("outcome"))
    return None


#: Access values the home-browser window takes over from the runner's headless browser
#: (headless is what these sites flag, WO-612 acceptance 2). See `session_only`.
SESSION_ONLY_ACCESS = ("bot_blocked", "unknown")
FRESH_FOR = timedelta(hours=24)
_READ_NOW = {Outcome.READ, Outcome.SELF_CLEARED, Outcome.READ_AFTER_CHALLENGE}


def fresh_read(store: Store, profile_id: str, broker_id: str,
               now: datetime | None = None) -> bool:
    """True when this site's latest decisive session visit read the page, within the last
    day. The runner then trusts the listings that visit stored (exposure.merge_listings)."""
    now = now or utcnow()
    skip = {Outcome.ERROR, Outcome.NO_BROWSER, Outcome.CACHED, Outcome.NOT_TRIED}
    for ev in store.events(profile_id, broker_id, limit=50):
        if ev.action != EVENT_ACTION or ev.detail.get("outcome") in skip:
            continue
        return ev.detail.get("outcome") in _READ_NOW and now - ev.ts < FRESH_FOR
    return False


def session_only(store: Store, profile_id: str, broker: Broker) -> bool:
    """True when the runner must not search this site with its headless browser.

    `bot_blocked`: always. `unknown`: once the home-browser session has visited the site for
    this person. (`unknown` is also the model default for a site nobody has researched, so
    a person who never runs a session keeps today's behaviour.)"""
    if broker.search_access == "bot_blocked":
        return True
    if broker.search_access not in SESSION_ONLY_ACCESS:
        return False
    return any(ev.action == EVENT_ACTION
               for ev in store.events(profile_id, broker.id, limit=200))


def notice_text(n: int) -> str:
    """Lock-screen safe (SEC-28): a count, never a site or a name."""
    return (f"{n} sites need one click from you, about a minute." if n != 1 else
            "1 site needs one click from you, about a minute.")


def maybe_notify(store: Store, profile_id: str, notifier: Notifier,
                 now: datetime | None = None) -> bool:
    """ONE notification when >= 3 sites are queued or the oldest waited 14 days. Repeats
    only when the queue grew since the last one or 14 days passed since it."""
    now = now or utcnow()
    q = queued_todos(store, profile_id)
    if not q:
        return False
    oldest = min(t.created_at for t in q)
    if len(q) < NOTICE_MIN_SITES and now - oldest < NOTICE_MAX_WAIT:
        return False
    last = next((ev for ev in store.events(profile_id, limit=500)
                 if ev.action == NOTICE_ACTION), None)
    if last is not None and len(q) <= int(last.detail.get("queued", 0)) and \
            now - last.ts < NOTICE_MAX_WAIT:
        return False
    try:
        notifier.notify("Free My ID needs you", notice_text(len(q)))
        flush = getattr(notifier, "flush", None)
        if callable(flush):
            flush()
    except Exception as e:  # noqa: BLE001 - a toast never fails a run
        log.debug("search session notice failed (%s)", type(e).__name__)
    store.log(Event(ts=now, profile_id=profile_id, actor=Actor.ENGINE, action=NOTICE_ACTION,
                    detail={"queued": len(q)}))
    return True


# --------------------------------------------------------------------------- the session


@dataclass
class SessionReport:
    mode: Mode
    outcomes: dict[str, str] = field(default_factory=dict)   # broker id -> Outcome value
    queued: int = 0
    notified: bool = False
    result: ExposureResult | None = None

    def count(self, *outcomes: str) -> int:
        return sum(1 for o in self.outcomes.values() if o in outcomes)


def has_display(platform: str | None = None) -> bool:
    platform = platform or sys.platform
    if platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def profile_dir() -> Path:
    """The app's own browser profile folder (never the person's everyday profile)."""
    from .. import paths
    return paths.home() / "browser_profile"


class SessionLock:
    """One session at a time (WO-612, SEC-WO612-4).

    An OS lock on `browser_profile.lock` (flock on POSIX, an msvcrt byte lock on Windows)
    held for the whole session: the kernel drops it when the holder exits, so a crashed
    session never blocks the next one and a live one is never taken over, however long it
    runs. The file holds the holder's PID (diagnostics), refreshed per site. Lock files
    from older versions (no OS lock held) are simply taken. Two processes racing: the
    second's non-blocking lock fails ("busy"); one that locked a file the first had just
    unlinked notices the changed inode and reports "busy" too."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    @staticmethod
    def _try_lock(fd: int) -> None:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(fd: int) -> None:
        if sys.platform == "win32":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            self._try_lock(fd)
        except OSError:
            os.close(fd)
            raise SessionUnavailable("busy") from None
        try:
            same = os.path.samestat(os.fstat(fd), os.stat(self.path))
        except OSError:
            same = False
        if not same:              # the previous holder unlinked it under us: it was busy
            self._unlock(fd)
            os.close(fd)
            raise SessionUnavailable("busy")
        self._fd = fd
        self.refresh()

    def refresh(self) -> None:
        """Rewrite the holder's PID and touch the file (once per site)."""
        if self._fd is None:
            return
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
            os.ftruncate(self._fd, 0)
            os.write(self._fd, f"{os.getpid()}\n".encode())
            os.utime(self.path)
        except OSError as e:
            log.debug("session lock refresh failed (%s)", type(e).__name__)

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        if sys.platform != "win32":
            # unlink while still holding it: a process that opened the old file then fails
            # the inode check above instead of sharing the lock with a newcomer
            with contextlib.suppress(OSError):
                self.path.unlink()
        try:
            self._unlock(fd)
        finally:
            os.close(fd)
        if sys.platform == "win32":
            with contextlib.suppress(OSError):   # another process may have it open
                self.path.unlink()


@contextlib.contextmanager
def _session_lock(folder: Path) -> Iterator[SessionLock]:
    """Hold `SessionLock` on `<folder>.lock` (next to the browser profile folder)."""
    lock = SessionLock(folder.parent / f"{folder.name}.lock")
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


def session_brokers(registry: Registry, profile: Any,
                    broker_ids: list[str] | None = None) -> list[Broker]:
    """Brokers the window visits: enabled, a search URL and a parser, priority order."""
    return [b for b in scan_brokers(registry, profile) if has_parser(b)
            and (not broker_ids or b.id in broker_ids)]


def run_session(store: Store, profile_id: str, *, mode: Mode = "background",
                registry: Registry | None = None, cfg: Config | None = None,
                hooks: SessionHooks | None = None, window: SiteWindow | None = None,
                notifier: Notifier | None = None, broker_ids: list[str] | None = None,
                refresh: bool = False, now: datetime | None = None,
                timeout_s: float = CHALLENGE_TIMEOUT_S, grace_s: float = BACKGROUND_GRACE_S,
                poll_s: float = POLL_S, test_headless: bool = False) -> SessionReport:
    """Search every enabled broker that has a `search:` spec in the home-browser window.

    Raises `exposure.ExposureRefused` without consent and `SessionUnavailable` when no
    window can be shown here. `window` / `notifier` are injectable for tests."""
    from .. import config as cfgmod
    from ..consent import consent_ok
    from . import exposure as ex
    from .handoff import get_notifier
    cfg = cfg or cfgmod.load()
    now = now or utcnow()
    profile = store.get_profile(profile_id)
    if profile is None:
        raise ex.ExposureRefused("no such person")
    ok, why = consent_ok(profile, store)
    if not ok:
        raise ex.ExposureRefused(why)
    if registry is None:
        from ..registry import load_registry
        registry = load_registry()
    brokers = session_brokers(registry, profile, broker_ids)
    report = SessionReport(mode=mode)
    lock: contextlib.AbstractContextManager[None] = contextlib.nullcontext()
    if window is None:
        from ..netpolicy import NetPolicy
        from .browser import BrowserManager
        from .outbox import dev_fixture_base
        fixture = dev_fixture_base()
        if not test_headless and not has_display():
            raise SessionUnavailable("no_display")
        bm = BrowserManager(NetPolicy(registry), headless=False,
                            cfg=cfg.model_copy(update={"max_retries": 1}), fixture_base=fixture)
        folder = profile_dir()
        window = PlaywrightWindow(bm, folder, mode, test_headless=test_headless)
        lock = _session_lock(folder)
    with lock:
        fetcher = SessionFetcher(window, mode, hooks, timeout_s=timeout_s, grace_s=grace_s,
                                 poll_s=poll_s)
        try:
            report.result = ex.scan_exposure(
                store, profile.id, registry=registry, cfg=cfg, fetch=fetcher,
                browser_fetch=fetcher, use_browser=False, site_fetch=fetcher,
                broker_ids=broker_ids, refresh=refresh, now=now, sleep=lambda _s: None)
        finally:
            fetcher.close()
    entries = {e.broker_id: e for e in report.result.entries}
    for b in brokers:
        run = fetcher.runs.get(b.id)
        entry = entries.get(b.id)
        if run is None:
            outcome = Outcome.CACHED if entry is not None and entry.status != \
                "check_by_hand" else Outcome.NOT_TRIED
            run = SiteRun(outcome)
        outcome = _settle(store, profile.id, b, run.outcome, mode,
                          entry.reason if entry else None, entry.check_url if entry else None)
        report.outcomes[b.id] = outcome
        store.log(Event(ts=now, profile_id=profile.id, broker_id=b.id, actor=Actor.ENGINE,
                        action=EVENT_ACTION, detail={
                            "outcome": outcome, "mode": mode, "elapsed_ms": run.elapsed_ms,
                            "waited_ms": run.waited_ms}))
    report.queued = pending_sites(store, profile.id)
    if mode == "background":
        report.notified = maybe_notify(store, profile.id, notifier or get_notifier(), now)
    return report


def _settle(store: Store, profile_id: str, broker: Broker, outcome: str, mode: Mode,
            reason: str | None, check_url: str | None) -> str:
    """Turn one site's run into to-dos. Returns the final Outcome value."""
    if outcome == _CHALLENGED:      # background only
        prev = _previous_outcome(store, profile_id, broker.id)
        if prev in (Outcome.CHALLENGE_RETRY, Outcome.QUEUED):
            _queue(store, profile_id, broker)
            return Outcome.QUEUED
        return Outcome.CHALLENGE_RETRY
    if outcome in _READ_OK:
        _close(store, profile_id, QUEUE_TOKEN + broker.id)
        _close(store, profile_id, HAND_TOKEN + broker.id)
    elif outcome in _HAND:
        _close(store, profile_id, QUEUE_TOKEN + broker.id)
        _hand_check(store, profile_id, broker, reason, check_url)
    return outcome


def run_for_profiles(store: Store, profile_ids: list[str], *, mode: Mode = "background",
                     registry: Registry | None = None, cfg: Config | None = None,
                     hooks: SessionHooks | None = None, notifier: Notifier | None = None,
                     window_factory: Callable[[], SiteWindow] | None = None
                     ) -> dict[str, SessionReport | str]:
    """The CLI / scheduler entry point: one session per person, never raising. Value per
    profile id: its `SessionReport`, or a short PII-free reason ("no_consent",
    "no_display", "busy", "error") when no session ran. Run it BEFORE `runner.run` so the
    runner finds today's reads (`fresh_read`)."""
    from .exposure import ExposureRefused
    out: dict[str, SessionReport | str] = {}
    for pid in profile_ids:
        try:
            out[pid] = run_session(store, pid, mode=mode, registry=registry, cfg=cfg,
                                   hooks=hooks, notifier=notifier,
                                   window=window_factory() if window_factory else None)
        except ExposureRefused:
            out[pid] = "no_consent"
        except SessionUnavailable as e:
            out[pid] = e.reason
        except Exception as e:  # noqa: BLE001 - one person's session never stops the run
            log.warning("search session failed (%s)", type(e).__name__)
            out[pid] = "error"
    return out
