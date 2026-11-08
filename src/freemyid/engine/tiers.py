"""Which tier handles a broker for a profile (docs/PLAN_V1.md D1). Pure functions, no I/O.

    AUTOMATIC  broker has data-driven `form` steps with real fill/click actions,
               `verification_status: verified`, no captcha, no `human` step, nothing the profile's permissions forbid, and the
               config allows browser automation.
    EMAIL      broker takes privacy requests by email (`opt_out_email` with `email` as its
               method or one of `alt_methods`) AND the profile has a removal mailbox.
    ASSISTED   everything else: the user does it in their own browser with copy buttons
               (or sends the prepared letter themselves when there is no mailbox).

`covered_by` brokers never get their own submission: `submit_target` names the parent and
`tier_for(..., registry=...)` reports the parent's tier.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import (
    Broker,
    Method,
    Profile,
    ProfileField,
    Registry,
    Tier,
    VerificationStatus,
)

if TYPE_CHECKING:
    from ..config import Config


def browser_automation_allowed(cfg: Config | None) -> bool:
    """Config switch for the Automatic tier. Missing attribute = allowed (default on).

    CHANGE REQUEST pending: `Config.browser_automation: bool = True`.
    """
    return bool(getattr(cfg, "browser_automation", True)) if cfg is not None else True


def has_email_route(broker: Broker) -> bool:
    return bool(broker.opt_out_email) and (
        broker.method == Method.EMAIL or Method.EMAIL in broker.alt_methods)


def _permissions_block(broker: Broker, profile: Profile) -> bool:
    perms = profile.permissions
    if broker.needs_id_upload and not perms.allow_id_upload:
        return True
    if broker.method == Method.ACCOUNT_REQUIRED and not perms.allow_account_creation:
        return True
    if ProfileField.PHONE in broker.required_fields and not perms.allow_phone_disclosure:
        return True
    return ProfileField.ID_DOCUMENT in broker.required_fields and not perms.allow_id_upload


_INTERACTIVE_STEPS = frozenset({"fill", "select", "check", "click", "submit"})


def has_real_form(broker: Broker) -> bool:
    """Form steps that actually do something (fill/click), not only page-health checks
    (goto/expect_text/human). PLAN_V1 'Registry decisions'."""
    return any(st.action in _INTERACTIVE_STEPS for st in broker.form)


def automatic_eligible(broker: Broker, profile: Profile, cfg: Config | None = None) -> bool:
    return (
        has_real_form(broker)
        and broker.verification_status == VerificationStatus.VERIFIED
        and not broker.has_captcha
        and broker.method != Method.ACCOUNT_REQUIRED       # never creates accounts itself
        and not any(st.action == "human" for st in broker.form)
        and not _permissions_block(broker, profile)
        and browser_automation_allowed(cfg)
    )


def can_scan(broker: Broker, cfg: Config | None = None) -> bool:
    """A broker the engine may search with the browser (re-scans in D4 scheduled runs)."""
    return (
        bool(broker.search_url_pattern)
        and broker.search is not None
        and bool(broker.search.result_selector)
        and broker.verification_status == VerificationStatus.VERIFIED
        and not broker.has_captcha
        and browser_automation_allowed(cfg)
    )


def lookup_pattern(broker: Broker, profile: Profile) -> str | None:
    """BL-IN-08: the broker's reverse-lookup pattern for this person's removal scope."""
    if profile.removal_scope == "phone":
        return broker.phone_search_url_pattern
    if profile.removal_scope == "email":
        return broker.email_search_url_pattern
    return None


def can_scan_value(broker: Broker, profile: Profile, cfg: Config | None = None) -> bool:
    """A phone/email-only person's reverse lookup on this broker may run in the browser."""
    return (
        bool(lookup_pattern(broker, profile))
        and broker.search is not None
        and bool(broker.search.result_selector)
        and broker.verification_status == VerificationStatus.VERIFIED
        and not broker.has_captcha
        and browser_automation_allowed(cfg)
    )


def value_applicable(broker: Broker, profile: Profile,
                     registry: Registry | None = None) -> bool:
    """BL-IN-08: brokers a phone/email-only removal goes to: those with a reverse lookup
    for the scope, or an email route (a letter naming only the value). Everything else is
    skipped, so the person never gets a to-do per site."""
    target = submit_target(broker, registry)
    return bool(lookup_pattern(broker, profile)) or has_email_route(target)


def submit_target(broker: Broker, registry: Registry | None) -> Broker:
    """The broker that actually receives the opt-out (`covered_by` parent, else itself)."""
    if broker.covered_by and registry is not None:
        try:
            return registry.get(broker.covered_by)
        except KeyError:
            return broker
    return broker


def tier_for(broker: Broker, profile: Profile, cfg: Config | None = None, *,
             registry: Registry | None = None) -> Tier:
    """Tier for (broker, profile). With `registry`, a covered_by broker gets its parent's tier."""
    target = submit_target(broker, registry)
    if profile.value_only:
        # BL-IN-08: form steps fill a name/address; a value-only removal never runs them
        if has_email_route(target) and profile.mailbox is not None:
            return Tier.EMAIL
        return Tier.ASSISTED
    if automatic_eligible(target, profile, cfg):
        return Tier.AUTOMATIC
    if has_email_route(target) and profile.mailbox is not None:
        return Tier.EMAIL
    return Tier.ASSISTED
