"""WO-345: tier_reason agrees with tier_for. Fake people, no network."""
from __future__ import annotations

import socket
from datetime import date
from itertools import product
from typing import get_args

import pytest

from freemyid.config import Config
from freemyid.engine.tiers import TierReason, tier_for, tier_reason
from freemyid.models import (
    Broker,
    FormStep,
    MailboxConfig,
    Method,
    Permissions,
    PostalContact,
    ProfileField,
    Registry,
    Tier,
    VerificationStatus,
)
from tests.conftest import make_profile

MB = MailboxConfig(address="removals@mail.example", imap_host="imap.mail.example",
                   smtp_host="smtp.mail.example", username="removals@mail.example")
HOST = "fakeb.example"
FORM = [
    FormStep(action="goto", url=f"https://{HOST}/optout"),
    FormStep(action="submit", selector="button"),
]
HEALTH = [
    FormStep(action="goto", url=f"https://{HOST}/optout"),
    FormStep(action="expect_text", value="Opt out"),
]
VERIFIED = {
    "verification_status": VerificationStatus.VERIFIED,
    "source_urls": [f"https://{HOST}/privacy"],
    "last_verified": date(2026, 11, 1),
}
OFF = Config(browser_automation=False)
CODES = (
    "no_email_route",
    "form_not_verified",
    "permissions_block",
    "automation_off",
    "email_ok",
)
ASSISTED = frozenset(CODES) - {"email_ok"}
# Contact and profile text that a reason must never carry.
_LEAKS = (
    "Jane", "Testperson", "Springfield", "Evergreen", "62704", "217-555-0142",
    "217-555-0199", "jane.testperson", "removals@", "privacy@", "Privacy Desk",
    "Example Road", "fakeb.example", "parent.example", "child.example",
    "https://", "http://", "@",
)


@pytest.fixture(autouse=True)
def block_network(monkeypatch, freemyid_env):
    """socket.connect and create_connection always raise. Runs after the suite guard."""
    assert freemyid_env is not None

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _broker(bid: str = "fakeb", **over) -> Broker:
    host = f"{bid}.example"
    data: dict = {
        "id": bid, "name": "Fake B", "url": f"https://{host}/",
        "category": "people_search", "domains": [host],
        "opt_out_url": f"https://{host}/optout", "method": Method.WEB_FORM,
    }
    data.update(over)
    return Broker(**data)


def _profile(**over):
    return make_profile(**over)


def _assert_code(reason: str | None, tier: Tier) -> None:
    if tier is Tier.AUTOMATIC:
        assert reason is None
    elif tier is Tier.EMAIL:
        assert reason == "email_ok"
    else:
        assert tier is Tier.ASSISTED
        assert reason in ASSISTED
    if reason is None:
        return
    assert reason in CODES
    assert reason.isidentifier()
    folded = reason.casefold()
    for bit in _LEAKS:
        assert bit.casefold() not in folded


