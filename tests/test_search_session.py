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
    p = _person(store)
    rep = ss.run_session(store, p.id, mode="background", registry=_registry(), cfg=CFG,
                         notifier=Notes(), refresh=True)
    assert seen == [(False, False)]
    assert set(rep.outcomes.values()) == {"no_browser"}
    assert not (tmp_path / "browser_profile.lock").exists()


def test_no_display_and_busy_profile(store, monkeypatch, tmp_path) -> None:
    p = _person(store)
    real_has_display = ss.has_display
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
