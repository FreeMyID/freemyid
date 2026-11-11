"""WO-339: a broker only gets fields its listings already show.

Seeded cases (random.Random(339)) cover required_fields set and unset, blind brokers with
no listing, and shown_fields subsets. Jane Q Testperson of Springfield, IL only.

The removal mailbox is the one email that may be sent when the listing does not show an
email (Listing.shown_fields: shown fields, plus the removal mailbox). A personal email,
a phone the listing does not show, a date of birth and a past address never are.
"""
from __future__ import annotations

import random
import re
import socket
from datetime import date
from typing import NamedTuple

import pytest

from freemyid.models import (
    Address,
    Broker,
    Listing,
    MailboxConfig,
    MatchLevel,
    Permissions,
    Profile,
    ProfileField,
)
from freemyid.submitters import base
from tests.conftest import make_profile

F = ProfileField
PHONE = "217-555-0142"
PERSONAL_EMAIL = "jane.testperson@example.com"
RELATIVE = "John Testperson"
PAST_STREET = "500 Former Lane"
PAST_ZIP = "62701"
CURRENT = Address(street="742 Evergreen Terrace", city="Springfield", state="IL",
                  zip="62704", current=True)
PAST = Address(street=PAST_STREET, city="Springfield", state="IL", zip=PAST_ZIP,
               current=False, to_year=2010)
MB = MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                   smtp_host="smtp.example.com", username="removals.testperson@example.com")
# Shown full name is sent as first + last. Middle stays a separate field (never folded in).
BARE_NAME = "Jane Testperson"
WITH_MIDDLE = "Jane Q Testperson"
# A fixed day keeps the "real age" check stable; base.py never reads the clock for age.
TODAY = date(2026, 11, 11)
_DOB_TEXT = ("1980-04-01", "04/01/1980", "4/1/1980", "1980/04/01", "04-01-1980", "1980")
_COPY_FIELD = {
    "Full name": F.FULL_NAME,
    "First name": F.FIRST_NAME,
    "Last name": F.LAST_NAME,
    "City": F.CITY,
    "State": F.STATE,
    "Street address": F.STREET_ADDRESS,
    "ZIP code": F.ZIP,
    "Age": F.AGE,
    "Phone": F.PHONE,
    "Email for removals": F.EMAIL,
}
_FORM_ATTR = {
    "full_name": F.FULL_NAME,
    "first": F.FIRST_NAME,
    "last": F.LAST_NAME,
    "middle": F.MIDDLE_NAME,
    "city": F.CITY,
    "state": F.STATE,
    "street": F.STREET_ADDRESS,
    "zip": F.ZIP,
    "age": F.AGE,
    "phone": F.PHONE,
}


class Case(NamedTuple):
    n: int
    label: str
    required: tuple[ProfileField, ...] | None
    shown: tuple[tuple[ProfileField, ...], ...]
    ages: tuple[int | None, ...]
    levels: tuple[MatchLevel, ...]
    phone_ok: bool
    mailbox: bool
    address: str


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: object) -> None:
    """Fail closed on any socket use, after the suite's loopback-only guard."""
    del freemyid_env

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network is disabled")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _broker(required: tuple[ProfileField, ...] | None) -> Broker:
    kw: dict[str, list[ProfileField]] = {}
    if required is not None:
        kw["required_fields"] = list(required)
    return Broker(id="fakeb", name="Fake B", url="https://fakeb.example/",
                  category="data_broker", domains=["fakeb.example"], method="email",
                  opt_out_email="privacy@fakeb.example", **kw)


def _profile(case: Case) -> Profile:
    if case.address == "current":
        addresses = [CURRENT]
    elif case.address == "both":
        addresses = [PAST, CURRENT]
    elif case.address == "past":
        addresses = [PAST]
    else:
        raise AssertionError(case.address)
    return make_profile(addresses=addresses, mailbox=MB if case.mailbox else None,
                        permissions=Permissions(allow_phone_disclosure=case.phone_ok))


