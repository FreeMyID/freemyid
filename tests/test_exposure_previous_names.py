"""Exposure scan: one optional previous-name (maiden name) search per site. Fake people,
fixture registry and fake fetchers only."""
from __future__ import annotations

from freemyid import config as cfgmod
from freemyid.engine import exposure as ex
from freemyid.engine._dev import fixture_registry
from freemyid.models import Address, PersonName
from freemyid.submitters.web_form import search_url
from tests.conftest import make_profile

MAIN = "https://devauto.example/name/jane-testperson/il"
MAIDEN = "https://devauto.example/name/jane-oldname/il"
OLDNAME = PersonName(first="Jane", last="Oldname")


def _reg():
    reg = fixture_registry()
    brokers = [b.model_copy(update={"search_access": "bot_blocked"}) if b.id == "devblocked"
               else b for b in reg.brokers]
    return reg.model_copy(update={"brokers": brokers})


def _saved(store, **over):
    p = make_profile(**over)
    store.save_profile(p)
    return p


def _page(path: str, name: str) -> str:
    return (f'<div class="result"><a class="view" href="{path}">View</a>'
            f'<span class="name">{name}</span><span class="age">Age 46</span>'
            f'<span class="loc">Springfield, IL</span></div>')


class Calls:
    def __init__(self, page):
        self.urls: list[str] = []
        self.page = page

    def __call__(self, broker, url):
        self.urls.append(url)
        return self.page(broker, url)


def _pages(broker, url):
    if broker.id != "devauto":
        return ex.Fetched(url, 200, "<p>No records found</p>")
    if "oldname" in url:
        return ex.Fetched(url, 200, _page("/p/maiden", "Jane Oldname"))
    return ex.Fetched(url, 200, _page("/p/now", "Jane Q Testperson"))


def _auto(reg):
    return next(b for b in reg.brokers if b.id == "devauto")


def test_search_url_takes_a_name():
    p = make_profile(previous_names=[OLDNAME])
    auto = _auto(_reg())
    assert search_url(auto, p) == MAIN
    assert search_url(auto, p, name=OLDNAME) == MAIDEN


def test_previous_name_url_rules():
    auto = _auto(_reg())
    assert ex.previous_name_url(auto, make_profile()) is None
    same = PersonName(first="Jane", middle="X", last="Testperson")   # same URL as main
    p = make_profile(previous_names=[same, OLDNAME])
    assert ex.previous_name_url(auto, p) == MAIDEN
    addr_only = auto.model_copy(update={"search_url_pattern":
                                        "https://devauto.example/where/{city}/{state}"})
    assert ex.previous_name_url(addr_only, p) is None


def test_previous_names_are_off_by_default(store):
    p = _saved(store, previous_names=[OLDNAME])
    calls = Calls(_pages)
    res = ex.scan_exposure(store, p.id, registry=_reg(), fetch=calls, use_browser=False)
    assert calls.urls == [MAIN]
    assert not res.entries[0].previous_name_checked


def test_previous_name_adds_one_search_and_merges_once(store):
    p = _saved(store, previous_names=[OLDNAME])
    calls, slept = Calls(_pages), []
    res = ex.scan_exposure(store, p.id, registry=_reg(), fetch=calls, use_browser=False,
                           previous_names=True, sleep=slept.append)
    assert calls.urls == [MAIN, MAIDEN]
    auto = next(e for e in res.entries if e.broker_id == "devauto")
    assert auto.previous_name_checked and not auto.old_address_checked
    assert auto.status == "found"
    assert sorted(li.url.rsplit("/", 1)[1] for li in auto.listings) == ["maiden", "now"]
    assert len(store.list_listings(p.id, "devauto")) == 2
    stored = ex.latest_exposure(store, p, _reg())
    assert stored is not None and stored.entries[0].previous_name_checked


def test_old_address_and_previous_name_together(store):
    p = _saved(store, previous_names=[OLDNAME],
               addresses=[Address(city="Springfield", state="IL", current=True),
                          Address(city="Shelbyville", state="IN", to_year=2015)])
    calls = Calls(_pages)
    res = ex.scan_exposure(store, p.id, registry=_reg(), fetch=calls, use_browser=False,
                           previous_names=True, old_addresses=True)
    assert calls.urls == [MAIN, "https://devauto.example/name/jane-testperson/in", MAIDEN]
    e = res.entries[0]
    assert e.old_address_checked and e.previous_name_checked


def test_failed_previous_name_search_keeps_the_main_answer(store):
    p = _saved(store, previous_names=[OLDNAME])

    def flaky(broker, url):
        if "oldname" in url:
            return ex.Fetched(url, 503, "busy")
        return _pages(broker, url)

    res = ex.scan_exposure(store, p.id, registry=_reg(), fetch=Calls(flaky),
                           use_browser=False, previous_names=True)
    e = res.entries[0]
    assert e.status == "found" and not e.previous_name_checked
    assert [li.url.rsplit("/", 1)[1] for li in e.listings] == ["now"]


