"""Exposure score 0-100: what was found, weighted by kind of site, always with coverage.

ROADMAP 3.2, docs/EXPOSURE.md "Exposure score". Pure and deterministic: the same entries
always give the same score, lines, drivers and headline. No I/O, no PII (texts carry site
names and counts only, never what a page showed).

Per site:
* confirmed listing: 15, +5 per extra confirmed listing (2 at most), +5 if one of them shows
  a phone number or street address;
* only "possible" listings: 5;
each part multiplied by the site's category weight (`CATEGORY_WEIGHT`, percent, rounded half
up) so a public people-search page counts more than a marketing database.
Relatives/associates named on confirmed listings: 2 each, 10 at most (not weighted).
Sites checked by hand add nothing (listed, not counted). The total stops at 100.

A low score or zero only ever means "on the sites we could check". No text here says or
implies that the person is safe; `coverage_note` / `headline` say what was not checked.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..exposure_models import (
    Coverage,
    ExposureEntry,
    ScoreBand,
    ScoreDriver,
    ScoreLine,
)
from ..models import BrokerCategory, MatchLevel

W_CONFIRMED_SITE = 15
W_EXTRA_LISTING = 5
MAX_EXTRA_PER_SITE = 2
W_CONTACT = 5
W_POSSIBLE_SITE = 5
W_RELATIVE = 2
MAX_RELATIVE_POINTS = 10
MAX_DRIVERS = 3

#: Percent of the site points each kind of site gets. Anyone can open a people-search or
#: background-check page about you for free or a few dollars; the others are harder to
#: reach or show less. Unknown category (older stored scans): 100.
CATEGORY_WEIGHT: dict[BrokerCategory, int] = {
    BrokerCategory.PEOPLE_SEARCH: 100,
    BrokerCategory.BACKGROUND_CHECK: 100,
    BrokerCategory.PHONE_LOOKUP: 80,
    BrokerCategory.FAMILY_TREE: 60,
    BrokerCategory.RISK_DATA: 60,
    BrokerCategory.DATA_BROKER: 50,
    BrokerCategory.OTHER: 50,
}

#: Score bands (inclusive lower bounds), used for the headline word.
BAND_LOW, BAND_MEDIUM, BAND_HIGH = 1, 25, 60


def weight(cat: BrokerCategory | None) -> int:
    return 100 if cat is None else CATEGORY_WEIGHT.get(cat, 50)


def _w(points: int, pct: int) -> int:
    return (points * pct + 50) // 100           # round half up, integers only


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


@dataclass(frozen=True)
class SitePoints:
    """One site's share of the score, split the way the explanation lines are."""
    entry: ExposureEntry
    confirmed: bool
    base: int          # 15 (confirmed) or 5 (possible), weighted
    extra: int         # extra confirmed listings, weighted
    extra_n: int
    contact: int       # phone/street address shown, weighted
    relatives: int     # relatives named (count, on confirmed listings)

    @property
    def total(self) -> int:
        return self.base + self.extra + self.contact


