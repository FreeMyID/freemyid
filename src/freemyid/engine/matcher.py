"""Deterministic listing matcher (rapidfuzz). No I/O.

A broker search result is turned into a `Candidate` by a parser, then `score()` decides:
  CONFIRMED = name match AND >= 2 supporting signals   -> auto-submit allowed
  POSSIBLE  = name match AND exactly 1 signal          -> REVIEW_MATCH todo
  NO_MATCH  = otherwise                                -> ignored

Signals: location (city+state, or state alone counts only together with a city), age +-2,
relative, phone, email. `match_reasons` holds signal NAMES only (never values).

SEC-99 household guard (a spouse or parent shares the city and the relatives): CONFIRMED is
capped at POSSIBLE when the shown age is more than AGE_CONFLICT_YEARS off, or when the name
matched only through a nickname group or fuzzily and no personal signal (age, phone, email)
backs it up.

SEC-103 (spouse close in age): when the shown first name is not one the person uses and is
not tied to them through one unambiguous nickname group (Peggy for a Margaret is; Patrick for
a Pat, Alex for an Alexandra or Chris for a Christina is not), only phone or email can confirm
it. An age within 2 years is not enough, because spouses are often that close in age.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from rapidfuzz import fuzz

from ..models import Listing, MatchLevel, Profile, ProfileField, utcnow
from . import nicknames

NAME_THRESHOLD = 88.0       # token_sort_ratio on normalized "first last"
RELATIVE_THRESHOLD = 85.0
#: SEC-99: an age shown more than this many years off the person's caps the match at POSSIBLE
#: (a spouse or parent in the same house shares the city and the relatives).
AGE_CONFLICT_YEARS = 5
#: SEC-99: signals a household does not share. A name that is not an exact match (only via a
#: nickname group, or only fuzzy) needs one of these to reach CONFIRMED.
PERSONAL_SIGNALS = frozenset({"age", "phone", "email"})
#: SEC-103: signals that tell two people of similar age in one household apart.
CONTACT_SIGNALS = frozenset({"phone", "email"})
USER_CONFIRMED = "user_confirmed"

_US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI",
    "wyoming": "WY", "district of columbia": "DC",
}
STATE_NAMES = {v: k.title() for k, v in _US_STATES.items()}


@dataclass
class Candidate:
    """One search result as parsed from a broker page. Values are page DATA only."""
    url: str
    name: str | None = None
    age: int | None = None
    locations: list[str] = field(default_factory=list)   # "Springfield, IL" style
    relatives: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    has_address: bool = False      # page shows a street address
    has_dob: bool = False


@dataclass
class MatchResult:
    level: MatchLevel
    score: float
    reasons: list[str]


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def digits(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    return d[-10:] if len(d) >= 10 else d


def parse_age(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"(?:age|aged)\D{0,3}(\d{1,3})", text, re.IGNORECASE) or re.search(r"\b(\d{2,3})\b",
                                                                            text)
    if m:
        v = int(m.group(1))
        return v if 0 < v < 131 else None
    return None


def parse_location(text: str) -> tuple[str, str | None]:
    """'Springfield, IL 62701' -> ('springfield', 'IL'). State may be a full name."""
    t = text.strip()
    m = re.match(r"^\s*(.+?)\s*,\s*([A-Za-z .]+?)(?:\s+\d{5}(?:-\d{4})?)?\s*$", t)
    if not m:
        return norm(t), None
    city, st = m.group(1), m.group(2).strip().rstrip(".")
    if len(st) == 2:
        return norm(city), st.upper()
    return norm(city), _US_STATES.get(st.lower())


def _profile_name_variants(p: Profile, groups: bool = True) -> list[str]:
    out: list[str] = []
    # given names: current and previous first names, the profile's own nicknames, and (if
    # `groups`) the common nickname groups for each (Robert <-> Bob). Every first is tried
    # with every last name the person has had (maiden name included).
    firsts: set[str] = set()
    for f in [*(n.first for n in p.all_names()), *p.nicknames]:
        firsts |= nicknames.expand(norm(f)) if groups else {norm(f)}
    lasts = [n.last for n in p.all_names()]
    for f in firsts:
        for la in lasts:
            out.append(norm(f"{f} {la}"))
    for n in p.all_names():
        out.append(norm(f"{n.first} {n.last}"))
        if n.middle:
            out.append(norm(f"{n.first} {n.middle} {n.last}"))
    return sorted({o for o in out if o})


def name_score(p: Profile, shown: str | None, groups: bool = True) -> float:
    s = norm(shown)
    if not s:
        return 0.0
    toks = s.split()
    # drop single-letter middle initials so "Jane Q Testperson" ~ "Jane Testperson"
    s2 = " ".join(t for t in toks if len(t) > 1) or s
    best = 0.0
    for v in _profile_name_variants(p, groups):
        best = max(best, fuzz.token_sort_ratio(v, s), fuzz.token_sort_ratio(v, s2))
    return float(best)


def exact_name(p: Profile, shown: str | None) -> bool:
    """The shown name is one the person has actually had or uses (their own first names and
    nicknames, any of their last names), not just a nickname-group or fuzzy match."""
    return name_score(p, shown, groups=False) >= 100.0


def _own_firsts(p: Profile) -> set[str]:
    return {norm(f) for f in [*(n.first for n in p.all_names()), *p.nicknames] if norm(f)}


def shown_first(p: Profile, shown: str | None) -> str | None:
    """The shown given name: the first token that is not an initial and not one of the
    person's last names ("Testperson, Patrick" -> "patrick")."""
    lasts = {t for n in p.all_names() for t in norm(n.last).split()}
    for t in norm(shown).split():
        if len(t) > 1 and t not in lasts:
            return t
    return None


