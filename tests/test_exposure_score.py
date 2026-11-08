"""Exposure score v2 (ROADMAP 3.2): category weights, top-3 drivers, band + headline,
coverage always shown, never "safe", stored per scan, exposure/1 JSON shape."""
from __future__ import annotations

import json
import re
from datetime import timedelta

import pytest

from freemyid.engine import exposure as ex
from freemyid.engine import exposure_score as xs
from freemyid.engine._dev import fixture_registry, fixture_server
from freemyid.exposure_models import (
    SCORE_VERSION,
    Coverage,
    ExposureEntry,
    ExposureListing,
    ExposureResult,
    coverage_note,
)
from freemyid.models import Actor, BrokerCategory, Event, MatchLevel, utcnow
from tests.conftest import make_profile

C, P = MatchLevel.CONFIRMED, MatchLevel.POSSIBLE


def _e(level=C, n=1, contact=False, rel=0, cat=BrokerCategory.PEOPLE_SEARCH, bid="x",
       name=None, status="found"):
    lis = [ExposureListing(url=f"https://{bid}.example/p/{i}", match_level=level,
                           contact_shown=contact, relatives_shown=rel) for i in range(n)]
    return ExposureEntry(broker_id=bid, broker_name=name or bid.upper(), status=status,
                         category=cat, match_level=level, listings=lis)


def _saved(store):
    p = make_profile()
    store.save_profile(p)
    return p


# ------------------------------------------------------------------ scoring table

@pytest.mark.parametrize(("entry", "points"), [
    (_e(), 15),
    (_e(n=2), 20),
    (_e(n=5), 25),                                   # extras capped at 2 per site
    (_e(contact=True), 20),
    (_e(n=3, contact=True), 30),
    (_e(P), 5),
    (_e(cat=BrokerCategory.BACKGROUND_CHECK), 15),
    (_e(cat=BrokerCategory.PHONE_LOOKUP), 12),
    (_e(cat=BrokerCategory.FAMILY_TREE), 9),
    (_e(cat=BrokerCategory.RISK_DATA), 9),
    (_e(cat=BrokerCategory.DATA_BROKER), 8),         # 7.5 rounds half up
    (_e(cat=BrokerCategory.DATA_BROKER, contact=True), 8 + 3),
    (_e(cat=BrokerCategory.OTHER), 8),
    (_e(P, cat=BrokerCategory.DATA_BROKER), 3),
    (_e(cat=None), 15),                              # older scans: no category, full weight
    (_e(status="not_found", level=None, n=0), 0),
    (_e(status="check_by_hand", level=None, n=0), 0),
])
def test_scoring_table(entry, points):
    score, lines = xs.score_entries([entry])
    assert score == points
    assert sum(ln.points for ln in lines) == score
    assert xs.score_entries([entry], weighted=False)[0] == xs.score_entries(
        [entry.model_copy(update={"category": None})])[0]


def test_relatives_unweighted_and_capped():
    assert xs.score_entries([_e(rel=2)])[0] == 15 + 4
    assert xs.score_entries([_e(rel=2, cat=BrokerCategory.DATA_BROKER)])[0] == 8 + 4
    assert xs.score_entries([_e(rel=50)])[0] == 15 + 10
    assert xs.score_entries([_e(P, rel=5)])[0] == 5       # only confirmed listings count


def test_cap_and_explanation_wording():
    big, lines = xs.score_entries([_e(n=3, contact=True, bid=f"s{i}") for i in range(5)])
    assert big == 100 and lines[-1].text == "The score stops at 100"
    assert sum(ln.points for ln in lines) == 100
    _, lines = xs.score_entries([_e(), _e(cat=BrokerCategory.DATA_BROKER, bid="y")])
    assert "fewer for sites that are not people-search sites" in lines[0].text
    _, lines = xs.score_entries([_e()])
    assert lines[0].text.endswith("(15 points each)")
    assert xs.score_entries([])[1][0].text == ("No listings of you were found on the sites "
                                               "we could check")


def test_score_is_deterministic_and_order_free():
    es = [_e(bid="a", n=2), _e(P, bid="b"), _e(bid="c", cat=BrokerCategory.DATA_BROKER),
          _e(bid="d", contact=True, rel=3)]
    first = (xs.score_entries(es), xs.drivers(es))
    assert (xs.score_entries(es[::-1])[0], xs.drivers(es[::-1])) == (first[0][0], first[1])


