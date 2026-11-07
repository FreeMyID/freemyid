"""D9 "Fill it in for me": filler + visible-window flow, against loopback-only fixtures.

Fixture pages live in freemyid/engine/_dev/site/devfill.example/ and are served by the dev
fixture server (127.0.0.1). Brokers are built here (not in the dev registry, so the e2e
dry-run counts do not change). Headless in tests; real use is headed.
Fake people only.
"""
from __future__ import annotations

from datetime import date

import pytest

from freemyid.engine import filler
from freemyid.engine._dev import fixture_server
from freemyid.engine.fill_for_me import (
    BANNER_ID,
    MSG_PRACTICE,
    fill_for_me,
    fill_for_me_sync,
    success_signals,
)
from freemyid.models import (
    Broker,
    Listing,
    ListingState,
    MailboxConfig,
    MatchLevel,
    ProfileField,
    Registry,
    RequestStatus,
    TodoKind,
)
from tests.conftest import fill_bounded, make_profile

F = ProfileField
H = "https://devfill.example"
SUCCESS = [{"action": "goto", "url": f"{H}/labels"},
           {"action": "human", "note": "person ticks the robot box and submits"},
           {"action": "expect_text", "value": "request has been received"}]


def _broker(bid: str, page: str, form=None, **kw) -> Broker:
    d = {"id": bid, "name": f"Dev Fill {bid}", "url": f"{H}/", "category": "people_search",
             "domains": ["devfill.example"], "opt_out_url": f"{H}/{page}", "method": "web_form",
             "required_fields": [F.FIRST_NAME, F.LAST_NAME, F.FULL_NAME, F.CITY, F.STATE,
                              F.EMAIL, F.LISTING_URL],
             "form": form or []}
    d.update(kw)
    return Broker(**d)


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 6), brokers=list(brokers))


def _mailbox() -> MailboxConfig:
    return MailboxConfig(address="removals.testperson@example.com",
                         imap_host="imap.example.com", smtp_host="smtp.example.com",
                         username="removals.testperson@example.com")


def _setup(store, broker: Broker, shown=(F.FULL_NAME, F.CITY, F.STATE)):
    p = make_profile(mailbox=_mailbox())
    store.save_profile(p)
    li = Listing(profile_id=p.id, broker_id=broker.id, url=f"{H}/p/jane-testperson-il",
                 match_score=95, match_level=MatchLevel.CONFIRMED, shown_fields=list(shown))
    store.save_listing(li)
    return p, li


# --------------------------------------------------------------------------- pure


@pytest.mark.parametrize("desc,want", [
    ({"label": "First name"}, "first_name"),
    ({"aria": "Given name"}, "first_name"),
    ({"name": "fname"}, "first_name"),
    ({"placeholder": "Family name"}, "last_name"),
    ({"id": "lastName"}, "last_name"),
    ({"label": "Surname"}, "last_name"),
    ({"label": "Your name"}, "full_name"),
    ({"label": "Full Name"}, "full_name"),
    ({"name": "emailAddress"}, "email"),
    ({"label": "Email address"}, "email"),
    ({"type": "email"}, "email"),
    ({"id": "town"}, "city"),
    ({"name": "zipCode"}, "zip"),
    ({"label": "Postal code"}, "zip"),
    ({"label": "Street address"}, "street"),
    ({"placeholder": "Paste the link to your listing"}, "listing_url"),
    ({"label": "Profile URL"}, "listing_url"),
    ({"label": "Web address"}, "listing_url"),
    ({"autocomplete": "address-level1"}, "state"),
    ({"tag": "select", "type": "select", "label": "State"}, "state"),
    ({"label": "Middle name"}, None),
    ({"label": "Phone number"}, None),
    ({"label": "Date of birth"}, None),
    ({"label": "Username"}, None),
    ({"name": "search", "placeholder": "Search people"}, None),
    ({"label": "Address line 2"}, None),
    ({"label": "Country"}, None),
])
def test_classify(desc, want):
    assert filler.classify(filler.Control(key="f0", **desc)) == want