def _params():
    phone_off = {"permissions": Permissions()}
    phone_on = {"permissions": Permissions(allow_phone_disclosure=True)}
    id_on = {"permissions": Permissions(allow_id_upload=True)}
    account_on = {"permissions": Permissions(allow_account_creation=True)}
    mail = {"mailbox": MB}
    rows = []

    def add(name, tier, reason, broker=None, profile=None, cfg=None):
        rows.append(pytest.param(broker or {}, profile or {}, cfg, tier, reason, id=name))

    add("email_ok", Tier.EMAIL, "email_ok",
        {"method": Method.EMAIL, "opt_out_email": f"privacy@{HOST}", "opt_out_url": None},
        mail)
    add("email_ok_alt", Tier.EMAIL, "email_ok",
        {"alt_methods": [Method.EMAIL], "opt_out_email": f"privacy@{HOST}"}, mail)
    add("address_is_not_a_route", Tier.ASSISTED, "no_email_route",
        {"opt_out_email": f"privacy@{HOST}"}, mail)
    add("no_email_route", Tier.ASSISTED, "no_email_route")
    add("health_check_only", Tier.ASSISTED, "no_email_route", {"form": HEALTH, **VERIFIED})
    add("form_not_verified", Tier.ASSISTED, "form_not_verified", {"form": FORM})
    add("form_broken", Tier.ASSISTED, "form_not_verified",
        {"form": FORM, "verification_status": VerificationStatus.BROKEN})
    add("permissions_phone", Tier.ASSISTED, "permissions_block",
        {"form": FORM, **VERIFIED, "required_fields": [ProfileField.PHONE]}, phone_off)
    add("permissions_id_upload", Tier.ASSISTED, "permissions_block",
        {"form": FORM, **VERIFIED, "needs_id_upload": True})
    add("permissions_id_field", Tier.ASSISTED, "permissions_block",
        {"form": FORM, **VERIFIED, "required_fields": [ProfileField.ID_DOCUMENT]})
    add("phone_allowed_is_automatic", Tier.AUTOMATIC, None,
        {"form": FORM, **VERIFIED, "required_fields": [ProfileField.PHONE]}, phone_on)
    add("id_allowed_is_automatic", Tier.AUTOMATIC, None,
        {"form": FORM, **VERIFIED, "needs_id_upload": True}, id_on)
    add("automation_off", Tier.ASSISTED, "automation_off",
        {"form": FORM, **VERIFIED}, {}, OFF)
    add("automation_on", Tier.AUTOMATIC, None, {"form": FORM, **VERIFIED}, {}, Config())
    add("missing_cfg_allows_automatic", Tier.AUTOMATIC, None, {"form": FORM, **VERIFIED})
    add("automatic_beats_email", Tier.AUTOMATIC, None,
        {"form": FORM, **VERIFIED, "alt_methods": [Method.EMAIL],
         "opt_out_email": f"privacy@{HOST}"}, mail)
    add("email_beats_unverified_form", Tier.EMAIL, "email_ok",
        {"form": FORM, "alt_methods": [Method.EMAIL], "opt_out_email": f"privacy@{HOST}"},
        mail)
    add("captcha", Tier.ASSISTED, "no_email_route",
        {"form": FORM, **VERIFIED, "has_captcha": True})
    add("human_step", Tier.ASSISTED, "no_email_route",
        {"form": [*FORM, FormStep(action="human", note="a person")], **VERIFIED})
    add("account_required", Tier.ASSISTED, "no_email_route",
        {"form": FORM, **VERIFIED, "method": Method.ACCOUNT_REQUIRED})
    add("account_allowed_still_assisted", Tier.ASSISTED, "no_email_route",
        {"form": FORM, **VERIFIED, "method": Method.ACCOUNT_REQUIRED}, account_on)
    add("permissions_before_automation_off", Tier.ASSISTED, "permissions_block",
        {"form": FORM, **VERIFIED, "required_fields": [ProfileField.PHONE]}, phone_off, OFF)
    add("email_route_without_mailbox", Tier.ASSISTED, "no_email_route",
        {"alt_methods": [Method.EMAIL], "opt_out_email": f"privacy@{HOST}"})
    add("unverified_form_without_mailbox", Tier.ASSISTED, "form_not_verified",
        {"form": FORM, "alt_methods": [Method.EMAIL], "opt_out_email": f"privacy@{HOST}"})
    add("value_phone_ignores_form", Tier.ASSISTED, "no_email_route",
        {"form": FORM, **VERIFIED}, {"removal_scope": "phone"})
    add("value_phone_email", Tier.EMAIL, "email_ok",
        {"form": FORM, **VERIFIED, "alt_methods": [Method.EMAIL],
         "opt_out_email": f"privacy@{HOST}"},
        {"removal_scope": "phone", "mailbox": MB})
    add("value_email_ignores_automation_off", Tier.ASSISTED, "no_email_route",
        {"form": FORM, **VERIFIED}, {"removal_scope": "email"}, OFF)
    add("value_email_with_mailbox", Tier.EMAIL, "email_ok",
        {"method": Method.EMAIL, "opt_out_email": f"privacy@{HOST}", "opt_out_url": None},
        {"removal_scope": "email", "mailbox": MB})
    add("postal", Tier.ASSISTED, "no_email_route",
        {"method": Method.POSTAL, "opt_out_url": None,
         "postal": PostalContact(recipient="Privacy Desk", lines=["1 Example Road"])})
    add("phone_method", Tier.ASSISTED, "no_email_route",
        {"method": Method.PHONE, "phone": "217-555-0199", "opt_out_url": None})
    return rows


