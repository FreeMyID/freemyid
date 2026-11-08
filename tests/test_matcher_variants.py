"""Matcher name variants: common nicknames, the profile's own nicknames, previous (maiden)
names. Fake people only."""
from __future__ import annotations

from datetime import date

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
