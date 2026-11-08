"""Letter / email / call-script rendering from jinja2 templates in freemyid/templates/.

`render(template, **vars) -> str` is the CLI-facing entry point (interfaces.py).
`letter_vars(...)` builds the variable set with DATA MINIMIZATION: only fields the broker's
listings already show (Listing.shown_fields) plus the removal mailbox are included.

Every email template starts with a `Subject: ...` line; `split_subject` separates it.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from ..models import Broker, Listing, Profile, ProfileField, StateLaw
from .matcher import STATE_NAMES

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATES = ("generic_removal", "ccpa", "state_privacy", "follow_up", "legal_demand",
             "postal_letter", "phone_script")
_ALIASES = {"generic": "generic_removal", "cpra": "ccpa", "california": "ccpa",
            "state": "state_privacy"}

_env = SandboxedEnvironment(loader=FileSystemLoader(str(TEMPLATES_DIR)),
                            undefined=StrictUndefined, autoescape=False,
                            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)


def _resolve(template: str) -> str:
    name = template.removesuffix(".j2").removesuffix(".txt")
    name = _ALIASES.get(name, name)
    if name not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}")
    return f"{name}.txt.j2"


def render(template: str, **vars: Any) -> str:
    """Render a named template. Missing variables raise (StrictUndefined)."""
    defaults: dict[str, Any] = {
        "listing_urls": [], "city": None, "state": None, "age": None, "phone": None,
        "statute_name": None, "citation": None, "response_days": None,
        "original_request_date": None, "response_deadline": None, "reference": None,
        "reply_requested_days": None, "reply_requested_by": None,
        "broker_postal": None, "complaint_urls": [], "today": date.today().isoformat(),
        "is_agent": False, "agent_name": None, "street_address": None, "zip": None,
        "extension_days": None, "verification_rules": [], "state_name": None,
    }
    defaults.update(vars)
    return _env.get_template(_resolve(template)).render(**defaults)


# Plain-words verification rules, per state, quoted in a letter ONLY when that state's law
# is cited (the letter_vars state_law is already engine.outbox.effective_law's result).
# Source: brokers/state_law_deletion_matrix.yaml common_rules.verification and
# .data_obtained_from_third_parties, both `evidence: statute_text` (2026-11-07):
# Va. Code 59.1-577; Minn. Stat. 325M.14 subd. 4(h), 4(k); KRS 367.3615(3)(d), (3)(e)
# (matrix 2026.11.07.2); oag.ca.gov/privacy/ccpa.
# Keep this in step with the matrix; never add a state whose text was not checked.
_VERIFY_LIMIT = ("If you cannot confirm who I am with reasonable effort, the law does not "
                 "require you to act until you can. If you need more to confirm it, please "
                 "ask me only for the information you reasonably need.")
_SUPPRESS_OK = ("If you got my data from someone else, you may keep a minimal record "
                "only so that it stays deleted.")
_MN_OPT_OUT = ("My request to stop selling my data and using it for targeted advertising "
               "generally does not need to be verified. You may refuse it only if you have "
               "a documented, good-faith belief that it is fraudulent.")
VERIFICATION_RULES: dict[str, list[str]] = {
    "VA": [_VERIFY_LIMIT, _SUPPRESS_OK],
    "MN": [_VERIFY_LIMIT, _MN_OPT_OUT, _SUPPRESS_OK],
    "KY": [_VERIFY_LIMIT, _SUPPRESS_OK],
}
AGENT_RULES: dict[str, str] = {
    "CA": "California lets an authorized agent make this request for me. The agent can "
          "be a person or a business registered with the California Secretary of State.",
}


def split_subject(text: str) -> tuple[str, str]:
    first, _, rest = text.partition("\n")
    if first.lower().startswith("subject:"):
        return first.split(":", 1)[1].strip(), rest.lstrip("\n")
    return "Personal data deletion request", text


def choose_template(state_law: StateLaw | None) -> str:
    """Initial-request template family for a law that is ALREADY known to apply and be in
    effect (see engine.outbox.effective_law): ccpa for CA, state_privacy for another state
    with a statute, generic_removal otherwise."""
    if state_law is None:
        return "generic_removal"
    if state_law.state.upper() == "CA":
        return "ccpa"
    return "state_privacy" if state_law.statute_name else "generic_removal"


def letter_vars(profile: Profile, broker: Broker, listings: list[Listing],
                state_law: StateLaw | None = None, *,
                original_request_date: datetime | None = None,
                reference: str | None = None, today: date | None = None) -> dict[str, Any]:
    """Variables for templates, limited to what the listings already show.

    If there are no listings (blind request to a non-searchable broker) only the name and
    the removal mailbox are included.
    """
    today = today or date.today()
    shown: set[ProfileField] = {f for li in listings for f in li.shown_fields}
    cur = next((a for a in profile.addresses if a.current), profile.addresses[0])
    v: dict[str, Any] = {
        # SEC-29: middle name / suffix only if the listing itself shows the middle name
        "name": profile.name.full if ProfileField.MIDDLE_NAME in shown
        else f"{profile.name.first} {profile.name.last}",
        "broker_name": broker.name,
        "listing_urls": [li.url for li in listings],
        "mailbox": profile.mailbox.address if profile.mailbox else None,
        "today": today.isoformat(),
        "is_agent": profile.consent.basis.value != "self",
        "agent_name": profile.consent.attested_by
        if profile.consent.basis.value != "self" else None,
    }
    if ProfileField.CITY in shown:
        v["city"] = cur.city
    if ProfileField.STATE in shown:
        v["state"] = cur.state
    if ProfileField.AGE in shown:
        v["age"] = profile.estimated_age(today)
    if ProfileField.STREET_ADDRESS in shown and cur.street:
        v["street_address"] = cur.street
    if ProfileField.ZIP in shown and cur.zip:
        v["zip"] = cur.zip
    if ProfileField.PHONE in shown and profile.permissions.allow_phone_disclosure and \
            profile.phones:
        v["phone"] = profile.phones[0]
    if state_law:
        v["statute_name"] = state_law.statute_name
        v["citation"] = state_law.citation
        v["response_days"] = state_law.response_days
        v["extension_days"] = state_law.extension_days
        st = state_law.state.upper()
        rules = list(VERIFICATION_RULES.get(st, []))
        if profile.consent.basis.value == "authorized_agent" and st in AGENT_RULES:
            rules.append(AGENT_RULES[st])
        v["verification_rules"] = rules
        v["state_name"] = STATE_NAMES.get(state_law.state, state_law.state)
        v["complaint_urls"] = [str(u) for u in [state_law.ag_complaint_url,
                                                *state_law.other_complaint_urls] if u]
    if original_request_date:
        v["original_request_date"] = original_request_date.date().isoformat()
        start = original_request_date.date()
        # SEC-90: a legal due date only from a VERIFIED window (effective_law has already
        # dropped response_days unless the matrix evidence is statute_text). Otherwise the
        # letter only says when we hoped for a reply, never that one was owed.
        if state_law and state_law.response_days:
            v["response_deadline"] = (start + timedelta(days=state_law.response_days)
                                      ).isoformat()
        elif broker.typical_processing_days:
            v["reply_requested_days"] = broker.typical_processing_days
            v["reply_requested_by"] = (start + timedelta(
                days=broker.typical_processing_days)).isoformat()
    if reference:
        v["reference"] = reference
    if broker.postal:
        v["broker_postal"] = "\n".join([broker.postal.recipient, *broker.postal.lines])
    return v
