"""WO-635: Cloudflare "Verify you are human" fails inside the fill window (field report
2026-11-13, F6).

1. Every Turnstile request a headed fill window makes is let through (a block would be our
   bug): the widget script, its frame, its own requests, and the site's own
   /cdn-cgi/challenge-platform/ requests. The site's background challenge-platform POSTs are
   not mistaken for the person pressing Submit.
2. When the widget itself reports failure, the window hands off: a plain message, the
   to-do card is kept with the next step, and the sighting is saved as evidence
   (CAPTCHA_ON_REQUEST / turnstile, reason codes only).
3. No evasion code exists anywhere in src/ (grep proof).

Fake people and fake sites only. The fixture page plays the widget's result events; no real
widget is loaded and nothing is solved.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from freemyid.engine import fill_for_me as ffm
from freemyid.engine._dev import fixture_server
from freemyid.engine.browser import BrowserManager, host_resolver_rules
from freemyid.models import (
    Broker,
    EvidenceKind,
    Listing,
    MailboxConfig,
    MatchLevel,
    ObstructionRecord,
    ProfileField,
    Registry,
    TodoKind,
)
from freemyid.netpolicy import NetPolicy, captcha_hosts
from tests.conftest import fill_bounded, make_profile

F = ProfileField
H = "https://devfill.example"
B = "https://broker.example"
CF = "https://challenges.cloudflare.com"
SUCCESS = [{"action": "human", "note": "person ticks the box and submits"},
           {"action": "expect_text", "value": "request has been received"}]
SRC = Path(__file__).resolve().parents[1] / "src" / "freemyid"


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 13), brokers=list(brokers))


def _broker(bid: str, host: str = H, page: str = "wo635-turnstile.html") -> Broker:
    dom = host.removeprefix("https://")
    return Broker(id=bid, name=f"Dev Fill {bid}", url=f"{host}/", category="people_search",
                  domains=[dom], opt_out_url=f"{host}/{page}", method="web_form",
                  required_fields=[F.FULL_NAME, F.EMAIL], form=SUCCESS)


# ------------------------------------------------------------- 1. nothing of Turnstile blocked


class _Frame:
    def __init__(self, parent: Any = None) -> None:
        self.parent_frame = parent


MAIN = _Frame()
SUB = _Frame(MAIN)
WIDGET = _Frame(SUB)        # a frame inside the widget frame


class _Req:
    def __init__(self, url: str, *, frame: _Frame | None, nav: bool,
                 hop: bool = False) -> None:
        self.url, self._frame, self._nav = url, frame, nav
        self.redirected_from = object() if hop else None

    @property
    def frame(self) -> _Frame:
        if self._frame is None:
            raise RuntimeError("no frame (worker)")
        return self._frame

    def is_navigation_request(self) -> bool:
        return self._nav


# (url, frame, is navigation) for one Turnstile check, as the widget makes them. Paths follow
# Turnstile's documented embed (api.js) and its challenge-platform frame; the exact path
# segments after /cdn-cgi/challenge-platform/ change between versions, so any path counts.
TURNSTILE_REQUESTS = [
    (f"{CF}/turnstile/v0/api.js?render=explicit", MAIN, False),
    (f"{CF}/turnstile/v0/g/abc123/api.js", MAIN, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/turnstile/if/ov2/av0/rcv/x/0x4AAA/light/normal/",
     SUB, True),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/orchestrate/chl_api/v1?ray=1", SUB, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/flow/ov1/0123:4567:abc/8f00/xyz", SUB, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/pat/8f00/1700000000000/abc/def/x", SUB, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/cmg/1", SUB, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/i/8f00/1700000000000/img.png", WIDGET, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/feedback-reports/x", SUB, False),
    (f"{CF}/cdn-cgi/challenge-platform/h/b/turnstile/if/x", SUB, False),   # worker-ish
]
SITE_REQUESTS = [            # the broker's own Cloudflare paths (same host: always fine)
    (f"{B}/cdn-cgi/challenge-platform/scripts/jsd/main.js", MAIN, False),
    (f"{B}/cdn-cgi/challenge-platform/h/b/jsd/r/0.123/8f00", MAIN, False),
    (f"{B}/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/v1?ray=1", MAIN, False),
]


def _real_bm() -> BrowserManager:
    return BrowserManager(NetPolicy(_registry(_broker("cf", B))), headless=True)


@pytest.mark.parametrize("url,frame,nav", TURNSTILE_REQUESTS)
def test_every_turnstile_request_is_let_through_in_the_fill_window(url: str, frame: _Frame,
                                                                   nav: bool) -> None:
    bm = _real_bm()
    hosts = bm.allowed_hosts(["broker.example"])
    is_main = bm._is_main_frame_navigation(_Req(url, frame=frame, nav=nav))
    assert bm.route_decision(url, is_main_frame_navigation=is_main, hosts=hosts,
                             allow_captcha_frames=True) == "captcha"
    for hop in (False, True):            # also when the widget redirects inside itself
        req = _Req(url, frame=frame, nav=nav, hop=hop)
        assert bm.request_verdict(req, hosts, allow_captcha_frames=True) == "ok"


def test_turnstile_worker_requests_are_let_through() -> None:
    """A request from a worker has no frame: it is not a main-frame navigation."""
    bm = _real_bm()
    url = f"{CF}/cdn-cgi/challenge-platform/h/b/flow/ov1/x"
    req = _Req(url, frame=None, nav=False)
    assert not bm._is_main_frame_navigation(req)
    assert bm.route_decision(url, is_main_frame_navigation=False,
                             hosts=bm.allowed_hosts(["broker.example"]),
                             allow_captcha_frames=True) == "captcha"


@pytest.mark.parametrize("url,frame,nav", SITE_REQUESTS)
def test_site_own_challenge_platform_requests_are_let_through(url: str, frame: _Frame,
                                                              nav: bool) -> None:
    bm = _real_bm()
    hosts = bm.allowed_hosts(["broker.example"])
    for captcha in (False, True):
        assert bm.route_decision(url, is_main_frame_navigation=nav, hosts=hosts,
                                 allow_captcha_frames=captcha) == "continue"


def test_turnstile_host_resolves_in_the_fill_window_only() -> None:
    bm = _real_bm()
    headed = bm.launch_args(captcha_hosts())[0]
    assert "EXCLUDE challenges.cloudflare.com" in headed
    assert "challenges.cloudflare.com" not in bm.launch_args()[0]
    assert "challenges.cloudflare.com" not in host_resolver_rules(set(), fixture_mode=True)


def test_turnstile_page_is_never_a_main_frame_destination() -> None:
    bm = _real_bm()
    hosts = bm.allowed_hosts(["broker.example"])
    url = f"{CF}/cdn-cgi/challenge-platform/h/b/turnstile/if/x"
    assert bm.route_decision(url, is_main_frame_navigation=True, hosts=hosts,
                             allow_captcha_frames=True) == "block"
    assert bm.request_verdict(_Req(url, frame=MAIN, nav=True), hosts, True) == "escape"


@pytest.mark.parametrize("url,method,kind,want", [
    (f"{B}/cdn-cgi/challenge-platform/h/b/jsd/r/0.1/8f", "POST", "xhr", False),
    (f"{B}/cdn-cgi/rum?x", "POST", "fetch", False),
    (f"{B}/api/optout", "POST", "fetch", True),
    (f"{B}/api/optout", "GET", "fetch", False),
])
def test_site_background_challenge_posts_are_not_a_submit(url: str, method: str, kind: str,
                                                         want: bool) -> None:
    assert ffm.submit_like_post(url, method, kind) is want


# ---------------------------------------------------------- 2. failure -> hand-off (browser)


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


@pytest.fixture
def short_grace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ffm, "_TURNSTILE_GRACE_S", 0.3)


WIDGET_ORIGIN = "https://widget.devfill.example"
_LISTENING = "() => !!window[Symbol.for('freemyid.turnstile')]"


@pytest.fixture(autouse=True)
def _fixture_widget_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture mode cannot serve challenges.cloudflare.com: the stand-in widget frame is
    served from widget.devfill.example, so that is the origin the listener trusts here."""
    monkeypatch.setattr(ffm, "_TURNSTILE_ORIGIN", WIDGET_ORIGIN)


