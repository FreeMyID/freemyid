"""Shared helpers for submitters: data minimization and evidence paths.

DATA MINIMIZATION (shared rule 6): a broker only ever gets
  * fields its listings already show (Listing.shown_fields), intersected with what the
    broker needs (Broker.required_fields, or name/city/state/url/email if unspecified);
  * for a "blind" broker (no search, so no listing): the name, plus city/state only if the
    broker requires them;
  * the removal mailbox (never a personal email);
  * a phone number only if shown AND required AND permissions.allow_phone_disclosure.
DOB, relatives and personal emails are never included. Address lines come only from the
address marked current; a past address is never a substitute.
"""
from __future__ import annotations

from types import SimpleNamespace

from ..models import (
    Address,
    Broker,
    Evidence,
    EvidenceKind,
    Listing,
    MatchLevel,
    Profile,
    ProfileField,
)

F = ProfileField
_DEFAULT_NEEDS = {F.FULL_NAME, F.CITY, F.STATE, F.LISTING_URL, F.EMAIL}
_NEVER = {F.DOB, F.ID_DOCUMENT}


def confirmed(listings: list[Listing]) -> list[Listing]:
    return [li for li in listings if li.match_level == MatchLevel.CONFIRMED]


def allowed_fields(profile: Profile, broker: Broker, listings: list[Listing]) -> set[F]:
    """Profile fields this broker may receive for these listings."""
    needs = set(broker.required_fields) or set(_DEFAULT_NEEDS)
    if F.FULL_NAME in needs:
        needs |= {F.FIRST_NAME, F.LAST_NAME}
    if listings:
        shown = {f for li in listings for f in li.shown_fields} | {F.LISTING_URL, F.EMAIL}
        if F.FULL_NAME in shown:
            shown |= {F.FIRST_NAME, F.LAST_NAME}
        out = (needs & shown) - _NEVER
    else:
        # No listing: the name, city/state only when this broker lists them, plus the mailbox.
        out = {F.FULL_NAME, F.FIRST_NAME, F.LAST_NAME}
        if F.CITY in broker.required_fields:
            out.add(F.CITY)
        if F.STATE in broker.required_fields:
            out.add(F.STATE)
        if F.EMAIL in needs:
            out.add(F.EMAIL)
    if F.PHONE in out and not profile.permissions.allow_phone_disclosure:
        out.discard(F.PHONE)
    return out


def shown_age(listings: list[Listing]) -> int | None:
    """SEC-115: the age the site itself shows (confirmed listings first), never the
    person's real age computed from their birth year. None if no listing shows one."""
    for li in [*confirmed(listings), *listings]:
        if li.age_shown is not None:
            return li.age_shown
    return None


def _current(profile: Profile) -> Address | None:
    """The address marked current. A past address is never used in its place."""
    return next((a for a in profile.addresses if a.current), None)


def value_copy_fields(profile: Profile, listings: list[Listing]) -> dict[str, str]:
    """BL-IN-08 Assisted card for a phone/email-only removal: the value(s) to remove (only
    with the matching explicit permission), the listing links and the removal mailbox.
    Never a name or an address."""
    out: dict[str, str] = {}
    if profile.removal_scope == "phone" and profile.permissions.allow_phone_disclosure:
        for i, ph in enumerate(profile.phones[:3]):
            out["Phone number" if i == 0 else f"Phone number {i + 1}"] = ph
    elif profile.removal_scope == "email" and profile.permissions.allow_email_disclosure:
        for i, em in enumerate(profile.emails[:3]):
            out["Email address" if i == 0 else f"Email address {i + 1}"] = em
    for i, li in enumerate(confirmed(listings) or listings):
        out["Listing link" if i == 0 else f"Listing link {i + 1}"] = li.url
    if profile.mailbox:
        out["Email for removals"] = profile.mailbox.address
    return out


