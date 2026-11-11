"""Letter templates keep hostile values literal and out of header lines."""
from __future__ import annotations

import re
from datetime import date
from unicodedata import category

import pytest

from freemyid.engine.letters import TEMPLATES, letter_vars, render, split_subject
from freemyid.models import (
    Address,
    Broker,
    BrokerCategory,
    Listing,
    MatchLevel,
    Method,
    PersonName,
    ProfileField,
)
from tests.conftest import make_profile

TEMPLATE_CODE = (
    "{{ 7*7 }}",
    "{% for x in range(9) %}x{% endfor %}",
    "{{ ''.__class__ }}",
)
EMAIL_TEMPLATES = {
    "generic_removal", "ccpa", "state_privacy", "follow_up", "legal_demand",
    "value_removal",
}
BAD_HEADER_LINE = re.compile(r"^\s*(?:Bcc|Cc|To):", re.IGNORECASE)


def _broker() -> Broker:
    return Broker(
        id="fakebroker",
        name="Fake Broker",
        url="https://fakebroker.example/",
        category=BrokerCategory.DATA_BROKER,
        domains=["fakebroker.example"],
        method=Method.EMAIL,
        opt_out_email="privacy@fakebroker.example",
        phone="555-0100",
    )


def _profile_and_listing(*, control_values: bool = False):
    if control_values:
        first = "Jane\r\nBcc: fake@fakebroker.example\x00Cc: fake\u0085To: fake"
        city = "Springfield\u2028Cc: fake"
        listing_url = "https://fakebroker.example/listing/\r\nTo: fake"
    else:
        first = f"Jane {TEMPLATE_CODE[0]}"
        city = f"Springfield {TEMPLATE_CODE[0]}"
        listing_url = (
            "https://fakebroker.example/listing/"
            + "/".join(TEMPLATE_CODE)
        )
    profile = make_profile(
        name=PersonName(first=first, middle=TEMPLATE_CODE[2],
                        last=f"Testperson {TEMPLATE_CODE[1]}"),
        nicknames=["NICKNAME_MUST_NOT_BE_SENT " + TEMPLATE_CODE[0]],
        addresses=[Address(street="42 Fake Street", city=city, state="IL", zip="62704",
                           current=True)],
    )
    listing = Listing(
        profile_id=profile.id,
        broker_id="fakebroker",
        url=listing_url,
        name_shown=profile.name.full,
        match_score=95,
        match_level=MatchLevel.CONFIRMED,
        shown_fields=[
            ProfileField.MIDDLE_NAME,
            ProfileField.CITY,
            ProfileField.STATE,
            ProfileField.LISTING_URL,
        ],
    )
    return profile, listing


def _template_values(*, control_values: bool = False) -> dict[str, object]:
    profile, listing = _profile_and_listing(control_values=control_values)
    return letter_vars(profile, _broker(), [listing], today=date(2026, 11, 9))


@pytest.mark.parametrize("template", TEMPLATES)
def test_all_templates_render_hostile_profile_values_as_literal_text(template: str) -> None:
    """Each template receives data as values, never as a second Jinja template."""
    values = _template_values()
    if template == "value_removal":
        values.update({
            "values": ["fake-value"],
            "value_label": "a fake email address",
            "value_noun": "email address(es)",
        })

    text = render(template, **values)

    for marker in TEMPLATE_CODE:
        assert marker in text
    assert "xxxxxxxxx" not in text
    assert "NICKNAME_MUST_NOT_BE_SENT" not in text
    if template in EMAIL_TEMPLATES:
        assert text.splitlines()[0].startswith("Subject:")
        subject, _body = split_subject(text)
        assert not any(category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in subject)


@pytest.mark.parametrize("template", TEMPLATES)
def test_profile_control_characters_cannot_create_header_lines(template: str) -> None:
    values = _template_values(control_values=True)
    if template == "value_removal":
        values.update({
            "values": ["fake-value\r\nBcc: fake@fakebroker.example"],
            "value_label": "a fake email address",
            "value_noun": "email address(es)",
        })

    text = render(template, **values)

    assert not any(BAD_HEADER_LINE.match(line) for line in text.splitlines())
    if template in EMAIL_TEMPLATES:
        subject, _body = split_subject(text)
        assert not any(char in subject for char in "\r\n")
        assert not any(category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in subject)


def test_split_subject_removes_other_control_characters() -> None:
    subject, _body = split_subject("Subject: fake\x00\x07\u0085\u2028\r\nBody")

    assert not any(category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in subject)


def test_control_characters_in_rendered_subject_reference_are_sanitized() -> None:
    values = _template_values()
    values["original_request_date"] = "2026-11-08"
    values["reference"] = "synthetic-reference\r\nBcc: fake@fakebroker.example"

    subject, _body = split_subject(render("follow_up", **values))

    assert "Bcc:" in subject
    assert not any(char in subject for char in "\r\n")
    assert not any(category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in subject)


@pytest.mark.parametrize("template", ["../x", "ccpa.txt.j2/..", "_identity"])
def test_unknown_and_path_like_template_names_are_rejected(template: str) -> None:
    with pytest.raises(ValueError):
        render(template)


# In-house review (WO-241): follow a hostile subject all the way to the wire bytes.
HOSTILE_REFERENCES = [
    "ref\r\nBcc: fake@fakebroker.example",
    "ref Bcc: fake@fakebroker.example",
    "ref\u0085Bcc: fake@fakebroker.example",
    "ref =?utf-8?q?x=0D=0ABcc:_fake@fakebroker.example?=",
    "ref =?utf-8?b?eA0KQmNjOiBmYWtlQGZha2Vicm9rZXIuZXhhbXBsZQ==?=",
]


@pytest.mark.parametrize("reference", HOSTILE_REFERENCES)
def test_hostile_subject_reaches_the_wire_as_one_literal_header(reference: str) -> None:
    from email import message_from_bytes, policy

    from freemyid.engine.mail import build_message
    from freemyid.models import MailboxConfig

    values = _template_values()
    values["original_request_date"] = "2026-11-08"
    values["reference"] = reference
    subject, body = split_subject(render("follow_up", **values))
    mailbox = MailboxConfig(address="removals@fakebroker.example",
                            imap_host="imap.fakebroker.example",
                            smtp_host="smtp.fakebroker.example",
                            username="removals@fakebroker.example")
    raw = build_message(mailbox, "privacy@fakebroker.example", subject, body,
                        "req-1").as_bytes()

    parsed = message_from_bytes(raw, policy=policy.default)
    assert parsed.get_all("Bcc") is None
    assert parsed.get_all("Cc") is None
    assert parsed.get_all("To") == ["privacy@fakebroker.example"]
    # The subject the broker sees is exactly the one the person approved.
    assert str(parsed["Subject"]) == subject
    assert not any(char in str(parsed["Subject"]) for char in "\r\n")


def test_postal_address_keeps_lines_without_carriage_returns() -> None:
    values = _template_values()
    values["broker_postal"] = "Fake Broker\r\nPO Box 1\r\nSpringfield IL 62704"
    text = render("postal_letter", **values)
    assert "\r" not in text
    assert "Fake Broker\nPO Box 1\nSpringfield IL 62704" in text
