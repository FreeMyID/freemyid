"""D10 listing finder: visible-window search, 'This is me' button, CONFIRMED listing.

Loopback fixtures only (freemyid/engine/_dev/site/devfind.example/: search page, results page,
two profile pages, a hostile page). Brokers are built here. Headless in tests; real use is
headed. Fake people only.
"""
from __future__ import annotations

import asyncio
import inspect
from datetime import date
from typing import Any

import pytest

from freemyid.engine import filler, listing_finder
from freemyid.engine._dev import fixture_server
from freemyid.engine.listing_finder import (
    BANNER_ID,
    BUTTON_ID,
    CANT_ID,
    MSG_DONE,
    MSG_FIND,
    MSG_REJECT,
    check_listing_url,
    find_listing,
    find_listing_sync,
    record_listing,
    search_values,
)
from freemyid.models import (
    Broker,
    ListingState,
    MatchLevel,
    ProfileField,
    Registry,
    Todo,
    TodoKind,
)
from tests.conftest import find_bounded, make_profile

F = ProfileField
H = "https://devfind.example"
RIGHT = f"{H}/p/jane-testperson-springfield-il"
WRONG = f"{H}/p/jane-testperson-shelbyville-il"
PATTERN = r"^/p/[a-z0-9-]+$"


def _broker(bid: str = "find_dev", **kw) -> Broker:
    d: dict[str, Any] = {"id": bid, "name": f"Dev Find {bid}", "url": f"{H}/search",
         "category": "people_search", "domains": ["devfind.example"],
         "opt_out_url": f"{H}/optout", "method": "web_form",
         "required_fields": [F.FULL_NAME, F.EMAIL, F.LISTING_URL]}
    d.update(kw)
    return Broker(**d)


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 6), brokers=list(brokers))


def _profile(store):
    p = make_profile()
    store.save_profile(p)
    return p


async def _click_me(page):
    await page.click(f"#{BUTTON_ID}")


async def _banner_says(page, text: str) -> None:
    await page.wait_for_function(
        "([id, t]) => { const b = document.getElementById(id); "
        "return !!b && b.textContent.includes(t); }", arg=[BANNER_ID, text], timeout=10_000)


# --------------------------------------------------------------------------- pure


@pytest.mark.parametrize("url,pattern,want", [
    (RIGHT, PATTERN, ""),
    (RIGHT + "#top", PATTERN, ""),
    ("https://www.devfind.example/p/jane-1", PATTERN, ""),          # subdomain is ok
    ("https://devfind.example.evil.example/p/jane", PATTERN, "off_host"),
    ("https://other.example/p/jane", PATTERN, "off_host"),
    ("https://devfind.example\\@evil.example/p/x", PATTERN, "bad_url"),
    ("https://user:pw@devfind.example/p/jane", PATTERN, "bad_url"),
    ("http://devfind.example/p/jane", PATTERN, "not_https"),
    ("javascript:alert(1)", PATTERN, "not_https"),
    (f"{H}/results?first=jane", PATTERN, "pattern_mismatch"),
    (f"{H}/p/jane/extra", PATTERN, "pattern_mismatch"),
    (f"{H}/search", None, "search_page"),
    (f"{H}/", None, "search_page"),
    (f"{H}/results?first=jane", None, ""),          # no pattern: any page but search/root
    (f"{H}/p/" + "a" * 3000, PATTERN, "bad_url"),   # bounded
    ("", PATTERN, "bad_url"),
])
def test_check_listing_url(url, pattern, want):
    b = _broker(listing_url_pattern=pattern)
    got, why = check_listing_url(b, url, search_url=f"{H}/search")
    assert why == want
    if want == "":
        assert got is not None and "#" not in got and got.startswith("https://")
    else:
        assert got is None


def test_search_values_are_minimal(profile):
    v = search_values(profile)
    assert v == {"first_name": "Jane", "last_name": "Testperson",
                 "full_name": "Jane Testperson", "city": "Springfield", "state": "IL"}


def test_button_script_is_text_only():
    js = listing_finder._init_js("__freemyid_test") + listing_finder._SET_MSG_JS
    for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                "Function("):
        assert bad not in js, bad
    assert "textContent" in js and "isTrusted" in js
    src = inspect.getsource(listing_finder)
    assert "innerHTML" not in src.replace("no innerHTML", "")


def test_record_listing_feeds_fill_for_me(store):
    b = _broker()
    p = _profile(store)
    li, ev = record_listing(store, p, b, RIGHT, b"\x89PNG fake")
    assert li.match_level == MatchLevel.CONFIRMED and "user_confirmed" in li.match_reasons
    plan = filler.plan_values(p, b, li)
    assert plan["listing_url"] == RIGHT and plan["full_name"] == "Jane Testperson"
    assert len(ev) == 1
    # again: same record, no duplicate listing
    li2, _ = record_listing(store, p, b, RIGHT)
    assert li2.id == li.id and len(store.list_listings(p.id, b.id)) == 1


