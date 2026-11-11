"""Every editable profile field survives loading and rebuilding an edit draft.

Only Profile id/created_at/updated_at are omitted from the aggregate: ids are checked
separately, while save_draft (outside this test) owns persisted creation/update times.
Known losses have independent strict per-leaf xfails; all other dump leaves are compared.
All names, contact details, mailbox settings and consent records below are synthetic.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from itertools import product
from typing import Any

import pytest

from freemyid.models import (
    Address,
    Consent,
    ConsentBasis,
    EmailMode,
    MailboxConfig,
    Permissions,
    PersonName,
    Profile,
    RemovalScope,
    ScheduleConfig,
)
from freemyid.wizard import draft as dr

Path = tuple[str | int, ...]
STAMP = datetime(2026, 11, 9, 12, tzinfo=UTC)


class _Today(date):
    @classmethod
    def today(cls) -> date:
        return date(2026, 11, 9)


@pytest.fixture(autouse=True)
def _offline_edit(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stub before any conversion so no OS secret-store lookup can happen.
    monkeypatch.setattr(dr, "_has_saved_password", lambda p: False)
    monkeypatch.setattr(dr, "date", _Today)


def _profile(index: int, basis: ConsentBasis, dob: bool, mode: EmailMode) -> Profile:
    minor = basis is ConsentBasis.GUARDIAN_OF_MINOR
    bits = (0, 15, 1, 2, 4, 8)[index % 6]
    return Profile(
        id=f"{index:032x}", label=f"Synthetic profile {index}",
        name=PersonName(first="Jane", middle="Q", last="Testperson", suffix="Jr."),
        nicknames=["Janie", "JQ"],
        previous_names=[
            PersonName(first="Jane", middle="Q", last="PreviousTestperson", suffix="Sr."),
            PersonName(first="Jane", last="EarlierTestperson", suffix="III"),
        ],
        addresses=[
            Address(street="1 Synthetic Test Lane", city="Springfield", state="IL",
                    zip="62701", current=True, from_year=2020),
            Address(street="2 Synthetic Test Lane", city="Springfield", state="IL",
                    zip="62702", from_year=2018, to_year=2019),
            Address(city="Springfield", state="IL", from_year=2015, to_year=2017),
        ],
        dob=date(2015 if minor else 1984, 2, 3) if dob else None,
        age=None if dob else (11 if minor else 42), is_minor=minor,
        phones=["217-555-0100", "217-555-0101"],
        emails=["jane.testperson@example.invalid", "old.testperson@example.invalid"],
        relatives=["Synthetic Relative Testperson", "Another Relative Testperson"],
        permissions=Permissions(
            allow_id_upload=bool(bits & 1), allow_account_creation=bool(bits & 2),
            allow_phone_disclosure=bool(bits & 4), allow_email_disclosure=bool(bits & 8),
        ),
        removal_scope=tuple(RemovalScope)[index % len(RemovalScope)],
        email_mode=mode,
        schedule=ScheduleConfig(weekly_recheck=bool(index % 2), weekday=index % 7,
                                hour=(index * 2) % 24, respect_broker_intervals=bool(index % 2)),
        consent=Consent(basis=basis, attested_by="Jane Q Testperson", attested_at=STAMP,
                        text_version="synthetic-old-consent-version",
                        authorization_doc="synthetic-authorization" if basis is
                        ConsentBasis.AUTHORIZED_AGENT else None),
        mailbox=MailboxConfig(
            address="removals.testperson@example.invalid", provider="other",
            imap_host="imap.example.invalid", imap_port=1993, imap_ssl=False,
            imap_starttls=True, smtp_host="smtp.example.invalid", smtp_port=1587,
            smtp_starttls=True, username="synthetic-mailbox-user", tls_cert_sha256="ab" * 32,
        ) if index % 2 else None,
        created_at=STAMP, updated_at=STAMP,
    )


PROFILES = [
    _profile(i, basis, dob, mode)
    for i, (basis, dob, mode) in enumerate(product(ConsentBasis, (False, True), EmailMode))
]


def _dump(profile: Profile) -> dict[str, Any]:
    return profile.model_dump(exclude={"id", "created_at", "updated_at"})


def _leaves(value: Any, path: Path = ()) -> dict[Path, Any]:
    if isinstance(value, dict) and value:
        return {leaf: item for key, child in value.items()
                for leaf, item in _leaves(child, (*path, key)).items()}
    if isinstance(value, list) and value:
        return {leaf: item for index, child in enumerate(value)
                for leaf, item in _leaves(child, (*path, index)).items()}
    return {path: value}


def _loss(path: Path, value: Any) -> str | None:
    if path == ("removal_scope",) and value != RemovalScope.FULL:
        return "src/freemyid/wizard/draft.py:527 omits removal_scope; rebuild defaults to full"
    if path == ("permissions", "allow_email_disclosure") and value:
        return "src/freemyid/wizard/draft.py:539-541 omits allow_email_disclosure; defaults False"
    if path == ("schedule", "respect_broker_intervals") and not value:
        return "src/freemyid/wizard/draft.py:542-543 omits respect_broker_intervals; defaults True"
    if path[0] == "previous_names" and path[-1] == "suffix" and value is not None:
        return "src/freemyid/wizard/draft.py:610-611 omits previous-name suffixes; rebuild is None"
    if path[0] == "addresses" and path[-1] in {"from_year", "to_year"} and value is not None:
        return f"src/freemyid/wizard/draft.py:612-613 omits address {path[-1]}; rebuild is None"
    return None


def _field_cases() -> list[Any]:
    cases = []
    for index, profile in enumerate(PROFILES):
        for path, expected in _leaves(_dump(profile)).items():
            reason = _loss(path, expected)
            marks = [pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason)] \
                if reason else []
            cases.append(pytest.param(index, path, expected, marks=marks,
                                      id=f"profile-{index}." + ".".join(map(str, path))))
    return cases


@pytest.mark.parametrize("index,path,expected", _field_cases())
def test_each_edit_field_round_trips(index: int, path: Path, expected: Any) -> None:
    rebuilt = dr.build_profile(dr.draft_from_profile(PROFILES[index]))
    actual = _leaves(_dump(rebuilt))
    assert actual[path] == expected


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
def test_complete_dump_except_independently_guarded_losses(profile: Profile) -> None:
    rebuilt = dr.build_profile(dr.draft_from_profile(profile))
    expected = _leaves(_dump(profile))
    actual = _leaves(_dump(rebuilt))
    assert actual.keys() == expected.keys()  # catches dropped or extra list items/fields too
    losses = {path for path, value in expected.items() if _loss(path, value)}
    assert {path: value for path, value in actual.items() if path not in losses} == {
        path: value for path, value in expected.items() if path not in losses
    }
    assert rebuilt.id == profile.id


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: p.id)
@pytest.mark.parametrize("keep", [False, True])
def test_edit_keeps_or_clears_original_consent(profile: Profile, keep: bool) -> None:
    draft = dr.draft_from_profile(profile, keep_consent=keep)
    if keep:
        assert draft.existing_consent is profile.consent
        assert dr.build_profile(draft).consent.model_dump() == profile.consent.model_dump()
    else:
        assert draft.existing_consent is None
        assert not draft.consent_ack


@pytest.mark.parametrize("saved", [False, True])
def test_mailbox_edit_holds_no_secret(monkeypatch: pytest.MonkeyPatch, saved: bool) -> None:
    profile = next(p for p in PROFILES if p.mailbox is not None)
    seen = []

    def has_saved_password(p: Profile) -> bool:
        seen.append(p.id)
        return saved

    monkeypatch.setattr(dr, "_has_saved_password", has_saved_password)
    draft = dr.draft_from_profile(profile)
    assert seen == [profile.id]
    assert draft.saved_password is saved and type(draft.saved_password) is bool
    assert not ({"password", "keyring_service"} & draft.mailbox.keys())
    assert draft.password == ""
    assert profile.mailbox is not None
    assert draft.mailbox == profile.mailbox.model_dump(exclude={"keyring_service"})
    assert draft.tls_pin == profile.mailbox.tls_cert_sha256