@pytest.mark.parametrize("desc", [
    {"type": "password", "label": "Password"},
    {"type": "file", "label": "Upload ID"},
    {"type": "checkbox", "label": "I agree"},
    {"type": "hidden", "name": "email"},
    {"label": "Name", "in_captcha": True},
    {"tag": "textarea", "type": "textarea", "name": "g-recaptcha-response"},
    {"label": "Email", "visible": False},
    {"label": "Email", "disabled": True},
])
def test_protected_controls_never_classified(desc):
    c = filler.Control(key="f0", **desc)
    assert c.protected()
    assert filler.classify(c) is None


@pytest.mark.parametrize("opts,code,want", [
    ([{"value": "NC", "text": "NC"}], "NC", "NC"),
    ([{"value": "37", "text": "North Carolina"}], "NC", "37"),
    ([{"value": "north carolina", "text": "x"}], "nc", "north carolina"),
    ([{"value": "7", "text": "NC - North Carolina"}], "NC", "7"),
    ([{"value": "SC", "text": "South Carolina"}], "NC", None),
])
def test_choose_state_option(opts, code, want):
    assert filler.choose_state_option(opts, code) == want


def test_plan_values_minimized(profile):
    b = _broker("fill_min", "labels", required_fields=[F.FULL_NAME, F.CITY, F.ZIP,
                                                          F.LISTING_URL, F.EMAIL])
    p = profile.model_copy(update={"mailbox": _mailbox()})
    li = Listing(profile_id=p.id, broker_id=b.id, url=f"{H}/p/x", match_score=90,
                 match_level=MatchLevel.CONFIRMED, shown_fields=[F.FULL_NAME, F.CITY])
    v = filler.plan_values(p, b, li)
    assert v["listing_url"] == li.url and v["email"] == "removals.testperson@example.com"
    assert "zip" not in v and "state" not in v and "street" not in v   # not shown
    assert "jane.testperson@example.com" not in v.values()             # personal email
    assert not any("555" in x for x in v.values())                     # phone never


def test_success_signals():
    b = _broker("fill_sig", "labels", form=[
        {"action": "goto", "url": f"{H}/labels"}, {"action": "expect_text", "value": "Remove"},
        {"action": "submit", "selector": "#send"},
        {"action": "expect_text", "value": "Request Received"},
        {"action": "wait_for", "selector": ".thanks"}])
    assert success_signals(b) == (["request received"], [".thanks"])
    assert success_signals(_broker("fill_none", "labels")) == ([], [])


# --------------------------------------------------------------------------- browser


async def _page(registry: Registry, url: str):
    from freemyid.engine.browser import BrowserManager
    from freemyid.engine.outbox import dev_fixture_base
    from freemyid.netpolicy import NetPolicy
    bm = BrowserManager(NetPolicy(registry), headless=True, fixture_base=dev_fixture_base())
    await bm.start()
    ctx = await bm.new_context(["devfill.example"])
    page = await ctx.new_page()
    await bm.goto(page, url, check_challenge=False)
    return bm, page


@pytest.mark.browser
async def test_fill_labels_page_leaves_protected_controls_alone(profile):
    b = _broker("fill_labels", "labels")
    p = profile.model_copy(update={"mailbox": _mailbox()})
    li = Listing(profile_id=p.id, broker_id=b.id, url=f"{H}/p/jane", match_score=95,
                 match_level=MatchLevel.CONFIRMED, shown_fields=[F.FULL_NAME, F.CITY, F.STATE])
    with fixture_server():
        bm, page = await _page(_registry(b), f"{H}/labels")
        try:
            rep = await filler.fill_page(page, filler.plan_values(p, b, li))
            val = page.input_value
            assert await val("#fn") == "Jane" and await val("#ln") == "Testperson"
            assert await val("input[type=email]") == "removals.testperson@example.com"
            assert await val("#ct") == "Springfield"
            assert await val("#st") == "Illinois"
            assert await val("#pu") == li.url
            for sel in ("#mn", "#zp", "#ph", "#pw", "#hp", "#hp2", "#capname",
                        "#g-recaptcha-response"):
                assert await val(sel) == "", sel
            assert not await page.is_checked("#robot")
            assert not await page.is_checked("#agree")
            assert await page.evaluate("document.querySelector('#up').files.length") == 0
            assert set(rep.filled) == {"first_name", "last_name", "email", "city", "state",
                                       "listing_url"}
            assert rep.withheld == ["zip"]      # box exists, zip not allowed for this broker
            assert rep.protected >= 8
            assert "full_name" not in rep.not_found   # first+last boxes cover it
        finally:
            await bm.close()