def test_real_widget_origin_is_cloudflare() -> None:
    text = (SRC / "engine" / "fill_for_me.py").read_text(encoding="utf-8")
    assert f'\n_TURNSTILE_ORIGIN = "{CF}"\n' in text


@pytest.mark.browser
async def test_failed_turnstile_hands_off_and_keeps_the_card(store: Any,
                                                             short_grace: None) -> None:
    b = _broker("wo635_fail")
    p = _setup(store, b)

    async def person(page: Any) -> None:
        await page.wait_for_function(_LISTENING)
        await page.click("#ts-fail")          # the widget answers "can't verify"

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=10, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "challenge_failed", res
    assert res.notice == ffm.NOTICES["challenge_failed"]
    assert "are you human" in res.notice and "Open the site myself" in res.notice
    todos = [t for t in store.list_todos(p.id) if t.kind == TodoKind.ASSISTED_OPT_OUT]
    assert len(todos) == 1 and todos[0].id == res.todo_id
    assert todos[0].body.startswith(ffm._HANDOFF_STEP["challenge_failed"])
    assert todos[0].copy_fields                       # values to copy, in the app
    assert not store.list_requests(p.id)              # nothing was sent
    # Evidence: the sighting, PII-free JSON, plus the screenshot (both encrypted at rest).
    evs = store.list_evidence(p.id, b.id)
    kinds = sorted(e.kind for e in evs)
    assert kinds == sorted([EvidenceKind.BLOCK_CAPTURE, EvidenceKind.SCREENSHOT])
    cap = next(e for e in evs if e.kind == EvidenceKind.BLOCK_CAPTURE)
    data = json.loads(store.read_evidence(cap))
    rec = ObstructionRecord.model_validate(data["obstruction"])
    assert rec.kind.value == "captcha_on_request" and rec.vendor is not None
    assert rec.vendor.value == "turnstile" and rec.surface == "optout_form"
    assert rec.confidence == "observed" and rec.request_id is None
    assert data["final_url"] == f"{H}/wo635-turnstile.html" and data["window"] == "helper"
    blob = json.dumps(data)
    for pii in ("Jane", "Testperson", "Springfield", "removals.testperson"):
        assert pii not in blob
    # Events and logs: codes only.
    ev = [e for e in store.events(p.id) if e.action == "obstruction_observed"]
    assert ev and ev[0].detail == {"kind": "captcha_on_request", "vendor": "turnstile",
                                   "surface": "optout_form", "window": "helper"}
    fb = [e for e in store.events(p.id) if e.action == "fill_for_me_fallback"]
    assert fb and fb[0].detail == {"reason": "challenge_failed", "submit_seen": False}


