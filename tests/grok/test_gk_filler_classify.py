"""WO-338: more label variants and state options for the form filler.

Fake control dicts only. No browser. Fake person: Jane Q Testperson, Springfield IL.
"""
from __future__ import annotations

import socket

import pytest

from freemyid.engine import filler
from freemyid.models import Broker, Listing, MailboxConfig, MatchLevel, ProfileField
from tests.conftest import make_profile

F = ProfileField


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: object) -> None:
    """Fail the test if anything opens a socket. Replaces the shared localhost guard."""
    del freemyid_env

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)


def test_network_fixture_blocks_sockets() -> None:
    with pytest.raises(OSError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(OSError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.mark.parametrize(("desc", "want"), [
    ({"label": "Given name"}, "first_name"),
    ({"label": "Forename"}, "first_name"),
    ({"label": "Christian name"}, "first_name"),
    ({"aria": "Given name"}, "first_name"),
    ({"label": "Surname"}, "last_name"),
    ({"label": "Last / family name"}, "last_name"),
    ({"label": "Family name"}, "last_name"),
    ({"placeholder": "Last/Family Name"}, "last_name"),
    ({"label": "ZIP / Postal code"}, "zip"),
    ({"label": "Postal code"}, "zip"),
    ({"name": "postalcode"}, "zip"),
    ({"name": "PostalCode"}, "zip"),
    ({"name": "zip5"}, "zip"),
    # The ZIP+4 extension box is not the 5-digit ZIP (review: PR #119).
    ({"name": "zip4"}, None),
    ({"name": "zipPlus4"}, None),
    ({"label": "E-mail address"}, "email"),
    ({"label": "E-mailaddress"}, "email"),
    ({"name": "emailaddress"}, "email"),
    ({"label": "Street address line 1"}, "street"),
    ({"label": "Address line 1"}, "street"),
    ({"label": "Postal address"}, "street"),
    ({"name": "address1"}, "street"),
    ({"name": "street1"}, "street"),
    ({"name": "streetaddress"}, "street"),
    ({"name": "addr1"}, "street"),
    ({"label": "Town/City"}, "city"),
    ({"label": "City/Town"}, "city"),
    ({"label": "Municipality"}, "city"),
    ({"label": "Province or state"}, "state"),
    ({"label": "State/Province"}, "state"),
    ({"label": "Web address"}, "listing_url"),
    ({"label": "Address line 2"}, None),
    # CodeRabbit #100: a numbered second line is not the street.
    ({"name": "address2"}, None),
    ({"name": "street2"}, None),
    ({"name": "addr2"}, None),
    ({"name": "addressLine2"}, None),
    ({"name": "address_line_2"}, None),
    ({"name": "street3"}, None),
    ({"label": "Middle name"}, None),
    ({"label": "Phone number"}, None),
    ({"label": "Country"}, None),
    ({"label": "Search"}, None),
    ({"label": "Confirmation code"}, None),
    ({"label": "Website"}, None),
    ({"label": "Credit card number"}, None),
    ({"label": "Cardholder name"}, None),
    ({"label": "Social security number"}, None),
    ({"label": "Passport number"}, None),
    ({"label": "Driver's license"}, None),
    ({"label": "Email address", "name": "website"}, None),
    ({"label": "Email address", "placeholder": "Phone number"}, None),
    ({"label": "First name", "name": "ssn"}, None),
    ({"label": "Given name", "name": "cardnumber"}, None),
])
def test_classify_label_variants(desc: dict[str, str], want: str | None) -> None:
    assert filler.classify(filler.Control(key="f0", **desc)) == want
    if want is not None:
        assert want in filler.KEYS


@pytest.mark.parametrize("desc", [
    {"type": "password", "label": "Email address"},
    {"type": "password", "label": "Given name"},
    {"label": "First name", "name": "cardnumber"},
    {"label": "Email address", "autocomplete": "cc-number"},
    {"label": "Given name", "autocomplete": "cc-given-name"},
    # CodeRabbit #101: every autocomplete token counts, not only the first.
    {"label": "Given name", "autocomplete": "billing cc-given-name"},
    {"label": "Last name", "autocomplete": "section-pay shipping cc-family-name"},
    {"label": "Full name", "autocomplete": "billing CC-Name"},
    {"label": "Full name", "name": "ssn"},
    {"label": "Name", "id": "social_security"},
    {"label": "First name", "placeholder": "Driver's license number"},
    {"label": "Email address", "name": "cvv"},
    {"label": "Name", "name": "cc_num"},
    {"label": "Cardholder name"},
    {"label": "Credit card number"},
    {"label": "Passport number"},
    {"label": "National ID number"},
])
def test_payment_and_id_never_classified(desc: dict[str, str]) -> None:
    control = filler.Control(key="f0", **desc)
    assert control.protected()
    assert control.fillable() is False
    assert filler.classify(control) is None


def test_ordinary_name_is_not_protected() -> None:
    control = filler.Control(key="f0", label="Given name")
    assert control.protected() is False
    assert filler.classify(control) == "first_name"
    middle = filler.Control(key="f1", label="Middle name")
    assert middle.protected() is False
    assert filler.classify(middle) is None


def _opt(value: str, text: str | None = None) -> dict[str, str]:
    return {"value": value, "text": value if text is None else text}


@pytest.mark.parametrize(("opts", "code", "want"), [
    ([_opt("CA - California")], "CA", "CA - California"),
    ([_opt("6", "California (CA)")], "CA", "6"),
    ([_opt("Calif.")], "CA", "Calif."),
    ([_opt("ca")], "CA", "ca"),
    ([_opt("ca")], "ca", "ca"),
    ([_opt("C.A.")], "CA", "C.A."),
    ([_opt("", "Select..."), _opt("ca", "California (CA)")], "CA", "ca"),
    ([_opt("Select..."), _opt("IL", "Illinois")], "IL", "IL"),
    ([_opt("", "Select...")], "IL", None),
    ([_opt("", "Select a state"), _opt("il", "Illinois")], "il", "il"),
    ([_opt("please select"), _opt("Illinois (IL)")], "IL", "Illinois (IL)"),
    ([_opt("IL - Illinois")], "IL", "IL - Illinois"),
    ([_opt("Ill.")], "IL", "Ill."),
    ([_opt("il", "illinois")], "IL", "il"),
    ([_opt("N.C.")], "NC", "N.C."),
    ([_opt("7", "NC - North Carolina")], "NC", "7"),
    ([_opt("37", "North Carolina")], "NC", "37"),
    ([_opt("north carolina", "x")], "nc", "north carolina"),
    ([_opt("NC")], "NC", "NC"),
    ([_opt("SC", "South Carolina")], "NC", None),
    ([_opt("PR - Puerto Rico")], "PR", "PR - Puerto Rico"),
    ([_opt("pr", "Puerto Rico (PR)")], "PR", "pr"),
    ([_opt("P.R.")], "PR", "P.R."),
    ([_opt("Puerto Rico")], "PR", "Puerto Rico"),
    ([_opt("D.C.")], "DC", "D.C."),
    ([_opt("dc", "District of Columbia")], "DC", "dc"),
    ([_opt("Washington, D.C.")], "DC", "Washington, D.C."),
    ([_opt("Washington, D.C.")], "WA", None),
    ([_opt("Washington")], "DC", None),
    ([_opt("Washington")], "WA", "Washington"),
    ([_opt("District of Columbia")], "WA", None),
    ([_opt("WV", "West Virginia")], "VA", None),
    ([_opt("WV", "West Virginia")], "WV", "WV"),
    ([_opt("Virginia")], "WV", None),
    ([_opt("AR", "Arkansas")], "KS", None),
    ([_opt("AR", "Arkansas")], "AR", "AR"),
    ([_opt("KS", "Kansas"), _opt("AR", "Arkansas")], "KS", "KS"),
    ([_opt("SC", "North Carolina")], "NC", None),
    ([_opt("SC", "North Carolina")], "SC", None),
    ([_opt("CA", "Colorado")], "CA", None),
    ([_opt("CA", "Colorado")], "CO", None),
    ([_opt("SC", "North Carolina"), _opt("NC", "North Carolina")], "NC", "NC"),
    ([_opt("", "Select..."), _opt("CO", "CO - Colorado"), _opt("CA", "CA - California")],
     "CA", "CA"),
    ([_opt("GU", "Guam")], "GU", "GU"),
    ([_opt("U.S. Virgin Islands")], "VI", "U.S. Virgin Islands"),
    ([_opt("American Samoa")], "AS", "American Samoa"),
    ([_opt("Northern Mariana Islands")], "MP", "Northern Mariana Islands"),
    ([_opt("W. Va.")], "WV", "W. Va."),
    ([_opt("N. Car.")], "NC", "N. Car."),
    ([], "IL", None),
    ([_opt("IL", "Illinois")], "ZZ", None),
    ([_opt("IL", "Illinois")], "", None),
])
def test_choose_state_option(opts: list[dict[str, str]], code: str, want: str | None) -> None:
    assert filler.choose_state_option(opts, code) == want


def test_state_menu_never_picks_the_wrong_one() -> None:
    options: list[dict[str, str]] = [{"value": "", "text": "Select..."}]
    for code, name in sorted(filler.STATE_NAMES.items()):
        options.append({"value": code.lower(), "text": f"{name} ({code})"})
    options.append({"value": "pr", "text": "Puerto Rico (PR)"})
    options.append({"value": "Calif.", "text": "Calif."})
    options.append({"value": "D.C.", "text": "D.C."})
    seen: dict[str, str] = {}
    for code in (*sorted(filler.STATE_NAMES), "PR"):
        got = filler.choose_state_option(options, code.lower())
        assert got, code
        assert got.strip().lower() not in {"select", "select..."}
        again = filler.choose_state_option([{"value": got, "text": got}], code)
        assert again == got
        seen.setdefault(got, code)
    assert len(seen) == len(filler.STATE_NAMES) + 1  # DC is already in STATE_NAMES; PR is not
    assert filler.choose_state_option([{"value": "Calif.", "text": "Calif."}], "IL") is None
    assert filler.choose_state_option([{"value": "Calif.", "text": "Calif."}], "CA") == "Calif."


def test_plan_values_still_minimized_for_jane() -> None:
    profile = make_profile(mailbox=MailboxConfig(
        address="removals.testperson@example.com", imap_host="imap.example.com",
        smtp_host="smtp.example.com", username="removals.testperson@example.com"))
    broker = Broker(
        id="fill_labels", name="Dev Fill", url="https://devfill.example/",
        category="people_search", domains=["devfill.example"],
        opt_out_url="https://devfill.example/opt", method="web_form",
        required_fields=[F.FULL_NAME, F.CITY, F.STATE, F.EMAIL, F.LISTING_URL])
    listing = Listing(
        profile_id=profile.id, broker_id=broker.id,
        url="https://devfill.example/p/jane-testperson-il", match_score=95,
        match_level=MatchLevel.CONFIRMED,
        shown_fields=[F.FULL_NAME, F.CITY, F.STATE])
    values = filler.plan_values(profile, broker, listing)
    assert set(values) <= set(filler.KEYS)
    assert values["first_name"] == "Jane"
    assert values["last_name"] == "Testperson"
    assert values["full_name"] == "Jane Testperson"
    assert values["city"] == "Springfield"
    assert values["state"] == "IL"
    assert values["email"] == "removals.testperson@example.com"
    assert values["listing_url"] == listing.url
    blob = " ".join(values.values())
    for hidden in ("Q", "62704", "Evergreen", "555", "1980", "jane.testperson@example.com"):
        assert hidden not in blob
    assert "zip" not in values and "street" not in values
    assert filler.classify(filler.Control(key="f0", label="Phone number")) is None
    assert filler.classify(filler.Control(key="f1", label="Social security number")) is None
