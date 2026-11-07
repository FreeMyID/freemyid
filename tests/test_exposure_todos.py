"""Exposure review to-dos, using only fake pages and dev brokers."""
from __future__ import annotations

import pytest

from freemyid.config import Config
from freemyid.engine import exposure as ex
from freemyid.engine._dev import fixture_registry
from freemyid.models import Consent, ConsentBasis, MatchLevel, TodoKind
from tests.conftest import make_profile

POSSIBLE = """<div class="result"><a class="view" href="/person/fake">View</a>
<span class="name">Jane Q Testperson</span>
<span class="loc">Springfield, IL</span></div>"""


@pytest.mark.parametrize("practice", [True, False])
def test_possible_review_is_immediate_and_deduplicated(store, practice: bool) -> None:
    profile = make_profile()
    store.save_profile(profile)
    cfg = Config(real_submissions_enabled=not practice, max_delay_s=0)
    for refresh in (False, False, True):
        result = ex.scan_exposure(
            store, profile.id, registry=fixture_registry(), cfg=cfg,
            broker_ids=["devauto"], use_browser=False, refresh=refresh,
            fetch=lambda broker, url: ex.Fetched(url, 200, POSSIBLE),
        )
        assert result.practice_mode is practice
        assert result.entries[0].match_level == MatchLevel.POSSIBLE
        todos = store.list_todos(profile.id)
        assert len(todos) == 1
        listing = store.list_listings(profile.id, "devauto")[0]
        assert todos[0].kind == TodoKind.REVIEW_MATCH
        assert todos[0].resume_token == f"review:{listing.id}"
        assert todos[0].links == [listing.url]


@pytest.mark.parametrize("hand", [False, True])
def test_confirmed_and_hand_checks_create_no_review(store, hand: bool) -> None:
    profile = make_profile()
    store.save_profile(profile)
    registry = fixture_registry()
    if hand:
        registry = registry.model_copy(update={"brokers": [
            b.model_copy(update={"search_access": "bot_blocked"}) for b in registry.brokers
        ]})
    html = POSSIBLE.replace("</div>", '<span class="age">Age 46</span></div>')
    result = ex.scan_exposure(
        store, profile.id, registry=registry, broker_ids=["devauto"], use_browser=False,
        fetch=lambda broker, url: ex.Fetched(url, 200, html),
    )
    assert result.entries[0].status == ("check_by_hand" if hand else "found")
    if not hand:
        assert result.entries[0].match_level == MatchLevel.CONFIRMED
    assert store.list_todos(profile.id) == []


def test_no_consent_creates_no_review_or_listing(store) -> None:
    profile = make_profile(consent=Consent(
        basis=ConsentBasis.SELF, attested_by="Pat Testperson", text_version="0"))
    store.save_profile(profile)

    def fetch(broker, url):
        pytest.fail("A person without valid permission must not be fetched")

    with pytest.raises(ex.ExposureRefused):
        ex.scan_exposure(store, profile.id, registry=fixture_registry(), fetch=fetch,
                         use_browser=False)
    assert store.list_todos(profile.id) == []
    assert store.list_listings(profile.id) == []


@pytest.mark.parametrize("accepted", [True, False])
def test_previous_review_answer_does_not_create_another_review(store, accepted: bool) -> None:
    profile = make_profile()
    store.save_profile(profile)
    kwargs = {
        "registry": fixture_registry(), "broker_ids": ["devauto"],
        "use_browser": False, "refresh": True,
        "fetch": lambda broker, url: ex.Fetched(url, 200, POSSIBLE),
    }
    ex.scan_exposure(store, profile.id, **kwargs)
    listing = store.list_listings(profile.id, "devauto")[0]
    store.save_listing(listing.model_copy(update={
        "match_level": MatchLevel.CONFIRMED if accepted else MatchLevel.NO_MATCH,
        "match_reasons": ["user_confirmed" if accepted else "user_rejected"],
    }))
    original = store.list_todos(profile.id)[0]
    store.complete_todo(original.id)
    ex.scan_exposure(store, profile.id, **kwargs)
    assert store.list_todos(profile.id) == []
    assert [t.id for t in store.list_todos(profile.id, open_only=False)] == [original.id]
    saved = store.list_listings(profile.id, "devauto")[0]
    assert saved.match_level == (MatchLevel.CONFIRMED if accepted else MatchLevel.NO_MATCH)
