"""WO-612 home-browser search session. Fake windows and dev .example brokers only; fake
people only. Nothing here touches the internet."""
from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from freemyid.config import Config
from freemyid.engine import search_session as ss
from freemyid.engine._dev import fixture_registry
from freemyid.models import Event, TodoKind, utcnow
from tests.conftest import make_profile

RESULT = """<div class="result"><a class="view" href="/person/jane-q-testperson">View</a>
<span class="name">Jane Q Testperson</span><span class="age">Age 46</span>
<span class="loc">Springfield, IL</span></div>"""
CHALLENGE = """<h1>Just a moment...</h1><p>Verify you are human.</p>
<div class="cf-turnstile" data-sitekey="0x0"></div>"""
FORBIDDEN = "<h1>Forbidden</h1>"
CFG = Config(max_delay_s=0)


def _registry(**access: str):
    """devauto (open), devblocked and a third copy dev403; `access` overrides
    search_access per broker id."""
    reg = fixture_registry()
    blocked = reg.get("devblocked")
    third = blocked.model_copy(update={
        "id": "dev403", "name": "Dev Forbidden Search", "domains": ["dev403.example"],
        "url": "https://dev403.example/",
        "search_url_pattern": "https://dev403.example/name/{first}-{last}/{state}",
        "opt_out_url": "https://dev403.example/optout", "form": [], "priority": 70})
    brokers = [b.model_copy(update={"search_access": access.get(b.id, b.search_access)})
               for b in [reg.get("devauto"), blocked, third]]
    return reg.model_copy(update={"brokers": brokers})


class FakeWindow:
    """Scripted window. `script` maps host -> "open" | "clears" (challenge, then the
    person/site clears it after `clear_after` looks) | "forbidden" | "always"."""

    def __init__(self, script: dict[str, str], clear_after: int = 2) -> None:
        self.script, self.clear_after = script, clear_after
        self.loads: list[str] = []
        self.looks = 0
        self.shown = 0
        self.closed = 0
        self._host = ""

    def _page(self, url: str) -> ss.View:
        kind = self.script[self._host]
        if kind == "open" or (kind == "clears" and self.looks >= self.clear_after):
            return ss.View(url, 200, RESULT, None)
        if kind == "forbidden":
            return ss.View(url, 403, FORBIDDEN, None)
        return ss.View(url, 403, CHALLENGE, "captcha_widget")

    async def load(self, broker, url: str) -> ss.View:
        self._host = urlsplit(url).hostname or ""
        self._url = url
        self.looks = 0
        self.loads.append(broker.id)
        return self._page(url)

    async def look(self) -> ss.View:
        self.looks += 1
        v = self._page(self._url)
        return ss.View(v.url, None, v.html, v.challenge)

    async def show(self) -> None:
        self.shown += 1

    async def close(self) -> None:
        self.closed += 1


class Hooks(ss.SessionHooks):
    def __init__(self, skip: set[str] | None = None) -> None:
        self.challenges: list[str] = []
        self.cleared: list[str] = []
        self.skip = skip or set()

    def on_challenge(self, broker_id: str, broker_name: str) -> None:
        self.challenges.append(broker_id)

    def on_cleared(self, broker_id: str) -> None:
        self.cleared.append(broker_id)

    def skip_requested(self, broker_id: str) -> bool:
        return broker_id in self.skip


class Notes:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.sent.append((title, body))


SCRIPT = {"devauto.example": "open", "devblocked.example": "clears",
          "dev403.example": "forbidden"}


def _person(store):
    p = make_profile()
    store.save_profile(p)
    return p


def _run(store, p, window, mode="attended", **kw):
    return ss.run_session(store, p.id, mode=mode, registry=kw.pop("registry", _registry()),
                          cfg=CFG, window=window, poll_s=0, refresh=True, **kw)


