"""Table-driven fake-name coverage for matcher variants and SEC-103 household cases."""
from __future__ import annotations

from datetime import date

import pytest

from freemyid.engine import matcher, nicknames
from freemyid.models import MatchLevel, PersonName
from tests.conftest import make_profile

TODAY = date(2026, 11, 8)


def _profile(first: str, last: str = "Testperson", **over):
    profile_data = {
        "name": PersonName(first=first, last=last),
        "relatives": ["Kim Testperson"],
        "phones": [],
        "emails": [],
    }
    profile_data.update(over)
    return make_profile(**profile_data)


def _candidate(shown: str, **over) -> matcher.Candidate:
    return matcher.Candidate(
        url="https://devauto.example/p/fake-name",
        name=shown,
        locations=["Springfield, IL"],
        age=47,
        relatives=["Kim Testperson"],
        **over,
    )


@pytest.mark.parametrize(
    ("profile_first", "shown_first"),
    [
        ("Margaret", "Peggy"),
        ("Peggy", "Margaret"),
        ("Robert", "Bob"),
        ("Bob", "Robert"),
        ("Elizabeth", "Liz"),
        ("Liz", "Elizabeth"),
        ("William", "Liam"),
        ("Liam", "William"),
    ],
)
def test_common_nickname_match_works_in_both_directions(
    profile_first: str, shown_first: str
) -> None:
    profile = _profile(profile_first)
    shown = f"{shown_first} Testperson"

    assert matcher.name_score(profile, shown) == 100.0
    assert matcher.score(profile, _candidate(shown), TODAY).level is MatchLevel.CONFIRMED


@pytest.mark.parametrize(
    ("profile_name", "shown"),
    [
        (PersonName(first="Pat", last="Testperson-Smith"), "Pat Testperson Smith"),
        (PersonName(first="Pat", last="Testperson Smith"), "Pat Testperson-Smith"),
        (PersonName(first="Pat", last="Testperson-Smith"), "Pat Testperson-Smith"),
        (PersonName(first="José", last="O’Neil"), "Jose O'Neil"),
        (PersonName(first="D'Arcy", last="Testperson"), "D Arcy Testperson"),
        (PersonName(first="Pat", middle="Quinn", last="Testperson"), "Pat Q. Testperson"),
        (PersonName(first="Pat", middle="Quinn", last="Testperson"), "Pat Testperson"),
        (PersonName(first="Pat", last="Testperson", suffix="Jr."), "Pat Testperson Jr."),
        (PersonName(first="Pat", last="Testperson", suffix="III"), "Pat Testperson III"),
        (PersonName(first="Pat", last="Testperson", suffix="Sr."), "Pat Testperson"),
    ],
)
def test_punctuation_surname_diacritic_initial_and_suffix_variants(
    profile_name: PersonName, shown: str
) -> None:
    profile = _profile(profile_name.first, profile_name.last, name=profile_name)

    assert matcher.name_score(profile, shown) >= matcher.NAME_THRESHOLD
    assert matcher.score(profile, _candidate(shown), TODAY).level is MatchLevel.CONFIRMED


@pytest.mark.parametrize(
    ("first", "shown"),
    [
        ("Pat", "Patrick Testperson"),
        ("Pat", "Testperson, Patrick"),
        ("Alexandra", "Alex Testperson"),
        ("Christina", "Chris Testperson"),
        ("Robert", "Bert Testperson"),
        ("Jane", "Jan Testperson"),
    ],
)
def test_sec103_possible_without_contact_and_confirmed_with_contact(
    first: str, shown: str
) -> None:
    profile = _profile(first, emails=["pat.testperson@example.com"])

    # Location, relative, and a close age can all be shared by another household member.
    assert matcher.score(profile, _candidate(shown), TODAY).level is MatchLevel.POSSIBLE
    assert matcher.score(
        profile, _candidate(shown, emails=["pat.testperson@example.com"]), TODAY
    ).level is MatchLevel.CONFIRMED


@pytest.mark.parametrize(
    ("first", "shown"),
    [
        ("Margaret", "Peggy Testperson"),
        ("Pat", "Pat Testperson"),
        ("Robert", "Bob Testperson"),
        ("Bob", "Robert Testperson"),
    ],
)
def test_sec103_unambiguous_nickname_or_own_name_can_confirm_on_age(
    first: str, shown: str
) -> None:
    profile = _profile(first)

    assert matcher.score(profile, _candidate(shown), TODAY).level is MatchLevel.CONFIRMED


@pytest.mark.parametrize(
    ("first", "shown"),
    [("Pat", "Patrick Testperson"), ("Alexandra", "Alex Testperson")],
)
def test_sec103_contact_signal_can_be_phone_or_email(first: str, shown: str) -> None:
    profile = _profile(first, phones=["217-555-0142"])
    candidate = _candidate(shown, phones=["2175550142"])

    result = matcher.score(profile, candidate, TODAY)

    assert result.level is MatchLevel.CONFIRMED
    assert "phone" in result.reasons


@pytest.mark.parametrize(
    ("left", "right"),
    [("pat", "patricia"), ("pat", "patrick"), ("chris", "christina"),
     ("chris", "christopher"), ("peggy", "margaret")],
)
def test_nickname_expansion_is_symmetric_without_chaining(left: str, right: str) -> None:
    assert right in nicknames.expand(left)
    assert left in nicknames.expand(right)


def test_nickname_expansion_does_not_chain_between_groups() -> None:
    assert "christina" in nicknames.expand("chris")
    assert "christopher" in nicknames.expand("chris")
    assert "christina" not in nicknames.expand("christopher")
