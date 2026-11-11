"""Playwright browser wrapper: allowlisted, polite, honest. Never bypasses bot protection.

* System browser first: on Windows Microsoft Edge (`channel="msedge"`, on every Windows
  10/11 machine) then `config.browser_channel`; elsewhere `config.browser_channel`; then
  Playwright's bundled Chromium. FREEMYID_BROWSER_EXECUTABLE overrides (dev machines).
* Dev fixture mode (`fixture_base`): every allowlisted request is answered by the local
  fixture server (http://127.0.0.1:<port>/<host><path>); nothing reaches the internet.
* Every request goes through a route handler: anything whose host is not in the broker's
  narrow allowlist (and the global NetPolicy) is aborted.
* SEC-16: Playwright routes only see the first URL of a redirect chain, and service workers
  bypass routes. So: service workers are blocked; every launch gets a Chromium
  `--host-resolver-rules` floor (off-list DNS names never resolve, even on a redirect hop);
  a request listener records off-list redirect hops / main-frame navigations and `goto` /
  `check_escaped` raise BlockedByPolicy (never retried). Residual gap: IP-literal and
  loopback redirect targets bypass the resolver floor; they are detected (BlockedByPolicy)
  but the request itself has already been sent. Full fix = allowlisting proxy (SEC-16 A).
* SEC-36: the headed human-in-the-loop windows (D9 fill_for_me, D10 listing finder) may
  opt in with `new_context(..., headed=True, allow_captcha_frames=True)`. Only then the
  CAPTCHA widget hosts (`netpolicy.captcha_subresource_allowed` / `captcha_hosts`) load as
  sub-frames / sub-resources (never a main-frame navigation, never headless, never in dev
  fixture mode), so the person can tick the robot box themselves. Free My ID never touches it.
* WO-612 search session: `persistent_context` opens ONE headed window of the installed
  browser on a dedicated Free My ID profile folder (never the person's everyday profile), so
  cookies a person earned by passing a site's check persist. "background" places the window
  off-screen (no focus steal) for scheduled runs; "visible" is the attended batch. Never
  headless (tests in dev fixture mode only). `retarget` swaps the allowlist per broker.
* Honest user agent: the browser's real UA + `config.user_agent_suffix`.
* Random delay min_delay_s..max_delay_s before each navigation, per-domain rate limit,
  retries with exponential backoff.
* CAPTCHA / challenge pages are DETECTED (`detect_challenge`) and handed to a human.
"""
from __future__ import annotations

import asyncio
import glob
import ipaddress
import logging
import os
import random
import re
import sys
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from .. import config as cfgmod
from ..netpolicy import (
    LOOPBACK_HOSTS,
    NetPolicy,
    _host_ok,
    captcha_hosts,
    captcha_subresource_allowed,
    host_of,
)

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright, Response

log = logging.getLogger(__name__)

_LOCAL_SCHEMES = ("data:", "about:", "blob:")

_CHALLENGE_FRAME = re.compile(
    r"(google\.com/recaptcha|recaptcha\.net|hcaptcha\.com|challenges\.cloudflare\.com|"
    r"turnstile|arkoselabs|funcaptcha|geo\.captcha-delivery\.com|perimeterx|px-captcha)", re.IGNORECASE)
_CHALLENGE_MARKUP = re.compile(
    r"(class=[\"'][^\"']*(g-recaptcha|h-captcha|cf-turnstile)|id=[\"'](challenge-form|"
    r"cf-challenge-running|px-captcha)[\"']|cf-chl-|data-sitekey=)", re.IGNORECASE)
_CHALLENGE_TEXT = re.compile(
    r"(verify (that )?you are (a )?human|are you a robot|checking your browser|"
    r"please complete the security check|press (and|&) hold|unusual traffic|"
    r"access denied|attention required)", re.IGNORECASE)


