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
    checked_at: datetime = Field(default_factory=utcnow)


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

    def by_status(self, status: EntryStatus) -> list[ExposureEntry]:
        return [e for e in self.entries if e.status == status]

    @property
    def confirmed_sites(self) -> int:
        return sum(1 for e in self.entries if e.match_level == MatchLevel.CONFIRMED)

    @property
    def possible_sites(self) -> int:
        return sum(1 for e in self.entries if e.match_level == MatchLevel.POSSIBLE)
