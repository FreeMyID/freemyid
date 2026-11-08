"""qa-security wave review 2026-11-08 (Marcus Webb). Fake people only.

Strict xfails mark open findings: each one starts passing (and so fails the suite) when fixed.
"""
from __future__ import annotations

from datetime import date

import pytest

from freemyid.engine import matcher, nicknames
from freemyid.models import MatchLevel, PersonName
from tests.conftest import make_profile

TODAY = date(2026, 11, 8)


def _household(first: str, shown: str, age: int = 60):
    """A profile and another member of the same household: same city, same child listed."""
    p = make_profile(name=PersonName(first=first, last="Testperson"),
                     relatives=["Kim Testperson"], phones=[], emails=[])
    c = matcher.Candidate(url="https://devauto.example/p/1", name=shown,
                          locations=["Springfield, IL"], age=age, relatives=["Kim Testperson"])
    return p, c


def test_nickname_expansion_is_symmetric_without_chaining():
    assert "patrick" in nicknames.expand("pat") and "patricia" in nicknames.expand("pat")
    assert "christina" not in nicknames.expand("christopher")


@pytest.mark.parametrize(("first", "shown"), [("Pat", "Patrick Testperson"),
                                              ("Alexandra", "Alex Testperson")])
def test_sec99_household_member_with_wrong_age_is_not_confirmed(first, shown):
    # Profile born 1980 (about 46). The listing is a 60-year-old in the same house who shares
    # the child as a relative. City and relative are household signals, and the age is 14 years
    # off: this must go to REVIEW_MATCH (POSSIBLE), never to auto-submit.
    p, c = _household(first, shown)
    assert matcher.score(p, c, TODAY).level is not MatchLevel.CONFIRMED


def test_sec99_guard_same_person_still_confirmed():
    # The fix must not lose the real person: right age plus city is still CONFIRMED.
    p, c = _household("Pat", "Pat Testperson", age=46)
    assert matcher.score(p, c, TODAY).level is MatchLevel.CONFIRMED