def _listings(profile: Profile, case: Case) -> list[Listing]:
    out: list[Listing] = []
    for i, shown in enumerate(case.shown):
        age = case.ages[i] if i < len(case.ages) else None
        level = case.levels[i] if i < len(case.levels) else MatchLevel.CONFIRMED
        out.append(Listing(
            profile_id=profile.id, broker_id="fakeb", url=f"https://fakeb.example/p/{i + 1}",
            name_shown=BARE_NAME, age_shown=age, locations_shown=["Springfield, IL"],
            match_score=90.0, match_level=level, shown_fields=list(shown)))
    return out


def _legal(profile: Profile, broker: Broker, listings: list[Listing]) -> set[ProfileField]:
    """Upper bound from shared rule 6. allowed_fields may be a subset; a superset is a leak."""
    if not listings:
        legal = {F.FULL_NAME, F.FIRST_NAME, F.LAST_NAME, F.EMAIL}
        if F.CITY in broker.required_fields:
            legal.add(F.CITY)
        if F.STATE in broker.required_fields:
            legal.add(F.STATE)
        return legal
    shown = {field for li in listings for field in li.shown_fields}
    legal = set(shown) | {F.LISTING_URL, F.EMAIL}
    if F.FULL_NAME in shown:
        legal |= {F.FIRST_NAME, F.LAST_NAME}
    legal -= {F.DOB, F.ID_DOCUMENT}
    if F.PHONE not in shown or not profile.permissions.allow_phone_disclosure:
        legal.discard(F.PHONE)
    return legal


def _current(profile: Profile) -> Address | None:
    return next((a for a in profile.addresses if a.current), None)


def _banned(profile: Profile, listings: list[Listing]) -> list[str]:
    return [PERSONAL_EMAIL, RELATIVE, PAST_STREET, PAST_ZIP, WITH_MIDDLE, *_DOB_TEXT]


def _real_age_unshown(profile: Profile, listings: list[Listing]) -> int | None:
    """The computed age, when no listing shows that same age (it must then never be sent)."""
    shown_ages = {li.age_shown for li in listings if li.age_shown is not None}
    real = profile.estimated_age(TODAY)
    return real if real is not None and real not in shown_ages else None


def _assert_text_clean(blob: str, profile: Profile, listings: list[Listing], where: str) -> None:
    for bad in _banned(profile, listings):
        assert bad not in blob, (where, bad)
    real = _real_age_unshown(profile, listings)
    if real is not None:
        # Whole number only: "55" inside the phone 217-555-0142 is not an age.
        assert not re.search(rf"(?<!\d){real}(?!\d)", blob), (where, real)
    if _current(profile) is None:
        assert "Springfield" not in blob and "Evergreen" not in blob, where
    if PHONE in blob:
        assert any(F.PHONE in li.shown_fields for li in listings), where
        assert profile.permissions.allow_phone_disclosure, where


def _assert_copy(profile: Profile, broker: Broker, listings: list[Listing],
                 allowed: set[ProfileField], legal: set[ProfileField]) -> dict[str, str]:
    copied = base.copy_fields(profile, broker, listings)
    current = _current(profile)
    urls = {li.url for li in listings}
    for key, value in copied.items():
        if key.startswith("Listing link"):
            assert listings and value in urls, key
            continue
        field = _COPY_FIELD[key]
        assert field in allowed and field in legal, (key, field)
        if key == "Full name":
            assert value == BARE_NAME
        elif key == "First name":
            assert value == profile.name.first
        elif key == "Last name":
            assert value == profile.name.last
        elif key == "City":
            assert current is not None and value == current.city
        elif key == "State":
            assert current is not None and value == current.state
        elif key == "Street address":
            assert current is not None and value == current.street
        elif key == "ZIP code":
            assert current is not None and value == current.zip
        elif key == "Age":
            assert value in {str(li.age_shown) for li in listings if li.age_shown is not None}
        elif key == "Phone":
            assert value == PHONE
        elif key == "Email for removals":
            assert profile.mailbox is not None and value == profile.mailbox.address
    _assert_text_clean("\n".join(copied.values()), profile, listings, "copy_fields")
    return copied


