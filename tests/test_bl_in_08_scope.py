"""BL-IN-08 contract: Profile.removal_scope, Permissions.allow_email_disclosure, Broker
reverse-lookup search patterns, and the consent gate. Fake people and brokers only."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from freemyid.consent import CURRENT_TEXT_VERSION, consent_ok
from freemyid.models import (
    Broker,
    Consent,
    ConsentBasis,
    Permissions,
    PersonName,
    Profile,
    RemovalScope,
)
from tests.conftest import make_profile

C = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
            text_version=CURRENT_TEXT_VERSION)
PHONE = "217-555-0142"
EMAIL = "jane.testperson@example.com"


def test_full_scope_is_the_default_and_still_needs_name_and_address():
    assert make_profile().removal_scope is RemovalScope.FULL
    with pytest.raises(ValidationError, match="name"):
        Profile(label="T", consent=C, addresses=[])
    with pytest.raises(ValidationError, match="address"):
        Profile(label="T", consent=C, name=PersonName(first="Jane", last="Testperson"))


def test_phone_scope_needs_only_a_phone():
    p = Profile(label="T", consent=C, removal_scope="phone", phones=[PHONE])
    assert p.value_only and p.addresses == [] and p.state_of_residence == ""
    assert p.name.first == "" and p.name.last == ""
    with pytest.raises(ValidationError, match="phone"):
        Profile(label="T", consent=C, removal_scope="phone")


def test_email_scope_needs_only_an_email():
    p = Profile(label="T", consent=C, removal_scope="email", emails=[EMAIL])
    assert p.value_only
    with pytest.raises(ValidationError, match="email"):
        Profile(label="T", consent=C, removal_scope="email", phones=[PHONE])


def test_value_profile_round_trips():
    p = Profile(label="T", consent=C, removal_scope="phone", phones=[PHONE],
                permissions=Permissions(allow_phone_disclosure=True))
    assert Profile.model_validate(p.model_dump(mode="json")) == p


def test_consent_gate_requires_the_matching_disclosure_flag():
    ph = Profile(label="T", consent=C, removal_scope="phone", phones=[PHONE])
    ok, why = consent_ok(ph)
    assert not ok and "phone" in why
    ph = ph.model_copy(update={"permissions": Permissions(allow_phone_disclosure=True)})
    assert consent_ok(ph) == (True, "")
    em = Profile(label="T", consent=C, removal_scope="email", emails=[EMAIL],
                 permissions=Permissions(allow_phone_disclosure=True))
    ok, why = consent_ok(em)
    assert not ok and "email" in why          # never implied by the scope or the phone flag
    em = em.model_copy(update={"permissions": Permissions(allow_email_disclosure=True)})
    assert consent_ok(em) == (True, "")


def test_full_scope_ignores_disclosure_flags():
    p = make_profile(consent=C)
    assert consent_ok(p) == (True, "")


def _broker(**over):
    data = {"id": "devphone", "name": "Dev Phone", "url": "https://devphone.example/",
            "category": "people_search", "domains": ["devphone.example"], "method": "email",
            "opt_out_email": "privacy@devphone.example"}
    data.update(over)
    return Broker.model_validate(data)


def test_broker_reverse_lookup_patterns_validate():
    b = _broker(phone_search_url_pattern="https://devphone.example/phone/{phone_digits}",
                email_search_url_pattern="https://devphone.example/email?q={email}")
    assert b.phone_search_url_pattern and b.email_search_url_pattern
    with pytest.raises(ValidationError, match="placeholders"):
        _broker(phone_search_url_pattern="https://devphone.example/{first}")
    with pytest.raises(ValidationError, match="placeholders"):
        _broker(email_search_url_pattern="https://devphone.example/{phone_digits}")
    with pytest.raises(ValidationError, match="broker domains"):
        _broker(phone_search_url_pattern="https://evil.example/{phone_digits}")
    with pytest.raises(ValidationError, match="broker domains"):
        _broker(email_search_url_pattern="http://devphone.example/{email}")
