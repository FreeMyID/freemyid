"""Exposure-score uncertainty and malformed-count regressions (WO-272).

The existing score measures exposure: adding a confirmed listing cannot LOWER it.
Owner ruling 2026-11-12: WO-272 AC3 ("a confirmed listing never raises the score") had the
direction backwards; the documented direction (docs/EXPOSURE.md) and existing tests win.
"""
from __future__ import annotations

from itertools import product

import pytest

from freemyid.engine import exposure_score as xs
from freemyid.exposure_models import (
    ExposureEntry,
    ExposureListing,
    coverage_note,
    coverage_of,
)
from freemyid.models import BrokerCategory, MatchLevel


def _entry(
    level: MatchLevel | None = MatchLevel.CONFIRMED,
    *,
    status: str = "found",
    category: BrokerCategory | None = None,
    relatives: int = 0,
) -> ExposureEntry:
    listings = [] if level is None else [ExposureListing(
        url="https://synthetic-site.example/listing/fake-marker",
        match_level=level,
        relatives_shown=relatives,
    )]
    return ExposureEntry(
        broker_id="synthetic-site", broker_name="Synthetic Site", status=status,
        category=category, match_level=level, listings=listings,
    )


@pytest.mark.parametrize("size", [0, 1, 7])
def test_unchecked_score_uses_existing_unavailable_band(size: int) -> None:
    entries = [_entry(None, status="check_by_hand") for _ in range(size)]
    score, lines = xs.score_entries(entries)
    cov = coverage_of(entries)
    assert score == 0 and sum(line.points for line in lines) == score
    assert xs.band(score, cov) == "not_checked"
    if size:
        assert "tells you nothing yet" in xs.headline(score, cov)
        assert "checking by hand" in coverage_note(cov)
    else:
        assert "no score yet" in xs.headline(score, cov)
        assert "No sites" in coverage_note(cov)


@pytest.mark.parametrize("manual", [0, 3])
def test_only_possible_results_say_so_and_never_claim_no_listings(manual: int) -> None:
    """AC2: every result uncertain (or checked by hand) -> the text says so. The coverage
    note and the score lines carry it; the headline stays as docs/CLI.md documents it."""
    entries = ([_entry(MatchLevel.POSSIBLE)]
               + [_entry(None, status="check_by_hand") for _ in range(manual)])
    score, lines = xs.score_entries(entries)
    cov = coverage_of(entries)
    headline = xs.headline(score, cov)
    assert cov.uncertain == 1 and cov.found == cov.not_found == 0
    assert score == xs.W_POSSIBLE_SITE == sum(line.points for line in lines)
    assert xs.band(score, cov) == "low"
    assert headline.startswith("Your exposure is low on the 1 site we could check.")
    assert "no listings" not in headline.lower()
    assert all("no listings" not in line.text.lower() for line in lines)
    assert any("may show you" in line.text for line in lines)
    assert "may show you" in coverage_note(cov)
    if manual:
        assert "3 sites were not checked" in headline
        assert "3 sites need checking by hand" in coverage_note(cov)


@pytest.mark.parametrize("category", [None, *BrokerCategory])
def test_confirmed_exposure_is_monotonic_in_existing_direction(
    category: BrokerCategory | None,
) -> None:
    for confirmed, possible in product(range(9), range(3)):
        entries = ([_entry(category=category) for _ in range(confirmed)]
                   + [_entry(MatchLevel.POSSIBLE, category=category) for _ in range(possible)])
        before = xs.score_entries(entries)[0]
        after = xs.score_entries([*entries, _entry(category=category)])[0]
        assert 0 <= before <= after <= 100
        assert xs.score_entries(entries[::-1])[0] == before


@pytest.mark.parametrize("bad_count", [None, -1, -1000000, False, True, "bad"])
def test_invalid_relative_counts_do_not_crash_or_subtract_exposure(bad_count: object) -> None:
    entry = _entry()
    listing = entry.listings[0].model_copy(update={"relatives_shown": bad_count})
    entry = entry.model_copy(update={"listings": [listing]})
    score, lines = xs.score_entries([entry])
    assert score == 15
    assert sum(line.points for line in lines) == score
    assert all(line.points >= 0 for line in lines)
    assert [driver.points for driver in xs.drivers([entry])] == [15]


def test_negative_count_cannot_cancel_another_listings_relatives() -> None:
    entry = _entry(relatives=3)
    bad = entry.listings[0].model_copy(update={"relatives_shown": -50})
    entry = entry.model_copy(update={"listings": [*entry.listings, bad]})
    score, lines = xs.score_entries([entry])
    assert score == 15 + 5 + 6
    assert sum(line.points for line in lines) == score
    assert any(driver.points == 6 for driver in xs.drivers([entry]))


def test_none_listing_collection_from_fake_keeps_confirmed_site_evidence() -> None:
    entry = _entry().model_copy(update={"listings": None})
    score, lines = xs.score_entries([entry])
    assert score == 15 and sum(line.points for line in lines) == score
    assert xs.drivers([entry])[0].points == 15


@pytest.mark.parametrize("relatives", [0, 1, 10, 10**30])
def test_large_relative_counts_stay_bounded_and_explanations_add_up(relatives: int) -> None:
    entries = [_entry(relatives=relatives) for _ in range(12)]
    score, lines = xs.score_entries(entries)
    assert score == 100
    assert sum(line.points for line in lines) == score
    assert all(0 < driver.points <= 100 for driver in xs.drivers(entries))