def _assert_form(profile: Profile, broker: Broker, listing: Listing | None) -> dict:
    group = [listing] if listing is not None else []
    allowed = base.allowed_fields(profile, broker, group)
    legal = _legal(profile, broker, group)
    assert allowed <= legal, (sorted(allowed - legal),)
    assert F.DOB not in allowed and F.ID_DOCUMENT not in allowed
    fv = base.form_vars(profile, broker, listing)
    current = _current(profile)
    attrs = vars(fv["profile"])
    assert set(attrs) <= set(_FORM_ATTR)
    for name, value in attrs.items():
        field = _FORM_ATTR[name]
        assert field in allowed and field in legal, name
        if name == "full_name":
            assert value == BARE_NAME
        elif name == "first":
            assert value == profile.name.first
        elif name == "last":
            assert value == profile.name.last
        elif name == "middle":
            assert value == profile.name.middle
        elif name == "city":
            assert current is not None and value == current.city
        elif name == "state":
            assert current is not None and value == current.state
        elif name == "street":
            assert current is not None and value == current.street
        elif name == "zip":
            assert current is not None and value == current.zip
        elif name == "age":
            assert value in {li.age_shown for li in group if li.age_shown is not None}
        elif name == "phone":
            assert value == PHONE
    if profile.mailbox is None:
        assert fv["mailbox"] is None
    else:
        assert fv["mailbox"].address == profile.mailbox.address
    if listing is None:
        assert fv["listing"] is None
    else:
        assert fv["listing"].url == listing.url
    parts = [str(v) for v in attrs.values()]
    if fv["mailbox"] is not None:
        parts.append(fv["mailbox"].address)
    if fv["listing"] is not None:
        parts.append(fv["listing"].url)
    _assert_text_clean("\n".join(parts), profile, group, "form_vars")
    return fv


def _assert_minimized(case: Case) -> dict[str, str]:
    profile = _profile(case)
    broker = _broker(case.required)
    listings = _listings(profile, case)
    allowed = base.allowed_fields(profile, broker, listings)
    legal = _legal(profile, broker, listings)
    assert allowed <= legal, (case.label or case.n, sorted(allowed - legal))
    assert F.DOB not in allowed and F.ID_DOCUMENT not in allowed
    copied = _assert_copy(profile, broker, listings, allowed, legal)
    if listings:
        for li in listings:
            _assert_form(profile, broker, li)
    else:
        _assert_form(profile, broker, None)
    _label_locks(case, profile, broker, listings, allowed, copied)
    return copied


