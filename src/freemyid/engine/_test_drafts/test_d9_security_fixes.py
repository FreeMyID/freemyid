"""Draft tests for the D9 security fixes (docs/SECURITY_REVIEW.md SEC-30..37 + D10 covered_by).

Inline pages (page.set_content) or the loopback dev fixture server only; fake requests for
the SEC-36 route decision (loopback fixtures can't host real CAPTCHA domains). Fake people.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from freemyid.engine import filler
from freemyid.engine._dev import fixture_server
from freemyid.engine.browser import BrowserManager
from freemyid.engine.fill_for_me import _Snap, fill_for_me, new_signal
from freemyid.models import (
    Broker,
    Listing,
    MailboxConfig,
    MatchLevel,
    ProfileField,
    Registry,
)
from freemyid.netpolicy import NetPolicy
from tests.conftest import make_profile

F = ProfileField
H = "https://devfill.example"
VALUES = {"first_name": "Jane", "last_name": "Testperson", "full_name": "Jane Testperson",
          "email": "removals.testperson@example.com",
          "listing_url": "https://devfill.example/p/jane-testperson"}
RECAPTCHA = "https://www.google.com/recaptcha/api2/anchor?k=x"
HCAPTCHA = "https://newassets.hcaptcha.com/captcha/v1/abc/static/hcaptcha.html"
TURNSTILE = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/if/x"


# --------------------------------------------------------------------------- fakes


class _Frame:
    def __init__(self, parent: Any = None) -> None:
        self.parent_frame = parent


MAIN = _Frame()
SUB = _Frame(parent=MAIN)


class _Req:
    def __init__(self, url: str, *, nav: bool, frame: _Frame = MAIN,
                 redirected_from: Any = None) -> None:
        self.url, self._nav, self.frame, self.redirected_from = url, nav, frame, redirected_from

    def is_navigation_request(self) -> bool:
        return self._nav


class _Route:
    def __init__(self, req: _Req) -> None:
        self.request = req
        self.did: str | None = None

    async def continue_(self) -> None:
        self.did = "continue"

    async def abort(self, code: str = "") -> None:
        self.did = "abort"

    async def fetch(self, **kw: Any) -> Any:
        raise AssertionError("no fixture fetch expected")

    async def fulfill(self, **kw: Any) -> None:
        self.did = "fulfill"


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 6), brokers=list(brokers))


def _bm(fixture_base: str | None = None) -> BrowserManager:
    b = Broker(id="dv", name="Dev", url=f"{H}/", category="people_search",
               domains=["devfill.example"], method="web_form", opt_out_url=f"{H}/labels")
    return BrowserManager(NetPolicy(_registry(b)), headless=True, fixture_base=fixture_base)


# --------------------------------------------------------------------------- SEC-36 (pure)


@pytest.mark.parametrize("url", [RECAPTCHA, HCAPTCHA, TURNSTILE])
def test_captcha_subresource_blocked_by_default(url):
    bm = _bm()
    hosts = bm.allowed_hosts(["devfill.example"])
    assert bm.route_decision(url, is_main_frame_navigation=False, hosts=hosts) == "block"
    assert bm.route_decision(url, is_main_frame_navigation=False, hosts=hosts,
                             allow_captcha_frames=False) == "block"


@pytest.mark.parametrize("url", [RECAPTCHA, HCAPTCHA, TURNSTILE])
def test_captcha_subresource_allowed_only_when_opted_in(url):
    bm = _bm()
    hosts = bm.allowed_hosts(["devfill.example"])
    assert bm.route_decision(url, is_main_frame_navigation=False, hosts=hosts,
                             allow_captcha_frames=True) == "captcha"
    # never as the page itself
    assert bm.route_decision(url, is_main_frame_navigation=True, hosts=hosts,
                             allow_captcha_frames=True) == "block"


@pytest.mark.parametrize("url", [
    "http://www.google.com/recaptcha/api.js",          # not https
    "https://www.google.com/search?q=x",               # google, but not the widget path
    "https://evil.example/recaptcha/",                 # not a CAPTCHA host
    "https://hcaptcha.com.evil.example/x",             # suffix lookalike
    "https://user:pw@www.google.com/recaptcha/",       # credentials
])
def test_non_widget_urls_stay_blocked_even_opted_in(url):
    bm = _bm()
    hosts = bm.allowed_hosts(["devfill.example"])
    assert bm.route_decision(url, is_main_frame_navigation=False, hosts=hosts,
                             allow_captcha_frames=True) == "block"


def test_fixture_mode_never_lets_captcha_out():
    bm = _bm("http://127.0.0.1:1")
    hosts = bm.allowed_hosts(["devfill.example"])
    assert bm.route_decision(RECAPTCHA, is_main_frame_navigation=False, hosts=hosts,
                             allow_captcha_frames=True) == "block"
    assert bm.route_decision(f"{H}/labels", is_main_frame_navigation=True,
                             hosts=hosts) == "fixture"


async def test_route_handler_with_fake_requests():
    bm = _bm()
    hosts = bm.allowed_hosts(["devfill.example"])
    blocked: list[str] = []
    default = bm.make_route_handler(hosts, blocked)            # headless / scheduled path
    opted = bm.make_route_handler(hosts, blocked, allow_captcha_frames=True)
    r = _Route(_Req(RECAPTCHA, nav=True, frame=SUB))           # the widget iframe
    await default(r)
    assert r.did == "abort" and blocked == ["www.google.com"]
    r = _Route(_Req(RECAPTCHA, nav=True, frame=SUB))
    await opted(r)
    assert r.did == "continue"
    r = _Route(_Req(RECAPTCHA, nav=True, frame=MAIN))          # top-level navigation
    await opted(r)
    assert r.did == "abort"
    r = _Route(_Req(f"{H}/labels", nav=True))
    await opted(r)
    assert r.did == "continue"


def test_escape_detector_captcha_frames():
    bm = _bm()
    hosts = bm.allowed_hosts(["devfill.example"])
    iframe_hop = _Req(TURNSTILE, nav=True, frame=SUB, redirected_from=object())
    assert bm.is_escape(iframe_hop, hosts)                          # default: escape
    assert not bm.is_escape(iframe_hop, hosts, allow_captcha_frames=True)
    main_nav = _Req(RECAPTCHA, nav=True, frame=MAIN)
    assert bm.is_escape(main_nav, hosts, allow_captcha_frames=True)  # still an escape
    off_list_iframe_hop = _Req("https://evil.example/x", nav=True, frame=SUB,
                               redirected_from=object())
    assert bm.is_escape(off_list_iframe_hop, hosts, allow_captcha_frames=True)
    assert not bm.is_escape(_Req(f"{H}/done", nav=True), hosts)


def test_resolver_rules_only_widen_for_the_opted_in_window():
    from freemyid.netpolicy import captcha_hosts
    bm = _bm()
    assert "www.google.com" not in bm.launch_args()[0]
    assert "EXCLUDE www.google.com" in bm.launch_args(captcha_hosts())[0]
    fx = _bm("http://127.0.0.1:1")
    assert "google" not in fx.launch_args(captcha_hosts())[0]


async def test_headless_context_ignores_the_opt_in():
    bm = _bm()
    try:
        try:
            await bm.start()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Playwright browser not available: {type(e).__name__}")
        ctx = await bm.new_context(["devfill.example"], allow_captcha_frames=True)
        assert ctx.freemyid_captcha_frames is False   # type: ignore[attr-defined]
        await ctx.close()
    finally:
        await bm.close()


# --------------------------------------------------------------------------- SEC-32 (pure)


def _snap(counts=(0,), present=(), form_left=2, url=f"{H}/optout") -> _Snap:
    return _Snap(list(counts), list(present), form_left, url)


def test_new_signal_rules():
    base = _snap(counts=(1,))
    assert new_signal(base, _snap(counts=(1,)), None) is None            # same form again
    assert new_signal(base, _snap(counts=(2,)), None) == "success_text"  # phrase is new
    assert new_signal(base, _snap(counts=(1,), form_left=0), None) == "success_text"
    assert new_signal(base, _snap(counts=(0,), form_left=0), None) is None   # help page
    assert new_signal(_snap(present=(True,)), _snap(present=(True,)), None) is None
    assert new_signal(_snap(present=(False,)), _snap(present=(True,)), None) == \
        "success_selector"
    pat = r"^/thanks"
    assert new_signal(base, _snap(counts=(1,), url=f"{H}/thanks"), pat) == "success_url"
    assert new_signal(_snap(url=f"{H}/thanks"), _snap(url=f"{H}/thanks"), pat) is None
    assert new_signal(base, _snap(url=f"{H}/optout#thanks"), r"thanks") is None


# --------------------------------------------------------------------------- page fixture


@pytest.fixture
async def page():
    from playwright.async_api import Error as PWError
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        try:
            b = await p.chromium.launch(headless=True)
        except PWError as e:
            pytest.skip(f"Playwright Chromium not available: {type(e).__name__}")
        ctx = await b.new_context()
        await ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith(
            ("about:", "data:")) else r.continue_())
        pg = await ctx.new_page()
        yield pg
        await b.close()


# --------------------------------------------------------------------------- SEC-30


async def test_sec30_more_honeypots(page):
    await page.set_content("""<html><body style="margin:0"><form>
      <label>First name <input id=real name=fn></label>
      <div style="position:relative">
        <label>Last name <input id=covered name=ln></label>
        <div style="position:absolute;inset:0;background:#fff"></div></div>
      <label style="clip-path:inset(50%);position:absolute">Email
        <input id=clipped name=em></label>
      <label>Website <input id=web name=site></label>
      <div style="position:fixed;top:-500px"><label>Your name <input id=above></label></div>
      <div style="height:60px;overflow:auto"><div style="height:400px"></div>
        <label>Profile URL <input id=scrolled name=purl></label></div>
    </form></body></html>""")
    await filler.fill_page(page, VALUES)
    assert await page.input_value("#real") == "Jane"
    for sel in ("#covered", "#clipped", "#web", "#above"):
        assert await page.input_value(sel) == "", sel
    # a box inside a scroll box is not a honeypot: it is scrolled into view and filled
    assert await page.input_value("#scrolled") == VALUES["listing_url"]
    assert await page.evaluate("[window.scrollX, window.scrollY]") == [0, 0]


async def test_long_page_box_below_the_fold_still_filled(page):
    await page.set_content("""<html><body><div style="height:3000px">intro</div>
      <form><label>First name <input id=fn></label></form></body></html>""")
    rep = await filler.fill_page(page, VALUES)
    assert rep.filled == ["first_name"] and await page.input_value("#fn") == "Jane"


# --------------------------------------------------------------------------- SEC-31 / 33 / 34


async def test_sec31_robot_and_marketing_wording_never_ticked(page):
    await page.set_content("""<html><body><form>
      <label><input type=checkbox id=ok name=consent> I am the person in this listing</label>
      <input type=checkbox id=a1 name=c1 aria-label="Verify you are a person">
      <input type=checkbox id=a2 name=human_ok>
      <input type=checkbox id=a3 name=c3 aria-labelledby=t3><span id=t3>Security check</span>
      <input type=checkbox id=a4 name=c4><label for=a4>Yes, send me the newsletter</label>
      <label><input type=checkbox id=a5 name=c5> Share with our partners</label>
      <label><input type=checkbox id=a6 name=bot> Continue</label>
    </form></body></html>""")
    sels = ["input#ok", "input[type=checkbox]"]
    n = await filler.tick_safe_checkboxes(page, sels)
    assert n == 1 and await page.is_checked("#ok")
    for i in range(1, 7):
        assert not await page.is_checked(f"#a{i}"), i


async def test_safe_checkbox_selector_cap(page):
    await page.set_content("""<html><body><form>""" + "".join(
        f"<label><input type=checkbox id=c{i}> I agree {i}</label>" for i in range(5)) +
        "</form></body></html>")
    n = await filler.tick_safe_checkboxes(page, [f"input#c{i}" for i in range(5)])
    assert n == 3                       # at most 3 registry selectors are used


def test_sec34_forged_scan_keys_are_refused():
    class _P:
        def locator(self, sel: str) -> str:
            return sel
    for key, tag in (('f0"], *, [x="', "input"), ("x1", "input"), ("f1", "button"),
                     ("f" + "9" * 7, "input")):
        assert filler._locator_for(_P(), filler.Control(key=key, tag=tag)) is None  # type: ignore[arg-type]
    assert filler._locator_for(_P(), filler.Control(key="f12", tag="input")) == \
        'input[data-freemyid-field="f12"]'  # type: ignore[arg-type]


async def test_sec34_marker_moved_onto_captcha_box_is_not_filled(page):
    # A hostile page moves our marker onto a CAPTCHA response box after the scan.
    await page.set_content("""<html><body><form>
      <label>First name <input id=fn name=fn></label>
      <div class="g-recaptcha"><input id=resp name=resp style="width:200px"></div>
    </form><script>
      const real = Element.prototype.setAttribute;
      Element.prototype.setAttribute = function (k, v) {
        if (k === 'data-freemyid-field' && this.id === 'fn') {
          return real.call(document.getElementById('resp'), k, v);
        }
        return real.call(this, k, v);
      };
    </script></body></html>""")
    await filler.fill_page(page, VALUES)
    assert await page.input_value("#resp") == ""


# --------------------------------------------------------------------------- flows


def _mailbox() -> MailboxConfig:
    return MailboxConfig(address="removals.testperson@example.com",
                         imap_host="imap.example.com", smtp_host="smtp.example.com",
                         username="removals.testperson@example.com")


def _broker(bid: str, page: str, **kw: Any) -> Broker:
    d: dict[str, Any] = {
        "id": bid, "name": f"Dev Fill {bid}", "url": f"{H}/", "category": "people_search",
        "domains": ["devfill.example"], "opt_out_url": f"{H}/{page}", "method": "web_form",
        "required_fields": [F.FIRST_NAME, F.LAST_NAME, F.FULL_NAME, F.EMAIL, F.LISTING_URL]}
    d.update(kw)
    return Broker(**d)


def _profile(store):
    p = make_profile(mailbox=_mailbox())
    store.save_profile(p)
    return p


def _listing(p, broker_id: str) -> Listing:
    return Listing(profile_id=p.id, broker_id=broker_id, url=f"{H}/p/jane-testperson-il",
                   match_score=100, match_level=MatchLevel.CONFIRMED,
                   shown_fields=[F.FULL_NAME, F.LISTING_URL])


async def test_ajax_success_on_same_page_counts(store):
    b = _broker("ff_ajax", "ajax", success_text=["your request has been received"])
    p = _profile(store)
    store.save_listing(_listing(p, b.id))

    async def person(pg):
        await pg.click("#send")

    with fixture_server():
        res = await fill_for_me(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=15, on_ready=person, close_delay_s=0)
    if res.reason == "browser_unavailable":
        pytest.skip("needs the Playwright browser")
    assert res.status == "submitted" and res.reason == "success_text", res
    evs = store.list_evidence(p.id, b.id)
    assert sorted(e.caption for e in evs) == ["confirmation page", "form as sent"]


async def test_late_text_plus_unrelated_post_is_not_success(store):
    b = _broker("ff_late", "late", success_text=["your request has been received"])
    p = _profile(store)
    store.save_listing(_listing(p, b.id))

    async def person(pg):
        await pg.wait_for_selector("#faq p")        # FAQ text rendered (no submit yet)
        await pg.click("#draft")                     # a POST, but nothing new appears

    with fixture_server():
        res = await fill_for_me(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=3, on_ready=person, close_delay_s=0)
    if res.reason == "browser_unavailable":
        pytest.skip("needs the Playwright browser")
    assert res.status == "fallback" and res.reason == "timeout" and res.submit_seen, res
    assert not store.list_requests(p.id)


async def test_covered_by_child_uses_listing_found_on_the_child(store):
    parent = _broker("ff_parent", "labels", success_text=["your request has been received"])
    child = _broker("ff_child", "labels", covered_by="ff_parent")
    p = _profile(store)
    li = _listing(p, child.id)                       # recorded by the listing finder (D10)
    store.save_listing(li)
    got: dict[str, str] = {}

    async def person(pg):
        got["url"] = await pg.input_value("#pu")
        await pg.click("#send")

    with fixture_server():
        res = await fill_for_me(store, p.id, child.id, registry=_registry(parent, child),
                                headed=False, timeout_s=15, on_ready=person, close_delay_s=0)
    if res.reason == "browser_unavailable":
        pytest.skip("needs the Playwright browser")
    assert res.broker_id == "ff_parent" and res.ok, res
    assert got["url"] == li.url and "listing_url" in res.filled
    assert store.get_request(res.request_id).listing_ids == [li.id]
