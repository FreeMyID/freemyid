"""Result models for the "find me first" exposure scan (ROADMAP 3.2, docs/EXPOSURE.md).

OWNER: automation-engineer. Built by `freemyid.engine.exposure`; read by the CLI
(`freemyid exposure`) and the dashboard (`exposure.latest_exposure(store, profile)`).

Data kept: listing URL, match level, signal NAMES and timestamps, plus counts. Never raw
HTML, never the names/ages/addresses a page showed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import MatchLevel, utcnow

#: found          the site shows a confirmed or possible listing
#: not_found      the site was read and shows nothing that matches
#: check_by_hand  not read automatically (bot protection, unknown access, error, offline):
#:                open `check_url` yourself
EntryStatus = Literal["found", "not_found", "check_by_hand"]

#: Why an entry is check_by_hand (stable codes; docs/EXPOSURE.md).
HAND_REASONS = {
    "bot_blocked": "This site blocks automatic checks.",
    "unknown_access": "We have not confirmed this site can be checked automatically yet.",
    "needs_browser": "This site needs a browser window to search.",
    "challenge": "The site asked for a 'prove you are human' check.",
    "http_error": "The site did not answer normally.",
    "network": "The site could not be reached.",
    "blocked_by_policy": "The site tried to send us somewhere we do not go.",
    "page_unrecognized": "The site's page has changed and could not be read.",
    "no_parser": "We cannot read this site's results automatically yet.",
    "offline": "Offline mode: nothing was fetched.",
    "too_large": "The page was too large to read safely.",
    "too_slow": "The site took too long to answer.",
    "missing_details": "This site's search needs details we do not have for you.",
}


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExposureListing(_M):
    url: str
    match_level: MatchLevel
    signals: list[str] = []          # matcher signal names: city, age, relative, phone, email
    contact_shown: bool = False      # the listing shows a phone number or street address
    relatives_shown: int = 0         # how many relatives/associates it names (count only)


class ExposureEntry(_M):
    broker_id: str
    broker_name: str
    status: EntryStatus
    reason: str | None = None        # HAND_REASONS key when check_by_hand
    match_level: MatchLevel | None = None   # best listing on this site
    signals: list[str] = []          # union over listings
    listings: list[ExposureListing] = []
    check_url: str | None = None     # the search page to open by hand (built from the profile)
    from_store: bool = False         # listings come from earlier runs, not this fetch
    old_address_checked: bool = False   # one previous-address search was read as well
    previous_name_checked: bool = False  # one previous-name (maiden name) search as well
    checked_at: datetime = Field(default_factory=utcnow)


class Coverage(_M):
    """How much of the registry the score is based on (ROADMAP 3.2: a score is always shown
    with its coverage). `found + uncertain + not_found + check_by_hand == sites_total`."""
    sites_total: int = 0      # sites with a search page we know about
    sites_checked: int = 0    # read automatically (this scan, or the 24-hour cache)
    found: int = 0            # shows a confirmed listing of you (incl. earlier runs)
    not_found: int = 0        # read and shows nothing that matches
    check_by_hand: int = 0    # not read, nothing known: open `check_url` yourself
    uncertain: int = 0        # shows only "possible" listings: needs "Is this you?"


def coverage_of(entries: list[ExposureEntry]) -> Coverage:
    return Coverage(
        sites_total=len(entries),
        sites_checked=sum(1 for e in entries
                          if e.status in ("found", "not_found") and not e.from_store),
        found=sum(1 for e in entries
                  if e.status == "found" and e.match_level == MatchLevel.CONFIRMED),
        not_found=sum(1 for e in entries if e.status == "not_found"),
        check_by_hand=sum(1 for e in entries if e.status == "check_by_hand"),
        uncertain=sum(1 for e in entries
                      if e.status == "found" and e.match_level != MatchLevel.CONFIRMED))


def _n(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def coverage_note(cov: Coverage) -> str:
    """One plain-English line to show next to the score. Never says "you are safe"."""
    if cov.sites_total == 0:
        return "No sites could be searched for you yet."
    if cov.sites_checked == 0:
        out = (f"We could not check any of the {_n(cov.sites_total, 'site', 'sites')} "
               "automatically, so this score does not mean you are safe.")
    else:
        out = (f"This score is based on the {_n(cov.sites_checked, 'site', 'sites')} we "
               f"could check, out of {cov.sites_total}. A low score does not mean you are "
               "safe.")
    if cov.check_by_hand:
        out += (f" {_n(cov.check_by_hand, 'site needs', 'sites need')} checking by hand.")
    if cov.uncertain:
        out += (f" {_n(cov.uncertain, 'site', 'sites')} may show you; please tell us if "
                f"{'it is' if cov.uncertain == 1 else 'they are'} you.")
    return out


#: The checklist Californians should do first (brokers/checklists.yaml; matrix: "point
#: Californians to DROP first"). `checklist_state.drop_first(profile)` decides.
DROP_CHECKLIST_ID = "ca_drop"
DROP_NOTE = ("You live in California. Start with California's free DROP request: one request "
             "asks every registered data broker to delete your information. Then deal with "
             "the sites below.")


class ScoreLine(_M):
    points: int
    text: str                        # plain English, PII-free


class ExposureResult(_M):
    version: Literal[1] = 1
    profile_id: str
    created_at: datetime = Field(default_factory=utcnow)
    offline: bool = False
    practice_mode: bool = True
    score: int = Field(ge=0, le=100)
    explanation: list[ScoreLine] = []
    entries: list[ExposureEntry] = []
    drop_first: bool = False         # California: do the ca_drop checklist first

    @property
    def coverage(self) -> Coverage:
        return coverage_of(self.entries)

    @property
    def coverage_note(self) -> str:
        return coverage_note(self.coverage)

    @property
    def first_checklist(self) -> str | None:
        return DROP_CHECKLIST_ID if self.drop_first else None

    def by_status(self, status: EntryStatus) -> list[ExposureEntry]:
        return [e for e in self.entries if e.status == status]

    @property
    def confirmed_sites(self) -> int:
        return sum(1 for e in self.entries if e.match_level == MatchLevel.CONFIRMED)

    @property
    def possible_sites(self) -> int:
        return sum(1 for e in self.entries if e.match_level == MatchLevel.POSSIBLE)