# --------------------------------------------------------------------------- browser


async def test_right_result_chosen_via_search_form(store):
    b = _broker(listing_url_pattern=PATTERN)
    p = _profile(store)
    review = Todo(profile_id=p.id, broker_id=b.id, kind=TodoKind.REVIEW_MATCH, title="Is this?")
    store.save_todo(review)
    seen = {}

    async def person(page):
        await _banner_says(page, MSG_FIND)
        seen["banner"] = await page.inner_text(f"#{BANNER_ID}")
        seen["fields"] = [await page.input_value(s) for s in ("#fn", "#ln", "#ct", "#st")]
        await page.click("#go")
        await page.wait_for_selector("#r-springfield")
        await page.wait_for_selector(f"#{BUTTON_ID}")
        await page.click("#r-springfield")
        await page.wait_for_url(RIGHT)
        await page.wait_for_selector(f"#{BUTTON_ID}")
        await _click_me(page)

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.status == "found", res
    assert res.listing_url == RIGHT and res.searched_with == "form" and res.rejected == 0
    assert seen["fields"] == ["Jane", "Testperson", "Springfield", "IL"]
    assert "Press the site's Search button first" in seen["banner"]
    lis = store.list_listings(p.id, b.id)
    assert len(lis) == 1 and lis[0].id == res.listing_id and lis[0].url == RIGHT
    assert lis[0].match_level == MatchLevel.CONFIRMED
    assert {"user_confirmed", "listing_finder"} <= set(lis[0].match_reasons)
    st = store.get_status(p.id, b.id)
    assert st.state == ListingState.FOUND and st.next_check_at is None
    evs = store.list_evidence(p.id, b.id)
    assert len(evs) == 1 and evs[0].listing_id == res.listing_id
    assert evs[0].relpath.startswith(f"{p.id}/{b.id}/")
    assert store.read_evidence(evs[0])[:4] == b"\x89PNG"
    ev = [e for e in store.events(p.id) if e.action == "listing_confirmed"]
    assert ev and ev[0].actor.value == "user" and ev[0].to_state == ListingState.FOUND
    assert all(t.id != review.id for t in store.list_todos(p.id))     # review closed
    blob = repr([e.detail for e in store.events(p.id)])
    for pii in ("Jane", "Testperson", "Springfield", "springfield"):
        assert pii not in blob


async def test_search_url_pattern_opens_results_directly(store):
    b = _broker(search_url_pattern=f"{H}/results?first={{first}}&last={{last}}"
                                   "&city={city}&state={state}")
    p = _profile(store)

    async def person(page):
        await page.wait_for_selector("#r-springfield")
        await page.click("#r-springfield")
        await page.wait_for_url(RIGHT)
        await page.wait_for_selector(f"#{BUTTON_ID}")
        await _click_me(page)

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.ok and res.searched_with == "search_url" and res.listing_url == RIGHT


async def test_pattern_mismatch_rejected_then_right_page_accepted(store):
    b = _broker(listing_url_pattern=PATTERN)
    p = _profile(store)

    async def person(page):
        await page.click("#go")
        await page.wait_for_selector("#r-springfield")
        await page.wait_for_selector(f"#{BUTTON_ID}")
        await _click_me(page)                    # on the results page: not a listing
        await _banner_says(page, MSG_REJECT["pattern_mismatch"])
        await page.click("#r-springfield")
        await page.wait_for_url(RIGHT)
        await page.wait_for_selector(f"#{BUTTON_ID}")
        await _click_me(page)

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.ok and res.listing_url == RIGHT
    assert res.rejected == 1 and res.last_rejection == "pattern_mismatch"
    rej = [e for e in store.events(p.id) if e.action == "listing_finder_rejected"]
    assert rej and rej[0].detail == {"why": "pattern_mismatch"}


async def test_search_page_itself_rejected(store):
    b = _broker()                                # no pattern
    p = _profile(store)

    async def person(page):
        await _click_me(page)
        await _banner_says(page, MSG_REJECT["search_page"])
        await page.close()

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "window_closed"
    assert res.last_rejection == "search_page" and not store.list_listings(p.id, b.id)


async def test_off_host_navigation_falls_back_blocked(store):
    b = _broker(listing_url_pattern=PATTERN)
    p = _profile(store)

    async def person(page):
        await page.click("#go")
        await page.wait_for_selector("#ad")
        await page.click("#ad", no_wait_after=True)   # sponsored link to another host

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "blocked" and res.todo_id
    assert not store.list_listings(p.id, b.id)


