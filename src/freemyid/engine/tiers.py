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

`tier_reason` is that same choice as a code (`email_ok`, `no_email_route`,
`form_not_verified`, `permissions_block`, `automation_off`), or None when the
tier is automatic. The code never includes contact data.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

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

TierReason = Literal[
    "no_email_route",
    "form_not_verified",
    "permissions_block",
    "automation_off",
    "email_ok",
]

# Assisted codes for the automatic-eligibility gates that have one. Any other
# gate (no real form, captcha, account, human step) stays `no_email_route`.
_ASSISTED_REASON: dict[str, TierReason] = {
    "not_verified": "form_not_verified",
    "permissions": "permissions_block",
    "automation": "automation_off",
}


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


def _automatic_block(broker: Broker, profile: Profile, cfg: Config | None) -> str | None:
    """First failed automatic check, or None when every check passes."""
    if not has_real_form(broker):
        return "no_form"
    if broker.verification_status != VerificationStatus.VERIFIED:
        return "not_verified"
    if broker.has_captcha:
        return "captcha"
    if broker.method == Method.ACCOUNT_REQUIRED:  # never creates accounts itself
        return "account"
    if any(st.action == "human" for st in broker.form):
        return "human"
    if _permissions_block(broker, profile):
        return "permissions"
    if not browser_automation_allowed(cfg):
        return "automation"
    return None


def automatic_eligible(broker: Broker, profile: Profile, cfg: Config | None = None) -> bool:
    return _automatic_block(broker, profile, cfg) is None


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


def tier_reason(broker: Broker, profile: Profile, cfg: Config | None = None, *,
                registry: Registry | None = None) -> TierReason | None:
    """Why `tier_for` chose this tier. One code, or None when the tier is automatic.

    email_ok           email: the site takes email and a removal mailbox is set.
    form_not_verified  assisted: the form steps are not verified.
    permissions_block  assisted: the profile disallows an ID or phone the site
                       requires, and that check is what blocked automatic.
    automation_off     assisted: browser automation is off, and that check is
                       what blocked automatic.
    no_email_route     assisted for any other reason, including no usable email
                       tier (no email route, or a route and no mailbox).

    A phone-only or email-only removal never runs a form, so it is only
    `email_ok` or `no_email_route`. Automatic has no code in this set.
    The result is a code or None, never an address, mailbox or URL.
    """
    target = submit_target(broker, registry)
    tier = tier_for(broker, profile, cfg, registry=registry)
    if tier is Tier.AUTOMATIC:
        return None
    if tier is Tier.EMAIL:
        return "email_ok"
    if profile.value_only:
        return "no_email_route"
    block = _automatic_block(target, profile, cfg)
    found = _ASSISTED_REASON.get(block) if block is not None else None
    if found is not None:
        return found
    return "no_email_route"