# ------------------------------------------------------------------ drivers

def test_top_three_drivers_plain_words():
    es = [_e(P, bid="small", name="Small"),
          _e(bid="big", n=3, contact=True, name="Big People"),
          _e(bid="mid", n=2, name="Mid Search"),
          _e(bid="mkt", cat=BrokerCategory.DATA_BROKER, name="Mkt Data", rel=5)]
    d = xs.drivers(es)
    assert len(d) == 3
    assert [x.broker_id for x in d] == ["big", "mid", None]
    assert d[0].points == 30 and d[0].text == ("Big People shows 3 listings of you with your "
                                               "phone number or street address")
    assert d[1].text == "Mid Search shows 2 listings of you"
    assert d[2].points == 10 and d[2].text.startswith("5 relatives or associates are named")
    for x in d:                                       # no URLs or values, only names/counts
        assert "http" not in x.text and ".example" not in x.text


def test_driver_ties_break_by_kind_then_name():
    es = [_e(bid="z", name="Zed"), _e(bid="a", name="Alpha"),
          _e(P, bid="p1", name="Aaa", cat=BrokerCategory.PEOPLE_SEARCH)]
    assert [x.broker_id for x in xs.drivers(es)] == ["a", "z", "p1"]
    assert xs.drivers([_e(P, bid="q", name="Q")])[0].text == (
        "Q may show you; please look and tell us if it is you")
    assert xs.drivers([]) == []


# ------------------------------------------------------------------ band + headline

def _cov(**kw):
    base = {"sites_total": 10, "sites_checked": 10, "found": 0, "not_found": 10,
            "check_by_hand": 0, "uncertain": 0}
    base.update(kw)
    return Coverage(**base)


@pytest.mark.parametrize(("score", "band"), [(0, "none_found"), (1, "low"), (24, "low"),
                                             (25, "medium"), (59, "medium"), (60, "high"),
                                             (100, "high")])
def test_bands(score, band):
    assert xs.band(score, _cov()) == band


def test_headline_is_scoped_to_what_was_checked():
    assert xs.headline(0, _cov()) == "We found no listings of you on the 10 sites we could check."
    h = xs.headline(30, _cov(sites_checked=4, check_by_hand=6, not_found=3, found=1))
    assert h == ("Your exposure is medium on the 4 sites we could check. 6 sites were not "
                 "checked, so there may be more.")
    nothing = _cov(sites_checked=0, not_found=0, check_by_hand=10)
    assert xs.band(0, nothing) == "not_checked"
    assert "tells you nothing yet" in xs.headline(0, nothing)
    assert "no score yet" in xs.headline(0, Coverage())


# ------------------------------------------------------------------ never "safe"

_FORBIDDEN = re.compile(r"\b(safe|safety|protected|secure|all clear|clean|no risk|"
                        r"nothing to worry|you're fine|you are fine)\b", re.IGNORECASE)


def _covs():
    for total in (0, 1, 7):
        for checked in range(total + 1):
            for hand in range(total - checked + 1):
                rest = total - checked - hand
                yield Coverage(sites_total=total, sites_checked=checked,
                               not_found=max(0, checked - 1), found=min(1, checked),
                               check_by_hand=hand, uncertain=rest)


@pytest.mark.parametrize("score", [0, 1, 12, 25, 60, 100])
def test_never_says_safe(score):
    for cov in _covs():
        assert not _FORBIDDEN.search(xs.headline(score, cov)), (score, cov)
        # the coverage note may only say it in the negative
        note = coverage_note(cov).replace("does not mean you are safe", "")
        assert not _FORBIDDEN.search(note), cov
    es = [_e(), _e(P, bid="b"), _e(bid="c", rel=3, contact=True),
          _e(status="check_by_hand", level=None, n=0, bid="h")]
    texts = [ln.text for ln in xs.score_entries(es)[1]] + [d.text for d in xs.drivers(es)]
    texts += [ln.text for ln in xs.score_entries([])[1]]
    for t in texts:
        assert not _FORBIDDEN.search(t), t


def test_zero_score_always_comes_with_coverage(store):
    p = _saved(store)
    with fixture_server():
        ex.scan_exposure(store, p.id, registry=fixture_registry(), offline=True)
    s = ex.exposure_summary(store, p.id, fixture_registry())
    assert s is not None and s.score == 0 and s.band == "not_checked"
    assert s.coverage.sites_total == 2 and s.coverage.check_by_hand == 2
    assert "does not mean you are safe" in s.coverage_note
    assert not _FORBIDDEN.search(s.headline)


