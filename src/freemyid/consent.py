"""The one consent gate. The CLI, the runner and the wizard all import it.

OWNER: orchestrator (written by peer session e8 for SEC-06).

Rules (fail closed):
* someone has to have typed their name to attest;
* the consent text version must be one this build knows about;
* a minor (``is_minor`` flag OR an age computed from dob/age under 18) needs
  GUARDIAN_OF_MINOR;
* an adult needs SELF or AUTHORIZED_AGENT (GUARDIAN_OF_MINOR is refused);
* AUTHORIZED_AGENT needs ``authorization_doc`` to name stored consent evidence
  for this same profile, and its encrypted file has to exist on disk.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from . import paths
from .models import ConsentBasis, Profile

if TYPE_CHECKING:  # pragma: no cover
    from .storage import Store

#: Version id of the consent text the wizard currently shows.
CURRENT_TEXT_VERSION = "2026-11-c"
#: Every consent text version a stored profile may have accepted. Add (never remove)
#: when the wording changes in a way that doesn't need everyone to consent again.
ACCEPTED_TEXT_VERSIONS: frozenset[str] = frozenset({"2026-11-a", "2026-11-b", CURRENT_TEXT_VERSION})
#: broker_id the wizard uses when it saves the signed authorization as evidence.
CONSENT_EVIDENCE_BROKER = "_consent"

ADULT_AGE = 18


def is_minor(p: Profile, today: date | None = None) -> bool:
    """True if the profile is flagged as a minor OR its estimated age is under 18."""
    if p.is_minor:
        return True
    age = p.estimated_age(today)
    return age is not None and age < ADULT_AGE


def authorization_on_file(p: Profile, store: Store) -> bool:
    """The signed authorization named in the consent is stored for this profile and on disk."""
    doc = p.consent.authorization_doc
    if not doc:
        return False
    for ev in store.list_evidence(p.id, CONSENT_EVIDENCE_BROKER):
        if ev.id == doc and ev.profile_id == p.id:
            return (paths.evidence_dir() / ev.relpath).is_file()
    return False


def consent_ok(p: Profile, store: Store | None = None, *,
               today: date | None = None) -> tuple[bool, str]:
    """Hard consent gate. Returns ``(ok, reason)``; reason is "" when ok.

    Pass ``store`` so the authorized-agent document can be checked. Without a store an
    AUTHORIZED_AGENT profile is refused (fail closed).
    """
    c = p.consent
    if not c.attested_by.strip():
        return False, "consent has no attesting name"
    if c.text_version not in ACCEPTED_TEXT_VERSIONS:
        return False, "consent was given to an older or unknown consent text; please re-confirm"
    if is_minor(p, today):
        if c.basis != ConsentBasis.GUARDIAN_OF_MINOR:
            return False, "minor profile requires parent/guardian consent"
        return True, ""
    if c.basis == ConsentBasis.GUARDIAN_OF_MINOR:
        return False, ("guardian consent only covers people under 18; this adult must "
                       "consent themselves or sign an agent authorization")
    if c.basis == ConsentBasis.AUTHORIZED_AGENT:
        if not c.authorization_doc:
            return False, "authorized agent needs the signed authorization attached"
        if store is None or not authorization_on_file(p, store):
            return False, "the signed authorization could not be found; please attach it again"
        return True, ""
    if c.basis == ConsentBasis.SELF:
        return True, ""
    return False, f"unknown consent basis {c.basis!r}"
