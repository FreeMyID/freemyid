"""Web-form fallback: the person's to-do names what happened, not a crash.

No browser and no network. A Playwright timeout is a class named TimeoutError that is not
the builtin one, so the reason match cannot import Playwright.
"""
from __future__ import annotations

import asyncio
import socket
from types import SimpleNamespace
from typing import Any, cast

import pytest

from freemyid.engine.browser import BlockedByPolicy, ChallengeEncountered
from freemyid.interfaces import RunContext
from freemyid.models import Broker, Listing, ListingState, MatchLevel, TodoKind
from freemyid.submitters import assisted
from freemyid.submitters.web_form import HumanStep, UnexpectedPage, WebFormSubmitter
from tests.conftest import make_profile

# Not a subclass of builtin TimeoutError. The submitter must match the type name.
_PLAYWRIGHT_TIMEOUT = type("TimeoutError", (Exception,), {})

CHALLENGE = (
    "Free My ID stopped because the site asked for a human check. "
    "Please finish it yourself."
)
HUMAN = "The site asked for a step only a person can do."
NO_LISTING = "Free My ID is not sure a listing here is yours, so this one needs you."
TIMEOUT = "The site took too long to answer. Please try this one yourself."
BLOCKED = (
    "The site tried to open a page Free My ID does not open. Please do this one yourself."
)
UNEXPECTED = (
    "The page did not look like the one Free My ID expected. Please do this one yourself."
)
ERROR = "Free My ID could not finish this one automatically. Please do it yourself."