@pytest.mark.browser
async def test_turnstile_that_recovers_is_not_handed_off(store: Any,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure the widget clears by itself within the fixed grace is not a hand-off."""
    monkeypatch.setattr(ffm, "_TURNSTILE_GRACE_S", 3.0)
    b = _broker("wo635_ok")
    p = _setup(store, b)

    async def person(page: Any) -> None:
        await page.wait_for_function(_LISTENING)
        await page.click("#ts-fail")
        await page.wait_for_function(
            "() => document.documentElement.getAttribute('data-freemyid-turnstile') "
            "=== 'failed'")
        await page.click("#ts-ok")
        await page.wait_for_function(
            "() => document.documentElement.getAttribute('data-freemyid-turnstile') === 'ok'")
        await page.click("button[type=submit]")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=10, on_ready=person, close_delay_s=0)
    assert res.status == "submitted", res
    assert not [e for e in store.events(p.id) if e.action == "obstruction_observed"]


@pytest.mark.browser
async def test_failure_message_from_another_origin_is_ignored(store: Any,
                                                             short_grace: None) -> None:
    b = _broker("wo635_origin")
    p = _setup(store, b)

    async def person(page: Any) -> None:
        await page.wait_for_function(_LISTENING)
        await page.click("#ts-wrong-origin")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=3, on_ready=person, close_delay_s=0)
    assert res.reason == "timeout", res


@pytest.mark.browser
async def test_page_script_cannot_forge_a_widget_failure(store: Any,
                                                         short_grace: None) -> None:
    """A synthetic event or a self-post from the page's own script is ignored (review LOW)."""
    b = _broker("wo635_forge")
    p = _setup(store, b)

    async def person(page: Any) -> None:
        await page.wait_for_function(_LISTENING)
        await page.click("#ts-forge")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=3, on_ready=person, close_delay_s=0)
    assert res.reason == "timeout", res
    assert not [e for e in store.events(p.id) if e.action == "obstruction_observed"]


