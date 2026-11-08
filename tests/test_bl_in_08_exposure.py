"""BL-IN-08 exposure scan for a phone/email-only person: only sites with a reverse lookup
for the scope are scanned, each number gets one lookup page, hits are POSSIBLE ("Is this
your number?"), and the name search is never used. Fake people and brokers, no network."""
from __future__ import annotations

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import exposure as ex
from freemyid.engine._dev import fixture_registry
from freemyid.models import (
    Consent,
    ConsentBasis,
    MatchLevel,
    Permissions,
    Profile,
    TodoKind,
)

C = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
            text_version=CURRENT_TEXT_VERSION)
P1, P2 = "217-555-0142", "217-555-0143"
URL1 = "https://devauto.example/phone/217-555-0142"
URL2 = "https://devauto.example/phone/217-555-0143"


def _reg():
    reg = fixture_registry()
    brokers = [b.model_copy(update={
        "phone_search_url_pattern": "https://devauto.example/phone/{phone_dashed}"})
        if b.id == "devauto" else b for b in reg.brokers]
    return reg.model_copy(update={"brokers": brokers})


def _person(store, phones=(P1,)):
    p = Profile(label="T", consent=C, removal_scope="phone", phones=list(phones),
                permissions=Permissions(allow_phone_disclosure=True))
    store.save_profile(p)
    return p


def _hit(path):
    return (f'<div class="result"><a class="view" href="{path}">View</a>'
            f'<span class="name">Someone Testperson</span>'
            f'<span class="loc">Springfield, IL</span></div>')


class Calls:
    def __init__(self, fail=()):
        self.urls: list[str] = []
        self.fail = set(fail)

    def __call__(self, broker, url):
        self.urls.append(url)
        if url in self.fail:
            return ex.Fetched(url, 503, "<p>busy</p>")
        if url == URL1:
            return ex.Fetched(url, 200, _hit("/p/one"))
        if url == URL2:
            return ex.Fetched(url, 200, _hit("/p/two"))
        return ex.Fetched(url, 200, "<p>No records found</p>")


def test_only_sites_with_a_reverse_lookup_are_scanned():
    p = Profile(label="T", consent=C, removal_scope="phone", phones=[P1])
    assert [b.id for b in ex.scan_brokers(_reg(), p)] == ["devauto"]
    assert "devauto" in [b.id for b in ex.scan_brokers(_reg())]          # full mode intact


def test_phone_lookup_hit_is_possible_and_asks_is_this_your_number(store):
    p = _person(store)
    calls = Calls()
    res = ex.scan_exposure(store, p.id, registry=_reg(), fetch=calls, use_browser=False,
                           sleep=lambda s: None)
    assert calls.urls == [URL1]                       # never a name search
    (e,) = res.entries
    assert e.status == "found" and e.match_level is MatchLevel.POSSIBLE
    assert e.check_url == URL1
    (li,) = store.list_listings(p.id, "devauto")
    assert li.match_reasons == ["phone_lookup"]
    todos = [t for t in store.list_todos(p.id) if t.kind == TodoKind.REVIEW_MATCH]
    assert todos and todos[0].title.startswith("Is this T's phone number?")
    assert res.coverage.found == 0 and res.coverage.uncertain == 1   # never "is you"


def test_each_number_gets_one_lookup_and_a_failed_one_keeps_stored_hits(store):
    p = _person(store, phones=(P1, P2))
    ex.scan_exposure(store, p.id, registry=_reg(), fetch=Calls(), use_browser=False,
                     sleep=lambda s: None)
    assert len(store.list_listings(p.id, "devauto")) == 2
    calls = Calls(fail={URL2})
    ex.scan_exposure(store, p.id, registry=_reg(), fetch=calls, use_browser=False,
                     refresh=True, sleep=lambda s: None)
    assert calls.urls == [URL1, URL2]
    assert all(li.gone_since is None for li in store.list_listings(p.id, "devauto"))


def test_no_permission_means_nothing_is_looked_up(store):
    p = Profile(label="T", consent=C, removal_scope="phone", phones=[P1],
                permissions=Permissions(allow_phone_disclosure=True))
    store.save_profile(p)
    p2 = p.model_copy(update={"permissions": Permissions()})
    calls = Calls()
    # the consent gate refuses first; the URL builder would refuse too
    store.save_profile(p2)
    try:
        ex.scan_exposure(store, p2.id, registry=_reg(), fetch=calls, use_browser=False,
                         sleep=lambda s: None)
    except ex.ExposureRefused:
        pass
    assert calls.urls == []
    assert ex._main_urls(_reg().get("devauto"), p2) == []
