"""Exposure v0.3: coverage counts + note, old-address searches, California DROP first."""
from __future__ import annotations

import pytest

from freemyid import checklist_state as cs
from freemyid.engine import exposure as ex
from freemyid.engine._dev import fixture_registry, fixture_server
from freemyid.exposure_models import (
    DROP_CHECKLIST_ID,
    Coverage,
    ExposureEntry,
    coverage_note,
    coverage_of,
)
from freemyid.models import Address, MatchLevel
from tests.conftest import make_profile


def _reg(**access):
    reg = fixture_registry()
    brokers = [b.model_copy(update={"search_access": access[b.id]}) if b.id in access else b
               for b in reg.brokers]
    return reg.model_copy(update={"brokers": brokers})


def _saved(store, **over):
    p = make_profile(**over)
    store.save_profile(p)
    return p


def _page(path: str, loc: str) -> str:
    return (f'<div class="result"><a class="view" href="{path}">View</a>'
            f'<span class="name">Jane Q Testperson</span><span class="age">Age 46</span>'
            f'<span class="loc">{loc}</span></div>')


class Calls:
    def __init__(self, page):
        self.urls: list[str] = []
        self.page = page

    def __call__(self, broker, url):
        self.urls.append(url)
        return self.page(broker, url)


SPRINGFIELD = Address(city="Springfield", state="IL", current=True)
SHELBYVILLE = Address(city="Shelbyville", state="IN", to_year=2015)
OGDENVILLE = Address(city="Ogdenville", state="OH", to_year=2001)


def _e(status, level=None, from_store=False, bid="b"):
    return ExposureEntry(broker_id=bid, broker_name=bid, status=status, match_level=level,
                         from_store=from_store)


# ------------------------------------------------------------------ coverage


def test_coverage_counts_partition_the_sites():
    entries = [_e("found", MatchLevel.CONFIRMED), _e("found", MatchLevel.POSSIBLE),
               _e("not_found"), _e("check_by_hand"), _e("check_by_hand"),
               _e("found", MatchLevel.CONFIRMED, from_store=True)]
    cov = coverage_of(entries)
    assert cov == Coverage(sites_total=6, sites_checked=3, found=2, not_found=1,
                           check_by_hand=2, uncertain=1)
    assert cov.found + cov.uncertain + cov.not_found + cov.check_by_hand == cov.sites_total


@pytest.mark.parametrize("level", [None, MatchLevel.NO_MATCH])
def test_found_page_with_nothing_matching_you_is_not_uncertain(level):
    # A page that was read but whose listings are all no_match (or gone) shows nothing that
    # matches: it counts as not found, never as "may show you" (no Is-this-you todo exists).
    entries = [_e("found", level), _e("found", MatchLevel.POSSIBLE, bid="p")]
    cov = coverage_of(entries)
    assert cov.uncertain == 1
    assert cov.not_found == 1
    assert cov.found + cov.uncertain + cov.not_found + cov.check_by_hand == cov.sites_total
    assert "1 site may show you" in coverage_note(cov)


@pytest.mark.parametrize("cov, parts", [
    (Coverage(), ["No sites could be searched"]),
    (Coverage(sites_total=3, check_by_hand=3),
     ["could not check any of the 3 sites", "does not mean you are safe",
      "3 sites need checking by hand"]),
    (Coverage(sites_total=4, sites_checked=1, not_found=1, check_by_hand=2, uncertain=1),
     ["based on the 1 site we could check, out of 4", "does not mean you are safe",
      "2 sites need checking by hand", "1 site may show you; please tell us if it is you"]),
])
def test_coverage_note_never_says_safe(cov, parts):
    note = coverage_note(cov)
    for part in parts:
        assert part in note
    assert "you are safe" not in note.replace("does not mean you are safe", "")


def test_fixture_scan_reports_coverage(store):
    p = _saved(store)
    with fixture_server():
        res = ex.scan_exposure(store, p.id, registry=fixture_registry(), use_browser=False)
    assert res.coverage == Coverage(sites_total=2, sites_checked=1, found=1, not_found=0,
                                    check_by_hand=1, uncertain=0)
    assert "1 site we could check, out of 2" in res.coverage_note
    stored = ex.latest_exposure(store, p, fixture_registry())
    assert stored is not None and stored.coverage == res.coverage


# ------------------------------------------------------------------ California


def test_drop_first_follows_the_current_address():
    assert cs.drop_first(make_profile(addresses=[{"city": "Fresno", "state": "ca",
                                                  "current": True}]))
    assert not cs.drop_first(make_profile())
    # moved away from California: the old address does not count
    assert not cs.drop_first(make_profile(addresses=[
        {"city": "Fresno", "state": "CA"}, {"city": "Springfield", "state": "IL",
                                             "current": True}]))
    # nothing marked current: the first address decides (Profile.state_of_residence)
    assert cs.drop_first(make_profile(addresses=[{"city": "Fresno", "state": "CA"}]))