def test_vocabulary_is_the_five_codes():
    assert set(get_args(TierReason)) == set(CODES)


def test_sockets_cannot_connect():
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


@pytest.mark.parametrize(("broker_kw", "profile_kw", "cfg", "tier", "reason"), _params())
def test_named_reason_agrees_with_tier(broker_kw, profile_kw, cfg, tier, reason):
    broker = _broker(**broker_kw)
    profile = _profile(**profile_kw)
    assert tier_for(broker, profile, cfg) is tier
    got = tier_reason(broker, profile, cfg)
    assert got == reason
    _assert_code(got, tier)
    _assert_no_contact(got, broker, profile)


def test_grid_reason_agrees_with_tier():
    """Cross the inputs that move a tier. The code and the tier stay paired."""
    seen: set[str | None] = set()
    profiles = [
        _profile(**kw) for kw in (
            {},
            {"mailbox": MB},
            {"permissions": Permissions(allow_phone_disclosure=True)},
            {"permissions": Permissions(allow_id_upload=True)},
            {"permissions": Permissions(allow_account_creation=True)},
            {"permissions": Permissions(allow_phone_disclosure=True, allow_id_upload=True)},
            {"removal_scope": "phone"},
            {"removal_scope": "phone", "mailbox": MB},
            {"removal_scope": "email"},
            {"removal_scope": "email", "mailbox": MB,
             "permissions": Permissions(allow_email_disclosure=True)},
        )
    ]
    cfgs = (None, Config(), OFF)
    n = 0
    for broker in _grid_brokers():
        for profile in profiles:
            for cfg in cfgs:
                tier = tier_for(broker, profile, cfg)
                reason = tier_reason(broker, profile, cfg)
                _assert_code(reason, tier)
                _assert_no_contact(reason, broker, profile)
                seen.add(reason)
                n += 1
    assert n > 1000
    assert seen == set(CODES) | {None}


def test_covered_by_follows_the_parent():
    parent = _broker(
        "parent", name="Parent Co", method=Method.EMAIL, opt_out_url=None,
        opt_out_email="privacy@parent.example")
    child = _broker(
        "child", covered_by="parent", form=_form("child.example"),
        **_verified("child.example"), alt_methods=[Method.EMAIL],
        opt_out_email="privacy@child.example")
    reg = Registry(version="t", updated=date(2026, 11, 1), brokers=[parent, child])
    profile = _profile(mailbox=MB)
    assert tier_for(child, profile) is Tier.AUTOMATIC
    assert tier_reason(child, profile) is None
    assert tier_for(child, profile, registry=reg) is Tier.EMAIL
    assert tier_reason(child, profile, registry=reg) == "email_ok"
    _assert_no_contact(tier_reason(child, profile, registry=reg), child, profile)

    auto_parent = _broker("parent", form=_form("parent.example"), **_verified("parent.example"))
    email_child = _broker(
        "child", covered_by="parent", method=Method.EMAIL, opt_out_url=None,
        opt_out_email="privacy@child.example")
    reg2 = Registry(version="t", updated=date(2026, 11, 1),
                    brokers=[auto_parent, email_child])
    assert tier_for(email_child, profile) is Tier.EMAIL
    assert tier_reason(email_child, profile) == "email_ok"
    assert tier_for(email_child, profile, registry=reg2) is Tier.AUTOMATIC
    assert tier_reason(email_child, profile, registry=reg2) is None