_DEFAULT_STEPS = [
    "1. Open the opt-out page with the button below.",
    "2. Find your listing and follow the site's removal steps.",
    "3. Use the Copy buttons to fill in the form.",
    "Never pay. Removal is free.",
]
_LEAK = "LEAK-failed-error"
_OFF_HOST = "blocked-host.test"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Any) -> None:
    """socket.connect and create_connection always raise, including localhost.

    Depends on freemyid_env so this runs after that fixture's own connect patch.
    """
    assert freemyid_env  # the shared home path; this fixture only needs it to run first

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("network is blocked in this test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _broker(**over: Any) -> Broker:
    data: dict[str, Any] = {
        "id": "fakew",
        "name": "Fake W",
        "url": "https://fakew.example/",
        "category": "people_search",
        "domains": ["fakew.example"],
        "method": "web_form",
        "opt_out_url": "https://fakew.example/optout",
        "form": [{"action": "fill", "selector": "#q", "value": "{{ first }}"}],
    }
    data.update(over)
    return Broker.model_validate(data)


def _listing(profile: Any, broker: Broker, level: MatchLevel) -> Listing:
    return Listing(
        profile_id=profile.id,
        broker_id=broker.id,
        url="https://fakew.example/people/jane-q-testperson",
        match_score=90,
        match_level=level,
    )


class _RaisingBrowser:
    """Stands in for BrowserManager. new_context raises; nothing is launched."""

    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.calls = 0

    async def new_context(self, domains: object) -> Any:
        self.calls += 1
        raise self.exc


class _OpenContext:
    async def new_page(self) -> Any:
        return SimpleNamespace()

    async def close(self) -> None:
        return None


class _QuietBrowser:
    """Gets as far as a form step, then lets run_steps raise HumanStep."""

    def __init__(self) -> None:
        self.calls = 0

    async def new_context(self, domains: object) -> _OpenContext:
        self.calls += 1
        return _OpenContext()

    async def goto(self, page: object, url: str, **_kwargs: object) -> None:
        return None


class _NoHandoff:
    async def request(self, *_args: object, **_kwargs: object) -> bool:
        raise AssertionError("a fallback must not ask the handoff to solve a check")


class _NoNotify:
    def notify(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("a fallback must not notify")


def _ctx(store: Any, broker: Broker, browser: Any) -> RunContext:
    return RunContext(
        profile=make_profile(),
        broker=broker,
        store=store,
        netpolicy=cast(Any, SimpleNamespace()),
        handoff=cast(Any, _NoHandoff()),
        notifier=cast(Any, _NoNotify()),
        mailer=None,
        dry_run=False,
        interactive=False,
        scratch={"browser": browser},
    )


def _assert_calm(body: str, line: str, *, default_steps: bool = True) -> None:
    assert body.splitlines()[0] == line
    low = body.lower()
    assert "error" not in low
    assert "failed" not in low
    assert "Testperson" not in body
    assert "Springfield" not in body
    if default_steps:
        assert body.splitlines()[1:] == _DEFAULT_STEPS


def _code(reason: str, detail: str | None) -> str:
    return f"fallback_assisted:{reason}" + (f":{detail}" if detail else "")


@pytest.mark.parametrize(
    ("exc", "reason", "detail", "line"),
    [
        (ChallengeEncountered("captcha_widget"), "challenge", "captcha_widget", CHALLENGE),
        (HumanStep(_LEAK), "human_step", None, HUMAN),
        (UnexpectedPage(_LEAK), "unexpected_page", "UnexpectedPage", UNEXPECTED),
        (BlockedByPolicy(_OFF_HOST), "blocked_by_policy", "BlockedByPolicy", BLOCKED),
        (_PLAYWRIGHT_TIMEOUT(_LEAK), "timeout", "TimeoutError", TIMEOUT),
        # 3.11+ aliases asyncio.TimeoutError to the builtin; the type name is TimeoutError.
        (TimeoutError(_LEAK), "timeout", "TimeoutError", TIMEOUT),
        (RuntimeError(_LEAK), "error", "RuntimeError", ERROR),
    ],
    ids=[
        "challenge",
        "human_step",
        "unexpected_page",
        "blocked_by_policy",
        "playwright_timeout",
        "asyncio_timeout",
        "error",
    ],
)
async def test_submit_fallback_reason_reaches_the_todo(
    store: Any, exc: BaseException, reason: str, detail: str | None, line: str,
) -> None:
    if type(exc) is _PLAYWRIGHT_TIMEOUT:
        assert not isinstance(exc, TimeoutError)
    if type(exc) is TimeoutError:
        assert asyncio.TimeoutError is TimeoutError
    broker = _broker()
    browser = _RaisingBrowser(exc)
    ctx = _ctx(store, broker, browser)
    out = await WebFormSubmitter().submit(ctx, [])
    assert browser.calls == 1
    assert out.new_state is ListingState.NEEDS_HUMAN
    assert out.request is None and out.evidence == []
    assert out.message == _code(reason, detail)
    assert _LEAK not in out.message and _OFF_HOST not in out.message
    assert len(out.todos) == 1
    todo = out.todos[0]
    assert todo.kind is TodoKind.ASSISTED_OPT_OUT
    assert todo.resume_token == "assisted:fakew"
    direct = assisted.todo_for(ctx.profile, broker, [], None, reason=reason)
    assert todo.body == direct.body
    assert todo.title == direct.title
    _assert_calm(todo.body, line)
    assert _LEAK not in todo.body and _OFF_HOST not in todo.body
    assert "captcha_widget" not in todo.body


@pytest.mark.parametrize("level", [None, MatchLevel.POSSIBLE])
async def test_missing_confirmed_listing_is_not_a_crash(
    store: Any, level: MatchLevel | None,
) -> None:
    broker = _broker(form=[{
        "action": "fill", "selector": "#u", "value": "{{ listing.url }}",
    }])
    browser = _RaisingBrowser(RuntimeError("should not run"))
    ctx = _ctx(store, broker, browser)
    listings = [] if level is None else [_listing(ctx.profile, broker, level)]
    out = await WebFormSubmitter().submit(ctx, listings)
    assert browser.calls == 0
    assert out.message == "fallback_assisted:no_confirmed_listing"
    assert out.new_state is ListingState.NEEDS_HUMAN
    direct = assisted.todo_for(
        ctx.profile, broker, listings, None, reason="no_confirmed_listing")
    assert out.todos[0].body == direct.body
    _assert_calm(out.todos[0].body, NO_LISTING)


async def test_confirmed_listing_still_tries_the_form(store: Any) -> None:
    broker = _broker(form=[{
        "action": "fill", "selector": "#u", "value": "{{ listing.url }}",
    }])
    browser = _RaisingBrowser(RuntimeError(_LEAK))
    ctx = _ctx(store, broker, browser)
    listings = [_listing(ctx.profile, broker, MatchLevel.CONFIRMED)]
    out = await WebFormSubmitter().submit(ctx, listings)
    assert browser.calls == 1
    assert out.message == "fallback_assisted:error:RuntimeError"
    assert _LEAK not in out.message
    _assert_calm(out.todos[0].body, ERROR)


async def test_human_form_step_is_its_own_reason(store: Any) -> None:
    broker = _broker(form=[{"action": "human", "note": _LEAK}])
    browser = _QuietBrowser()
    ctx = _ctx(store, broker, browser)
    out = await WebFormSubmitter().submit(ctx, [])
    assert browser.calls == 1
    assert out.message == "fallback_assisted:human_step"
    assert _LEAK not in out.message
    direct = assisted.todo_for(ctx.profile, broker, [], None, reason="human_step")
    assert out.todos[0].body == direct.body
    _assert_calm(out.todos[0].body, HUMAN)


def test_each_reason_is_one_calm_line_then_todays_steps() -> None:
    broker = _broker(steps=["Open the opt-out page.", "Type your removal email."])
    seen: set[str] = set()
    for reason, line in (
        ("challenge", CHALLENGE),
        ("human_step", HUMAN),
        ("no_confirmed_listing", NO_LISTING),
        ("timeout", TIMEOUT),
        ("blocked_by_policy", BLOCKED),
        ("unexpected_page", UNEXPECTED),
        ("error", ERROR),
    ):
        todo = assisted.todo_for(make_profile(), broker, [], None, reason=reason)
        assert todo.kind is TodoKind.ASSISTED_OPT_OUT
        assert todo.body.splitlines() == [
            line,
            "1. Open the opt-out page.",
            "2. Type an email address you can check.",
            assisted.NO_MAILBOX_NOTE,
            "Never pay. Removal is free.",
        ]
        assert "error" not in todo.body.lower()
        assert "failed" not in todo.body.lower()
        assert "removal email" not in todo.body.lower()
        seen.add(line)
    assert len(seen) == 7


def test_no_reason_keeps_todays_steps_only() -> None:
    todo = assisted.todo_for(make_profile(), _broker(), [], None)
    assert todo.body.splitlines() == _DEFAULT_STEPS