def _label_locks(case: Case, profile: Profile, broker: Broker, listings: list[Listing],
                 allowed: set[ProfileField], copied: dict[str, str]) -> None:
    """Named rows are the regressions for leaks the sweep found in base.py."""
    blob = "\n".join(copied.values())
    if case.label == "blind-unset":
        assert copied["Full name"] == BARE_NAME
        assert copied["Email for removals"] == MB.address
        assert "City" not in copied and "State" not in copied and "Phone" not in copied
        form = base.form_vars(profile, broker, None)
        assert form["profile"].full_name == BARE_NAME
        assert not hasattr(form["profile"], "city")
        assert not hasattr(form["profile"], "middle")
    elif case.label == "blind-requires-city-not-street":
        assert copied["City"] == "Springfield" and copied["State"] == "IL"
        assert copied["Full name"] == BARE_NAME
        for key in ("Street address", "ZIP code", "Phone", "Age"):
            assert key not in copied
        assert F.PHONE not in allowed and F.DOB not in allowed and F.STREET_ADDRESS not in allowed
    elif case.label == "listing-hides-name":
        assert F.FULL_NAME not in allowed and F.FIRST_NAME not in allowed
        assert "Full name" not in copied and "Testperson" not in blob
        assert copied["City"] == "Springfield" and "State" not in copied
        assert PHONE not in blob
    elif case.label == "first-name-does-not-widen":
        form = base.form_vars(profile, broker, listings[0])
        assert form["profile"].first == "Jane"
        assert not hasattr(form["profile"], "last")
        assert not hasattr(form["profile"], "full_name")
        assert copied.get("First name") == "Jane"
        assert "Last name" not in copied and "Full name" not in copied
        assert "Testperson" not in blob
    elif case.label == "past-address-not-used":
        for key in ("City", "State", "Street address", "ZIP code"):
            assert key not in copied
        assert PAST_STREET not in blob and PAST_ZIP not in blob
        assert copied["Full name"] == BARE_NAME
        form = base.form_vars(profile, broker, listings[0])
        assert not any(hasattr(form["profile"], name) for name in
                       ("city", "state", "street", "zip"))
    elif case.label == "shown-current-fields-arrive":
        assert copied["Full name"] == BARE_NAME
        assert copied["Street address"] == CURRENT.street
        assert copied["ZIP code"] == CURRENT.zip
        assert copied["City"] == "Springfield" and copied["State"] == "IL"
        assert copied["Phone"] == PHONE and copied["Age"] == str(case.ages[0])
        assert copied["Email for removals"] == MB.address
        form = base.form_vars(profile, broker, listings[0])
        assert form["profile"].age == case.ages[0] and form["profile"].middle == "Q"
        assert form["profile"].street == CURRENT.street
        assert "1980" not in blob and PERSONAL_EMAIL not in blob and RELATIVE not in blob
    elif case.label == "phone-not-shown":
        assert F.PHONE not in allowed and PHONE not in blob
        assert copied["Full name"] == BARE_NAME
    elif case.label == "phone-needs-permission":
        assert F.PHONE not in allowed and PHONE not in blob
    elif case.label == "dob-shown-withheld":
        assert F.DOB not in allowed and F.AGE not in allowed
        form = base.form_vars(profile, broker, listings[0])
        assert not hasattr(form["profile"], "age")
        assert "1980" not in blob


def _ages_ok() -> tuple[int, ...]:
    real = make_profile().estimated_age(TODAY)
    return tuple(n for n in (33, 52, 61, 70) if n != real)