def test_attended_open_challenge_then_clear_and_403(store) -> None:
    """Acceptance 1: 1 parsed result, 1 handoff that resumes, 1 hand-check to-do."""
    p = _person(store)
    win, hooks = FakeWindow(SCRIPT), Hooks()
    rep = _run(store, p, win, hooks=hooks, timeout_s=5)
    assert rep.outcomes == {"devauto": "read", "devblocked": "read_after_challenge",
                            "dev403": "hand_check"}
    assert hooks.challenges == ["devblocked"] and hooks.cleared == ["devblocked"]
    assert win.shown == 1 and win.closed == 1
    found = {e.broker_id: e.status for e in rep.result.entries}
    assert found["devauto"] == "found"
    assert found["dev403"] == "check_by_hand"
    todos = store.list_todos(p.id)
    assert [(t.broker_id, t.resume_token) for t in todos] == [("dev403", "hand_check:dev403")]
    assert rep.queued == 0 and rep.notified is False


def test_session_reads_bot_blocked_and_unknown_brokers(store) -> None:
    """A plain exposure scan never tries these; the home-browser window does."""
    p = _person(store)
    reg = _registry(devauto="bot_blocked", devblocked="unknown", dev403="js_required")
    win = FakeWindow({h: "open" for h in SCRIPT})
    rep = _run(store, p, win, registry=reg)
    assert set(rep.outcomes.values()) == {"read"}
    assert sorted(set(win.loads)) == ["dev403", "devauto", "devblocked"]


def test_attended_skip_and_timeout_become_hand_checks(store) -> None:
    p = _person(store)
    win = FakeWindow({"devauto.example": "always", "devblocked.example": "always",
                      "dev403.example": "open"})
    rep = _run(store, p, win, hooks=Hooks(skip={"devauto"}), timeout_s=0.05)
    assert rep.outcomes["devauto"] == "skipped"
    assert rep.outcomes["devblocked"] == "timed_out"
    tokens = sorted(t.resume_token for t in store.list_todos(p.id))
    assert tokens == ["hand_check:devauto", "hand_check:devblocked"]


def test_background_never_shows_and_queues_after_one_retry(store) -> None:
    """Acceptance 2: a challenge in a scheduled run never pops a window; first run =
    retry next time, second run = queued for the person; ONE notice at 3 queued."""
    p = _person(store)
    script = {h: "always" for h in SCRIPT}
    notes = Notes()
    win = FakeWindow(script)
    rep1 = _run(store, p, win, mode="background", notifier=notes, grace_s=0.02)
    assert set(rep1.outcomes.values()) == {"challenge_retry"}
    assert store.list_todos(p.id) == [] and notes.sent == [] and win.shown == 0
    win2 = FakeWindow(script)
    rep2 = _run(store, p, win2, mode="background", notifier=notes, grace_s=0.02)
    assert set(rep2.outcomes.values()) == {"queued"} and win2.shown == 0
    todos = store.list_todos(p.id)
    assert {t.kind for t in todos} == {TodoKind.CAPTCHA} and len(todos) == 3
    assert rep2.queued == 3 and rep2.notified is True
    assert notes.sent == [("Free My ID needs you",
                           "3 sites need one click from you, about a minute.")]
    # a third background run: still queued, no second notice (the queue did not grow)
    rep3 = _run(store, p, FakeWindow(script), mode="background", notifier=notes,
                grace_s=0.02)
    assert set(rep3.outcomes.values()) == {"queued"} and len(store.list_todos(p.id)) == 3
    assert len(notes.sent) == 1


def test_background_self_clearing_interstitial_is_read(store) -> None:
    p = _person(store)
    win = FakeWindow({**SCRIPT, "dev403.example": "open"}, clear_after=1)
    rep = _run(store, p, win, mode="background", notifier=Notes(), grace_s=5)
    assert rep.outcomes["devblocked"] == "self_cleared" and win.shown == 0


def test_attended_batch_clears_the_queue(store) -> None:
    p = _person(store)
    script = {h: "always" for h in SCRIPT}
    for _ in range(2):
        _run(store, p, FakeWindow(script), mode="background", notifier=Notes(), grace_s=0.01)
    assert ss.pending_sites(store, p.id) == 3
    rep = _run(store, p, FakeWindow({h: "clears" for h in SCRIPT}), hooks=Hooks(),
               timeout_s=5)
    assert set(rep.outcomes.values()) == {"read_after_challenge"}
    assert ss.pending_sites(store, p.id) == 0 and store.list_todos(p.id) == []