def test_exposure_result_points_californians_to_drop(store):
    ca = _saved(store, addresses=[{"city": "Fresno", "state": "CA", "current": True}])
    il = _saved(store)
    for p, want in ((ca, True), (il, False)):
        res = ex.scan_exposure(store, p.id, registry=fixture_registry(), offline=True)
        assert res.drop_first is want
        assert res.first_checklist == (DROP_CHECKLIST_ID if want else None)
        assert ex.latest_exposure(store, p, fixture_registry()).drop_first is want


def test_checklist_list_puts_drop_first_for_californians():
    cf = cs.load_checklists()
    assert cf is not None and DROP_CHECKLIST_ID in {c.id for c in cf.checklists}
    ca = make_profile(addresses=[{"city": "Fresno", "state": "CA", "current": True}])
    first = cs.first_checklist(ca, cf)
    assert first == DROP_CHECKLIST_ID
    doc = cs.list_doc(cf, {}, ca.id, first)
    assert doc["start_with"] == DROP_CHECKLIST_ID
    assert doc["checklists"][0]["id"] == DROP_CHECKLIST_ID
    assert sorted(i["id"] for i in doc["checklists"]) == sorted(c.id for c in cf.checklists)
    # everyone else: file order, no start_with
    assert cs.first_checklist(make_profile(), cf) is None
    plain = cs.list_doc(cf, {}, "x")
    assert plain["start_with"] is None
    assert [i["id"] for i in plain["checklists"]] == [c.id for c in cf.checklists]
    # a checklist file without ca_drop never points at it
    other = cf.model_copy(update={"checklists": [c for c in cf.checklists
                                                 if c.id != DROP_CHECKLIST_ID]})
    assert cs.first_checklist(ca, other) is None


# ------------------------------------------------------------------ old addresses


def _two_pages(broker, url):
    if broker.id != "devauto":
        return ex.Fetched(url, 200, "<p>No records found</p>")
    if url.endswith("/in"):
        return ex.Fetched(url, 200, _page("/p/old", "Shelbyville, IN"))
    return ex.Fetched(url, 200, _page("/p/now", "Springfield, IL"))


def test_old_addresses_are_off_by_default(store):
    p = _saved(store, addresses=[SPRINGFIELD, SHELBYVILLE])
    calls = Calls(_two_pages)
    res = ex.scan_exposure(store, p.id, registry=_reg(devblocked="bot_blocked"),
                           fetch=calls, use_browser=False)
    assert calls.urls == ["https://devauto.example/name/jane-testperson/il"]
    assert not res.entries[0].old_address_checked


def test_old_address_adds_one_search_and_merges_once(store):
    p = _saved(store, addresses=[SPRINGFIELD, OGDENVILLE, SHELBYVILLE])
    calls = Calls(_two_pages)
    slept: list[float] = []
    res = ex.scan_exposure(store, p.id, registry=_reg(devblocked="open"), fetch=calls,
                           use_browser=False, old_addresses=True, sleep=slept.append)
    # devauto: current + the most recent previous address (IN, not the older OH);
    # devblocked: current + one old-address search too, nothing more
    assert calls.urls == ["https://devauto.example/name/jane-testperson/il",
                          "https://devauto.example/name/jane-testperson/in",
                          "https://devblocked.example/name/jane-testperson/il",
                          "https://devblocked.example/name/jane-testperson/in"]
    assert len(slept) == 3                    # a polite gap before every request but the first
    auto = res.entries[0]
    assert auto.old_address_checked and auto.status == "found"
    assert sorted(li.url for li in auto.listings) == [
        "https://devauto.example/p/now", "https://devauto.example/p/old"]
    # one merge: neither page's listing is marked gone by the other
    assert all(li.gone_since is None for li in store.list_listings(p.id, "devauto"))
    stored = ex.latest_exposure(store, p, fixture_registry())
    assert stored is not None and stored.entries[0].old_address_checked


def test_old_address_skipped_when_main_search_fails_or_url_is_the_same(store):
    def challenge(broker, url):
        return ex.Fetched(url, 403, "<iframe src='https://challenges.cloudflare.com'>")

    p = _saved(store, addresses=[SPRINGFIELD, SHELBYVILLE])
    calls = Calls(challenge)
    res = ex.scan_exposure(store, p.id, registry=_reg(devblocked="bot_blocked"),
                           fetch=calls, use_browser=False, old_addresses=True)
    assert len(calls.urls) == 1 and res.entries[0].reason == "challenge"

    # same state as now: the {state}-only URL would be identical, so no extra request
    q = _saved(store, addresses=[SPRINGFIELD, Address(city="Capital City", state="IL")])
    calls = Calls(_two_pages)
    ex.scan_exposure(store, q.id, registry=_reg(devblocked="bot_blocked"), fetch=calls,
                     use_browser=False, old_addresses=True)
    assert len(calls.urls) == 1


