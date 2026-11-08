"""SEC-104: stored listings are re-scored with the current matcher before they are escalated
or re-sent, and listings kept only because an extra page was unreadable never become new send
targets. Fake people and brokers only."""
from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import _dev, matcher
from freemyid.engine.runner import keep_unchecked, rescore_stored, run
from freemyid.models import (
    Consent,
    ConsentBasis,
    Listing,
    MatchLevel,
    PersonName,
    TodoKind,
    utcnow,
)
from tests.conftest import make_profile

TODAY = date(2026, 11, 8)
BROKER = "devauto"


def _person(store, **over):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Robert Testperson",
                text_version=CURRENT_TEXT_VERSION)
    kw = {"name": PersonName(first="Robert", last="Testperson"),
          "relatives": ["Kim Testperson"], "phones": [], "emails": []}
    kw.update(over)
    p = make_profile(consent=c, **kw)
    store.save_profile(p)
    return p


def _stale(p, url="https://devauto.example/p/bert", name="Bert Testperson", age=None,
           reasons=("city", "relative"), level=MatchLevel.CONFIRMED):
    """A listing saved by an older matcher: a household member (Bert can be an Albert) with
    the same city and child, CONFIRMED on household signals only."""
    return Listing(profile_id=p.id, broker_id=BROKER, url=url, name_shown=name, age_shown=age,
                   locations_shown=["Springfield, IL"], relatives_shown=["Kim Testperson"],
                   match_score=94.0, match_level=level, match_reasons=list(reasons))


def _broker():
    return next(b for b in _dev.fixture_registry().brokers if b.id == BROKER)


# ------------------------------------------------------------------ matcher.rescore


def test_rescore_lowers_a_stale_household_listing(store):
    p = _person(store)
    new = matcher.rescore(p, _stale(p), TODAY)
    assert new.match_level is MatchLevel.POSSIBLE
    assert new.match_reasons == ["city", "relative"]


def test_rescore_never_raises_a_level(store):
    p = _person(store)
    li = _stale(p, name="Robert Testperson", age=46, level=MatchLevel.POSSIBLE,
                reasons=("city",))
    assert matcher.rescore(p, li, TODAY) is li


def test_rescore_keeps_the_persons_own_answers(store):
    p = _person(store)
    li = _stale(p, reasons=("city", "relative", "user_confirmed"))
    assert matcher.rescore(p, li, TODAY) is li


def test_rescore_carries_phone_and_email_signals(store):
    # a Listing keeps no phone values; the stored exact-match signal still counts
    p = _person(store)
    li = _stale(p, age=46, reasons=("city", "age", "relative", "phone"))
    assert matcher.rescore(p, li, TODAY) is li
    without = _stale(p, age=46, reasons=("city", "age", "relative"))
    assert matcher.rescore(p, without, TODAY).match_level is MatchLevel.POSSIBLE


def test_rescore_keeps_a_listing_still_confirmed(store):
    p = _person(store)
    li = _stale(p, name="Robert Testperson", age=46, reasons=("city", "age", "relative"))
    assert matcher.rescore(p, li, TODAY) is li


# ------------------------------------------------------------------ runner helpers


def test_rescore_stored_saves_and_asks_is_this_you(store):
    p = _person(store)
    store.save_listing(_stale(p))
    gone = _stale(p, url="https://devauto.example/p/old").model_copy(
        update={"gone_since": utcnow()})
    store.save_listing(gone)
    assert rescore_stored(store, p, _broker(), utcnow()) == 1
    by_url = {li.url: li for li in store.list_listings(p.id, BROKER)}
    assert by_url["https://devauto.example/p/bert"].match_level is MatchLevel.POSSIBLE
    assert by_url["https://devauto.example/p/old"].match_level is MatchLevel.CONFIRMED
    todos = [t for t in store.list_todos(p.id) if t.kind == TodoKind.REVIEW_MATCH]
    assert len(todos) == 1 and todos[0].links == ["https://devauto.example/p/bert"]
    assert rescore_stored(store, p, _broker(), utcnow()) == 0       # idempotent


def test_rescore_stored_no_todo_while_a_confirmed_listing_remains(store):
    p = _person(store)
    store.save_listing(_stale(p))
    store.save_listing(_stale(p, url="https://devauto.example/p/me", name="Robert Testperson",
                              age=46, reasons=("city", "age", "relative")))
    assert rescore_stored(store, p, _broker(), utcnow()) == 1
    assert not [t for t in store.list_todos(p.id) if t.kind == TodoKind.REVIEW_MATCH]


def test_keep_unchecked_rescores_kept_listings(store):
    p = _person(store)
    store.save_listing(_stale(p))
    kept = keep_unchecked(store, p, _broker(), [])
    assert [li.match_level for li in kept] == [MatchLevel.POSSIBLE]


def test_web_search_marks_kept_listings_unchecked(store, monkeypatch):
    from freemyid.submitters import web_form
    p = _person(store, previous_names=[PersonName(first="Robert", last="Oldname")])
    store.save_listing(_stale(p, name="Robert Testperson", age=46,
                              reasons=("city", "age", "relative")))

    async def page(bm, ctx, url):
        if "oldname" in url:
            raise web_form.UnexpectedPage("search_http_503")
        return [], b"png"

    monkeypatch.setattr(web_form, "_search_page", page)
    ctx = SimpleNamespace(broker=_broker(), profile=p, store=store, now=None,
                          scratch={"browser": object(),
                                   "search_variants": {"previous_names": True}})
    out = asyncio.run(web_form.search_listings(ctx))
    assert [li.url for li in out] == ["https://devauto.example/p/bert"]
    assert ctx.scratch["unchecked_urls"] == {"https://devauto.example/p/bert"}


# ------------------------------------------------------------------ end to end


def test_run_rescores_stored_listings_before_anything_else(store):
    p = _person(store)
    store.save_listing(_stale(p))
    reg = _dev.fixture_registry()
    with _dev.fixture_server():
        run(store, reg, [p], scan_only=False, dry_run=True, interactive=False,
            broker_ids=[BROKER], notifier=SimpleNamespace(notify=lambda *a, **k: None))
    li = next(x for x in store.list_listings(p.id, BROKER)
              if x.url == "https://devauto.example/p/bert")
    assert li.match_level is not MatchLevel.CONFIRMED
    ev = [e for e in store.events(p.id) if e.action == "rescored"]
    assert ev and ev[0].detail == {"downgraded": 1}       # counts only, no PII