def test_notice_rules(store) -> None:
    p = _person(store)
    reg = _registry()
    notes = Notes()
    now = utcnow()
    ss._queue(store, p.id, reg.get("devauto"))
    assert ss.maybe_notify(store, p.id, notes, now) is False          # 1 < 3, fresh
    assert ss.maybe_notify(store, p.id, notes, now + timedelta(days=15)) is True
    assert notes.sent[-1][1] == "1 site needs one click from you, about a minute."
    assert ss.maybe_notify(store, p.id, notes, now + timedelta(days=16)) is False
    ss._queue(store, p.id, reg.get("devauto"))                          # no duplicate
    assert ss.pending_sites(store, p.id) == 1


def test_events_are_pii_free(store) -> None:
    """Acceptance 4: broker id, outcome enum, mode and timings only."""
    p = _person(store)
    _run(store, p, FakeWindow(SCRIPT), hooks=Hooks(), timeout_s=5)
    evs: list[Event] = [e for e in store.events(p.id, limit=100)
                        if e.action == ss.EVENT_ACTION]
    assert len(evs) == 3
    for e in evs:
        assert set(e.detail) == {"outcome", "mode", "elapsed_ms", "waited_ms"}
        assert e.detail["outcome"] in {o.value for o in ss.Outcome}
        assert e.broker_id in {"devauto", "devblocked", "dev403"}
    blob = repr([e.detail for e in evs]).lower()
    for pii in ("jane", "testperson", "springfield", "http"):
        assert pii not in blob


def test_off_allowlist_and_window_failure(store) -> None:
    from freemyid.engine.browser import BlockedByPolicy

    class Escaping(FakeWindow):
        async def load(self, broker, url):
            if broker.id == "devauto":
                raise BlockedByPolicy("elsewhere.example")
            if broker.id == "dev403":
                raise ss.WindowUnavailable
            return await super().load(broker, url)

    p = _person(store)
    rep = _run(store, p, Escaping({**SCRIPT, "devblocked.example": "open"}))
    assert rep.outcomes == {"devauto": "blocked_by_policy", "devblocked": "read",
                            "dev403": "no_browser"}


def test_no_consent_refused(store) -> None:
    from freemyid.engine.exposure import ExposureRefused
    from freemyid.models import Consent, ConsentBasis
    p = make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                     text_version="0"))
    store.save_profile(p)
    with pytest.raises(ExposureRefused):
        _run(store, p, FakeWindow(SCRIPT))


# --------------------------------------------------------------------------- launch rules


def _bm(fixture: str | None = None):
    from freemyid.engine.browser import BrowserManager
    from freemyid.netpolicy import NetPolicy
    return BrowserManager(NetPolicy(_registry()), headless=False, cfg=CFG,
                          fixture_base=fixture)


def test_persistent_launch_is_headed_and_background_is_off_screen() -> None:
    bm = _bm()
    bg = bm.persistent_launch_kwargs("background")
    assert bg["headless"] is False and bg["no_viewport"] is True
    assert "--window-position=-32000,-32000" in bg["args"]
    assert any(a.startswith("--host-resolver-rules=") for a in bg["args"])
    vis = bm.persistent_launch_kwargs("visible")
    assert vis["headless"] is False
    assert not any(a.startswith("--window-position") for a in vis["args"])
    with pytest.raises(ValueError):
        bm.persistent_launch_kwargs("background", test_headless=True)   # not in fixture mode
    with pytest.raises(ValueError):
        bm.persistent_launch_kwargs("minimised")
    assert _bm("http://127.0.0.1:1").persistent_launch_kwargs(
        "background", test_headless=True)["headless"] is True