def test_missing_parent_uses_the_child():
    child = _broker("child", covered_by="parent")

    class _Gone:
        def get(self, _broker_id: str) -> Broker:
            raise KeyError(_broker_id)

    profile = _profile()
    gone = _Gone()
    assert tier_for(child, profile, registry=gone) is Tier.ASSISTED  # type: ignore[arg-type]
    assert tier_reason(child, profile, registry=gone) == "no_email_route"  # type: ignore[arg-type]


def test_reason_does_not_log(caplog):
    caplog.set_level(0)
    broker = _broker(
        method=Method.PHONE, phone="217-555-0199", opt_out_url=None,
        opt_out_email=f"privacy@{HOST}",
        postal=PostalContact(recipient="Privacy Desk", lines=["1 Example Road"]))
    # Phone method with an address that is not an email method, plus a postal block.
    profile = _profile(mailbox=MB)
    reason = tier_reason(broker, profile)
    assert reason == "no_email_route"
    assert caplog.records == []
    _assert_no_contact(reason, broker, profile)


def _form(host: str) -> list[FormStep]:
    return [
        FormStep(action="goto", url=f"https://{host}/optout"),
        FormStep(action="submit", selector="button"),
    ]


def _verified(host: str) -> dict:
    return {
        "verification_status": VerificationStatus.VERIFIED,
        "source_urls": [f"https://{host}/privacy"],
        "last_verified": date(2026, 11, 1),
    }


def _grid_brokers() -> list[Broker]:
    brokers: list[Broker] = []
    forms = ("none", "health", "real")
    humans = (False, True)
    verified = ("unverified", "verified", "broken")
    flags = (False, True)
    routes = ("web", "address_not_method", "alt_email", "primary_email", "account",
              "account_alt_email")
    for route, form, human, status, captcha, needs_id, phone_req in product(
            routes, forms, humans, verified, flags, flags, flags):
        steps: list[FormStep] = []
        if form == "health":
            steps = list(HEALTH)
        elif form == "real":
            steps = list(FORM)
        if human:
            steps = [*steps, FormStep(action="human", note="a person")]
        data: dict = {"form": steps, "has_captcha": captcha, "needs_id_upload": needs_id,
                      "phone": "217-555-0199"}
        if phone_req:
            data["required_fields"] = [ProfileField.PHONE]
        if status == "verified":
            data.update(VERIFIED)
        elif status == "broken":
            data["verification_status"] = VerificationStatus.BROKEN
        if route == "address_not_method":
            data["opt_out_email"] = f"privacy@{HOST}"
        elif route == "alt_email":
            data["alt_methods"] = [Method.EMAIL]
            data["opt_out_email"] = f"privacy@{HOST}"
        elif route == "primary_email":
            data["method"] = Method.EMAIL
            data["opt_out_email"] = f"privacy@{HOST}"
            data["opt_out_url"] = None
        elif route == "account":
            data["method"] = Method.ACCOUNT_REQUIRED
        elif route == "account_alt_email":
            data["method"] = Method.ACCOUNT_REQUIRED
            data["alt_methods"] = [Method.EMAIL]
            data["opt_out_email"] = f"privacy@{HOST}"
        brokers.append(_broker(**data))
    return brokers


def _assert_no_contact(reason: str | None, broker: Broker, profile) -> None:
    if reason is None:
        return
    blob = reason.casefold()
    bits = [
        broker.opt_out_email or "", broker.phone or "", broker.name, str(broker.url),
        str(broker.opt_out_url or ""), profile.name.first, profile.name.last,
        profile.name.middle or "", profile.label,
    ]
    if broker.postal is not None:
        bits.append(broker.postal.recipient)
        bits.extend(broker.postal.lines)
    bits.extend(profile.phones)
    bits.extend(profile.emails)
    if profile.mailbox is not None:
        bits.append(profile.mailbox.address)
        bits.append(profile.mailbox.username)
    for address in profile.addresses:
        bits.extend([address.street or "", address.city, address.state, address.zip or ""])
    for bit in bits:
        if len(bit) >= 3:
            assert bit.casefold() not in blob
    for bit in _LEAKS:
        assert bit.casefold() not in blob
