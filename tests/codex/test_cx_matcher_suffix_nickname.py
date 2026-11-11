"""Property-style matcher checks for suffixes and nickname confirmation."""
from __future__ import annotations

from datetime import date

from freemyid.engine import matcher
from freemyid.models import Address, MatchLevel, PersonName
from tests.conftest import make_profile

TODAY = date(2026, 11, 9)
SUFFIX_FORMS = {
    "jr": ("Jr", "Jr."),
    "sr": ("Sr", "Sr."),
    "iii": ("III",),
}
NICKNAME_PAIRS = (
    ("Margaret", "Peggy", True),
    ("Robert", "Bob", True),
    ("Pat", "Patrick", False),
    ("Alexandra", "Alex", False),
    ("Christina", "Chris", False),
    ("Robert", "Bert", False),
)


def _profile(first: str, suffix: str | None = None):
    return make_profile(
        label="Jane Q Testperson",
        name=PersonName(first=first, last="Testperson", suffix=suffix),
        addresses=[Address(city="Springfield", state="IL", current=True)],
        dob=date(1980, 4, 1),
        relatives=["Kim Testperson"],
        phones=["217-555-0142"],
        emails=["jane.testperson@example.com"],
    )


def _candidate(name: str, *, age: int | None = None, phone: bool = False,
               email: bool = False) -> matcher.Candidate:
    return matcher.Candidate(
        url="https://devauto.example/p/synthetic-matcher-result",
        name=name,
        age=age,
        locations=["Springfield, IL"],
        relatives=["Kim Testperson"],
        phones=["(217) 555-0142"] if phone else [],
        emails=["JANE.TESTPERSON@example.com"] if email else [],
    )


def test_matching_suffix_never_lowers_score_across_forms() -> None:
    for suffix_group, shown_forms in SUFFIX_FORMS.items():
        own_suffix = shown_forms[0]
        with_suffix = _profile("Jane", own_suffix)
        without_suffix = _profile("Jane")
        for shown_suffix in shown_forms:
            shown = f"Jane Q Testperson {shown_suffix}"
            assert matcher.name_score(with_suffix, shown) >= matcher.name_score(
                without_suffix, shown
            ), (suffix_group, own_suffix, shown_suffix)


def test_conflicting_suffix_never_raises_score_for_any_pair() -> None:
    plain = _profile("Jane")
    for owned_group, own_forms in SUFFIX_FORMS.items():
        for shown_group, shown_forms in SUFFIX_FORMS.items():
            if owned_group == shown_group:
                continue
            for own_suffix in own_forms:
                profile = _profile("Jane", own_suffix)
                for shown_suffix in shown_forms:
                    shown = f"Jane Q Testperson {shown_suffix}"
                    baseline = matcher.name_score(plain, shown)
                    actual = matcher.name_score(profile, shown)
                    assert actual <= baseline, (
                        own_suffix, shown_suffix, actual, baseline,
                    )


def test_nickname_with_shared_household_signals_needs_personal_evidence() -> None:
    """City+relative cannot confirm a nickname; personal evidence follows SEC-99/103."""
    for first, shown_first, age_can_disambiguate in NICKNAME_PAIRS:
        profile = _profile(first)
        shown = f"{shown_first} Testperson"

        without_personal_detail = matcher.score(profile, _candidate(shown), TODAY)
        assert without_personal_detail.level is MatchLevel.POSSIBLE, (
            first, shown_first, without_personal_detail,
        )
        assert "city" in without_personal_detail.reasons
        assert "relative" in without_personal_detail.reasons
        assert not {"age", "phone", "email"}.intersection(without_personal_detail.reasons)

        with_age = matcher.score(profile, _candidate(shown, age=46), TODAY)
        if age_can_disambiguate:
            assert with_age.level is MatchLevel.CONFIRMED, (first, shown_first, with_age)
            assert "age" in with_age.reasons
        else:
            assert with_age.level is MatchLevel.POSSIBLE, (first, shown_first, with_age)

        for signal in ("phone", "email"):
            result = matcher.score(
                profile,
                _candidate(shown, **{signal: True}),
                TODAY,
            )
            assert result.level is MatchLevel.CONFIRMED, (first, shown_first, signal, result)
            assert signal in result.reasons