class ChallengeEncountered(Exception):
    """A CAPTCHA / bot challenge / block page. `kind` is a short PII-free label."""

    def __init__(self, kind: str, url: str = "") -> None:
        super().__init__(kind)
        self.kind = kind
        self.url = url


class BlockedByPolicy(Exception):
    """Navigation target is not on the allowlist."""


def detect_challenge(html: str, frame_urls: list[str] | None = None,
                     status: int | None = None) -> str | None:
    """Pure function: return a challenge label or None. Tested against fixtures."""
    for u in frame_urls or []:
        if _CHALLENGE_FRAME.search(u):
            return "captcha_frame"
    if _CHALLENGE_FRAME.search(html) and re.search(r"<iframe|<script", html, re.IGNORECASE):
        return "captcha_frame"
    if _CHALLENGE_MARKUP.search(html):
        return "captcha_widget"
    # body text check (strip tags crudely; keep it cheap)
    text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    if _CHALLENGE_TEXT.search(text):
        return "challenge_text"
    if status in (403, 429, 503):
        return f"http_{status}"
    return None


def channel_candidates(configured: str | None, platform: str | None = None) -> list[str]:
    """Browser channels to try, in order (PLAN_V1 D1: Edge on Windows, no download)."""
    platform = platform or sys.platform
    out: list[str] = []
    if platform == "win32":
        out.append("msedge")
    if configured and configured not in out:
        out.append(configured)
    return out


def _cached_headless_shell() -> str | None:
    """Newest Playwright headless shell in the user cache (dev fixture runs only)."""
    pat = os.path.expanduser(
        "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")
    found = sorted(glob.glob(pat))
    return found[-1] if found else None


def fixture_url(base: str, url: str) -> str:
    """https://host/path?q -> <base>/host/path?q (dev fixture server)."""
    sp = urlsplit(url)
    path = sp.path or "/"
    return f"{base.rstrip('/')}/{sp.hostname}{path}" + (f"?{sp.query}" if sp.query else "")


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def host_resolver_rules(allowed: set[str], fixture_mode: bool = False) -> str:
    """Chromium `--host-resolver-rules` value: every DNS name fails unless allowlisted.

    Fixture mode only needs the local fixture server (broker hosts are answered by routes).
    The rules also apply to IP literals (verified: an unlisted 127.0.0.1 fails with
    ERR_NAME_NOT_RESOLVED), so allowlisted IPs are excluded without a `*.` wildcard.
    """
    hosts = set(LOOPBACK_HOSTS) if fixture_mode else set(allowed)
    rules = ["MAP * ~NOTFOUND"]
    for h in sorted(hosts):
        if not h or any(c in h for c in ", "):
            continue
        if _is_ip(h):
            rules.append(f"EXCLUDE [{h}]" if ":" in h else f"EXCLUDE {h}")
        else:
            rules += [f"EXCLUDE {h}", f"EXCLUDE *.{h}"]
    return ", ".join(rules)


class RateLimiter:
    """Minimum spacing between requests to the same domain (per process)."""

    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = min_interval_s
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, host: str) -> None:
        async with self._lock:
            now = time.monotonic()
            nxt = self._last.get(host, 0.0) + self.min_interval_s
            delay = max(0.0, nxt - now)
            self._last[host] = now + delay
        if delay:
            await asyncio.sleep(delay)