async def test_window_closed_falls_back_to_assisted_card(store):
    b = _broker()
    p = _profile(store)

    async def person(page):
        await page.close()

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "window_closed"
    todos = store.list_todos(p.id)
    assert [t.kind for t in todos] == [TodoKind.ASSISTED_OPT_OUT]
    assert todos[0].id == res.todo_id
    assert store.get_status(p.id, b.id).state == ListingState.UNKNOWN


async def test_fallback_prefers_existing_review_card(store):
    b = _broker()
    p = _profile(store)
    review = Todo(profile_id=p.id, broker_id=b.id, kind=TodoKind.REVIEW_MATCH, title="Is this?")
    store.save_todo(review)
    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=1, close_delay_s=0)
    assert res.reason == "timeout" and res.todo_id == review.id
    assert len(store.list_todos(p.id)) == 1


async def test_cant_find_button(store):
    b = _broker()
    p = _profile(store)

    async def person(page):
        await page.click(f"#{CANT_ID}")

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "user_cant_find" and res.todo_id


async def test_button_injection_is_text_only_in_page(store):
    b = _broker(listing_url_pattern=PATTERN)
    p = _profile(store)
    seen = {}

    async def person(page):
        await _banner_says(page, MSG_FIND)
        btn = page.locator(f"#{BUTTON_ID}")
        seen["text"] = await btn.text_content()
        seen["children"] = await btn.evaluate("e => e.children.length")
        seen["tag"] = await btn.evaluate("e => e.tagName")
        seen["banner_html_tags"] = await page.evaluate(
            "id => Array.from(document.getElementById(id).querySelectorAll('*'))"
            ".map(e => e.tagName)", BANNER_ID)
        # markup in a message stays text
        await page.evaluate(listing_finder._SET_MSG_JS,
                            [BANNER_ID, ["<img id=pwn src=x onerror=1>"], False])
        seen["pwn"] = await page.query_selector("#pwn")
        seen["literal"] = await page.inner_text(f"#{BANNER_ID}")
        await page.close()

    with fixture_server():
        await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                           timeout_s=30, on_ready=person, close_delay_s=0)
    assert seen["text"] == "This is me" and seen["children"] == 0 and seen["tag"] == "BUTTON"
    assert set(seen["banner_html_tags"]) == {"DIV"}
    assert seen["pwn"] is None and "<img id=pwn" in seen["literal"]


async def test_page_script_cannot_call_binding_or_fake_click(store):
    b = _broker()                                # no pattern: /hostile would be accepted
    p = _profile(store)
    seen = {}

    async def person(page):
        await page.goto(f"{H}/hostile")
        await page.wait_for_selector(f"#{BUTTON_ID}")
        seen["exposed"] = await page.evaluate(
            "() => Object.getOwnPropertyNames(window).filter(k => k.startsWith('__freemyid'))")
        await page.evaluate(f"document.getElementById('{BUTTON_ID}').click()")  # untrusted
        await page.evaluate(
            f"document.getElementById('{BUTTON_ID}').dispatchEvent("
            "new MouseEvent('click', {bubbles: true}))")
        await asyncio.sleep(1.5)
        seen["listings_before_real_click"] = len(store.list_listings(p.id, b.id))
        await _click_me(page)                    # a real (trusted) click

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=0)
    assert seen["exposed"] == []
    assert seen["listings_before_real_click"] == 0
    assert res.ok and res.listing_url == f"{H}/hostile"


async def test_done_banner_shown(store):
    b = _broker(listing_url_pattern=PATTERN)
    p = _profile(store)
    seen = {}

    async def person(page):
        await page.goto(WRONG)
        await page.wait_for_selector(f"#{BUTTON_ID}")
        await _click_me(page)
        await _banner_says(page, MSG_DONE)
        seen["done"] = True

    with fixture_server():
        res = await find_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                 timeout_s=30, on_ready=person, close_delay_s=1.5)
    assert res.ok and res.listing_url == WRONG and seen.get("done")


async def test_refusals(store):
    from freemyid.models import Consent, ConsentBasis
    b = _broker()
    reg = _registry(b)
    p = _profile(store)
    assert (await find_listing(store, p.id, "nope", registry=reg)).reason == "unknown_broker"
    assert (await find_listing(store, "no-such-id", b.id, registry=reg)).reason == "no_profile"
    bad = p.model_copy(update={"consent": Consent(basis=ConsentBasis.SELF,
                                                  attested_by="Jane Q Testperson",
                                                  text_version="v0-old")})
    store.save_profile(bad)
    r = await find_listing(store, p.id, b.id, registry=reg)
    assert r.status == "refused" and r.reason == "consent" and not store.list_todos(p.id)


@pytest.mark.browser
def test_sync_wrapper_timeout(store):
    b = _broker()
    p = _profile(store)
    with fixture_server():
        res = find_listing_sync(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=1, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "timeout" and res.todo_id
