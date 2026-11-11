"""WO-602: brokers that were never searched are "not checked", never "found".

A blind broker (no search spec) is still set to FOUND so a request can go out (state
machine unchanged), but the run summary, RunReport counts and `presumed_listed` keep it
apart from a listing that was really seen. Fake people and fake brokers only.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from freemyid.engine import runner as rmod
from freemyid.engine.runner import NO_SEARCH_LINE, PRESUMED_WORDS, Runner, presumed_listed
from freemyid.models import (
    Broker,
    Listing,
    ListingState,
    MatchLevel,
    Registry,
    SearchSpec,
)
from tests.conftest import make_profile

T0 = datetime(2026, 11, 1, tzinfo=UTC)


def _broker(bid: str, *, searchable: bool) -> Broker:
    extra = {}
    if searchable:
        extra = {"search_url_pattern": f"https://{bid}.example/name/{{first}}-{{last}}",
                 "search": SearchSpec(result_selector=".card")}
    return Broker(id=bid, name=f"Fake {bid}", url=f"https://{bid}.example/",
                  category="people_search", domains=[f"{bid}.example"], method="email",
                  opt_out_email=f"privacy@{bid}.example", **extra)


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="2026.11.11-test", updated=T0.date(), brokers=list(brokers))


class Rec:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.calls.append((title, body, url))


def _run(store, reg, profile, monkeypatch, *, seen: dict[str, bool]):
    """scan_only run; brokers in `seen` are "searched" through a fake search that returns one
    CONFIRMED (True) or no (False) listing. Everything else stays blind."""
    monkeypatch.setattr(rmod, "consent_ok", lambda p, s: (True, ""))
    monkeypatch.setattr(rmod.tiers, "can_scan", lambda b, cfg=None: b.id in seen)

    async def fake_browser(self):
        return object()

    async def fake_search(ctx):
        if not seen[ctx.broker.id]:
            return []
        return [Listing(profile_id=ctx.profile.id, broker_id=ctx.broker.id,
                        url=f"https://{ctx.broker.id}.example/p/1",
                        match_score=95, match_level=MatchLevel.CONFIRMED,
                        match_reasons=["name", "city"])]

    monkeypatch.setattr(Runner, "browser", fake_browser)
    monkeypatch.setattr("freemyid.submitters.web_form.search_listings", fake_search)
    store.save_profile(profile)
    r = Runner(store, reg, scan_only=True, dry_run=False, interactive=False, broker_ids=None,
               only_due=False, notifier=Rec(), now=T0)
    return asyncio.run(r.run([profile]))


@pytest.fixture
def jane():
    return make_profile()


def test_blind_registry_never_says_found(store, jane, monkeypatch) -> None:
    reg = _registry(*(_broker(f"blind{i}", searchable=False) for i in range(3)))
    rep = _run(store, reg, jane, monkeypatch, seen={})
    # the state machine is unchanged: FOUND still lets a request go out later
    assert rep.per_profile[jane.id] == {ListingState.FOUND: 3}
    assert rep.presumed[jane.id] == 3
    assert rep.searched.get(jane.id, 0) == 0 and rep.blind[jane.id] == 3
    lines = rep.summary_lines()
    assert not any("found" in ln.lower() for ln in lines), lines
    assert NO_SEARCH_LINE in lines
    assert any(f"{PRESUMED_WORDS}: 3" in ln for ln in lines)
    # no state names in the summary
    assert not any("_" in ln or "needs human" in ln for ln in lines)
    for st in store.list_statuses(jane.id):
        assert presumed_listed(store, st)


def test_mixed_registry_splits_found_from_not_checked(store, jane, monkeypatch) -> None:
    reg = _registry(_broker("seenone", searchable=True), _broker("cleanone", searchable=True),
                    _broker("blindone", searchable=False))
    rep = _run(store, reg, jane, monkeypatch, seen={"seenone": True, "cleanone": False})
    counts = rep.per_profile[jane.id]
    assert counts[ListingState.FOUND] == 2 and counts[ListingState.NOT_FOUND] == 1
    assert rep.presumed[jane.id] == 1
    assert rep.searched[jane.id] == 2 and rep.blind[jane.id] == 1
    lines = rep.summary_lines()
    assert NO_SEARCH_LINE not in lines
    row = next(ln for ln in lines if ln.startswith(f"{jane.label}:"))
    assert "found on the site: 1" in row
    assert f"{PRESUMED_WORDS}: 1" in row
    assert "not on the site when we looked: 1" in row
    st = {s.broker_id: s for s in store.list_statuses(jane.id)}
    assert not presumed_listed(store, st["seenone"])
    assert presumed_listed(store, st["blindone"])
    assert not presumed_listed(store, st["cleanone"])      # NOT_FOUND is never presumed


def test_events_stay_pii_free(store, jane, monkeypatch) -> None:
    reg = _registry(_broker("seenone", searchable=True), _broker("blindone", searchable=False))
    _run(store, reg, jane, monkeypatch, seen={"seenone": True})
    blob = repr([e.detail for e in store.events(jane.id)])
    for pii in ("Jane", "Testperson", "Springfield", "217-555", "example.com/p"):
        assert pii not in blob
    presumed = [e for e in store.events(jane.id) if e.action == "presumed_listed"]
    assert [e.broker_id for e in presumed] == ["blindone"]
    assert presumed[0].detail == {"blind": True}

