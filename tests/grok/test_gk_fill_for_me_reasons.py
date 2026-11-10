"""WO-347: why fill-for-me stopped. Fake browser only. No network, no real browser."""
from __future__ import annotations

import asyncio
import logging
import re
import socket
from datetime import date
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit

import pytest

from freemyid.config import Config
from freemyid.engine import fill_for_me as ffm
from freemyid.engine.filler import FillReport
from freemyid.models import (
    Broker,
    Listing,
    ListingState,
    MatchLevel,
    ProfileField,
    Registry,
    RequestStatus,
    TodoKind,
)
from tests.conftest import make_profile

HOST = "https://broker.example"
FORM = f"{HOST}/opt-out"
_PII = (
    "Jane", "Testperson", "Springfield", "Evergreen", "62704", "217-555",
    "jane.testperson",
)
_CODE = re.compile(r"[A-Za-z0-9_:<.-]{1,64}")
_ID = re.compile(r"[0-9a-f]{32}")


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any socket connect fails the test. Localhost is not an exception."""
    def _refuse(*_a: object, **_k: object) -> None:
        raise OSError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)


@pytest.fixture(autouse=True)
def _no_real_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    from freemyid.engine import browser as browser_mod

    def _refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("real browser")

    monkeypatch.setattr(browser_mod.BrowserManager, "__init__", _refuse)
    monkeypatch.setattr(browser_mod.BrowserManager, "start", _refuse)


@pytest.fixture(autouse=True)
def _fake_fill(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fill_page(_page: object, _values: object, timeout_ms: int = 5000) -> FillReport:
        return FillReport(filled=["full_name"], controls=[("name", "fn")])

    monkeypatch.setattr(ffm.filler, "fill_page", fill_page)
    monkeypatch.setattr(ffm, "_POLL_S", 0.01)


def _broker(bid: str) -> Broker:
    return Broker(
        id=bid, name=f"Dev Fill {bid}", url=f"{HOST}/", category="people_search",
        domains=["broker.example"], opt_out_url=FORM, method="web_form",
        required_fields=[ProfileField.FULL_NAME],
        success_text=["your request has been received"],
        steps=["Open the opt-out page with the button below.", "Press Submit yourself."],
    )


def _registry(broker: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 10), brokers=[broker])


class _Req:
    def __init__(self, page: _Page) -> None:
        self.url = page.url
        self.method = "POST"
        self.resource_type = "xhr"
        self.frame = page.main_frame

    def is_navigation_request(self) -> bool:
        return False


class _Route:
    def __init__(self, page: _Page) -> None:
        self.request = _Req(page)

    async def fallback(self) -> None:
        return None


class _Page:
    """Just enough of a page for fill_for_me's poll. No Playwright."""

    def __init__(self, mode: str, flip_to: str | None = None,
                 after_submit_to: str | None = None) -> None:
        self.mode = mode
        self.flip_to = flip_to
        self.after_submit_to = after_submit_to
        self._url = FORM
        self._count = 0
        self._snaps = 0
        self.handler: Any = None
        self.did_submit = False
        self.main_frame: _Page = self
        self.context = SimpleNamespace(freemyid_hosts={"broker.example"})

    @property
    def url(self) -> str:
        return self._url

    def is_closed(self) -> bool:
        return self.mode == "closed"

    def on(self, _event: str, _callback: object) -> None:
        return None

    async def screenshot(self, **_kw: object) -> bytes:
        return b"\x89PNG\r\n\x1a\n"

    async def evaluate(self, _js: str, arg: object = None) -> object:
        if isinstance(arg, list) and arg and arg[0] == ffm.BANNER_ID:
            self._snaps += 1
            if self.flip_to and self._snaps >= 2:
                self._url = self.flip_to
            return {"counts": [self._count], "present": [], "formLeft": 1}
        return True

    async def route(self, _pattern: str, handler: object) -> None:
        self.handler = handler


class _Ctx:
    def __init__(self, page: _Page) -> None:
        self._page = page

    async def new_page(self) -> _Page:
        return self._page

    async def close(self) -> None:
        return None


class _Browser:
    def __init__(self, page: _Page) -> None:
        self.page = page

    async def start(self) -> None:
        return None

    async def new_context(self, _domains: list[str], headed: bool = True,
                          allow_captcha_frames: bool = False) -> _Ctx:
        return _Ctx(self.page)

    async def close(self) -> None:
        return None

    async def goto(self, page: _Page, url: str, *, check_challenge: bool = True,
                   timeout_ms: int = 30000) -> None:
        page._url = url

    def check_escaped(self, _page: _Page) -> None:
        return None

    def url_allowed(self, url: str, _hosts: set[str]) -> bool:
        return urlsplit(url).hostname == "broker.example"