def test_turnstile_state_is_read_passively() -> None:
    """The listener only reads the widget's own result messages: it never posts, clicks,
    or touches the widget frame."""
    js = ffm._TURNSTILE_WATCH_JS
    assert "addEventListener('message'" in js and "e.origin !== origin" in js
    assert "!e.isTrusted" in js and "e.source === window" in js
    for bad in ("postMessage(", ".click(", "contentWindow", "contentDocument",
                "dispatchEvent(", "webdriver", "defineProperty"):
        assert bad not in js


# ------------------------------------------------------------------ 3. grep proof: no evasion

_EVASION = re.compile(
    r"(playwright[-_]stealth|puppeteer-extra|undetected[-_]chrom|stealth\.min\.js|"
    r"navigator\.webdriver\s*=|defineProperty\([^)]*webdriver|"
    r"--disable-blink-features=AutomationControlled|AutomationControlled|"
    r"excludeSwitches|enable-automation|"
    r"2captcha|anti-?captcha|capsolver|capmonster|deathbycaptcha|nopecha|"
    r"canvas[-_ ]?fingerprint|webgl[-_ ]?vendor|hardwareConcurrency\s*=|"
    r"setUserAgentOverride|userAgentMetadata)", re.IGNORECASE)


ROOT = SRC.parents[1]


def _scanned_files() -> list[Path]:
    """Product code, its dependency list, and the packaging (installer, spec, Docker)."""
    out = [f for f in SRC.rglob("*")
           if f.suffix in (".py", ".js", ".html", ".json") and "zzz_legacy" not in f.parts]
    out.append(ROOT / "pyproject.toml")
    out += [f for f in (ROOT / "packaging").rglob("*")
            if f.is_file() and f.suffix not in (".ico", ".png", ".bmp", ".icns", ".exe")]
    return out


def test_evasion_scan_covers_dependencies_and_packaging() -> None:
    files = {f.relative_to(ROOT).as_posix() for f in _scanned_files()}
    assert "pyproject.toml" in files
    assert any(f.startswith("packaging/windows/") for f in files)
    assert _EVASION.search('dependencies = ["playwright-stealth>=1.0"]')
    assert _EVASION.search("args=['--disable-blink-features=AutomationControlled']")


def test_no_evasion_code_in_the_product() -> None:
    hits = []
    for f in _scanned_files():
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(),
                                 1):
            if _EVASION.search(line) and "noqa: evasion-list" not in line:
                hits.append(f"{f.relative_to(ROOT)}:{n}")
    assert hits == []
