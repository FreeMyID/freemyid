"""Offline failure outcomes for the interactive, single-broker listing finder."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from playwright.async_api import TimeoutError as PageTimeoutError

from freemyid import config
from freemyid.engine import listing_finder
from freemyid.models import Broker, Registry


@dataclass
class FakeResponse:
    status: int = 200
    html: str = "<html><body>synthetic results</body></html>"
    error: Exception | None = None

    async def text(self) -> str:
        # Like Playwright: strict UTF-8 decode of body().
        return (await self.body()).decode("utf-8")

    async def body(self) -> bytes:
        # Playwright's Response.body(); the finder reads raw bytes (in-house review).
        if self.error:
            raise self.error
        return self.html.encode("latin-1")


class FakePage:
    def __init__(self, selector_error: Exception | None = None) -> None:
        self.selector_error = selector_error
        self.main_frame = object()

    def is_closed(self) -> bool:
        return False

    async def wait_for_selector(self, *_args: Any, **_kw: Any) -> None:
        if self.selector_error:
            raise self.selector_error

    async def evaluate(self, *_args: Any) -> None:
        pass


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.pages = [page]
        self.callback: Callable[..., Any] | None = None
        self.closed = False

    async def expose_binding(self, _binding: str, callback: Callable[..., Any]) -> None:
        self.callback = callback

    async def add_init_script(self, _script: str) -> None:
        pass

    async def new_page(self) -> FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, response: FakeResponse | None = None,
                 error: Exception | None = None, selector_error: Exception | None = None,
                 close_error: bool = False, start_error: bool = False) -> None:
        self.response = response or FakeResponse()
        self.error = error
        self.context = FakeContext(FakePage(selector_error))
        self.close_error = close_error
        self.start_error = start_error
        self.closed = False

    async def start(self) -> None:
        if self.start_error:
            raise RuntimeError("synthetic startup failure")

    async def new_context(self, *_args: Any, **_kw: Any) -> FakeContext:
        return self.context

    async def goto(self, *_args: Any, **_kw: Any) -> FakeResponse:
        if self.error:
            raise self.error
        return self.response

    def check_escaped(self, _page: FakePage) -> None:
        pass

    async def close(self) -> None:
        self.closed = True
        if self.close_error:
            raise RuntimeError("synthetic cleanup failure")


@pytest.fixture
def finder_inputs(store: Any, profile: Any) -> tuple[Any, Registry]:
    store.save_profile(profile)
    broker = Broker(
        id="synthetic_finder", name="Synthetic finder", url="https://finder.example/search",
        domains=["finder.example"], category="people_search", method="web_form",
        opt_out_url="https://finder.example/remove", required_fields=["full_name", "email"],
        search_url_pattern="https://finder.example/search?first={first}&last={last}",
    )
    registry = Registry(version="test", updated=date(2026, 11, 10), brokers=[broker])
    return profile, registry


@pytest.mark.parametrize("browser,reason", [
    (FakeBrowser(error=TimeoutError("Jane Q Testperson https://finder.example/private")),
     "timeout"),
    (FakeBrowser(error=PageTimeoutError("synthetic page text")), "timeout"),
    (FakeBrowser(response=FakeResponse(status=403)), "http_403"),
    (FakeBrowser(response=FakeResponse(status=429)), "http_429"),
    (FakeBrowser(response=FakeResponse(status=500)), "http_error"),
    (FakeBrowser(response=FakeResponse(status=404)), "http_error"),
    (FakeBrowser(response=FakeResponse(html="")), "empty_body"),
    (FakeBrowser(response=FakeResponse(html=" \n\t")), "empty_body"),
    (FakeBrowser(selector_error=UnicodeError("synthetic bad encoding")),
     "invalid_encoding"),
    (FakeBrowser(error=RuntimeError("synthetic truncated transfer")), "page_error"),
    (FakeBrowser(selector_error=PageTimeoutError("synthetic missing selector")), "timeout"),
    (FakeBrowser(error=type("SyntheticPrivatePageText", (Exception,), {})("private")),
     "page_error"),
])
async def test_listing_finder_failure_outcomes(
    store: Any, finder_inputs: tuple[Any, Registry], browser: FakeBrowser, reason: str,
) -> None:
    profile, registry = finder_inputs
    # Headless: HTTP 403/429 fall back at once (a visible window lets the person try).
    result = await listing_finder.find_listing(
        store, profile.id, "synthetic_finder", registry=registry, browser=browser,
        cfg=config.Config(), timeout_s=1, close_delay_s=0, headed=False,
    )
    assert result.status == "fallback" and result.reason == reason
    assert not result.ok and result.todo_id
    assert result.listing_id is None and result.listing_url is None
    assert not store.list_listings(profile.id, "synthetic_finder")
    assert browser.context.closed
    events = [e for e in store.events(profile.id) if e.action == "listing_finder_fallback"]
    assert events[-1].detail["reason"] == reason
    assert len(reason) <= 40 and reason.replace("_", "").isalnum()


async def test_listing_finder_failing_middle_session_does_not_stop_next(
    store: Any, finder_inputs: tuple[Any, Registry],
) -> None:
    """Three independent existing-API calls; this is not a new multi-broker scanner."""
    profile, registry = finder_inputs
    results = []
    for status in (403, 500, 429):
        result = await listing_finder.find_listing(
            store, profile.id, "synthetic_finder", registry=registry,
            browser=FakeBrowser(response=FakeResponse(status=status)), cfg=config.Config(),
            timeout_s=1, headed=False,
        )
        results.append(result)
    assert [r.reason for r in results] == ["http_403", "http_error", "http_429"]
    assert all(r.status == "fallback" for r in results)


@pytest.mark.parametrize("start_error", [False, True])
async def test_listing_finder_cleanup_failure_preserves_outcome(
    store: Any, finder_inputs: tuple[Any, Registry], monkeypatch: pytest.MonkeyPatch,
    start_error: bool,
) -> None:
    from freemyid.engine import browser as browser_module

    profile, registry = finder_inputs
    fake = FakeBrowser(response=FakeResponse(status=429), close_error=True,
                       start_error=start_error)
    monkeypatch.setattr(browser_module, "BrowserManager", lambda *_a, **_kw: fake)
    result = await listing_finder.find_listing(
        store, profile.id, "synthetic_finder", registry=registry, cfg=config.Config(),
        timeout_s=1, headed=False,
    )
    assert result.status == "fallback"
    assert result.reason == ("browser_unavailable" if start_error else "http_429")
    assert fake.closed


# In-house review (WO-273): SEC-36 lets the person get past a robot check in a VISIBLE
# window (never solved by us). A 403/429/503 there must not close the window at once.
@pytest.mark.parametrize("status", [403, 429, 503])
async def test_headed_window_stays_open_on_robot_check_status(
    store: Any, finder_inputs: tuple[Any, Registry], status: int,
) -> None:
    profile, registry = finder_inputs
    result = await listing_finder.find_listing(
        store, profile.id, "synthetic_finder", registry=registry,
        browser=FakeBrowser(response=FakeResponse(status=status)), cfg=config.Config(),
        timeout_s=1, close_delay_s=0, headed=True,
    )
    # The person was given the window; nobody clicked, so it ends by timing out.
    assert result.status == "fallback" and result.reason == "timeout"


@pytest.mark.parametrize("status", [404, 500])
async def test_headed_window_still_falls_back_on_other_http_errors(
    store: Any, finder_inputs: tuple[Any, Registry], status: int,
) -> None:
    profile, registry = finder_inputs
    result = await listing_finder.find_listing(
        store, profile.id, "synthetic_finder", registry=registry,
        browser=FakeBrowser(response=FakeResponse(status=status)), cfg=config.Config(),
        timeout_s=1, close_delay_s=0, headed=True,
    )
    assert result.reason == "http_error"


async def test_legacy_encoded_page_is_not_rejected(
    store: Any, finder_inputs: tuple[Any, Registry],
) -> None:
    """Response.text() is strict UTF-8; a Latin-1 page must still reach the person."""
    profile, registry = finder_inputs
    response = FakeResponse(html="<html><body>Caf\xe9 r\xe9sultats</body></html>")
    result = await listing_finder.find_listing(
        store, profile.id, "synthetic_finder", registry=registry,
        browser=FakeBrowser(response=response), cfg=config.Config(),
        timeout_s=1, close_delay_s=0, headed=False,
    )
    assert result.reason == "timeout"


async def test_unavailable_response_body_does_not_close_the_window(
    store: Any, finder_inputs: tuple[Any, Registry],
) -> None:
    class NoBody(FakeResponse):
        async def body(self) -> bytes:
            raise RuntimeError("synthetic: body not kept")

    profile, registry = finder_inputs
    result = await listing_finder.find_listing(
        store, profile.id, "synthetic_finder", registry=registry,
        browser=FakeBrowser(response=NoBody()), cfg=config.Config(),
        timeout_s=1, close_delay_s=0, headed=False,
    )
    assert result.reason == "timeout"