def test_run_session_builds_a_headed_window(store, monkeypatch, tmp_path) -> None:
    """Acceptance 2: outside dev fixture tests the session window is never headless."""
    seen: list[tuple[bool, str]] = []

    class Spy(ss.PlaywrightWindow):
        def __init__(self, bm, folder, mode, test_headless=False):
            seen.append((bm.headless, test_headless))
            super().__init__(bm, folder, mode, test_headless)

        async def load(self, broker, url):
            raise ss.WindowUnavailable

    monkeypatch.setattr(ss, "PlaywrightWindow", Spy)
    monkeypatch.setattr(ss, "profile_dir", lambda: tmp_path / "browser_profile")
    monkeypatch.setattr(ss, "has_display", lambda platform=None: True)
    monkeypatch.setattr(ss, "background_supported", lambda platform=None: True)  # Windows
    p = _person(store)
    rep = ss.run_session(store, p.id, mode="background", registry=_registry(), cfg=CFG,
                         notifier=Notes(), refresh=True)
    assert seen == [(False, False)]
    assert set(rep.outcomes.values()) == {"no_browser"}
    assert not (tmp_path / "browser_profile.lock").exists()


def test_no_display_and_busy_profile(store, monkeypatch, tmp_path) -> None:
    p = _person(store)
    real_has_display = getattr(ss, "real_has_display", ss.has_display)  # conftest stubs it
    monkeypatch.setattr(ss, "has_display", lambda platform=None: False)
    with pytest.raises(ss.SessionUnavailable, match="no_display"):
        ss.run_session(store, p.id, registry=_registry(), cfg=CFG, notifier=Notes())
    folder = tmp_path / "browser_profile"
    with ss._session_lock(folder), pytest.raises(ss.SessionUnavailable, match="busy"), \
            ss._session_lock(folder):
        pass
    assert real_has_display("win32") is True


# --------------------------------------------------------------------------- rule 5 grep


def test_rule5_no_code_path_acts_on_a_page_in_the_session() -> None:
    """Acceptance 3: the session only reads (content, frame URLs, url). It never clicks,
    types, presses, fills, evaluates script in or locates challenge frames."""
    src = Path(ss.__file__).read_text(encoding="utf-8")
    code = re.sub(r'"""(.|\n)*?"""', "", src)        # docstrings may name the rules
    for bad in (".click(", ".fill(", ".type(", ".press(", ".check(", ".tap(", "evaluate(",
                "frame_locator", "add_init_script", "dispatch_event", ".mouse", ".keyboard",
                "set_input_files", "stealth", "solver"):
        assert bad not in code, bad
    bsrc = Path(ss.__file__).with_name("browser.py").read_text(encoding="utf-8")
    start = bsrc.index("async def persistent_context")
    body = bsrc[start:bsrc.index("def retarget", start)]
    # the only script run is reading the UA on the app's own blank first page
    assert body.count("evaluate(") == 1 and "navigator.userAgent" in body
    for bad in (".click(", ".fill(", ".type(", "frame_locator", "add_init_script"):
        assert bad not in body, bad


# --------------------------------------------------------------------------- real window


def _browser_registry():
    """devauto (open), devclear (interstitial that clears by itself) and dev404 (no page:
    an HTTP error). All `bot_blocked` so the plain scan would never try them."""
    reg = fixture_registry()
    base = reg.get("devblocked")

    def site(bid: str, prio: int):
        return base.model_copy(update={
            "id": bid, "name": f"Dev {bid}", "domains": [f"{bid}.example"],
            "url": f"https://{bid}.example/", "form": [], "priority": prio,
            "search_url_pattern": f"https://{bid}.example/name/{{first}}-{{last}}/{{state}}",
            "opt_out_url": f"https://{bid}.example/optout", "search_access": "bot_blocked"})

    auto = reg.get("devauto").model_copy(update={"search_access": "bot_blocked"})
    return reg.model_copy(update={"brokers": [auto, site("devclear", 80),
                                              site("dev404", 70)]})


