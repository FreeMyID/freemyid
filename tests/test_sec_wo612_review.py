"""qa-security review of WO-612 (home-browser search session), wave 2026-11-11c.

Each strict xfail demonstrates one open finding; the fix flips it to a pass (and strict
then forces the marker off). Fake people only; no test touches the internet. The one
browser test runs headless Chromium in dev fixture mode (same as test_search_session).
"""
from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from freemyid import paths
from freemyid.engine import search_session as ss
from freemyid.engine.exposure import FetchFailed

from .conftest import make_profile
from .test_cli_json_headless import _app, fake_run  # noqa: F401  (fixture re-export)
from .test_search_session import CFG, Hooks, Notes, _browser_registry, _registry

# --------------------------------------------------------------------------- F1 profile PII


@pytest.mark.xfail(strict=True, reason="SEC-WO612-1: `freemyid wipe` leaves the app's "
                   "browser profile (history/cache with search URLs) on disk")
def test_wipe_covers_the_session_browser_profile() -> None:
    assert ss.profile_dir().name in paths.OWNED_ENTRIES
    assert "browser_profile.lock" in paths.OWNED_ENTRIES


@pytest.mark.browser
@pytest.mark.xfail(strict=True, reason="SEC-WO612-1: the persistent Chromium profile keeps "
                   "the person's name (search URLs / page text) in plaintext files")
def test_session_profile_keeps_no_plaintext_pii(store, monkeypatch, tmp_path) -> None:
    from playwright.sync_api import sync_playwright

    from freemyid.engine._dev import fixture_server
    # The full browser (not the headless shell, which keeps no history or cache) is what
    # the real Edge window is; run it headless in fixture mode via the dev override.
    pw = sync_playwright().start()
    try:
        exe = pw.chromium.executable_path
    finally:
        pw.stop()
    if not Path(exe).exists():
        pytest.skip("full Chromium not installed")
    monkeypatch.setenv("FREEMYID_BROWSER_EXECUTABLE", exe)
    folder = tmp_path / "browser_profile"
    monkeypatch.setattr(ss, "profile_dir", lambda: folder)
    p = make_profile()
    store.save_profile(p)
    with fixture_server():
        ss.run_session(store, p.id, mode="background", registry=_browser_registry(),
                       cfg=CFG, hooks=Hooks(), notifier=Notes(), refresh=True,
                       test_headless=True, timeout_s=5, grace_s=5, poll_s=0.2)
    hits = []
    for f in folder.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                if b"testperson" in f.read_bytes().lower():
                    hits.append(str(f.relative_to(folder)))
            except OSError:
                continue
    assert hits == [], hits


# --------------------------------------------------------------------------- F2 --headless


@pytest.mark.xfail(strict=True, reason="SEC-WO612-2: `run --headless --scheduled` (the "
                   "macOS launchd / Linux systemd job) still opens a headed window when a "
                   "display exists")
def test_headless_scheduled_run_never_opens_a_window(store, monkeypatch,
                                                     fake_run) -> None:  # noqa: F811
    calls: list = []
    monkeypatch.setattr(ss, "has_display", lambda platform=None: True)   # a Mac / desktop
    monkeypatch.setattr(ss, "run_for_profiles", lambda *a, **k: calls.append(k) or {})
    store.save_profile(make_profile())
    res = CliRunner().invoke(_app(), ["run", "--headless", "--scheduled"])
    assert res.exit_code == 0, res.output
    assert calls == []          # --headless = "No prompts or windows"


def test_has_display_is_true_on_macos_without_any_check() -> None:
    """Context for F2: on darwin the guard is unconditional, so it never skips there."""
    real = getattr(ss, "real_has_display", ss.has_display)
    assert real("darwin") is True


# --------------------------------------------------------------------------- F3 hung page


class _HungLook:
    """First load shows a challenge; every later look never returns (a page whose main
    thread is busy: Playwright's page.content() has no timeout)."""

    async def load(self, broker, url):
        return ss.View(url, 403, "<h1>Just a moment...</h1>", "interstitial")

    async def look(self):
        await asyncio.sleep(3600)

    async def show(self):
        return None

    async def close(self):
        return None


@pytest.mark.xfail(strict=True, reason="SEC-WO612-3: the grace/timeout limit is only "
                   "checked between looks; a look that never returns hangs the scheduled run")