def _count(value: object) -> int:
    """Ignore missing or invalid counts from older data and injected fetchers."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def site_points(e: ExposureEntry, weighted: bool = True) -> SitePoints | None:
    """None when the site adds nothing (not found, or nothing known)."""
    pct = weight(e.category) if weighted else 100
    if e.match_level == MatchLevel.CONFIRMED:
        conf = [li for li in (e.listings or []) if li.match_level == MatchLevel.CONFIRMED]
        n_extra = max(0, min(MAX_EXTRA_PER_SITE, len(conf) - 1))
        contact = any(li.contact_shown for li in conf)
        return SitePoints(entry=e, confirmed=True, base=_w(W_CONFIRMED_SITE, pct),
                          extra=_w(W_EXTRA_LISTING * n_extra, pct), extra_n=n_extra,
                          contact=_w(W_CONTACT, pct) if contact else 0,
                          relatives=sum(_count(li.relatives_shown) for li in conf))
    if e.match_level == MatchLevel.POSSIBLE:
        return SitePoints(entry=e, confirmed=False, base=_w(W_POSSIBLE_SITE, pct), extra=0,
                          extra_n=0, contact=0, relatives=0)
    return None


def _each(points: int, sites: list[SitePoints]) -> str:
    if all(weight(s.entry.category) == 100 for s in sites):
        return f"{points} points each"
    return f"up to {points} points each, fewer for sites that are not people-search sites"


def score_entries(entries: list[ExposureEntry],
                  weighted: bool = True) -> tuple[int, list[ScoreLine]]:
    """Exposure score 0-100 plus the lines that explain it. The points on the lines add up
    to the score (a negative "stops at 100" line when capped)."""
    sites = [sp for e in entries if (sp := site_points(e, weighted)) is not None]
    confirmed = [s for s in sites if s.confirmed]
    possible = [s for s in sites if not s.confirmed]
    lines: list[ScoreLine] = []
    if confirmed:
        lines.append(ScoreLine(points=sum(s.base for s in confirmed), text=(
            f"{_plural(len(confirmed), 'site shows', 'sites show')} a listing that is you "
            f"({_each(W_CONFIRMED_SITE, confirmed)})")))
        with_extra = [s for s in confirmed if s.extra_n]
        extra = sum(s.extra_n for s in with_extra)
        if extra:
            lines.append(ScoreLine(points=sum(s.extra for s in with_extra), text=(
                f"{_plural(extra, 'extra listing', 'extra listings')} of you on the same "
                f"sites ({_each(W_EXTRA_LISTING, with_extra)}, up to {MAX_EXTRA_PER_SITE} "
                "per site)")))
        contact = [s for s in confirmed if s.contact]
        if contact:
            lines.append(ScoreLine(points=sum(s.contact for s in contact), text=(
                f"{_plural(len(contact), 'of them shows', 'of them show')} your phone "
                f"number or street address ({_each(W_CONTACT, contact)})")))
        rel = sum(s.relatives for s in confirmed)
        if rel:
            lines.append(ScoreLine(points=min(MAX_RELATIVE_POINTS, W_RELATIVE * rel), text=(
                f"{_plural(rel, 'relative or associate is', 'relatives or associates are')} "
                f"named next to you ({W_RELATIVE} points each, up to {MAX_RELATIVE_POINTS})")))
    if possible:
        lines.append(ScoreLine(points=sum(s.base for s in possible), text=(
            f"{_plural(len(possible), 'site may show', 'sites may show')} you; please look "
            f"and tell us ({_each(W_POSSIBLE_SITE, possible)})")))
    raw = sum(ln.points for ln in lines)
    if raw > 100:
        lines.append(ScoreLine(points=100 - raw, text="The score stops at 100"))
    hand = sum(1 for e in entries if e.status == "check_by_hand" and e.match_level is None)
    if hand:
        lines.append(ScoreLine(points=0, text=(
            f"{_plural(hand, 'site', 'sites')} could not be checked automatically; open "
            f"{'it' if hand == 1 else 'them'} yourself (not counted)")))
    if not lines:
        lines.append(ScoreLine(points=0, text="No listings of you were found on the sites "
                                              "we could check"))
    return max(0, min(100, raw)), lines


def _site_text(s: SitePoints) -> str:
    name = s.entry.broker_name
    if not s.confirmed:
        return f"{name} may show you; please look and tell us if it is you"
    n = 1 + s.extra_n
    out = f"{name} shows {'a listing' if n == 1 else f'{n} listings'} of you"
    if s.contact:
        out += " with your phone number or street address"
    return out


def drivers(entries: list[ExposureEntry], weighted: bool = True) -> list[ScoreDriver]:
    """The top 3 things adding to the score, biggest first. Ties: confirmed before
    possible, then site name, so the order never changes between runs."""
    sites = [sp for e in entries if (sp := site_points(e, weighted)) is not None]
    cands: list[tuple[int, int, str, ScoreDriver]] = [
        (-s.total, 0 if s.confirmed else 1, s.entry.broker_name.lower(),
         ScoreDriver(points=s.total, text=_site_text(s), broker_id=s.entry.broker_id))
        for s in sites if s.total > 0]
    rel = sum(s.relatives for s in sites if s.confirmed)
    if rel:
        pts = min(MAX_RELATIVE_POINTS, W_RELATIVE * rel)
        cands.append((-pts, 2, "", ScoreDriver(points=pts, text=(
            f"{_plural(rel, 'relative or associate is', 'relatives or associates are')} "
            "named next to you on those listings"))))
    cands.sort(key=lambda c: c[:3])
    return [c[3] for c in cands[:MAX_DRIVERS]]


def band(score: int, cov: Coverage) -> ScoreBand:
    if score == 0 and cov.sites_checked == 0 and cov.found == 0 and cov.uncertain == 0:
        return "not_checked"
    if score < BAND_LOW:
        return "none_found"
    if score < BAND_MEDIUM:
        return "low"
    if score < BAND_HIGH:
        return "medium"
    return "high"


def headline(score: int, cov: Coverage) -> str:
    """One line to show with the number. Always scoped to the sites we could check; never
    says "safe", "clean" or "protected"."""
    b = band(score, cov)
    if cov.sites_total == 0:
        return "No sites could be searched for you yet, so there is no score yet."
    if b == "not_checked":
        return ("We could not check any sites automatically, so this score tells you "
                "nothing yet. Please check the sites listed below by hand.")
    where = (f"on the {_plural(cov.sites_checked, 'site', 'sites')} we could check"
             if cov.sites_checked else "on the sites we could check")
    if b == "none_found":
        out = f"We found no listings of you {where}."
    else:
        out = f"Your exposure is {b} {where}."
    if cov.check_by_hand:
        out += (f" {_plural(cov.check_by_hand, 'site was', 'sites were')} not checked, so "
                "there may be more.")
    return out
