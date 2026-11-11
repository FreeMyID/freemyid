"""WO-601 part 2 search specs against the synthetic fixtures in tests/fixtures/search/.

The specs mirror docs/handoff/broker-researcher-wo601.md (usphonebook and smartbackgroundchecks
live only in the private registry; fastpeoplesearch is also in the sample). Fake people only.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from freemyid.engine import exposure as ex
from freemyid.engine import matcher
from freemyid.engine._dev import fixture_registry
from freemyid.models import MatchLevel, SearchSpec
from freemyid.registry import load_registry
from tests.conftest import make_profile

FIX = Path(__file__).parent / "fixtures" / "search"
SAMPLE = Path(__file__).resolve().parents[1] / "brokers" / "registry.sample.yaml"
TODAY = date(2026, 11, 11)

SPECS = {
    "usphonebook": SearchSpec(
        result_selector="div.success-wrapper-block[itemscope]",
        name_selector="h3.ls_number-text > span[itemprop=name]",
        age_selector="h3.ls_number-text",
        location_selector="span[itemprop=address]",
        relatives_selector="a[itemprop=relatedTo] > span[itemprop=name]",
        link_selector="a.ls_contacts-btn"),
    "fastpeoplesearch": SearchSpec(
        result_selector="div.people-list > div.card",
        name_selector="h3.card-title span.larger",
        age_selector="h3.card-title span.grey",
        location_selector="h3.card-title span.grey",
        link_selector="a.link-to-details"),
    "smartbackgroundchecks": SearchSpec(
        result_selector="div.card-block.w-100",
        name_selector="a.name-list-title",
        age_selector="h2 > span.h2SubTitle",
        location_selector="h2 > span.h2SubTitle",
        link_selector="a.name-list-title"),
}
DOMAINS = {
    "usphonebook": ["www.usphonebook.com", "usphonebook.com"],
    "fastpeoplesearch": ["www.fastpeoplesearch.com", "fastpeoplesearch.com"],
    "smartbackgroundchecks": ["www.smartbackgroundchecks.com", "smartbackgroundchecks.com"],
}
SEARCH_URL = {
    "usphonebook": "https://www.usphonebook.com/jane-testperson/il/springfield",
    "fastpeoplesearch": "https://www.fastpeoplesearch.com/name/jane-testperson_springfield-il",
    "smartbackgroundchecks": "https://www.smartbackgroundchecks.com/people/jane-testperson",
}


def _broker(bid: str):
    base = fixture_registry().get("devauto")
    return base.model_copy(update={"id": bid, "domains": DOMAINS[bid], "search": SPECS[bid]})


def _cands(bid: str) -> list[matcher.Candidate]:
    html = (FIX / f"{bid}.html").read_text()
    return ex.parse_candidates(_broker(bid), SEARCH_URL[bid], html)


def _jane():
    return make_profile(dob=date(1962, 4, 1))        # 64 on TODAY, as on the fixture cards


def test_sample_fastpeoplesearch_spec_matches_the_handoff():
    reg = load_registry(SAMPLE)
    assert reg.get("fastpeoplesearch").search == SPECS["fastpeoplesearch"]


def test_usphonebook_reads_cards_not_ads_and_every_relative_and_place():
    cands = _cands("usphonebook")
    assert [c.url for c in cands] == [                # itemscope-less ad slot and teasers excluded
        "https://www.usphonebook.com/jane-testperson/FAKEaaaaaaaaaaaaaaaaaaaaaaaa01",
        "https://www.usphonebook.com/john-example/FAKEbbbbbbbbbbbbbbbbbbbbbbbb02"]
    jane = cands[0]
    assert jane.name == "Jane Q Testperson" and jane.age == 64
    # CR-D: current city plus both past places, both relatives (not just the first)
    assert jane.locations == ["Springfield, IL", "Peoria, IL", "Decatur, IL"]
    assert jane.relatives == ["John Testperson", "Mary Example"]
    assert cands[1].age is None and cands[1].relatives == []


def test_fastpeoplesearch_reads_age_or_city_from_the_grey_span():
    cands = _cands("fastpeoplesearch")
    assert len(cands) == 3
    assert all(c.url.startswith("https://www.fastpeoplesearch.com/") for c in cands)
    assert (cands[0].name, cands[0].age) == ("Jane Q Testperson", 64)
    assert cands[1].age is None and cands[1].locations == ["Peoria, IL"]


def test_smartbackgroundchecks_splits_age_and_city_and_skips_sponsored_cards():
    cands = _cands("smartbackgroundchecks")
    assert len(cands) == 2                           # mw-100 WAM cards excluded
    jane, other = cands
    assert jane.age == 64 and jane.locations == ["Age 64", "Springfield, IL"]   # CR-A
    assert other.age is None and "Peoria, IL" in other.locations


def test_each_wired_spec_scores_only_the_fake_person():
    p = _jane()
    # fastpeoplesearch's card shows name + age only (one signal): review, not auto-submit
    want = {"usphonebook": MatchLevel.CONFIRMED, "smartbackgroundchecks": MatchLevel.CONFIRMED,
            "fastpeoplesearch": MatchLevel.POSSIBLE}
    for bid in SPECS:
        listings = matcher.score_all(p, bid, _cands(bid), TODAY)
        assert [(li.match_level, "jane-testperson" in li.url) for li in listings] == [
            (want[bid], True)], bid


def test_searchpeoplefree_stays_unwired_until_cr_b():
    reg = load_registry(SAMPLE)
    b = reg.get("searchpeoplefree")
    assert b.search is None or not b.search.result_selector
