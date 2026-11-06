"""Shared helpers for submitters: data minimization and evidence paths.

DATA MINIMIZATION (shared rule 6): a broker only ever gets
  * fields its listings already show (Listing.shown_fields), intersected with what the
    broker needs (Broker.required_fields, or name/city/state/url/email if unspecified);
  * for a "blind" broker (no search, so no listing): the name, plus city/state only if the
    broker requires them;
  * the removal mailbox (never a personal email);
  * a phone number only if shown AND required AND permissions.allow_phone_disclosure.
DOB, relatives and personal emails are never included.
"""
from __future__ import annotations

from types import SimpleNamespace

from ..models import Broker, Evidence, EvidenceKind, Listing, MatchLevel, Profile, ProfileField

F = ProfileField
_DEFAULT_NEEDS = {F.FULL_NAME, F.CITY, F.STATE, F.LISTING_URL, F.EMAIL}
_BLIND_OK = {F.FULL_NAME, F.FIRST_NAME, F.LAST_NAME, F.MIDDLE_NAME, F.CITY, F.STATE,
             F.LISTING_URL, F.EMAIL}
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
    else:
        shown = set(_BLIND_OK)
    out = (needs & shown) - _NEVER
    if F.PHONE in out and not profile.permissions.allow_phone_disclosure:
        out.discard(F.PHONE)
    out.add(F.FULL_NAME)      # the name is how any broker finds the record
    return out


def _current(profile: Profile):
    return next((a for a in profile.addresses if a.current), profile.addresses[0])


def copy_fields(profile: Profile, broker: Broker, listings: list[Listing]) -> dict[str, str]:
    """Label -> value for the Assisted card's Copy buttons. Minimized (see module doc)."""
    allowed = allowed_fields(profile, broker, listings)
    cur = _current(profile)
    out: dict[str, str] = {}
    if F.FULL_NAME in allowed:
        out["Full name"] = f"{profile.name.first} {profile.name.last}"
    if F.FIRST_NAME in allowed and F.FIRST_NAME in broker.required_fields:
        out["First name"] = profile.name.first
    if F.LAST_NAME in allowed and F.LAST_NAME in broker.required_fields:
        out["Last name"] = profile.name.last
    if F.CITY in allowed:
        out["City"] = cur.city
    if F.STATE in allowed:
        out["State"] = cur.state
    if F.STREET_ADDRESS in allowed and cur.street:
        out["Street address"] = cur.street
    if F.ZIP in allowed and cur.zip:
        out["ZIP code"] = cur.zip
    if F.AGE in allowed and (age := profile.estimated_age()) is not None:
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
    if F.FULL_NAME in allowed or F.FIRST_NAME in allowed:
        p.update(first=profile.name.first, last=profile.name.last,
                 full_name=f"{profile.name.first} {profile.name.last}")
    if F.MIDDLE_NAME in allowed and profile.name.middle:
        p["middle"] = profile.name.middle
    if F.CITY in allowed:
        p["city"] = cur.city
    if F.STATE in allowed:
        p["state"] = cur.state
    if F.STREET_ADDRESS in allowed and cur.street:
        p["street"] = cur.street
    if F.ZIP in allowed and cur.zip:
        p["zip"] = cur.zip
    if F.AGE in allowed:
        p["age"] = profile.estimated_age()
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