@pytest.mark.browser
@pytest.mark.parametrize("mode", ["attended", "background"])
def test_real_window_fixture_mode(store, monkeypatch, tmp_path, mode) -> None:
    """Acceptance 1 in a real (fixture-mode) browser: 1 read, 1 challenge that resumes once
    it clears, 1 hand-check; every request stays on the allowlist or is aborted."""
    from freemyid.engine._dev import fixture_server
    from freemyid.engine.browser import BrowserManager

    decisions: list[tuple[str, str]] = []
    real = BrowserManager.route_decision

    def spy(self, url, **kw):
        what = real(self, url, **kw)
        decisions.append((urlsplit(url).hostname or url[:12], what))
        return what

    monkeypatch.setattr(BrowserManager, "route_decision", spy)
    monkeypatch.setattr(ss, "profile_dir", lambda: tmp_path / "browser_profile")
    p = _person(store)
    hooks = Hooks()
    with fixture_server():
        rep = ss.run_session(store, p.id, mode=mode, registry=_browser_registry(),
                             cfg=CFG, hooks=hooks, notifier=Notes(), refresh=True,
                             test_headless=True, timeout_s=20, grace_s=20, poll_s=0.2)
    cleared = "read_after_challenge" if mode == "attended" else "self_cleared"
    assert rep.outcomes == {"devauto": "read", "devclear": cleared, "dev404": "hand_check"}
    banner = ["devclear"] if mode == "attended" else []       # background: never shown
    assert hooks.challenges == banner and hooks.cleared == banner
    status = {e.broker_id: e.status for e in rep.result.entries}
    assert status["devauto"] == "found"
    assert [t.resume_token for t in store.list_todos(p.id)] == ["hand_check:dev404"]
    allowed = {"devauto.example", "devclear.example", "dev404.example"}
    assert ("tracker.invalid", "block") in decisions
    assert all(h in allowed for h, what in decisions if what != "block"), decisions
    assert (tmp_path / "browser_profile").is_dir()            # the app's own profile folder


# --------------------------------------------------------------------------- the runner


class NoBrowser:
    """A runner browser that fails the test if anything uses it."""

    def __getattr__(self, name):
        raise AssertionError(f"headless browser used for a session-only site ({name})")


@pytest.mark.parametrize("access", ["bot_blocked", "unknown"])
def test_runner_never_searches_session_only_sites_headless(store, access) -> None:
    """Acceptance 2: the runner's headless browser never tries a bot_blocked site (blind
    until the home-browser session reads it), nor an unknown one the session has taken
    over; the session's listings count instead."""
    from freemyid.engine import runner
    reg = _registry(devauto=access)

    def scan(p):
        runner.run(store, reg, [p], scan_only=True, dry_run=True, interactive=False,
                   broker_ids=["devauto"], browser=NoBrowser(), cfg=CFG)
        return [e.action for e in store.events(p.id, "devauto", limit=20)]

    if access == "bot_blocked":
        blind = _person(store)
        assert "presumed_listed" in scan(blind)                      # never read: blind
        assert store.get_status(blind.id, "devauto").last_scan_at is None
    p = _person(store)
    _run(store, p, FakeWindow({"devauto.example": "open"}), broker_ids=["devauto"])
    assert ss.fresh_read(store, p.id, "devauto")
    acts = scan(p)
    assert "scanned" in acts and "scan_failed" not in acts          # the session's read
    st = store.get_status(p.id, "devauto")
    assert st.state.value == "found" and st.last_scan_at is not None
    later = utcnow() + timedelta(days=2)
    assert not ss.fresh_read(store, p.id, "devauto", later)          # stale after a day


def test_run_for_profiles_never_raises(store, monkeypatch) -> None:
    from freemyid.models import Consent, ConsentBasis
    ok = _person(store)
    no = make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                      text_version="0"))
    store.save_profile(no)
    out = ss.run_for_profiles(store, [ok.id, no.id, "f" * 32], registry=_registry(),
                              cfg=CFG, notifier=Notes(),
                              window_factory=lambda: FakeWindow(SCRIPT))
    assert isinstance(out[ok.id], ss.SessionReport)
    assert out[no.id] == "no_consent" and out["f" * 32] == "no_consent"
    monkeypatch.setattr(ss, "has_display", lambda platform=None: False)
    assert ss.run_for_profiles(store, [ok.id], registry=_registry(), cfg=CFG) == \
        {ok.id: "no_display"}


@pytest.mark.parametrize("outcome,takes_over", [
    ("read", True), ("self_cleared", True), ("read_after_challenge", True),
    ("challenge_retry", True), ("queued", True), ("timed_out", True), ("skipped", True),
    ("no_browser", False), ("error", False), ("not_tried", False), ("cached", False),
    ("hand_check", False), ("blocked_by_policy", False)])
