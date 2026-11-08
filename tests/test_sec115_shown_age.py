"""SEC-115: forms, copy fields and letters send the age the listing itself shows, never the
person's real age computed from their birth year. Fake people and brokers only."""
from __future__ import annotations

from datetime import date

from freemyid.engine import letters
from freemyid.models import Broker, Listing, MatchLevel, ProfileField
from freemyid.submitters import base
from tests.conftest import make_profile

F = ProfileField
B = Broker.model_validate({
    "id": "fakeb", "name": "Fake B", "url": "https://fakeb.example/",
    "category": "people_search", "domains": ["fakeb.example"], "method": "email",
    "opt_out_email": "privacy@fakeb.example",
    "required_fields": ["full_name", "city", "state", "age"]})
REAL_AGE = make_profile().estimated_age(date(2026, 11, 8))      # born 1980: 46


def _listing(p, age, level=MatchLevel.CONFIRMED, url="https://fakeb.example/p/1"):
    return Listing(profile_id=p.id, broker_id=B.id, url=url, name_shown="Jane Testperson",
                   age_shown=age, locations_shown=["Springfield, IL"], match_score=90.0,
                   match_level=level, shown_fields=[F.LISTING_URL, F.FULL_NAME, F.CITY,
                                                    F.STATE] + ([F.AGE] if age else []))


def test_shown_age_prefers_confirmed_listings():
    p = make_profile()
    poss = _listing(p, 60, MatchLevel.POSSIBLE, "https://fakeb.example/p/2")
    assert base.shown_age([poss, _listing(p, 52)]) == 52
    assert base.shown_age([_listing(p, None)]) is None


def test_copy_fields_send_the_listing_age_not_the_real_one():
    p = make_profile()
    out = base.copy_fields(p, B, [_listing(p, 52)])
    assert out["Age"] == "52" and str(REAL_AGE) not in out.values()


def test_form_vars_age_is_the_listing_age_or_absent():
    p = make_profile()
    assert base.form_vars(p, B, _listing(p, 52))["profile"].age == 52
    assert not hasattr(base.form_vars(p, B, _listing(p, None))["profile"], "age")


def test_letter_age_is_the_listing_age():
    p = make_profile()
    v = letters.letter_vars(p, B, [_listing(p, 52)])
    assert v["age"] == 52
    body = letters.render("generic_removal", **v)
    assert "Approximate age shown: 52" in body and f"age shown: {REAL_AGE}" not in body
    assert letters.letter_vars(p, B, [_listing(p, None)]).get("age") is None