@pytest.mark.browser
async def test_fill_aria_placeholder_name_id(profile):
    b = _broker("fill_aria", "aria")
    p = profile.model_copy(update={"mailbox": _mailbox()})
    li = Listing(profile_id=p.id, broker_id=b.id, url=f"{H}/p/jane", match_score=95,
                 match_level=MatchLevel.CONFIRMED, shown_fields=[F.FULL_NAME, F.CITY, F.STATE])
    with fixture_server():
        bm, page = await _page(_registry(b), f"{H}/aria")
        try:
            rep = await filler.fill_page(page, filler.plan_values(p, b, li))
            val = page.input_value
            assert await val("[name=x1]") == "Jane"
            assert await val("[name=x2]") == "Testperson"
            assert await val("[name=emailAddress]") == "removals.testperson@example.com"
            assert await val("#town") == "Springfield"
            assert await val("[name=stateCode]") == "IL"
            assert await val("[name=zipCode]") == ""
            assert await val("[name=x3]") == li.url
            assert await val("[name=search]") == ""
            assert "zip" in rep.withheld and rep.unknown >= 1
        finally:
            await bm.close()


async def test_fill_for_me_success_records_like_web_form(store):
    b = _broker("fill_ok", "labels", form=SUCCESS, needs_email_verification=True)
    p, li = _setup(store, b)
    seen = {}

    async def person(page):
        seen["banner"] = await page.inner_text(f"#{BANNER_ID}")
        seen["robot"] = await page.is_checked("#robot")
        await page.click("#send")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.status == "submitted", res
    assert res.reason == "success_text" and res.submit_seen
    assert "not a robot" in seen["banner"] and MSG_PRACTICE in seen["banner"]
    assert res.practice_mode and seen["robot"] is False
    st = store.get_status(p.id, b.id)
    assert st.state == ListingState.AWAITING_VERIFICATION and st.attempts == 1
    assert st.next_check_at is not None
    req = store.get_request(res.request_id)
    assert req.status == RequestStatus.SENT and req.listing_ids == [li.id]
    evs = store.list_evidence(p.id, b.id)
    assert len(evs) == 2 and all(e.relpath.startswith(f"{p.id}/{b.id}/") for e in evs)
    assert store.read_evidence(evs[0])[:4] == b"\x89PNG"
    ev = [e for e in store.events(p.id) if e.action == "submitted"]
    assert ev and ev[0].actor.value == "user" and ev[0].detail["via"] == "fill_for_me"
    blob = repr([e.detail for e in store.events(p.id)])
    for pii in ("Jane", "Testperson", "Springfield", "removals.testperson"):
        assert pii not in blob


async def test_success_closes_open_assisted_todo(store):
    from freemyid.engine.handoff import persist_todo
    from freemyid.submitters.assisted import assisted_todo
    b = _broker("fill_todo", "labels", form=SUCCESS)
    p, li = _setup(store, b)
    t = persist_todo(store, assisted_todo(p, b, [li]))

    async def person(page):
        await page.click("#send")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.ok
    assert all(x.id != t.id for x in store.list_todos(p.id))
    assert store.get_status(p.id, b.id).state == ListingState.SUBMITTED


async def test_window_closed_falls_back_to_assisted_card(store):
    b = _broker("fill_closed", "labels", form=SUCCESS)
    p, _ = _setup(store, b)

    async def person(page):
        await page.close()

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=20, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "window_closed"
    todos = store.list_todos(p.id)
    assert [t.kind for t in todos] == [TodoKind.ASSISTED_OPT_OUT] and todos[0].id == res.todo_id
    assert store.get_status(p.id, b.id).state == ListingState.UNKNOWN
    assert not store.list_requests(p.id)


