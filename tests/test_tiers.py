"""Draft tests for engine/tiers.py (qa to adopt). Fake people and fake brokers only."""
from __future__ import annotations

from datetime import date

import pytest

from tests.conftest import make_profile
from vanish.config import Config
from vanish.engine.tiers import can_scan, submit_target, tier_for
from vanish.models import (
    Broker,
    FormStep,
    MailboxConfig,
    Method,
    Permissions,
    Registry,
    SearchSpec,
    Tier,
    VerificationStatus,
)

MB = MailboxConfig(address="removals@mail.example", imap_host="imap.mail.example",
                   smtp_host="smtp.mail.example", username="removals@mail.example")


def broker(**over) -> Broker:
    data = {"id": "fakeb", "name": "Fake B", "url": "https://fakeb.example/",
            "category": "people_search", "domains": ["fakeb.example"],
            "opt_out_url": "https://fakeb.example/optout", "method": Method.WEB_FORM}
    data.update(over)
    return Broker(**data)


VERIFIED = {"verification_status": VerificationStatus.VERIFIED,
            "source_urls": ["https://fakeb.example/privacy"],
            "last_verified": date(2026, 11, 1)}
FORM = [FormStep(action="goto", url="https://fakeb.example/optout"),
        FormStep(action="submit", selector="button")]


@pytest.fixture
def with_mb():
    return make_profile(mailbox=MB)


@pytest.fixture
def no_mb():
    return make_profile()


def test_automatic_needs_form_verified_no_captcha(no_mb):
    assert tier_for(broker(form=FORM, **VERIFIED), no_mb) == Tier.AUTOMATIC
    assert tier_for(broker(form=FORM), no_mb) == Tier.ASSISTED                 # unverified
    assert tier_for(broker(**VERIFIED), no_mb) == Tier.ASSISTED                # no form
    assert tier_for(broker(form=FORM, has_captcha=True, **VERIFIED), no_mb) == Tier.ASSISTED


def test_automatic_respects_config_switch(no_mb):
    b = broker(form=FORM, **VERIFIED)
    assert tier_for(b, no_mb, Config()) == Tier.AUTOMATIC
    off = Config()
    object.__setattr__(off, "browser_automation", False)
    assert tier_for(b, no_mb, off) == Tier.ASSISTED


def test_human_step_or_blocked_permission_is_not_automatic(no_mb):
    human = [*FORM, FormStep(action="human", note="solve it")]
    assert tier_for(broker(form=human, **VERIFIED), no_mb) == Tier.ASSISTED
    b = broker(form=FORM, required_fields=["phone"], **VERIFIED)
    assert tier_for(b, no_mb) == Tier.ASSISTED
    p = make_profile(permissions=Permissions(allow_phone_disclosure=True))
    assert tier_for(b, p) == Tier.AUTOMATIC
    assert tier_for(broker(form=FORM, needs_id_upload=True, **VERIFIED), no_mb) == Tier.ASSISTED


def test_email_tier_needs_mailbox_and_email_method(with_mb, no_mb):
    b = broker(alt_methods=[Method.EMAIL], opt_out_email="privacy@fakeb.example")
    assert tier_for(b, with_mb) == Tier.EMAIL
    assert tier_for(b, no_mb) == Tier.ASSISTED
    primary = broker(method=Method.EMAIL, opt_out_email="privacy@fakeb.example",
                     opt_out_url=None)
    assert tier_for(primary, with_mb) == Tier.EMAIL
    # an address without email listed as a method is not used
    assert tier_for(broker(opt_out_email="privacy@fakeb.example"), with_mb) == Tier.ASSISTED


def test_automatic_beats_email(with_mb):
    b = broker(form=FORM, alt_methods=[Method.EMAIL], opt_out_email="privacy@fakeb.example",
               **VERIFIED)
    assert tier_for(b, with_mb) == Tier.AUTOMATIC


def test_covered_by_uses_parent(with_mb):
    parent = broker(id="parent", name="P", url="https://parent.example/",
                    domains=["parent.example"], opt_out_url=None, method=Method.EMAIL,
                    opt_out_email="privacy@parent.example")
    child = broker(id="child", covered_by="parent")
    reg = Registry(version="t", updated=date(2026, 11, 1), brokers=[parent, child])
    assert submit_target(child, reg).id == "parent"
    assert tier_for(child, with_mb, registry=reg) == Tier.EMAIL
    assert tier_for(child, with_mb) == Tier.ASSISTED       # without registry: itself


def test_can_scan():
    spec = SearchSpec(result_selector=".r")
    pat = "https://fakeb.example/name/{first}-{last}"
    assert can_scan(broker(search_url_pattern=pat, search=spec, **VERIFIED))
    assert not can_scan(broker(search_url_pattern=pat, search=spec))
    assert not can_scan(broker(search_url_pattern=pat, **VERIFIED))


def test_health_check_only_form_is_assisted(no_mb):
    health = [FormStep(action="goto", url="https://fakeb.example/optout"),
              FormStep(action="expect_text", value="Opt out")]
    assert tier_for(broker(form=health, **VERIFIED), no_mb) == Tier.ASSISTED