def copy_fields(profile: Profile, broker: Broker, listings: list[Listing]) -> dict[str, str]:
    """Label -> value for the Assisted card's Copy buttons. Minimized (see module doc)."""
    if profile.value_only:
        return value_copy_fields(profile, listings)
    allowed = allowed_fields(profile, broker, listings)
    cur = _current(profile)
    out: dict[str, str] = {}
    if F.FULL_NAME in allowed:
        out["Full name"] = f"{profile.name.first} {profile.name.last}"
    if F.FIRST_NAME in allowed and F.FIRST_NAME in broker.required_fields:
        out["First name"] = profile.name.first
    if F.LAST_NAME in allowed and F.LAST_NAME in broker.required_fields:
        out["Last name"] = profile.name.last
    if cur is not None and F.CITY in allowed:
        out["City"] = cur.city
    if cur is not None and F.STATE in allowed:
        out["State"] = cur.state
    if cur is not None and F.STREET_ADDRESS in allowed and cur.street:
        out["Street address"] = cur.street
    if cur is not None and F.ZIP in allowed and cur.zip:
        out["ZIP code"] = cur.zip
    if F.AGE in allowed and (age := shown_age(listings)) is not None:
        out["Age"] = str(age)
    if F.PHONE in allowed and profile.phones:
        out["Phone"] = profile.phones[0]
    for i, li in enumerate(confirmed(listings) or listings):
        out["Listing link" if i == 0 else f"Listing link {i + 1}"] = li.url
    if F.EMAIL in allowed and profile.mailbox:
        out["Email for removals"] = profile.mailbox.address
    return out


def form_vars(profile: Profile, broker: Broker, listing: Listing | None) -> dict:
    """Variables for FormStep.value templates. Only allowed fields exist; anything else is
    undefined, so a form step asking for it fails (and the run drops to Assisted)."""
    lis = [listing] if listing else []
    allowed = allowed_fields(profile, broker, lis)
    cur = _current(profile)
    p: dict[str, object] = {}
    if F.FULL_NAME in allowed:
        p["full_name"] = f"{profile.name.first} {profile.name.last}"
    if F.FIRST_NAME in allowed:
        p["first"] = profile.name.first
    if F.LAST_NAME in allowed:
        p["last"] = profile.name.last
    if F.MIDDLE_NAME in allowed and profile.name.middle:
        p["middle"] = profile.name.middle
    if cur is not None and F.CITY in allowed:
        p["city"] = cur.city
    if cur is not None and F.STATE in allowed:
        p["state"] = cur.state
    if cur is not None and F.STREET_ADDRESS in allowed and cur.street:
        p["street"] = cur.street
    if cur is not None and F.ZIP in allowed and cur.zip:
        p["zip"] = cur.zip
    if F.AGE in allowed and (age := shown_age(lis)) is not None:
        p["age"] = age          # SEC-115: the listing's own age, never a computed one
    if F.PHONE in allowed and profile.phones:
        p["phone"] = profile.phones[0]
    return {
        "profile": SimpleNamespace(**p),
        "listing": SimpleNamespace(url=listing.url) if listing else None,
        "mailbox": SimpleNamespace(address=profile.mailbox.address) if profile.mailbox else None,
        "broker": SimpleNamespace(id=broker.id, name=broker.name),
    }


def evidence(profile_id: str, broker_id: str, kind: EvidenceKind, ext: str, *,
             listing_id: str | None = None, request_id: str | None = None,
             caption: str | None = None) -> Evidence:
    """Evidence record with relpath <profile_id>/<broker_id>/<id>.<ext> (sha set on save)."""
    ev = Evidence(profile_id=profile_id, broker_id=broker_id, kind=kind, relpath="x",
                  sha256="", listing_id=listing_id, request_id=request_id, caption=caption)
    return ev.model_copy(update={"relpath": f"{profile_id}/{broker_id}/{ev.id}.{ext}"})