def _install_submit(monkeypatch: pytest.MonkeyPatch, page: _Page) -> None:
    """The person's submit lands between polls, the way a real click does."""
    real = asyncio.sleep

    async def sleep(delay: float = 0, result: object = None) -> object:
        if delay == ffm._POLL_S and page.handler is not None and not page.did_submit:
            page.did_submit = True
            await page.handler(_Route(page))
            page._count = 1
            if page.after_submit_to:
                page._url = page.after_submit_to
            await real(0)
            return result
        return await real(delay, result)

    monkeypatch.setattr(asyncio, "sleep", sleep)


def _code_like(text: str) -> bool:
    return _CODE.fullmatch(text) is not None or _ID.fullmatch(text) is not None


def _assert_value(val: object) -> None:
    if isinstance(val, bool) or val is None or isinstance(val, int):
        return
    if isinstance(val, str):
        assert _code_like(val), val
        return
    if isinstance(val, list):
        for item in val:
            _assert_value(item)
        return
    raise AssertionError(type(val))


def _assert_codes_only(store: Any, caplog: pytest.LogCaptureFixture, pid: str) -> None:
    blob = caplog.text + repr([(e.action, e.detail) for e in store.events(pid)])
    for secret in _PII:
        assert secret not in blob, secret
    assert "http" not in blob
    assert "Next step" not in caplog.text
    assert "@" not in caplog.text
    for event in store.events(pid):
        for key, val in event.detail.items():
            assert _code_like(key), key
            _assert_value(val)


async def _run(store: Any, bid: str, page: _Page, *,
               monkeypatch: pytest.MonkeyPatch | None = None) -> Any:
    if page.mode == "success" and monkeypatch is not None:
        _install_submit(monkeypatch, page)
    broker = _broker(bid)
    profile = make_profile()
    store.save_profile(profile)
    if page.mode == "success":
        store.save_listing(Listing(
            profile_id=profile.id, broker_id=broker.id, url=f"{HOST}/p/jane-testperson-il",
            match_score=95, match_level=MatchLevel.CONFIRMED,
            shown_fields=[ProfileField.FULL_NAME]))
    return await ffm.fill_for_me(
        store, profile.id, broker.id, registry=_registry(broker), browser=_Browser(page),
        headed=False, timeout_s=1, close_delay_s=0, state_laws={}, cfg=Config()), profile


@pytest.mark.parametrize("url,want", [
    (f"{HOST}/opt-out", False),
    (f"{HOST}/done", False),
    (f"{HOST}/labels", False),
    (f"{HOST}/error", True),
    (f"{HOST}/error.html", True),
    (f"{HOST}/opt-out/500", True),
    (f"{HOST}/server-error", True),
    (f"{HOST}/opt-out?error=1", True),
    (f"{HOST}/opt-out?ok=1", False),
])
def test_error_page_url(url: str, want: bool) -> None:
    assert ffm._url_is_error_page(url) is want


def test_done_page_is_not_an_error_miss() -> None:
    assert ffm._missed_on_error_page(FORM, f"{HOST}/done") is False
    assert ffm._missed_on_error_page(FORM, f"{HOST}/error") is True
    assert ffm._missed_on_error_page(f"{HOST}/error", f"{HOST}/error") is False


def test_error_type_keeps_the_generic_assisted_reason() -> None:
    assert ffm._todo_reason("error:TimeoutError") == "error"
    assert ffm._todo_reason("error_page") == "error_page"
    assert ffm._todo_reason("timeout") == "timeout"
    assert ffm._todo_reason("window_closed") == "window_closed"
    assert ffm._todo_reason("blocked") is None


def test_fallback_todo_reuses_the_card(store: Any) -> None:
    profile = make_profile()
    store.save_profile(profile)
    broker = _broker("ff_reuse")
    first = ffm._fallback_todo(store, profile, broker, [], None, "timeout")
    second = ffm._fallback_todo(store, profile, broker, [], None, "window_closed")
    todos = store.list_todos(profile.id)
    assert first == second and len(todos) == 1
    assert todos[0].body.startswith(ffm._NEXT_STEP["timeout"])
    assert ffm._NEXT_STEP["window_closed"] not in todos[0].body
    assert "Never pay." in todos[0].body


def test_generic_error_todo_is_unchanged(store: Any) -> None:
    profile = make_profile()
    store.save_profile(profile)
    broker = _broker("ff_err")
    ffm._fallback_todo(store, profile, broker, [], None, "error")
    body = store.list_todos(profile.id)[0].body
    assert body.startswith("Free My ID could not finish this one automatically.")
    assert "Next step:" not in body