async def test_timeout_falls_back_and_reuses_card(store):
    b = _broker("fill_slow", "labels", form=SUCCESS)
    p, _ = _setup(store, b)
    with fixture_server():
        r1 = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                               timeout_s=1, close_delay_s=0)
        r2 = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                               timeout_s=1, close_delay_s=0)
    assert r1.reason == "timeout" and r1.filled and not r1.submit_seen
    assert r1.todo_id == r2.todo_id and len(store.list_todos(p.id)) == 1


async def test_no_success_signal_is_unverified(store):
    b = _broker("fill_nosig", "labels")        # no form steps: nothing to check against
    p, _ = _setup(store, b)

    async def person(page):
        await page.click("#send")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=3, on_ready=person, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "unverified" and res.submit_seen
    assert res.todo_id and store.get_status(p.id, b.id).state == ListingState.UNKNOWN


async def test_success_text_already_on_page_needs_a_submit(store):
    form = [{"action": "expect_text", "value": "your request has been received"}]
    b = _broker("fill_base", "fullname", form=form)
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=1, close_delay_s=0)
    assert res.reason == "timeout"                    # instructions text is not success
    assert set(res.filled) == {"full_name", "state", "email"}

    async def person(page):
        assert await page.input_value("#sx") == "IL"
        await page.click("button")

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=8, on_ready=person, close_delay_s=0)
    assert res.ok


async def test_nothing_to_fill_falls_back(store):
    b = _broker("fill_empty", "empty", form=SUCCESS)
    p, _ = _setup(store, b)
    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=5, close_delay_s=0)
    assert res.status == "fallback" and res.reason == "nothing_filled" and res.todo_id


async def test_data_minimization_in_flow(store):
    b = _broker("fill_dm", "labels", form=SUCCESS)
    p, _ = _setup(store, b, shown=(F.FULL_NAME, F.CITY))    # listing does not show state
    got = {}

    async def person(page):
        got["state"] = await page.input_value("#st")
        await page.close()

    with fixture_server():
        res = await fill_bounded(store, p.id, b.id, registry=_registry(b), headed=False,
                                timeout_s=20, on_ready=person, close_delay_s=0)
    assert got["state"] == "" and "state" in res.withheld


async def test_refusals(store):
    from freemyid.models import Consent, ConsentBasis
    b = _broker("fill_ref", "labels", form=SUCCESS)
    mail = Broker(id="fill_mail", name="Dev Mail", url=f"{H}/", category="data_broker",
                  domains=["devfill.example"], method="email",
                  opt_out_email="privacy@devfill.example")
    reg = _registry(b, mail)
    p, _ = _setup(store, b)
    assert (await fill_for_me(store, p.id, "fill_mail", registry=reg)).reason == \
        "not_a_web_form"
    assert (await fill_for_me(store, p.id, "nope", registry=reg)).reason == "unknown_broker"
    bad = p.model_copy(update={"consent": Consent(basis=ConsentBasis.SELF,
                                                  attested_by="Jane Q Testperson",
                                                  text_version="v0-old")})
    store.save_profile(bad)
    r = await fill_for_me(store, p.id, b.id, registry=reg)
    assert r.status == "refused" and r.reason == "consent"
    assert not store.list_todos(p.id)


@pytest.mark.browser
def test_sync_wrapper_and_covered_by_child(store):
    parent = _broker("fill_parent", "labels", form=SUCCESS)
    child = _broker("fill_child", "labels", covered_by="fill_parent")
    p, _ = _setup(store, parent)
    with fixture_server():
        res = fill_for_me_sync(store, p.id, "fill_child", registry=_registry(parent, child),
                               headed=False, timeout_s=1, close_delay_s=0)
    assert res.broker_id == "fill_parent" and res.reason == "timeout"
    assert store.list_todos(p.id)[0].broker_id == "fill_parent"