def test_hung_page_cannot_hang_the_session() -> None:
    broker = _registry().get("devblocked")
    fetcher = ss.SessionFetcher(_HungLook(), "background", grace_s=0.3, timeout_s=0.3,
                                poll_s=0.05)
    box: dict = {}

    def go() -> None:
        try:
            fetcher(broker, "https://devblocked.example/name/jane-testperson/il")
        except FetchFailed as e:
            box["failed"] = str(e)

    t = threading.Thread(target=go, daemon=True)
    t.start()
    t.join(5)
    assert not t.is_alive(), "session still waiting on a hung page"
    assert box.get("failed") == "challenge"


# --------------------------------------------------------------------------- F4 lock


def test_live_session_lock_is_not_taken_over(tmp_path: Path) -> None:
    folder = tmp_path / "browser_profile"
    lock = folder.parent / "browser_profile.lock"
    with ss._session_lock(folder):
        old = time.time() - 4 * 3600          # a long attended batch, holder still running
        os.utime(lock, (old, old))
        with pytest.raises(ss.SessionUnavailable, match="busy"), ss._session_lock(folder):
            pass


def test_session_lock_holds_pid_and_a_dead_holders_lock_is_taken(tmp_path: Path) -> None:
    """SEC-WO612-4 fix: the OS lock dies with its holder; a leftover file (a crash, or an
    older version's lock) never blocks the next session, and the file names the holder."""
    folder = tmp_path / "browser_profile"
    lock = folder.parent / "browser_profile.lock"
    lock.write_text("999999999\n")                 # nobody holds an OS lock on it
    with ss._session_lock(folder) as held:
        assert lock.read_text().strip() == str(os.getpid())
        held.refresh()
        assert lock.read_text().strip() == str(os.getpid())
    assert not lock.exists()
    with ss._session_lock(folder):                  # released: free again
        pass


def test_session_lock_race_on_an_unlinked_file_is_busy(tmp_path: Path, monkeypatch) -> None:
    """Two processes: the second locked the file the first had just unlinked. The inode
    check reports busy instead of both holding a lock."""
    folder = tmp_path / "browser_profile"
    lock = ss.SessionLock(folder.parent / "browser_profile.lock")
    real_stat = os.stat

    def moved(path, *a, **k):
        st = real_stat(path, *a, **k)
        if Path(path) == lock.path:
            return os.stat_result((st.st_mode, st.st_ino + 1, *tuple(st)[2:]))
        return st

    monkeypatch.setattr(ss.os, "stat", moved)
    with pytest.raises(ss.SessionUnavailable, match="busy"):
        lock.acquire()
    monkeypatch.undo()
    lock.acquire()
    lock.release()


# --------------------------------------------------------------------------- CR-C/D parity


@pytest.mark.browser
def test_browser_parser_matches_static_parser_on_wo601_fixtures() -> None:
    """CR-C/D: `web_form.parse_results` (runner, live DOM, inner_text) must read the same
    candidates as `exposure.parse_candidates` (scan / session, static HTML). Headless, every
    request answered locally; nothing leaves the machine."""
    from playwright.async_api import async_playwright

    from freemyid.submitters import web_form
    from tests import test_search_specs_wo601 as wo601

    def key(cands):
        return [(c.url, c.name, c.age, c.locations, c.relatives) for c in cands]

    async def browser_side() -> dict[str, list]:
        out: dict[str, list] = {}
        async with async_playwright() as pw:
            b = await pw.chromium.launch(headless=True,
                                         args=["--host-resolver-rules=MAP * ~NOTFOUND"])
            try:
                for bid in wo601.SPECS:
                    html = (wo601.FIX / f"{bid}.html").read_text()
                    url = wo601.SEARCH_URL[bid]
                    page = await b.new_page()

                    def answerer(html: str, url: str):
                        async def answer(route) -> None:   # one arg: Playwright counts them
                            if route.request.url == url:
                                await route.fulfill(status=200, body=html,
                                                    content_type="text/html")
                            else:
                                await route.abort("blockedbyclient")
                        return answer

                    await page.route("**/*", answerer(html, url))
                    await page.goto(url, wait_until="domcontentloaded")
                    out[bid] = key(await web_form.parse_results(page, wo601._broker(bid)))
                    await page.close()
            finally:
                await b.close()
        return out

    live = asyncio.run(browser_side())
    for bid in wo601.SPECS:
        assert live[bid] == key(wo601._cands(bid)), bid