class BrowserManager:
    """Lazily launched, shared by all brokers in one run. One context per broker."""

    def __init__(self, netpolicy: NetPolicy, *, headless: bool | None = None,
                 cfg: cfgmod.Config | None = None, fixture_base: str | None = None) -> None:
        self.cfg = cfg or cfgmod.load()
        self.fixture_base = fixture_base
        self.netpolicy = netpolicy
        self.headless = self.cfg.headless if headless is None else headless
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ua: str | None = None
        self._headed: list[Browser] = []
        self._persistent: BrowserContext | None = None
        self.rate = RateLimiter(self.cfg.min_delay_s)
        self.fast = self.cfg.max_delay_s <= 0 or bool(fixture_base)   # dev/test: no sleeps

    async def start(self) -> None:
        """Launch now (so a missing browser is detected up front).

        On failure the Playwright driver is stopped too (SEC-26: otherwise its subprocess
        transport outlives the event loop -> "Event loop is closed" warnings).
        """
        try:
            await self._ensure()
        except BaseException:
            await self.close()
            raise

    async def _ensure(self) -> Browser:
        if self._browser:
            return self._browser
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._launch(self.headless)
        return self._browser

    def launch_args(self, extra_hosts: set[str] | None = None) -> list[str]:
        """Browser-wide network floor (SEC-16 b). `extra_hosts` (the CAPTCHA widget hosts,
        SEC-36) are only ever passed for a headed fill/finder window; never in fixture mode."""
        allowed = set(self.netpolicy.allowed)
        if extra_hosts and not self.fixture_base:
            allowed |= extra_hosts
        rules = host_resolver_rules(allowed, bool(self.fixture_base))
        return [f"--host-resolver-rules={rules}"]

    async def _launch(self, headless: bool, extra_hosts: set[str] | None = None) -> Browser:
        assert self._pw
        args = self.launch_args(extra_hosts)
        exe = os.environ.get("FREEMYID_BROWSER_EXECUTABLE")
        if exe:
            return await self._pw.chromium.launch(executable_path=exe, headless=headless,
                                                  args=args)
        for chan in channel_candidates(self.cfg.browser_channel):
            try:
                return await self._pw.chromium.launch(channel=chan, headless=headless,
                                                      args=args)
            except Exception as e:  # noqa: BLE001 - try the next one
                log.info("browser channel %s unavailable (%s)", chan, type(e).__name__)
        try:
            return await self._pw.chromium.launch(headless=headless, args=args)
        except Exception:
            shell = _cached_headless_shell() if self.fixture_base else None
            if shell is None:
                raise
            return await self._pw.chromium.launch(executable_path=shell, headless=headless,
                                                  args=args)

    async def user_agent(self) -> str:
        if self._ua is None:
            b = await self._ensure()
            ctx = await b.new_context(service_workers="block")
            pg = await ctx.new_page()
            real = await pg.evaluate("navigator.userAgent")
            await ctx.close()
            self._ua = f"{real} {self.cfg.user_agent_suffix}".strip()
        return self._ua

    def allowed_hosts(self, domains: list[str], extra: list[str] | None = None) -> set[str]:
        return self.netpolicy.for_broker(domains, extra)

    def url_allowed(self, url: str, hosts: set[str]) -> bool:
        if url.startswith(_LOCAL_SCHEMES):
            return True
        host = host_of(url)
        if not host:                      # unparseable / hostless URL -> blocked
            return False
        return _host_ok(host, hosts) and self.netpolicy.is_allowed(host)

    @staticmethod
    def _is_main_frame_navigation(req: Any) -> bool:
        """True for a top-level document load (any page, popups included). Anything we
        cannot judge (no frame, e.g. a worker) counts as one: the strict side."""
        try:
            return bool(req.is_navigation_request()) and req.frame.parent_frame is None
        except Exception:  # noqa: BLE001
            return True

    def route_decision(self, url: str, *, is_main_frame_navigation: bool, hosts: set[str],
                       allow_captcha_frames: bool = False) -> str:
        """What the route handler does with a request: "fixture" (answered by the local dev
        server), "continue", "captcha" (a CAPTCHA widget sub-resource in an opted-in headed
        window, SEC-36; continued) or "block". Pure; unit-tested with fake requests."""
        if self.url_allowed(url, hosts):
            if self.fixture_base and not url.startswith(_LOCAL_SCHEMES):
                return "fixture"
            return "continue"
        if allow_captcha_frames and not self.fixture_base and captcha_subresource_allowed(
                url, is_main_frame_navigation=is_main_frame_navigation):
            return "captcha"
        return "block"

    def is_escape(self, req: Any, hosts: set[str], allow_captcha_frames: bool = False) -> bool:
        """Off-list redirect hop (any frame) or off-list main-frame navigation (SEC-16).
        In an opted-in headed window a CAPTCHA sub-frame / sub-resource is not an escape,
        but a main-frame navigation to a CAPTCHA host still is (SEC-36)."""
        try:
            hop = req.redirected_from is not None
        except Exception:  # noqa: BLE001
            hop = True
        nav = self._is_main_frame_navigation(req)
        if not (hop or nav) or self.url_allowed(req.url, hosts):
            return False
        return not (allow_captcha_frames and not nav and not self.fixture_base and
                    captcha_subresource_allowed(req.url, is_main_frame_navigation=False))

    def make_route_handler(self, hosts: set[str], blocked: list[str],
                           allow_captcha_frames: bool = False) -> Callable[[Any], Awaitable[None]]:
        async def _route(route: Any) -> None:
            req = route.request
            url = req.url
            what = self.route_decision(
                url, is_main_frame_navigation=self._is_main_frame_navigation(req), hosts=hosts,
                allow_captcha_frames=allow_captcha_frames)
            if what == "fixture":
                try:
                    resp = await route.fetch(url=fixture_url(str(self.fixture_base), url),
                                             max_redirects=0)
                    await route.fulfill(response=resp)
                except Exception:  # noqa: BLE001
                    await route.abort("failed")
            elif what in ("continue", "captcha"):
                await route.continue_()
            else:
                blocked.append(host_of(url) or "?")
                await route.abort("blockedbyclient")
        return _route

    async def new_context(self, domains: list[str], extra: list[str] | None = None,
                          storage_state: Any = None, headed: bool = False,
                          allow_captcha_frames: bool = False) -> BrowserContext:
        """One context per broker. `allow_captcha_frames` (default False) is honoured only
        for a headed window (the person is there to tick the box); ignored otherwise."""
        hosts = self.allowed_hosts(domains, extra)
        captcha_ok = bool(allow_captcha_frames and headed and not self.fixture_base)
        if allow_captcha_frames and not captcha_ok:
            log.info("allow_captcha_frames ignored (headless or fixture mode)")
        if headed:
            await self._ensure()
            b = await self._launch(False, captcha_hosts() if captcha_ok else None)
            self._headed.append(b)
        else:
            b = await self._ensure()
        ctx = await b.new_context(user_agent=await self.user_agent(),
                                  storage_state=storage_state, locale="en-US",
                                  service_workers="block")
        blocked: list[str] = []
        escaped: list[str] = []

        def _on_request(req: Any) -> None:
            # Redirect hops never reach the route handler (SEC-16): record off-list ones.
            if self.is_escape(req, hosts, captcha_ok):
                escaped.append(host_of(req.url) or "?")

        ctx.on("request", _on_request)
        await ctx.route("**/*", self.make_route_handler(hosts, blocked, captcha_ok))
        ctx.freemyid_blocked = blocked  # type: ignore[attr-defined]
        ctx.freemyid_escaped = escaped  # type: ignore[attr-defined]
        ctx.freemyid_hosts = hosts      # type: ignore[attr-defined]
        ctx.freemyid_captcha_frames = captcha_ok  # type: ignore[attr-defined]
        return ctx

    #: Off-screen placement for the background window (WO-612): plain window-manager flags,
    #: nothing about the browser's identity changes.
    BACKGROUND_ARGS = ("--window-position=-32000,-32000", "--window-size=1280,900",
                       "--no-first-run", "--no-default-browser-check")
    #: The attended window: an explicit on-screen position (SEC-WO612-7), so a profile or
    #: OS that remembered the off-screen spot can never hide the window the person needs.
    VISIBLE_ARGS = ("--window-position=80,60", "--window-size=1280,900", "--no-first-run",
                    "--no-default-browser-check")

    def persistent_args(self, window: str) -> list[str]:
        """Launch flags for the search-session window: the SEC-16 network floor (+ the
        CAPTCHA widget hosts, SEC-36: the window is headed so a person can tick the box)
        and window placement only."""
        extra = captcha_hosts() if not self.fixture_base else None
        place = self.BACKGROUND_ARGS if window == "background" else self.VISIBLE_ARGS
        return [*self.launch_args(extra), *place]

    def persistent_launch_kwargs(self, window: str, test_headless: bool = False
                                 ) -> dict[str, Any]:
        """Keyword arguments for `launch_persistent_context` (pure; unit-tested)."""
        if window not in ("background", "visible"):
            raise ValueError(window)
        if test_headless and not self.fixture_base:
            raise ValueError("headless search sessions are for dev fixture tests only")
        return {"headless": bool(test_headless), "args": self.persistent_args(window),
                "locale": "en-US", "service_workers": "block",
                "no_viewport": not test_headless}

    async def persistent_context(self, user_data_dir: str, *, window: str = "background",
                                 test_headless: bool = False) -> BrowserContext:
        """WO-612: one headed window of the installed browser on a dedicated profile folder.

        `window` is "background" (off-screen, scheduled runs) or "visible" (attended batch).
        `test_headless` exists only for CI in dev fixture mode; anywhere else it raises.
        The allowlist starts empty (everything blocked) until `retarget` names a broker."""
        kw = self.persistent_launch_kwargs(window, test_headless)
        from playwright.async_api import async_playwright
        if self._pw is None:
            self._pw = await async_playwright().start()
        launch = self._pw.chromium.launch_persistent_context
        exe = os.environ.get("FREEMYID_BROWSER_EXECUTABLE")
        ctx: BrowserContext | None = None
        if exe:
            ctx = await launch(user_data_dir, executable_path=exe, **kw)
        else:
            for chan in channel_candidates(self.cfg.browser_channel):
                try:
                    ctx = await launch(user_data_dir, channel=chan, **kw)
                    break
                except Exception as e:  # noqa: BLE001 - try the next one
                    log.info("browser channel %s unavailable (%s)", chan, type(e).__name__)
            if ctx is None:
                try:
                    ctx = await launch(user_data_dir, **kw)
                except Exception:
                    shell = _cached_headless_shell() if test_headless else None
                    if shell is None:
                        raise
                    ctx = await launch(user_data_dir, executable_path=shell, **kw)
        self._persistent = ctx
        captcha_ok = not self.fixture_base and not test_headless
        hosts: set[str] = set()
        blocked: list[str] = []
        escaped: list[str] = []

        def _on_request(req: Any) -> None:
            if self.is_escape(req, hosts, captcha_ok):
                escaped.append(host_of(req.url) or "?")

        ctx.on("request", _on_request)
        await ctx.route("**/*", self.make_route_handler(hosts, blocked, captcha_ok))
        ctx.freemyid_blocked = blocked  # type: ignore[attr-defined]
        ctx.freemyid_escaped = escaped  # type: ignore[attr-defined]
        ctx.freemyid_hosts = hosts      # type: ignore[attr-defined]
        ctx.freemyid_captcha_frames = captcha_ok  # type: ignore[attr-defined]
        # Honest UA: this browser's own UA string plus the suffix, read on a blank page.
        probe = ctx.pages[0] if ctx.pages else await ctx.new_page()
        real = await probe.evaluate("navigator.userAgent")
        self._ua = f"{real} {self.cfg.user_agent_suffix}".strip()
        await ctx.set_extra_http_headers({"User-Agent": self._ua})
        return ctx

    def retarget(self, ctx: BrowserContext, domains: list[str],
                 extra: list[str] | None = None) -> list[str]:
        """Point the session window's allowlist at one broker, in place (the route handler
        and request listener hold these objects). Clears the per-broker escape record.

        Returns the off-allowlist hosts the previous site tried to reach since its last
        check (SEC-WO612-5) so the caller can mark that site BLOCKED_BY_POLICY; they are
        never silently dropped (logged here as well)."""
        dropped = list(ctx.freemyid_escaped)  # type: ignore[attr-defined]
        if dropped:
            log.warning("search window: the previous site tried to leave the allowlist "
                        "(%d request(s)); recorded as blocked_by_policy", len(dropped))
        hosts: set[str] = ctx.freemyid_hosts  # type: ignore[attr-defined]
        hosts.clear()
        hosts.update(self.allowed_hosts(domains, extra))
        ctx.freemyid_escaped.clear()  # type: ignore[attr-defined]
        ctx.freemyid_blocked.clear()  # type: ignore[attr-defined]
        return dropped

    async def polite_delay(self, host: str) -> None:
        if self.fast:
            return
        await self.rate.wait(host)
        await asyncio.sleep(random.uniform(self.cfg.min_delay_s, self.cfg.max_delay_s))

    def escaped(self, page: Page) -> str | None:
        """Off-list host this page reached or tried to reach (redirect hop / navigation)."""
        hosts: set[str] = getattr(page.context, "freemyid_hosts", set())
        esc: list[str] = getattr(page.context, "freemyid_escaped", [])
        if esc:
            return esc[0]
        if not self.url_allowed(page.url, hosts):
            return host_of(page.url) or "?"
        return None

    def check_escaped(self, page: Page) -> None:
        """Raise BlockedByPolicy if the page left the allowlist. Call after every
        navigation, click or submit."""
        h = self.escaped(page)
        if h is not None:
            raise BlockedByPolicy(h)

    async def goto(self, page: Page, url: str, *, check_challenge: bool = True,
                   timeout_ms: int = 30000) -> Response | None:
        hosts: set[str] = getattr(page.context, "freemyid_hosts", set())
        if not self.url_allowed(url, hosts):
            raise BlockedByPolicy(host_of(url) or "?")
        host = host_of(url) or ""
        last: Exception | None = None
        for attempt in range(max(1, self.cfg.max_retries)):
            await self.polite_delay(host)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                self.check_escaped(page)
                if resp is not None and resp.status in (500, 502, 504) and \
                        attempt + 1 < self.cfg.max_retries:
                    raise RuntimeError(f"http_{resp.status}")
                if check_challenge:
                    await self.raise_if_challenge(page, resp.status if resp else None)
                return resp
            except (ChallengeEncountered, BlockedByPolicy):
                raise
            except Exception as e:
                esc: list[str] = getattr(page.context, "freemyid_escaped", [])
                if esc:
                    raise BlockedByPolicy(esc[0]) from e
                last = e
                if not self.fast:
                    await asyncio.sleep(min(60.0, 2.0 ** (attempt + 1)))
        assert last is not None
        raise last

    async def raise_if_challenge(self, page: Page, status: int | None = None) -> None:
        kind = await page_challenge(page, status)
        if kind:
            raise ChallengeEncountered(kind, page.url)

    async def kill(self) -> None:
        """Last resort when `close` hangs (SEC-WO612-3): stop the Playwright driver, which
        ends the browser it launched. Forgets every handle."""
        pw, self._pw = self._pw, None
        self._persistent, self._browser = None, None
        self._headed.clear()
        if pw is not None:
            await pw.stop()

    async def close(self) -> None:
        try:
            if self._persistent is not None:
                ctx, self._persistent = self._persistent, None
                await ctx.close()
            for hb in self._headed:
                await hb.close()
            self._headed.clear()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        finally:
            self._browser = None
            self._pw = None


async def page_challenge(page: Page, status: int | None = None) -> str | None:
    html = await page.content()
    frames = [f.url for f in page.frames]
    return detect_challenge(html, frames, status)
