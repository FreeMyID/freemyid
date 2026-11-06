"""Playwright browser wrapper: allowlisted, polite, honest. Never bypasses bot protection.

* System Chrome first (`config.browser_channel`), then Playwright's bundled Chromium.
* Every request goes through a route handler: anything whose host is not in the broker's
  narrow allowlist (and the global NetPolicy) is aborted.
* Honest user agent: the browser's real UA + `config.user_agent_suffix`.
* Random delay min_delay_s..max_delay_s before each navigation, per-domain rate limit,
  retries with exponential backoff.
* CAPTCHA / challenge pages are DETECTED (`detect_challenge`) and handed to a human.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from .. import config as cfgmod
from ..netpolicy import NetPolicy, _host_ok

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
                 cfg: cfgmod.Config | None = None) -> None:
        self.cfg = cfg or cfgmod.load()
        self.netpolicy = netpolicy
        self.headless = self.cfg.headless if headless is None else headless
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ua: str | None = None
        self._headed: list[Browser] = []
        self.rate = RateLimiter(self.cfg.min_delay_s)
        self.fast = self.cfg.max_delay_s <= 0      # dev/test mode: no sleeps

    async def _ensure(self) -> Browser:
        if self._browser:
            return self._browser
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._launch(self.headless)
        return self._browser

    async def _launch(self, headless: bool) -> Browser:
        assert self._pw
        chan = self.cfg.browser_channel
        if chan:
            try:
                return await self._pw.chromium.launch(channel=chan, headless=headless)
            except Exception as e:  # noqa: BLE001 - fall back to bundled chromium
                log.info("system browser channel %s unavailable (%s); using bundled",
                         chan, type(e).__name__)
        return await self._pw.chromium.launch(headless=headless)

    async def user_agent(self) -> str:
        if self._ua is None:
            b = await self._ensure()
            ctx = await b.new_context()
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
        host = urlsplit(url).hostname or ""
        return bool(host) and _host_ok(host, hosts) and self.netpolicy.is_allowed(host)

    async def new_context(self, domains: list[str], extra: list[str] | None = None,
                          storage_state: Any = None, headed: bool = False) -> BrowserContext:
        hosts = self.allowed_hosts(domains, extra)
        if headed:
            await self._ensure()
            b = await self._launch(False)
            self._headed.append(b)
        else:
            b = await self._ensure()
        ctx = await b.new_context(user_agent=await self.user_agent(),
                                  storage_state=storage_state, locale="en-US")
        blocked: list[str] = []

        async def _route(route: Any) -> None:
            url = route.request.url
            if self.url_allowed(url, hosts):
                await route.continue_()
            else:
                blocked.append(urlsplit(url).hostname or "?")
                await route.abort("blockedbyclient")

        await ctx.route("**/*", _route)
        ctx.vanish_blocked = blocked  # type: ignore[attr-defined]
        ctx.vanish_hosts = hosts      # type: ignore[attr-defined]
        return ctx

    async def polite_delay(self, host: str) -> None:
        if self.fast:
            return
        await self.rate.wait(host)
        await asyncio.sleep(random.uniform(self.cfg.min_delay_s, self.cfg.max_delay_s))

    async def goto(self, page: Page, url: str, *, check_challenge: bool = True,
                   timeout_ms: int = 30000) -> Response | None:
        hosts: set[str] = getattr(page.context, "vanish_hosts", set())
        if not self.url_allowed(url, hosts):
            raise BlockedByPolicy(urlsplit(url).hostname or "?")
        host = urlsplit(url).hostname or ""
        last: Exception | None = None
        for attempt in range(max(1, self.cfg.max_retries)):
            await self.polite_delay(host)
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if resp is not None and resp.status in (500, 502, 504) and \
                        attempt + 1 < self.cfg.max_retries:
                    raise RuntimeError(f"http_{resp.status}")
                if check_challenge:
                    await self.raise_if_challenge(page, resp.status if resp else None)
                return resp
            except ChallengeEncountered:
                raise
            except Exception as e:  # noqa: BLE001
                last = e
                if not self.fast:
                    await asyncio.sleep(min(60.0, 2.0 ** (attempt + 1)))
        assert last is not None
        raise last

    async def raise_if_challenge(self, page: Page, status: int | None = None) -> None:
        kind = await page_challenge(page, status)
        if kind:
            raise ChallengeEncountered(kind, page.url)

    async def close(self) -> None:
        try:
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
