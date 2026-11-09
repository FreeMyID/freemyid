"""Shared fixtures. Every test runs with a throwaway FREEMYID_HOME and FREEMYID_TEST_KEY, an
in-memory keyring and outbound network blocked. Fake people only (Jane Q Testperson)."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import signal
import socket
import sys
import threading
import weakref
from datetime import date
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend

from freemyid.consent import CURRENT_TEXT_VERSION

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]

# The full broker registry (brokers/registry.yaml) is private: public checkouts and builds
# only have brokers/registry.sample.yaml. FREEMYID_TEST_NO_FULL_REGISTRY=1 runs the suite as
# a public checkout would (the file on disk is never moved or renamed).
NO_FULL_REGISTRY_ENV = "FREEMYID_TEST_NO_FULL_REGISTRY"


def full_registry_path() -> Path | None:
    """brokers/registry.yaml if this checkout has it (and we are not simulating without)."""
    if os.environ.get(NO_FULL_REGISTRY_ENV, "").strip() not in ("", "0"):
        return None
    p = ROOT / "brokers" / "registry.yaml"
    return p if p.exists() else None

# ----------------------------------------------------------------------------- browser + hangs
# Real-browser tests skip when Playwright's Chromium cannot be launched, unless
# FREEMYID_REQUIRE_BROWSER=1 (CI), which turns that skip into a failure.
REQUIRE_BROWSER_ENV = "FREEMYID_REQUIRE_BROWSER"
BROWSER_LAUNCH_TIMEOUT_MS = 30_000
# Per-test watchdog (POSIX): a hung test fails instead of hanging the whole run.
TEST_TIMEOUT_ENV = "FREEMYID_TEST_TIMEOUT"
DEFAULT_TEST_TIMEOUT_S = 180


def browser_required() -> bool:
    return os.environ.get(REQUIRE_BROWSER_ENV, "").strip() not in ("", "0")


def no_browser(reason: str) -> None:
    """Skip (or, with FREEMYID_REQUIRE_BROWSER=1, fail) because no browser is usable."""
    msg = f"Playwright Chromium not available: {reason}"
    if browser_required():
        pytest.fail(f"{msg} ({REQUIRE_BROWSER_ENV}=1 makes this a failure)", pytrace=False)
    pytest.skip(msg)


_probe: dict[str, str | None] = {}


def chromium_probe() -> str | None:
    """None if Playwright's bundled Chromium launches headless, else why not.

    Runs once per session, in its own thread (so it never touches a test's event loop) and
    bounded: a launch that never returns counts as unavailable instead of hanging the run.
    """
    if "r" in _probe:
        return _probe["r"]
    box: dict[str, str | None] = {}

    def run() -> None:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True, timeout=BROWSER_LAUNCH_TIMEOUT_MS)
                b.close()
            box["r"] = None
        except Exception as e:  # noqa: BLE001 - any launch problem means "no browser"
            first = (str(e).strip().splitlines() or [""])[0][:200]
            box["r"] = f"{type(e).__name__}: {first}"

    t = threading.Thread(target=run, name="chromium-probe", daemon=True)
    t.start()
    t.join(BROWSER_LAUNCH_TIMEOUT_MS / 1000 + 30)
    _probe["r"] = box.get("r", "browser launch did not finish in time")
    return _probe["r"]


# ----------------------------------------------------------------------------- OS markers
# Registered in pyproject.toml (windows_only, posix_only, macos_only, linux_only, browser).
# Each OS marker skips the test everywhere else, so the CI matrix runs it only where it belongs.
OS_MARKERS: dict[str, tuple[bool, str]] = {
    "windows_only": (sys.platform == "win32", "Windows only"),
    "posix_only": (sys.platform != "win32", "Linux/macOS only"),
    "macos_only": (sys.platform == "darwin", "macOS only"),
    "linux_only": (sys.platform.startswith("linux"), "Linux only"),
}
# Tests that touch the real OS scheduler (schtasks / systemd --user / launchd). They run only
# on disposable CI runners (CI=true, set by GitHub Actions), never in a developer's session,
# and must also carry the matching OS marker.
REAL_SCHEDULER = "real_scheduler"


def on_ci() -> bool:
    return os.environ.get("CI", "").strip().lower() == "true"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", f"{REAL_SCHEDULER}: installs/removes a real scheduled job; runs only with "
                   "CI=true and needs an OS marker (CR: register in pyproject.toml)")


# Tests in tests/test_web_*.py read the built website (web/dist). The Python CI job does not
# build it, so they are auto-marked web_dist and skip when web/dist is missing; pages.yml runs
# them right after its build with FREEMYID_REQUIRE_WEB_DIST=1, which turns the skip into a failure.
WEB_DIST = ROOT / "web" / "dist"
REQUIRE_WEB_DIST_ENV = "FREEMYID_REQUIRE_WEB_DIST"


def web_dist_missing() -> bool:
    return not (WEB_DIST / "index.html").is_file()


_READS_DIST = re.compile(r"web/dist|[\"']dist[\"']")
_reads_dist_cache: dict[Path, bool] = {}


def reads_built_site(path: Path) -> bool:
    """tests/test_web_*.py always read web/dist; vendor suites (tests/codex, tests/copilot) do when
    their source names it. Both get the web_dist mark, so build.yml skips them and pages.yml
    runs them strictly right after its build."""
    if path.name.startswith("test_web_"):
        return True
    if path.parent.name not in ("codex", "copilot") or not path.name.startswith("test_"):
        return False
    if path not in _reads_dist_cache:
        _reads_dist_cache[path] = bool(_READS_DIST.search(path.read_text(encoding="utf-8")))
    return _reads_dist_cache[path]


def pytest_collection_modifyitems(config, items):
    for item in items:
        if reads_built_site(Path(str(item.fspath))):
            item.add_marker(pytest.mark.web_dist)
        os_marks = [m for m in OS_MARKERS if item.get_closest_marker(m) is not None]
        for m in os_marks:
            ok, why = OS_MARKERS[m]
            if not ok:
                item.add_marker(pytest.mark.skip(reason=f"{why} ({m})"))
        if item.get_closest_marker(REAL_SCHEDULER) is not None:
            if not os_marks:
                item.add_marker(pytest.mark.skip(
                    reason=f"{REAL_SCHEDULER} test without an OS marker never runs"))
            elif not on_ci():
                item.add_marker(pytest.mark.skip(
                    reason="touches the real OS scheduler: runs only on CI (CI=true)"))


def pytest_runtest_setup(item):
    if item.get_closest_marker("web_dist") is not None and web_dist_missing():
        msg = f"built website not found ({WEB_DIST}/index.html): run pnpm build in web/"
        if os.environ.get(REQUIRE_WEB_DIST_ENV, "").strip() not in ("", "0"):
            pytest.fail(f"{msg} ({REQUIRE_WEB_DIST_ENV}=1 makes this a failure)", pytrace=False)
        pytest.skip(msg)
    if item.get_closest_marker("browser") is not None:
        reason = chromium_probe()
        if reason is not None:
            no_browser(reason)


# Every Playwright connection opened by a test, so a hung test can be unblocked: a cancelled
# Playwright call can itself wait forever, and a dead driver does not fail pending calls by
# itself. So: kill the driver, then close the connection, which errors every pending and later
# call and lets the code under test unwind (private Playwright API; tests only).
_connections: weakref.WeakSet = weakref.WeakSet()


def _track_playwright_connections() -> None:
    try:
        from playwright._impl._connection import Connection
    except Exception:  # noqa: BLE001 - Playwright missing or reorganised: no tracking
        return
    if getattr(Connection.run, "_freemyid_tracked", False):
        return
    orig = Connection.run

    async def run(self):
        _connections.add(self)
        return await orig(self)

    run._freemyid_tracked = True  # type: ignore[attr-defined]
    setattr(Connection, "run", run)  # noqa: B010 - mypy: no method-assign


_track_playwright_connections()


def kill_playwright_drivers() -> int:
    n = 0
    for conn in list(_connections):
        proc = getattr(getattr(conn, "_transport", None), "_proc", None)
        if proc is None or proc.returncode is not None:
            continue
        with contextlib.suppress(Exception):   # no "Future exception was never retrieved"
            conn._transport.on_error_future.add_done_callback(
                lambda f: f.cancelled() or f.exception())
        with contextlib.suppress(Exception):
            proc.kill()
        with contextlib.suppress(Exception):
            conn.cleanup("Playwright driver killed by the test hang guard")
        n += 1
    return n


class FillHang(AssertionError):
    """A browser flow did not return within its bound (it would hang the app)."""


async def bounded(aw, seconds: float, what: str):
    """Await `aw`; after `seconds` kill the Playwright driver and fail with FillHang.

    Plain asyncio.wait_for is not enough: cancelling a Playwright call that is stuck can hang
    too (seen with page.evaluate inside a route handler while a navigation is paused).
    """
    task = asyncio.ensure_future(aw)
    done, _ = await asyncio.wait({task}, timeout=seconds)
    if task in done:
        return task.result()
    kill_playwright_drivers()
    with contextlib.suppress(BaseException):
        await asyncio.wait_for(task, 20)
    raise FillHang(f"{what} did not return within {seconds:g}s")


async def flow_bounded(fn, *args, **kw):
    """Run a browser flow (fill_for_me / find_listing) so it can never hang a test, and
    skip (or with FREEMYID_REQUIRE_BROWSER=1 fail) cleanly when no browser can start.

    Bound: the flow's own timeout_s plus 10s.
    """
    secs = float(kw.get("timeout_s", 600)) + 10
    res = await bounded(fn(*args, **kw), secs, getattr(fn, "__name__", "browser flow"))
    if getattr(res, "reason", "") == "browser_unavailable":
        no_browser(f"{getattr(fn, '__name__', 'flow')} could not start a browser")
    return res


async def fill_bounded(*args, **kw):
    from freemyid.engine.fill_for_me import fill_for_me
    return await flow_bounded(fill_for_me, *args, **kw)


async def find_bounded(*args, **kw):
    from freemyid.engine.listing_finder import find_listing
    return await flow_bounded(find_listing, *args, **kw)


# SEC-39 (open, src): fill_for_me never returns once the person submits a form that navigates
# the main frame. engine/fill_for_me.py `_watch` (the page.route handler) awaits
# `_snapshot()` -> page.evaluate() while that navigation request is paused in the route;
# Playwright never resolves that evaluate, so the request never continues, the person's
# click never returns and the poll loop's own evaluate blocks too: timeout_s is never
# checked. Strict: when the fix lands these XPASS and fail the run, so remove the marker.
SEC39_HANG = pytest.mark.xfail(
    raises=FillHang, strict=True,
    reason="SEC-39: fill_for_me hangs after a navigating form submit (src fix pending)")


def _test_timeout_s() -> float:
    try:
        return float(os.environ.get(TEST_TIMEOUT_ENV, DEFAULT_TEST_TIMEOUT_S))
    except ValueError:
        return DEFAULT_TEST_TIMEOUT_S


@pytest.fixture(autouse=True)
def _hang_watchdog(request):
    secs = _test_timeout_s()
    usable = (secs > 0 and sys.platform != "win32" and hasattr(signal, "setitimer")
              and threading.current_thread() is threading.main_thread())
    if not usable:
        yield
        return

    def fire(signum, frame):
        signal.setitimer(signal.ITIMER_REAL, 0)
        kill_playwright_drivers()   # else the event loop's own cleanup can hang too
        pytest.fail(f"{request.node.nodeid} ran longer than {secs:g}s (hung?); "
                    f"raise {TEST_TIMEOUT_ENV} if it is just slow", pytrace=True)

    old = signal.signal(signal.SIGALRM, fire)
    signal.setitimer(signal.ITIMER_REAL, secs)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


class MemoryKeyring(KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.store.get((service, username))

    def set_password(self, service, username, password):
        self.store[(service, username)] = password

    def delete_password(self, service, username):
        from keyring.errors import PasswordDeleteError
        if (service, username) not in self.store:
            raise PasswordDeleteError("missing")
        del self.store[(service, username)]


_real_connect = socket.socket.connect


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
        raise RuntimeError(f"network blocked in tests: {host}")
    return _real_connect(self, address)


@pytest.fixture(autouse=True)
def _no_real_scheduler(request, monkeypatch):
    """Nothing reaches schtasks/systemctl/launchctl/crontab unless the test is marked
    real_scheduler (and so is on CI). Tests that fake `scheduler._run` replace this."""
    if request.node.get_closest_marker(REAL_SCHEDULER) is not None:
        return
    from freemyid import scheduler

    def refuse(args, input=None):
        raise RuntimeError(f"real scheduler blocked in tests: {args[:1]}")
    monkeypatch.setattr(scheduler, "_run", refuse)


@pytest.fixture(autouse=True)
def freemyid_env(tmp_path, monkeypatch):
    home = tmp_path / "vhome"
    monkeypatch.setenv("FREEMYID_HOME", str(home))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "unit-test-key-not-secret")
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    from freemyid import registry
    monkeypatch.setattr(registry, "_loaded", None)        # no fallback state across tests
    monkeypatch.setattr(registry, "load_warnings", [])
    if full_registry_path() is None:
        real_full = registry.bundled_full_registry_path
        repo_full = (ROOT / "brokers" / "registry.yaml").resolve()

        def no_repo_full() -> Path:   # hide only the checkout's own private registry
            p = real_full()
            return tmp_path / "no-full-registry.yaml" if p.resolve() == repo_full else p
        monkeypatch.setattr(registry, "bundled_full_registry_path", no_repo_full)
    kr = MemoryKeyring()
    old = keyring.get_keyring()
    keyring.set_keyring(kr)
    from freemyid import logging_setup
    with logging_setup._lock:
        saved = set(logging_setup._pii)
        logging_setup._pii.clear()
    # cli.main() calls logging_setup.setup(), which attaches a StreamHandler bound to the
    # (CliRunner / capture) stderr of that test. Without this, those handlers leak into later
    # tests, write to closed streams and make setup() a no-op (it is idempotent).
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield home
    for h in list(root.handlers):
        if h not in saved_handlers:
            root.removeHandler(h)
            h.close()
    root.setLevel(saved_level)
    keyring.set_keyring(old)
    with logging_setup._lock:
        logging_setup._pii.clear()
        logging_setup._pii.update(saved)


@pytest.fixture
def memkeyring() -> MemoryKeyring:
    return keyring.get_keyring()  # type: ignore[return-value]


@pytest.fixture
def store(freemyid_env):
    from freemyid.storage import Store
    s = Store()
    yield s
    s.close()


@pytest.fixture
def fake_registry():
    from freemyid.registry import load_registry
    return load_registry(FIXTURES / "registry_min.yaml")


def make_profile(**over):
    from freemyid.models import Address, Consent, ConsentBasis, PersonName, Profile
    data = {
        "label": "Tester",
        "consent": Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                           text_version=CURRENT_TEXT_VERSION),
        "name": PersonName(first="Jane", middle="Q", last="Testperson"),
        "addresses": [Address(street="742 Evergreen Terrace", city="Springfield", state="il",
                              zip="62704", current=True)],
        "dob": date(1980, 4, 1),
        "phones": ["217-555-0142"],
        "emails": ["jane.testperson@example.com"],
        "relatives": ["John Testperson"],
    }
    data.update(over)
    return Profile(**data)


@pytest.fixture
def profile():
    return make_profile()