def test_failed_old_address_search_keeps_the_main_answer(store):
    def flaky(broker, url):
        if url.endswith("/in"):
            raise RuntimeError("boom")
        return _two_pages(broker, url)

    p = _saved(store, addresses=[SPRINGFIELD, SHELBYVILLE])
    res = ex.scan_exposure(store, p.id, registry=_reg(devblocked="bot_blocked"),
                           fetch=Calls(flaky), use_browser=False, old_addresses=True)
    auto = res.entries[0]
    assert auto.status == "found" and not auto.old_address_checked
    assert [li.url for li in auto.listings] == ["https://devauto.example/p/now"]


def test_old_address_url_needs_a_city_or_state_pattern():
    reg = fixture_registry()
    auto = next(b for b in reg.brokers if b.id == "devauto")
    p = make_profile(addresses=[SPRINGFIELD, SHELBYVILLE])
    assert ex.old_address_url(auto, p) == "https://devauto.example/name/jane-testperson/in"
    name_only = auto.model_copy(update={
        "search_url_pattern": "https://devauto.example/name/{first}-{last}"})
    assert ex.old_address_url(name_only, p) is None
    assert ex.old_address_url(auto, make_profile()) is None


def test_old_addresses_follow_the_config_flag(store):
    from freemyid import config as cfgmod
    p = _saved(store, addresses=[SPRINGFIELD, SHELBYVILLE])
    cfg = cfgmod.Config(min_delay_s=0, max_delay_s=0, exposure_old_addresses=True)
    calls = Calls(_two_pages)
    ex.scan_exposure(store, p.id, registry=_reg(devblocked="bot_blocked"), fetch=calls,
                     use_browser=False, cfg=cfg)
    assert len(calls.urls) == 2


# ------------------------------------------------------------------ CLI


def test_cli_exposure_json_gains_coverage_and_drop(store, monkeypatch):
    import json

    from typer.testing import CliRunner

    from freemyid import cli
    p = _saved(store, addresses=[{"city": "Fresno", "state": "CA", "current": True}])
    monkeypatch.setattr(cli, "_registry", fixture_registry)
    runner = CliRunner()
    r = runner.invoke(cli.app, ["exposure", "--json", "--offline", "--profile", p.id])
    assert r.exit_code == 0, r.output
    prof = json.loads(r.stdout)["profiles"][0]
    assert prof["coverage"] == {"sites_total": 2, "sites_checked": 0, "found": 0,
                                "not_found": 0, "check_by_hand": 2, "uncertain": 0}
    assert "could not check any of the 2 sites" in prof["coverage_note"]
    assert prof["drop_first"] is True and prof["first_checklist"] == DROP_CHECKLIST_ID
    assert prof["counts"]["check_by_hand"] == 2          # old fields unchanged
    assert all(e["old_address_checked"] is False for e in prof["entries"])
    r = runner.invoke(cli.app, ["exposure", "--offline", "--profile", p.id])
    text = " ".join(r.stdout.split())           # rich wraps long lines
    assert r.exit_code == 0 and "does not mean you are safe" in text
    assert f"freemyid checklist show {DROP_CHECKLIST_ID}" in text


def test_cli_checklist_list_starts_with_drop_in_california(store):
    import json

    from typer.testing import CliRunner

    from freemyid.cli import app
    ca = _saved(store, label="CA", addresses=[{"city": "Fresno", "state": "CA",
                                                "current": True}])
    il = _saved(store, label="IL")
    runner = CliRunner()
    doc = json.loads(runner.invoke(app, ["checklist", "list", "--json", "-p", ca.id]).stdout)
    assert doc["start_with"] == DROP_CHECKLIST_ID
    assert doc["checklists"][0]["id"] == DROP_CHECKLIST_ID
    out = runner.invoke(app, ["checklist", "list", "-p", ca.id]).stdout
    assert out.startswith("You live in California")
    rows = [ln for ln in out.splitlines() if ln.startswith(("[ ]", "[x]"))]
    assert rows[0].startswith(f"[ ] {DROP_CHECKLIST_ID}")
    doc = json.loads(runner.invoke(app, ["checklist", "list", "--json", "-p", il.id]).stdout)
    assert doc["start_with"] is None
    assert "You live in California" not in runner.invoke(
        app, ["checklist", "list", "-p", il.id]).stdout