def other_persons_name(p: Profile, shown: str | None) -> bool:
    """SEC-103: the shown first name is a known given name the person does not use and is not
    tied to them through exactly one nickname group. It may belong to someone else in the
    house: Patrick for a Pat (Pat is also Patricia), Alex for an Alexandra (Alex is also
    Alexander), Chris for a Christina, Bert for a Robert (Bert is also Albert)."""
    s = shown_first(p, shown)
    if s is None:
        return False
    own = _own_firsts(p)
    if s in own:
        return False
    groups = nicknames.groups_of(s)
    if not groups:
        return False            # not a known given name: SEC-99 rules alone apply
    return not any(len(g := nicknames.groups_of(f)) == 1 and groups == g for f in own)


def score(profile: Profile, c: Candidate, today: date | None = None) -> MatchResult:
    ns = name_score(profile, c.name)
    if ns < NAME_THRESHOLD:
        return MatchResult(MatchLevel.NO_MATCH, round(ns * 0.5, 1), [])
    reasons: list[str] = []

    # location: city + state from any current/previous address
    prof_locs = {(norm(a.city), a.state) for a in profile.addresses}
    for loc in c.locations:
        city, st = parse_location(loc)
        if any(city == pc and (st is None or st == ps) for pc, ps in prof_locs):
            reasons.append("city")
            break

    est = profile.estimated_age(today)
    if est is not None and c.age is not None and abs(est - c.age) <= 2:
        reasons.append("age")

    if profile.relatives and c.relatives:
        rels = [norm(r) for r in profile.relatives]
        if any(fuzz.token_sort_ratio(norm(x), r) >= RELATIVE_THRESHOLD
               for x in c.relatives for r in rels):
            reasons.append("relative")

    pphones = {digits(x) for x in profile.phones if digits(x)}
    if pphones and any(digits(x) in pphones for x in c.phones):
        reasons.append("phone")

    pemails = {e.strip().lower() for e in profile.emails}
    if pemails and any(e.strip().lower() in pemails for e in c.emails):
        reasons.append("email")

    n = len(reasons)
    level = MatchLevel.CONFIRMED if n >= 2 else MatchLevel.POSSIBLE if n == 1 else \
        MatchLevel.NO_MATCH
    if level == MatchLevel.CONFIRMED:
        # SEC-99: never auto-submit for another member of the household
        age_conflict = est is not None and c.age is not None and \
            abs(est - c.age) > AGE_CONFLICT_YEARS
        loose_name = not exact_name(profile, c.name) and \
            not PERSONAL_SIGNALS.intersection(reasons)
        # SEC-103: a name that may be another household member's needs phone or email
        other_name = not CONTACT_SIGNALS.intersection(reasons) and \
            other_persons_name(profile, c.name)
        if age_conflict or loose_name or other_name:
            level = MatchLevel.POSSIBLE
    sc = min(100.0, round(ns * 0.5 + 12.5 * n, 1))
    return MatchResult(level, sc, reasons)


def shown_fields(c: Candidate) -> list[ProfileField]:
    """What the listing itself displays (data minimization input)."""
    out: list[ProfileField] = [ProfileField.LISTING_URL]
    if c.name:
        out += [ProfileField.FULL_NAME, ProfileField.FIRST_NAME, ProfileField.LAST_NAME]
    if c.locations:
        out += [ProfileField.CITY, ProfileField.STATE]
    if c.age is not None:
        out.append(ProfileField.AGE)
    if c.phones:
        out.append(ProfileField.PHONE)
    if c.has_address:
        out += [ProfileField.STREET_ADDRESS, ProfileField.ZIP]
    if c.has_dob:
        out.append(ProfileField.DOB)
    return out


def to_listing(profile: Profile, broker_id: str, c: Candidate,
               today: date | None = None) -> Listing:
    r = score(profile, c, today)
    now = utcnow()
    return Listing(
        profile_id=profile.id, broker_id=broker_id, url=c.url, name_shown=c.name,
        age_shown=c.age, locations_shown=c.locations[:10], relatives_shown=c.relatives[:20],
        match_score=r.score, match_level=r.level, match_reasons=r.reasons,
        shown_fields=shown_fields(c), first_seen=now, last_seen=now,
    )


def score_all(profile: Profile, broker_id: str, cands: list[Candidate],
              today: date | None = None) -> list[Listing]:
    """Score candidates, drop NO_MATCH, de-duplicate by URL (best score wins)."""
    best: dict[str, Listing] = {}
    for c in cands:
        li = to_listing(profile, broker_id, c, today)
        if li.match_level == MatchLevel.NO_MATCH:
            continue
        cur = best.get(li.url)
        if cur is None or li.match_score > cur.match_score:
            best[li.url] = li
    return sorted(best.values(), key=lambda x: -x.match_score)