def test_unknown_site_is_session_only_after_a_real_visit(store, outcome, takes_over) -> None:
    """SEC-WO612-6: only a read or a challenge makes an `unknown` site session-only. A
    session that never got a window, hit network trouble or had nothing to visit leaves the
    runner's normal handling in place. `bot_blocked` is always session-only."""
    from freemyid.models import Actor
    reg = _registry(devauto="unknown")
    broker = reg.get("devauto")
    p = _person(store)
    assert not ss.session_only(store, p.id, broker)
    store.log(Event(ts=utcnow(), profile_id=p.id, broker_id="devauto", actor=Actor.ENGINE,
                    action=ss.EVENT_ACTION, detail={"outcome": outcome, "mode": "background"}))
    assert ss.session_only(store, p.id, broker) is takes_over
    blocked = _registry(devauto="bot_blocked").get("devauto")
    assert ss.session_only(store, p.id, blocked)


def test_background_window_is_windows_only_until_wo616(store, monkeypatch) -> None:
    """SEC-WO612-2: off Windows a background window would be a real visible window, so the
    engine refuses it; the attended (visible on purpose) session still runs anywhere."""
    assert ss.background_supported("win32") is True
    assert ss.background_supported("darwin") is False
    assert ss.background_supported("linux") is False
    monkeypatch.setattr(ss, "has_display", lambda platform=None: True)
    monkeypatch.setattr(ss, "background_supported", lambda platform=None: False)
    p = _person(store)
    with pytest.raises(ss.SessionUnavailable, match="no_display"):
        ss.run_session(store, p.id, mode="background", registry=_registry(), cfg=CFG,
                       notifier=Notes())


class HangingLoad(FakeWindow):
    """`hang` hosts never finish loading (a page whose main thread is stuck)."""

    def __init__(self, script, hang: set[str]) -> None:
        super().__init__(script)
        self.hang = hang

    async def load(self, broker, url):
        if urlsplit(url).hostname in self.hang:
            import asyncio
            await asyncio.sleep(3600)
        return await super().load(broker, url)


def test_hung_load_closes_the_window_records_error_and_the_run_goes_on(store) -> None:
    """SEC-WO612-3: a load past `step_s` closes the window (the next site opens a fresh
    one), records ERROR (the next run tries again) and the session carries on."""
    import time as _time
    win = HangingLoad(SCRIPT, hang={"devauto.example"})
    p = _person(store)
    t = _time.monotonic()
    rep = ss.run_session(store, p.id, mode="background", registry=_registry(), cfg=CFG,
                         window=win, poll_s=0, refresh=True, notifier=Notes(),
                         step_s=0.2, look_s=0.2)
    assert _time.monotonic() - t < 10
    assert rep.outcomes["devauto"] == "error"
    assert rep.outcomes["devblocked"] == "self_cleared"
    assert rep.outcomes["dev403"] == "hand_check"
    assert win.closed >= 2                    # once after the hang, once at the end


def test_site_and_session_budgets(store) -> None:
    """Each site has a budget from its first page and the session one overall; out of
    budget = ERROR without a visit."""
    now = [0.0]
    win = FakeWindow(SCRIPT)
    beats: list[int] = []
    f = ss.SessionFetcher(win, "background", grace_s=0.5, poll_s=0, clock=lambda: now[0],
                          site_s=10, session_s=100, heartbeat=lambda: beats.append(1))
    reg = _registry()
    auto, blocked = reg.get("devauto"), reg.get("devblocked")
    f(auto, "https://devauto.example/name/jane-testperson/il")
    assert beats == [1]
    now[0] = 11.0                             # devauto's own budget is used up
    with pytest.raises(ss.FetchFailed, match="network"):
        f(auto, "https://devauto.example/name/jane-testperson/il?again")
    assert beats == [1]                       # same site: no new heartbeat
    now[0] = 101.0                            # the whole session is out of time
    with pytest.raises(ss.FetchFailed, match="network"):
        f(blocked, "https://devblocked.example/name/jane-testperson/il")
    assert f.runs["devblocked"].outcome == "error" and win.loads == ["devauto"]
    assert beats == [1, 1]                    # the lock is refreshed per site
    f.close()
