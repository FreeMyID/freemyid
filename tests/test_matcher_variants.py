"""Matcher name variants: common nicknames, the profile's own nicknames, previous (maiden)
names. Fake people only."""
from __future__ import annotations

from datetime import date

import pytest

from freemyid.engine import matcher, nicknames
from freemyid.models import MatchLevel, PersonName
from tests.conftest import make_profile

TODAY = date(2026, 11, 8)


def _p(**over):
    base = {"name": PersonName(first="Margaret", middle="Q", last="Testperson"),
            "previous_names": [PersonName(first="Margaret", last="Oldname")]}
    base.update(over)
    return make_profile(**base)


def _c(name, **kw):
    kw.setdefault("locations", ["Springfield, IL"])
    kw.setdefault("age", 46)
    return matcher.Candidate(url="https://devauto.example/p/1", name=name, **kw)


def test_expand_is_symmetric_and_does_not_chain():
    assert "peggy" in nicknames.expand("margaret")
    assert "margaret" in nicknames.expand("peggy")
    assert "christina" not in nicknames.expand("christopher")
    assert {"christopher", "christina"} <= nicknames.expand("chris")
    assert nicknames.expand("zebulonia") == {"zebulonia"}
    assert nicknames.expand("") == set()


def test_common_nickname_matches_and_still_needs_two_signals():
    p = _p()
    assert matcher.score(p, _c("Peggy Testperson"), TODAY).level == MatchLevel.CONFIRMED
    one = matcher.score(p, _c("Peggy Testperson", locations=[]), TODAY)
    assert one.level == MatchLevel.POSSIBLE and one.reasons == ["age"]
    none = matcher.score(p, _c("Peggy Testperson", locations=[], age=None), TODAY)
    assert none.level == MatchLevel.NO_MATCH


def test_reverse_direction_profile_uses_the_short_form():
    p = _p(name=PersonName(first="Bob", last="Testperson"), previous_names=[])
    assert matcher.name_score(p, "Robert Testperson") == 100.0


def test_maiden_name_with_a_nickname():
    p = _p()
    assert matcher.name_score(p, "Peggy Oldname") == 100.0
    assert matcher.score(p, _c("Maggie Oldname"), TODAY).level == MatchLevel.CONFIRMED


def test_profile_nicknames_are_expanded_too():
    p = _p(name=PersonName(first="Zebulonia", last="Testperson"), previous_names=[],
           nicknames=["Liz"])
    assert matcher.name_score(p, "Elizabeth Testperson") == 100.0


def test_unrelated_first_name_does_not_match():
    p = _p()
    assert matcher.score(p, _c("Patricia Testperson"), TODAY).level == MatchLevel.NO_MATCH
    assert matcher.score(p, _c("Peggy Otherfamily"), TODAY).level == MatchLevel.NO_MATCH


def test_default_profile_unchanged():
    p = make_profile()
    assert matcher.name_score(p, "Jane Q Testperson") == 100.0
    assert matcher.score(p, _c("Jane Testperson", age=None, phones=["2175550142"]),
                         TODAY).level == MatchLevel.CONFIRMED


# ------------------------------------------------------------ SEC-99 household guard


def _house(first, shown, age, **kw):
    p = make_profile(name=PersonName(first=first, last="Testperson"),
                     relatives=["Kim Testperson"], phones=["217-555-0142"], emails=[])
    c = matcher.Candidate(url="https://devauto.example/p/1", name=shown, age=age,
                          locations=["Springfield, IL"], relatives=["Kim Testperson"], **kw)
    return matcher.score(p, c, TODAY)


def test_age_gap_caps_at_possible_even_with_exact_name_and_phone():
    r = _house("Pat", "Pat Testperson", 60, phones=["2175550142"])
    assert r.level == MatchLevel.POSSIBLE
    assert _house("Pat", "Pat Testperson", 51).level == MatchLevel.CONFIRMED  # 5 off: ok
    assert _house("Pat", "Pat Testperson", 52).level == MatchLevel.POSSIBLE


def test_nickname_group_name_needs_a_personal_signal():
    # city + relative only: the household shares both
    assert _house("Pat", "Patrick Testperson", None).level == MatchLevel.POSSIBLE
    assert _house("Margaret", "Peggy Testperson", 46).level == MatchLevel.CONFIRMED
    assert _house("Pat", "Patrick Testperson", None,
                  phones=["217-555-0142"]).level == MatchLevel.CONFIRMED


# ------------------------------------------------------------ SEC-103 close-age spouse


@pytest.mark.parametrize(("first", "shown"), [
    ("Pat", "Patrick Testperson"),          # Pat is also Patricia
    ("Pat", "Testperson, Patrick"),         # surname-first layout
    ("Alexandra", "Alex Testperson"),       # Alex is also Alexander
    ("Christina", "Chris Testperson"),      # Chris: three groups
    ("Robert", "Bert Testperson"),          # Bert is also Albert
    ("Jane", "Jan Testperson"),             # fuzzy, and Jan is Janet
])
def test_sec103_another_persons_name_needs_phone_or_email(first, shown):
    # city + relative + an age within 2 years: a spouse can show all three
    assert _house(first, shown, 47).level == MatchLevel.POSSIBLE
    assert _house(first, shown, 47, phones=["217-555-0142"]).level == MatchLevel.CONFIRMED


@pytest.mark.parametrize(("first", "shown"), [
    ("Margaret", "Peggy Testperson"),       # one group, both sides
    ("Robert", "Bob Testperson"),
    ("Bob", "Robert Testperson"),
    ("Pat", "Pat Testperson"),              # the person's own name
    ("Jane", "Jane Q Testperson"),
    ("Jane", "Jayne Testperson"),           # fuzzy, not a known given name: SEC-99 rules
])
def test_sec103_same_person_still_confirmed_on_age(first, shown):
    assert _house(first, shown, 47).level == MatchLevel.CONFIRMED


def test_sec103_own_nickname_is_trusted():
    p = make_profile(name=PersonName(first="Pat", last="Testperson"), nicknames=["Patrick"],
                     relatives=["Kim Testperson"], phones=[], emails=[])
    c = matcher.Candidate(url="https://devauto.example/p/1", name="Patrick Testperson",
                          age=47, locations=["Springfield, IL"], relatives=["Kim Testperson"])
    assert matcher.score(p, c, TODAY).level == MatchLevel.CONFIRMED


def test_groups_of():
    assert nicknames.groups_of("pat") == {"patricia", "patrick"}
    assert nicknames.groups_of("peggy") == {"margaret"}
    assert nicknames.groups_of("zebulon") == frozenset()


def test_exact_name_with_household_signals_still_confirms_when_age_unknown():
    assert _house("Pat", "Pat Testperson", None).level == MatchLevel.CONFIRMED


def test_own_nickname_counts_as_exact():
    p = make_profile(name=PersonName(first="Patricia", last="Testperson"), nicknames=["Trish"])
    assert matcher.exact_name(p, "Trish Testperson")
    assert not matcher.exact_name(p, "Patty Testperson")