@pytest.mark.parametrize("mode,flip_to,reason", [
    ("timeout", None, "timeout"),
    ("closed", None, "window_closed"),
    ("error", f"{HOST}/error", "error_page"),
    ("query", f"{HOST}/opt-out?error=1", "error_page"),
    ("other", f"{HOST}/done", "timeout"),
])
async def test_stop_reason_and_next_step(store: Any, caplog: pytest.LogCaptureFixture,
                                        mode: str, flip_to: str | None, reason: str) -> None:
    caplog.set_level(logging.DEBUG, logger="freemyid.engine.fill_for_me")
    page = _Page("error" if mode == "query" else mode, flip_to=flip_to)
    res, profile = await _run(store, f"ff_{mode}", page)
    assert res.status == "fallback" and res.reason == reason and not res.ok
    assert res.submit_seen is False and res.filled == ["full_name"]
    assert not store.list_requests(profile.id)
    todos = store.list_todos(profile.id)
    assert len(todos) == 1 and todos[0].id == res.todo_id
    assert todos[0].kind == TodoKind.ASSISTED_OPT_OUT
    assert todos[0].links == [FORM]
    assert todos[0].body.startswith(ffm._NEXT_STEP[reason])
    assert "1. Open the opt-out page with the button below." in todos[0].body
    for code, step in ffm._NEXT_STEP.items():
        if code != reason:
            assert step not in todos[0].body
    fallback = [e for e in store.events(profile.id) if e.action == "fill_for_me_fallback"]
    assert len(fallback) == 1
    assert fallback[0].detail == {"reason": reason, "submit_seen": False}
    assert f"code={reason} " in caplog.text
    assert "filled=1" in caplog.text and "submit_seen=0" in caplog.text
    _assert_codes_only(store, caplog, profile.id)


async def test_reasons_are_distinct(store: Any) -> None:
    got: list[str] = []
    for mode, flip, bid in (
        ("timeout", None, "ff_a"),
        ("closed", None, "ff_b"),
        ("error", f"{HOST}/error", "ff_c"),
    ):
        res, _profile = await _run(store, bid, _Page(mode, flip_to=flip))
        got.append(res.reason)
    assert got == ["timeout", "window_closed", "error_page"]
    assert len(set(got)) == 3


async def test_success_path_golden(store: Any, monkeypatch: pytest.MonkeyPatch,
                                   caplog: pytest.LogCaptureFixture) -> None:
    """The success bookkeeping stays what a real submit already records."""
    caplog.set_level(logging.DEBUG, logger="freemyid.engine.fill_for_me")
    res, profile = await _run(store, "ff_ok", _Page("success"), monkeypatch=monkeypatch)
    assert res.status == "submitted" and res.ok
    assert res.reason == "success_text" and res.submit_seen is True
    assert res.practice_mode is True and res.todo_id is None
    assert res.filled == ["full_name"] and len(res.evidence_ids) == 2
    status = store.get_status(profile.id, "ff_ok")
    assert status.state == ListingState.SUBMITTED and status.attempts == 1
    assert status.next_check_at is not None
    req = store.get_request(res.request_id)
    assert req.status == RequestStatus.SENT and req.method.value == "web_form"
    assert req.listing_ids and req.dry_run is False
    shots = store.list_evidence(profile.id, "ff_ok")
    assert sorted(e.caption for e in shots) == ["confirmation page", "form as sent"]
    assert store.read_evidence(shots[0])[:4] == b"\x89PNG"
    events = {e.action: e for e in store.events(profile.id)}
    assert set(events) == {"fill_for_me_filled", "submitted"}
    assert events["fill_for_me_filled"].detail == {
        "filled": ["full_name"], "not_found": [], "withheld": [],
        "protected": 0, "unknown": 0, "errors": 0, "ticked": 0,
    }
    done = events["submitted"]
    assert done.actor.value == "user"
    assert done.from_state == ListingState.UNKNOWN
    assert done.to_state == ListingState.SUBMITTED
    assert done.detail["via"] == "fill_for_me"
    assert done.detail["signal"] == "success_text"
    assert done.detail["method"] == "web_form"
    assert done.detail["request_id"] == res.request_id
    assert store.list_todos(profile.id) == []
    assert "fallback" not in caplog.text
    _assert_codes_only(store, caplog, profile.id)


async def test_success_signal_beats_an_error_url(store: Any, monkeypatch: pytest.MonkeyPatch,
                                                 caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="freemyid.engine.fill_for_me")
    page = _Page("success", after_submit_to=f"{HOST}/error")
    res, profile = await _run(store, "ff_beat", page, monkeypatch=monkeypatch)
    assert res.status == "submitted" and res.reason == "success_text"
    assert not any(e.action == "fill_for_me_fallback" for e in store.events(profile.id))
    _assert_codes_only(store, caplog, profile.id)
