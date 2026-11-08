"""BL-IN-02: exposure score trend (one point per day, offline scans skipped, plain-English
note that never says "safe"). Synthetic PII-free scan events only."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from freemyid.engine import exposure as ex
from freemyid.models import Actor, Event

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
P1, P2 = "a" * 32, "b" * 32


def _entry(status, level=None, from_store=False):
    return {"broker_id": "devauto", "status": status, "match_level": level,
            "from_store": from_store}


def _scan(store, pid, ts, score, entries, offline=False):
    store.log(Event(ts=ts, profile_id=pid, actor=Actor.ENGINE, action=ex.EVENT_ACTION,
                    detail={"score": score, "offline": offline, "entries": entries}))


FULL = [_entry("found", "confirmed"), _entry("not_found"), _entry("check_by_hand")]
LESS = [_entry("found", "confirmed"), _entry("check_by_hand"), _entry("check_by_hand")]


def test_no_scans():
    assert ex.trend_note([]) == "No scans yet."


def test_first_scan_note(store):
    _scan(store, P1, T0, 40, FULL)
    t = ex.exposure_trend(store, P1)
    assert len(t.points) == 1 and t.change is None and t.since is None
    assert "first scan" in t.note


def test_change_since_previous_day(store):
    _scan(store, P1, T0, 40, FULL)
    _scan(store, P1, T0 + timedelta(days=30), 28, FULL)
    t = ex.exposure_trend(store, P1)
    assert [p.score for p in t.points] == [40, 28]
    assert t.change == -12 and t.since == T0.date()
    assert t.note == "Your score went down 12 points since 2026-10-01."
    p = t.points[-1]
    assert (p.sites_total, p.sites_checked, p.found) == (3, 2, 1)


def test_one_point_per_day_last_scan_wins(store):
    _scan(store, P1, T0, 40, FULL)
    _scan(store, P1, T0 + timedelta(hours=3), 35, FULL)
    _scan(store, P1, T0 + timedelta(days=1), 35, FULL)
    t = ex.exposure_trend(store, P1)
    assert [p.score for p in t.points] == [35, 35]
    assert t.note == "Your score is the same as on 2026-10-01."


def test_offline_scans_are_skipped(store):
    _scan(store, P1, T0, 40, FULL)
    _scan(store, P1, T0 + timedelta(days=2), 10, FULL, offline=True)
    assert [p.score for p in ex.exposure_trend(store, P1).points] == [40]


def test_fewer_sites_checked_is_flagged(store):
    _scan(store, P1, T0, 40, FULL)
    _scan(store, P1, T0 + timedelta(days=7), 41, LESS)
    t = ex.exposure_trend(store, P1)
    assert t.change == 1
    assert t.note.startswith("Your score went up 1 point since")
    assert "may not be real" in t.note
    assert "safe" not in t.note.lower()


def test_trend_is_per_person_and_limited(store):
    for i in range(5):
        _scan(store, P1, T0 + timedelta(days=i), 50 - i, FULL)
    _scan(store, P2, T0, 99, FULL)
    t = ex.exposure_trend(store, P1, limit=3)
    assert [p.score for p in t.points] == [48, 47, 46]