# ------------------------------------------------------------------ stored per scan

def test_scan_stores_score_version_drivers_and_category(store):
    p = _saved(store)
    assert ex.exposure_summary(store, p.id, fixture_registry()) is None
    with fixture_server():
        res = ex.scan_exposure(store, p.id, registry=fixture_registry(), use_browser=False)
    by = {e.broker_id: e for e in res.entries}
    assert by["devauto"].category == BrokerCategory.PEOPLE_SEARCH
    assert res.score == 17 and res.score_version == SCORE_VERSION == 2
    assert [d.broker_id for d in res.drivers] == ["devauto", None]
    assert [d.points for d in res.drivers] == [15, 2]
    ev = next(e for e in store.events(p.id) if e.action == ex.EVENT_ACTION)
    assert ev.detail["score_version"] == 2 and ev.detail["drivers"]
    blob = json.dumps(ev.detail).lower()
    for pii in ("testperson", "springfield", "jane", "http"):
        assert pii not in blob
    assert ex.latest_exposure(store, p, fixture_registry()) == res
    s = ex.exposure_summary(store, p, fixture_registry())
    assert s is not None and s == ex.summarize(res)
    assert s.score == 17 and s.band == "low" and re.search(r"sites? we could check", s.headline)
    assert ex.exposure_trend(store, p.id).points[-1].score_version == 2


def test_older_v1_scan_still_reads_and_trend_flags_formula_change(store):
    p = _saved(store)
    old = utcnow() - timedelta(days=3)
    store.log(Event(ts=old, profile_id=p.id, actor=Actor.ENGINE, action=ex.EVENT_ACTION,
                    detail={"version": 1, "score": 20, "offline": False,
                            "practice_mode": True, "explanation": [[20, "x"]],
                            "entries": [{"broker_id": "devauto", "status": "found",
                                         "reason": None, "match_level": "confirmed",
                                         "signals": [], "from_store": False,
                                         "checked_at": old.isoformat(), "listings": []}]}))
    r = ex.latest_exposure(store, p, fixture_registry())
    assert r is not None and r.score_version == 1 and r.score == 20
    assert r.entries[0].category is None
    with fixture_server():
        ex.scan_exposure(store, p.id, registry=fixture_registry(), use_browser=False)
    t = ex.exposure_trend(store, p.id)
    assert [pt.score_version for pt in t.points] == [1, 2]
    assert "way the score is worked out changed" in t.note


def test_summary_of_result_is_pure():
    r = ExposureResult(profile_id="a" * 32, score=0, entries=[])
    s = ex.summarize(r)
    assert s.band == "not_checked" and s.drivers == [] and "no score yet" in s.headline


# ------------------------------------------------------------------ CLI / JSON shape

def test_cli_exposure_json_score_fields(store, monkeypatch):
    from typer.testing import CliRunner

    from freemyid import cli
    p = _saved(store)
    monkeypatch.setattr(cli, "_registry", fixture_registry)
    runner = CliRunner()
    with fixture_server():
        r = runner.invoke(cli.app, ["exposure", "--json", "--profile", p.id])
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)                         # exactly one JSON object
    assert doc["schema"] == "exposure/1"
    prof = doc["profiles"][0]
    assert {"score", "score_version", "band", "headline", "drivers", "coverage",
            "coverage_note", "explanation", "trend"} <= set(prof)
    assert isinstance(prof["score"], int) and 0 <= prof["score"] <= 100
    assert prof["band"] in {"not_checked", "none_found", "low", "medium", "high"}
    assert prof["score_version"] == 2
    assert len(prof["drivers"]) <= 3
    for d in prof["drivers"]:
        assert set(d) == {"points", "text", "broker_id"}
        assert isinstance(d["points"], int) and isinstance(d["text"], str)
    assert re.search(r"sites? we could check", prof["headline"])
    assert not _FORBIDDEN.search(prof["headline"])
    r = runner.invoke(cli.app, ["exposure", "--offline", "--profile", p.id])
    text = " ".join(r.stdout.split())
    assert r.exit_code == 0 and "does not mean you are safe" in text
    assert "What adds most to your score" in text
