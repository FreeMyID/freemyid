"""D9 additions: Broker.success_text, success_url_pattern and safe_checkboxes.

Loopback fixtures only (freemyid/engine/_dev/site/devfill.example/). Fake people only.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from freemyid.engine import filler
from freemyid.engine._dev import fixture_server
from freemyid.engine.fill_for_me import success_signals, url_matches
from freemyid.models import (
    Broker,
    Listing,
    ListingState,
    MailboxConfig,
    MatchLevel,
    ProfileField,
    Registry,
)
from tests.conftest import fill_bounded, make_profile

F = ProfileField
H = "https://devfill.example"


def _broker(bid: str, page: str, **kw) -> Broker:
    d: dict[str, Any] = {"id": bid, "name": f"Dev Fill {bid}", "url": f"{H}/", "category": "people_search",
         "domains": ["devfill.example"], "opt_out_url": f"{H}/{page}", "method": "web_form",
         "required_fields": [F.FIRST_NAME, F.LAST_NAME, F.FULL_NAME, F.CITY, F.STATE,
                             F.EMAIL, F.LISTING_URL]}
    # safe_checkboxes / success_text are set WITHOUT model validation, so these tests keep
    # exercising the engine's own defence-in-depth against registry data that the model
    # validators (SEC-31/32) would normally refuse.
    raw: dict[str, Any] = {k: kw.pop(k) for k in ("safe_checkboxes", "success_text") if k in kw}
    d.update(kw)
    return Broker(**d).model_copy(update=raw)


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 6), brokers=list(brokers))


def _setup(store, broker: Broker):
    p = make_profile(mailbox=MailboxConfig(
        address="removals.testperson@example.com", imap_host="imap.example.com",
        smtp_host="smtp.example.com", username="removals.testperson@example.com"))
    store.save_profile(p)
    li = Listing(profile_id=p.id, broker_id=broker.id, url=f"{H}/p/jane-testperson-il",
                 match_score=95, match_level=MatchLevel.CONFIRMED,
                 shown_fields=[F.FULL_NAME, F.CITY, F.STATE])
    store.save_listing(li)
    return p, li


async def _submit(page):
    await page.click("#send")


# --------------------------------------------------------------------------- pure


def test_success_signals_include_success_text():
    b = _broker("sig_st", "labels", success_text=["  Request Received ", "", "thanks!"],
                form=[{"action": "submit", "selector": "#send"},
                      {"action": "expect_text", "value": "request received"}])
    texts, sels = success_signals(b)
    assert texts == ["request received", "thanks!"] and sels == []


@pytest.mark.parametrize("pattern,url,want", [
    (r"^/done$", f"{H}/done", True),
    (r"^/done$", f"{H}/done?x=1", False),
    (r"thanks", f"{H}/a?status=thanks", True),      # query is part of the target
    (r"thanks", f"{H}/a#thanks", False),            # fragment is not
    (r"^/done", "", False),
    (None, f"{H}/done", False),
    (r"^/done", f"{H}/" + "x" * 5000 + "/done", False),   # bounded input
])
def test_url_matches(pattern, url, want):
    assert url_matches(pattern, url) is want


# --------------------------------------------------------------------------- browser


async def test_success_text_from_registry(store):
    b = _broker("ff_st", "labels", success_text=["Your request has been received"])
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=_submit, close_delay_s=0)
    assert res.ok and res.reason == "success_text"
    assert store.get_status(p.id, b.id).state == ListingState.SUBMITTED


async def test_success_url_pattern(store):
    b = _broker("ff_url", "labels", success_url_pattern=r"^/done$")
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=_submit, close_delay_s=0)
    assert res.ok and res.reason == "success_url" and res.submit_seen


async def test_success_url_needs_navigation_first(store):
    # The opt-out page itself matches: without the person submitting, it is not success.
    b = _broker("ff_url_base", "labels", success_url_pattern=r"^/labels")
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=2, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "timeout"


async def test_success_text_already_on_page_needs_submit(store):
    b = _broker("ff_st_base", "fullname", success_text=["your request has been received"])
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=2, close_delay_s=0)
    assert res.reason == "timeout"


async def test_url_pattern_counts_as_signal_not_unverified(store):
    # Submit lands on /done but the pattern wants something else: timeout, not unverified.
    b = _broker("ff_url_miss", "labels", success_url_pattern=r"^/elsewhere$")
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=3, on_ready=_submit, close_delay_s=0)
    assert res.reason == "timeout" and res.submit_seen


@pytest.mark.browser
async def test_safe_checkboxes_only_real_visible_main_frame_outside_captcha(store):
    from freemyid.engine.browser import BrowserManager
    from freemyid.engine.outbox import dev_fixture_base
    from freemyid.netpolicy import NetPolicy
    b = _broker("ff_cb", "consent", safe_checkboxes=[".safe", "#news ~ nothing", "[[bad"])
    with fixture_server():
        bm = BrowserManager(NetPolicy(_registry(b)), headless=True,
                            fixture_base=dev_fixture_base())
        await bm.start()
        try:
            ctx = await bm.new_context(["devfill.example"])
            page = await ctx.new_page()
            await bm.goto(page, f"{H}/consent", check_challenge=False)
            n = await filler.tick_safe_checkboxes(page, b.safe_checkboxes)
            assert n == 1
            assert await page.is_checked("#agree")
            for sel in ("#news", "#hiddencb", "#offcb", "#discb", "#robot"):
                assert not await page.is_checked(sel), sel
            assert await page.input_value("#txt") == ""
            fr = page.frame_locator("#fr")
            assert not await fr.locator("#framecb").is_checked()
            # idempotent: an already ticked box is left alone
            assert await filler.tick_safe_checkboxes(page, b.safe_checkboxes) == 0
        finally:
            await bm.close()


async def test_fill_for_me_ticks_safe_checkboxes_and_nothing_else(store):
    b = _broker("ff_cb_flow", "consent", safe_checkboxes=["#agree", "#robot", "#news"],
                success_url_pattern=r"^/done$")
    p, _ = _setup(store, b)
    seen = {}

    async def person(page):
        seen["agree"] = await page.is_checked("#agree")
        seen["robot"] = await page.is_checked("#robot")
        seen["news"] = await page.is_checked("#news")
        await page.click("#send")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.ok
    # SEC-31: a marketing box ("Send me offers") is refused even when the registry picks it
    assert seen == {"agree": True, "robot": False, "news": False}
    ev = [e for e in store.events(p.id) if e.action == "fill_for_me_filled"]
    assert ev and ev[0].detail["ticked"] == 1


async def test_no_safe_checkboxes_ticks_nothing(store):
    b = _broker("ff_cb_none", "consent", success_url_pattern=r"^/done$")
    p, _ = _setup(store, b)
    seen = {}

    async def person(page):
        seen["agree"] = await page.is_checked("#agree")
        await page.click("#send")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.ok and seen["agree"] is False