def _build_cases() -> list[Case]:
    shown_age = 52 if 52 in _ages_ok() else _ages_ok()[0]
    every = tuple(F)
    corners = [
        Case(0, "blind-unset", None, (), (), (), True, True, "both"),
        Case(1, "blind-requires-city-not-street",
             (F.CITY, F.STATE, F.STREET_ADDRESS, F.ZIP, F.PHONE, F.DOB, F.AGE),
             (), (), (), True, True, "both"),
        Case(2, "listing-hides-name", None, ((F.CITY,),), (None,), (MatchLevel.CONFIRMED,),
             True, True, "both"),
        Case(3, "first-name-does-not-widen",
             (F.FIRST_NAME, F.LAST_NAME, F.FULL_NAME), ((F.FIRST_NAME,),),
             (None,), (MatchLevel.CONFIRMED,), False, False, "current"),
        Case(4, "past-address-not-used",
             (F.FULL_NAME, F.CITY, F.STATE, F.STREET_ADDRESS, F.ZIP),
             ((F.FULL_NAME, F.CITY, F.STATE, F.STREET_ADDRESS, F.ZIP),),
             (None,), (MatchLevel.CONFIRMED,), False, False, "past"),
        Case(5, "shown-current-fields-arrive", every, (every,), (shown_age,),
             (MatchLevel.CONFIRMED,), True, True, "both"),
        Case(6, "phone-not-shown", (F.PHONE, F.FULL_NAME), ((F.FULL_NAME,),),
             (None,), (MatchLevel.POSSIBLE,), True, True, "current"),
        Case(7, "phone-needs-permission", (F.PHONE, F.FULL_NAME),
             ((F.PHONE, F.FULL_NAME),), (None,), (MatchLevel.CONFIRMED,), False, False,
             "current"),
        Case(8, "dob-shown-withheld", (F.DOB, F.AGE, F.FULL_NAME), ((F.DOB, F.FULL_NAME),),
             (None,), (MatchLevel.CONFIRMED,), False, True, "current"),
    ]
    rng = random.Random(339)
    pool = list(F)
    ages = (None, *_ages_ok())
    levels = (MatchLevel.CONFIRMED, MatchLevel.POSSIBLE)
    random_rows: list[Case] = []
    for n in range(9, 48):
        count = 0 if rng.randrange(4) == 0 else rng.randint(1, 3)
        shown, row_ages, row_levels = [], [], []
        for _ in range(count):
            shown.append(tuple(rng.sample(pool, rng.randint(0, len(pool)))))
            row_ages.append(rng.choice(ages))
            row_levels.append(rng.choice(levels))
        required = None
        if rng.randrange(2) == 1:
            required = tuple(rng.sample(pool, rng.randint(1, len(pool))))
        random_rows.append(Case(
            n, "", required, tuple(shown), tuple(row_ages), tuple(row_levels),
            bool(rng.randrange(2)), bool(rng.randrange(2)),
            rng.choice(("current", "both", "past"))))
    return corners + random_rows


CASES = _build_cases()


def _case_id(case: Case) -> str:
    if case.label:
        return case.label
    kind = "blind" if not case.shown else f"li{len(case.shown)}"
    needed = "unset" if case.required is None else f"req{len(case.required)}"
    return f"{case.n}-{kind}-{needed}-{case.address}"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_generated_broker_gets_only_shown_or_blind_fields(case: Case) -> None:
    _assert_minimized(case)


def test_case_matrix_covers_blind_unset_past_and_shown_subsets() -> None:
    assert len(CASES) >= 40
    assert any(not case.shown for case in CASES)
    assert any(case.required is None for case in CASES)
    assert any(case.required for case in CASES)
    assert any(case.address == "past" for case in CASES)
    assert any(case.shown and set(case.shown[0]) < set(F) for case in CASES)
    assert {case.label for case in CASES} >= {
        "blind-unset", "listing-hides-name", "past-address-not-used",
        "first-name-does-not-widen", "dob-shown-withheld",
    }


def test_socket_connect_and_create_connection_raise() -> None:
    with socket.socket() as sock, pytest.raises(AssertionError, match="network is disabled"):
        sock.connect(("example.com", 443))
    with pytest.raises(AssertionError, match="network is disabled"):
        socket.create_connection(("example.com", 80))


def test_real_age_check_is_whole_number_and_date_stable() -> None:
    """CodeRabbit #113: the age guard must not depend on today's date or digit substrings."""
    aged_55 = make_profile(dob=date(1971, 4, 1), addresses=[CURRENT],
                           permissions=Permissions(allow_phone_disclosure=True))
    assert aged_55.estimated_age(TODAY) == 55
    li = Listing(profile_id=aged_55.id, broker_id="fakeb", url="https://fakeb.example/p/1",
                 name_shown=BARE_NAME, match_score=90.0, match_level=MatchLevel.CONFIRMED,
                 shown_fields=[F.FULL_NAME, F.PHONE])
    _assert_text_clean(f"{BARE_NAME}\n{PHONE}", aged_55, [li], "phone holds 55")
    with pytest.raises(AssertionError):
        _assert_text_clean(f"{BARE_NAME}\nAge 55", aged_55, [li], "age sent")