class _Cfg(cfgmod.Config):
    # stands in for the config field until the orchestrator adds it (CHANGE REQUEST)
    exposure_previous_names: bool = True


def test_previous_names_follow_the_config_flag(store):
    p = _saved(store, previous_names=[OLDNAME])
    cfg = _Cfg(min_delay_s=0, max_delay_s=0)
    calls = Calls(_pages)
    ex.scan_exposure(store, p.id, registry=_reg(), fetch=calls, use_browser=False, cfg=cfg)
    assert calls.urls == [MAIN, MAIDEN]


def test_scan_event_stays_pii_free(store):
    p = _saved(store, previous_names=[OLDNAME])
    ex.scan_exposure(store, p.id, registry=_reg(), fetch=Calls(_pages), use_browser=False,
                     previous_names=True)
    blob = repr([ev.detail for ev in store.events(p.id, limit=100)]).lower()
    assert "oldname" not in blob and "testperson" not in blob


# ------------------------------------------------- unread extra page: unknown, not gone


def test_failed_extra_page_never_marks_earlier_listings_gone(store):
    p = _saved(store, previous_names=[OLDNAME])
    ex.scan_exposure(store, p.id, registry=_reg(), fetch=Calls(_pages), use_browser=False,
                     previous_names=True)

    def flaky(broker, url):
        if "oldname" in url:
            return ex.Fetched(url, 503, "busy")
        return _pages(broker, url)

    res = ex.scan_exposure(store, p.id, registry=_reg(), fetch=Calls(flaky),
                           use_browser=False, previous_names=True, refresh=True)
    assert sorted(li.url.rsplit("/", 1)[1] for li in res.entries[0].listings) == \
        ["maiden", "now"]
    assert all(li.gone_since is None for li in store.list_listings(p.id, "devauto"))


def test_search_variants_follow_config():
    from freemyid.engine.runner import search_variants
    assert search_variants(cfgmod.Config()) == {"old_addresses": False,
                                                "previous_names": False}
    assert search_variants(_Cfg(exposure_old_addresses=True)) == {"old_addresses": True,
                                                                  "previous_names": True}


def _ctx(store, p, variants):
    from types import SimpleNamespace
    return SimpleNamespace(broker=_auto(_reg()), profile=p, store=store, now=None,
                           scratch={"browser": object(), "search_variants": variants})


def _fake_pages(monkeypatch, fail_maiden=False):
    from freemyid.engine import matcher
    from freemyid.submitters import web_form
    seen = []

    async def page(bm, ctx, url):
        seen.append(url)
        if "oldname" in url:
            if fail_maiden:
                raise web_form.UnexpectedPage("search_http_503")
            c = matcher.Candidate(url="https://devauto.example/p/maiden", name="Jane Oldname",
                                  age=46, locations=["Springfield, IL"])
        else:
            c = matcher.Candidate(url="https://devauto.example/p/now",
                                  name="Jane Q Testperson", age=46,
                                  locations=["Springfield, IL"])
        return matcher.score_all(ctx.profile, ctx.broker.id, [c]), b"png"

    monkeypatch.setattr(web_form, "_search_page", page)
    return seen


def test_runner_search_reads_the_same_extra_pages(store, monkeypatch):
    import asyncio

    from freemyid.submitters import web_form
    p = _saved(store, previous_names=[OLDNAME])
    seen = _fake_pages(monkeypatch)
    off = asyncio.run(web_form.search_listings(_ctx(store, p, {})))
    assert seen == [MAIN] and [li.url for li in off] == ["https://devauto.example/p/now"]
    seen.clear()
    ctx = _ctx(store, p, {"previous_names": True})
    on = asyncio.run(web_form.search_listings(ctx))
    assert seen == [MAIN, MAIDEN] and len(on) == 2
    assert ctx.scratch["search_screenshot"] == b"png"


def test_runner_search_keeps_stored_listing_when_extra_page_fails(store, monkeypatch):
    import asyncio

    from freemyid.engine.runner import merge_listings
    from freemyid.models import utcnow
    from freemyid.submitters import web_form
    p = _saved(store, previous_names=[OLDNAME])
    _fake_pages(monkeypatch)
    ctx = _ctx(store, p, {"previous_names": True})
    merge_listings(store, p, ctx.broker, asyncio.run(web_form.search_listings(ctx)), utcnow())
    _fake_pages(monkeypatch, fail_maiden=True)
    again = asyncio.run(web_form.search_listings(_ctx(store, p, {"previous_names": True})))
    merge_listings(store, p, ctx.broker, again, utcnow())
    assert len(again) == 2
    assert all(li.gone_since is None for li in store.list_listings(p.id, "devauto"))
