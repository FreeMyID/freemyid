"""WO-634: the "Fill it in for me" window closed the moment it loaded a site (field report
2026-11-13, F5). One regression test per root cause, plus the "never close silently" rule.

Root causes covered:
  1. The headed window announced the HEADLESS browser's UA ("HeadlessChrome"), so bot walls
     refused it at once; the empty page then ended as `nothing_filled` with no message.
  2. A sub-resource / sub-frame redirect hop to an unlisted host (tracking pixel, widget)
     counted as an escape and ended the window, though the network floor stops it anyway.
  3. A main-frame redirect to an unlisted host ends the window (correct) but silently.
  4. A form drawn by a script after load was never waited for (`nothing_filled`).

Fake people and fake sites only (dev fixture server on 127.0.0.1, routes in fixture mode).
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from freemyid.engine import fill_for_me as ffm
from freemyid.engine._dev import fixture_server
from freemyid.engine.browser import BrowserManager
from freemyid.models import (
    Broker,
    Listing,
    MailboxConfig,
    MatchLevel,
    ProfileField,
    Registry,
    TodoKind,
)
from freemyid.netpolicy import NetPolicy
from tests.conftest import fill_bounded, make_profile
from tests.test_wizard_dashboard import TOKEN, _assisted, env  # noqa: F401
from tests.test_wizard_polish import _fill_env, _settle

F = ProfileField
H = "https://devfill.example"
SUCCESS = [{"action": "human", "note": "person submits"},
           {"action": "expect_text", "value": "request has been received"}]


def _broker(bid: str, page: str) -> Broker:
    return Broker(id=bid, name=f"Dev Fill {bid}", url=f"{H}/", category="people_search",
                  domains=["devfill.example"], opt_out_url=f"{H}/{page}", method="web_form",
                  required_fields=[F.FULL_NAME, F.EMAIL], form=SUCCESS)


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 13), brokers=list(brokers))


def _setup(store: Any, broker: Broker) -> Any:
    p = make_profile(mailbox=MailboxConfig(
        address="removals.testperson@example.com", imap_host="imap.example.com",
        smtp_host="smtp.example.com", username="removals.testperson@example.com"))
    store.save_profile(p)
    store.save_listing(Listing(profile_id=p.id, broker_id=broker.id,
                               url=f"{H}/p/jane-testperson-il", match_score=95,
                               match_level=MatchLevel.CONFIRMED,
                               shown_fields=[F.FULL_NAME]))
    return p


def _assert_card(store: Any, pid: str, res: Any, reason: str) -> None:
    todos = [t for t in store.list_todos(pid) if t.kind == TodoKind.ASSISTED_OPT_OUT]
    assert len(todos) == 1 and todos[0].id == res.todo_id       # the card is kept
    assert todos[0].body.startswith(ffm._HANDOFF_STEP[reason])
    assert "Open the site myself" in todos[0].body
    assert res.notice == ffm.NOTICES[reason]


# --------------------------------------------------------------------- 1. honest UA (fakes)


class _CDP:
    def __init__(self, ua: str) -> None:
        self.ua = ua

    async def send(self, method: str) -> dict[str, str]:
        assert method == "Browser.getVersion"
        return {"userAgent": self.ua}

    async def detach(self) -> None:
        return None


class _Ctx:
    def __init__(self) -> None:
        self.handlers: list[str] = []

    def on(self, event: str, _cb: object) -> None:
        self.handlers.append(event)

    async def route(self, _pattern: str, _handler: object) -> None:
        return None


class _FakeBrowser:
    def __init__(self, ua: str) -> None:
        self.ua = ua
        self.ctx_kwargs: dict[str, Any] = {}

    async def new_browser_cdp_session(self) -> _CDP:
        return _CDP(self.ua)

    async def new_context(self, **kw: Any) -> _Ctx:
        self.ctx_kwargs = kw
        return _Ctx()


HEADLESS_UA = "Mozilla/5.0 (Windows NT 10.0) HeadlessChrome/131.0.0.0 Safari/537.36 Edg/131"
HEADED_UA = "Mozilla/5.0 (Windows NT 10.0) Chrome/131.0.0.0 Safari/537.36 Edg/131"


async def test_headed_window_announces_its_own_ua(monkeypatch: pytest.MonkeyPatch) -> None:
    bm = BrowserManager(NetPolicy(_registry(_broker("ua", "labels"))), headless=True)
    shared, headed = _FakeBrowser(HEADLESS_UA), _FakeBrowser(HEADED_UA)

    async def ensure() -> Any:
        bm._browser = shared  # type: ignore[assignment]
        return shared

    async def launch(_headless: bool, _extra: Any = None) -> Any:
        return headed

    monkeypatch.setattr(bm, "_ensure", ensure)
    monkeypatch.setattr(bm, "_launch", launch)
    await bm.new_context(["devfill.example"], headed=True, allow_captcha_frames=True)
    ua = headed.ctx_kwargs["user_agent"]
    assert ua.startswith(HEADED_UA) and "Headless" not in ua
    assert ua.endswith(bm.cfg.user_agent_suffix.strip())
    await bm.new_context(["devfill.example"])                    # headless: its own UA
    assert shared.ctx_kwargs["user_agent"].startswith(HEADLESS_UA)


# ------------------------------------------------------------- 2-3. redirect verdicts (pure)


class _Frame:
    def __init__(self, parent: Any = None) -> None:
        self.parent_frame = parent


class _Req:
    def __init__(self, url: str, *, frame: _Frame, nav: bool, hop: bool) -> None:
        self.url, self.frame, self._nav = url, frame, nav
        self.redirected_from = object() if hop else None

    def is_navigation_request(self) -> bool:
        return self._nav


MAIN = _Frame()
SUB = _Frame(MAIN)


@pytest.mark.parametrize("url,frame,nav,want", [
    ("https://www.devfill.example/form", MAIN, True, "ok"),       # same company, www.
    ("https://elsewhere.example/optout", MAIN, True, "escape"),   # page left the site
    ("https://tracker.example/px.gif", MAIN, False, "stopped"),   # pixel hop: never sent
    ("https://widgets.example/embed", SUB, True, "stopped"),      # sub-frame hop
    ("https://198.51.100.7/px.gif", MAIN, False, "escape"),       # IP literal: strict
    ("https://localhost/px.gif", MAIN, False, "escape"),          # loopback: strict
])
def test_redirect_hop_verdicts(url: str, frame: _Frame, nav: bool, want: str) -> None:
    bm = BrowserManager(NetPolicy(_registry(_broker("v", "labels"))), headless=True)
    hosts = bm.allowed_hosts(["devfill.example"])
    assert bm.request_verdict(_Req(url, frame=frame, nav=nav, hop=True), hosts) == want


def test_hop_to_another_listed_broker_is_still_an_escape() -> None:
    """The floor resolves every registry domain, so such a hop really is sent: strict."""
    other = Broker(id="other", name="Other", url="https://other.example/",
                   category="people_search", domains=["other.example"], method="web_form",
                   opt_out_url="https://other.example/optout")
    bm = BrowserManager(NetPolicy(_registry(_broker("v", "labels"), other)), headless=True)
    hosts = bm.allowed_hosts(["devfill.example"])
    req = _Req("https://other.example/px.gif", frame=MAIN, nav=False, hop=True)
    assert bm.request_verdict(req, hosts) == "escape"


# --------------------------------------------------------------- 2-4. fixture-mode browser


@pytest.mark.browser
async def test_same_company_redirect_to_www_still_fills(store: Any) -> None:
    b = _broker("wo634_www", "wo634-to-www.html")
    p = _setup(store, b)
    seen: dict[str, str] = {}

    async def person(page: Any) -> None:
        seen["url"] = page.url
        await page.click("button[type=submit]")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.reason != "blocked" and res.filled == ["full_name"], res
    assert seen["url"].startswith("https://www.devfill.example/")


@pytest.mark.browser
async def test_redirected_pixel_and_frame_do_not_end_the_window(store: Any) -> None:
    b = _broker("wo634_px", "wo634-pixel.html")
    p = _setup(store, b)
    seen: dict[str, Any] = {}

    async def person(page: Any) -> None:
        seen["blocked"] = list(page.context.freemyid_blocked)
        seen["escaped"] = list(page.context.freemyid_escaped)
        await page.click("button[type=submit]")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.status == "submitted" and res.reason == "success_text", res
    assert seen["escaped"] == []
    assert {"tracker.example", "widgets.example"} <= set(seen["blocked"])


@pytest.mark.browser
@pytest.mark.parametrize("page", ["wo634-away.redirect", "wo634-js-away.html"])
async def test_redirect_to_unlisted_host_stops_with_a_message(store: Any, page: str) -> None:
    b = _broker("wo634_away", page)
    p = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=8, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "blocked", res
    _assert_card(store, p.id, res, "blocked")
    ev = [e for e in store.events(p.id) if e.action == "fill_for_me_fallback"]
    assert ev and ev[0].detail == {"reason": "blocked", "submit_seen": False}
    assert "elsewhere.example" not in repr([e.detail for e in store.events(p.id)])


@pytest.mark.browser
async def test_bot_wall_is_named_not_nothing_filled(store: Any) -> None:
    b = _broker("wo634_wall", "wo634-wall.html")
    p = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=5, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "challenge", res
    _assert_card(store, p.id, res, "challenge")


@pytest.mark.browser
async def test_empty_page_says_so(store: Any) -> None:
    b = _broker("wo634_empty", "empty")
    p = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=5, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "nothing_filled", res
    _assert_card(store, p.id, res, "nothing_filled")


@pytest.mark.browser
async def test_form_drawn_after_load_is_waited_for(store: Any) -> None:
    b = _broker("wo634_slow", "wo634-slow.html")
    p = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=10, close_delay_s=0)
    assert res.filled == ["full_name"], res
    assert res.reason == "timeout"          # nobody pressed Submit in this test


@pytest.mark.browser
async def test_stop_banner_is_shown_before_the_window_closes() -> None:
    """The stop message is put in the window itself (best effort, then the app says it)."""
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        try:
            br = await pw.chromium.launch(headless=True)
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"no browser: {type(e).__name__}")
        page = await br.new_page()
        await page.set_content("<html><body><p>site</p></body></html>")
        await ffm._show_stop(page, ffm.NOTICES["blocked"], 0)
        text = await page.inner_text(f"#{ffm.BANNER_ID}")
        await br.close()
    assert text == ffm.NOTICES["blocked"]


# ------------------------------------------------------------------------ card and app


def test_handoff_rewrites_the_next_step_on_the_kept_card(store: Any) -> None:
    b = _broker("wo634_card", "labels")
    p = _setup(store, b)
    first = ffm._fallback_todo(store, p, b, [], None, "timeout")
    second = ffm._fallback_todo(store, p, b, [], None, None, handoff="blocked")
    third = ffm._fallback_todo(store, p, b, [], None, None, handoff="nothing_filled")
    todos = store.list_todos(p.id)
    assert first == second == third and len(todos) == 1
    body = todos[0].body
    assert body.startswith(ffm._HANDOFF_STEP["nothing_filled"])
    assert body.count("Next step:") == 1 and "Never pay." in body


def test_notices_are_plain_and_value_free() -> None:
    for reason, text in ffm.NOTICES.items():
        assert reason in ffm._HANDOFF_STEP
        assert "Open the site myself" in text and len(text) < 220
        for word in ("Playwright", "allowlist", "policy", "http", "Error"):
            assert word not in text


@pytest.mark.parametrize("reason", sorted(ffm.NOTICES))
def test_app_shows_why_the_window_stopped(env: Any, monkeypatch: pytest.MonkeyPatch,  # noqa: F811
                                          reason: str) -> None:
    res = SimpleNamespace(status="fallback", reason=reason, submit_seen=False, todo_id=None,
                          notice=ffm.NOTICES[reason])
    c, store, t, f, _ = _fill_env(env, monkeypatch, res)
    c.post(f"/todo/{t.id}/fill", data=f)
    r = _settle(c)
    assert r.status_code == 303 and f"msg=fill_{reason}" in r.headers["location"]
    page = c.get(r.headers["location"]).text
    assert "Open the site myself" in page
    assert any(x.id == t.id for x in store.list_todos())       # card kept


def test_unknown_reason_keeps_the_generic_message(env: Any,  # noqa: F811
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    res = SimpleNamespace(status="fallback", reason="<script>", submit_seen=False,
                          todo_id=None)
    c, _s, t, f, _ = _fill_env(env, monkeypatch, res)
    c.post(f"/todo/{t.id}/fill", data=f)
    assert "msg=fill_none" in _settle(c).headers["location"]


_ = (TOKEN, _assisted)


# ------------------------------------------------------------------ registry health check


def _rh() -> Any:
    import importlib.util
    import sys

    from tests.conftest import ROOT
    spec = importlib.util.spec_from_file_location("registry_health",
                                                  ROOT / "tools" / "registry_health.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("registry_health", mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("domains,url,want", [
    (["devfill.example"], "https://devfill.example/optout", []),
    (["devfill.example"], "https://www.devfill.example/optout", []),
    (["www.devfill.example"], "https://www.devfill.example/optout", ["optout_www_only"]),
    (["www.devfill.example", "devfill.example"], "https://www.devfill.example/o", []),
    (["devfill.example"], "https://portal.elsewhere.example/o", ["optout_host"]),
])
def test_health_flags_optout_host_outside_domains(domains: list[str], url: str,
                                                  want: list[str]) -> None:
    rh = _rh()
    raw = {"id": "x", "method": "web_form", "domains": domains, "opt_out_url": url}
    got = rh.optout_host_findings(raw)
    assert [c for _lvl, c, _d in got] == want
    if want == ["optout_host"]:
        assert got[0][0] == rh.ERROR
    assert rh.optout_host_findings({**raw, "method": "email"}) == []


def test_online_check_follows_redirects_against_the_broker_own_domains() -> None:
    rh = _rh()
    reg = _registry(_broker("v", "labels"), Broker(
        id="other", name="Other", url="https://other.example/", category="people_search",
        domains=["other.example"], method="web_form",
        opt_out_url="https://other.example/optout"))
    pol = rh._BrokerPolicy(NetPolicy(reg), ["devfill.example"])
    assert pol.is_allowed("https://www.devfill.example/optout")
    assert not pol.is_allowed("https://other.example/optout")   # on the registry, not ours
    assert not pol.is_allowed("https://elsewhere.example/")
