"""QA (Marcus Webb) for the "Is this you?" route: guards, no PII on the card or in logs/events,
and SEC-123 (a "No" must win over a matcher-made CONFIRMED). Fake people only."""
from __future__ import annotations

import logging
import re

import pytest

from freemyid.models import MatchLevel, Todo, TodoKind

from .test_wizard_review_match import TOKEN, _level, env  # noqa: F401  (fixture)

CITY, AGE, REL = "Springfield", 61, "Jon Q Testperson"


@pytest.mark.parametrize("host", ["evil.example", "127.0.0.1.evil.example", ""])
def test_wrong_host_rejected_before_anything(env, host):  # noqa: F811
    c, store, p, li, t, f, _ = env
    r = c.post(f"/todo/{t.id}/review/yes", data=f, headers={"Host": host})
    assert r.status_code == 403
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE


def test_no_session_cookie_rejected(env):  # noqa: F811
    c, store, p, li, t, f, _ = env
    c.cookies.clear()
    assert c.post(f"/todo/{t.id}/review/yes", data=f).status_code == 403
    # the ?t= bootstrap is GET-only
    assert c.post(f"/todo/{t.id}/review/yes?t={TOKEN}", data=f).status_code == 403
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE


def test_x_csrf_header_path_also_checked(env):  # noqa: F811
    c, store, p, li, t, _f, _ = env
    r = c.post(f"/todo/{t.id}/review/yes", data={"listing_id": li.id},
               headers={"X-CSRF": "0" * 64})
    assert r.status_code == 403
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE


def test_card_shows_signal_names_never_values(env):  # noqa: F811
    c, store, p, li, _t, _f, _ = env
    rich = li.model_copy(update={
        "name_shown": "Jane Q Testperson", "age_shown": AGE, "locations_shown": [f"{CITY}, IL"],
        "relatives_shown": [REL], "match_reasons": ["city", "relative", "Springfield-raw"]})
    store.save_listing(rich)
    for path in ("/", "/more", f"/profile/{p.id}"):
        h = c.get(path).text
        assert "Yes, this is me" in h, path
        for leak in (CITY + ",", REL, "Springfield-raw", rich.url):
            assert leak not in h, (path, leak)
        # The age as a standalone number; "61" inside a random hex token (CSRF, ids) is no leak.
        assert not re.search(rf"(?<![0-9A-Za-z]){AGE}(?![0-9A-Za-z])", h), (path, AGE)
    assert "the city and a relative&#x27;s name" in c.get("/").text or \
        "the city and a relative's name" in c.get("/").text


@pytest.mark.parametrize("answer", ["yes", "no"])
def test_answer_logs_and_events_hold_no_pii(env, answer, caplog):  # noqa: F811
    c, store, p, li, t, f, _ = env
    store.save_listing(li.model_copy(update={"name_shown": "Jane Q Testperson",
                                             "locations_shown": [f"{CITY}, IL"]}))
    with caplog.at_level(logging.DEBUG):
        assert c.post(f"/todo/{t.id}/review/{answer}", data=f).status_code == 303
    text = caplog.text + repr([(e.action, e.detail) for e in store.events(p.id)])
    for leak in ("Jane", "Testperson", CITY, li.url, "example.com"):
        assert leak not in text, leak


def _matcher_confirmed(store, p, li, t):
    """A later scan saw one more matching detail: the matcher (not the person) made the
    listing CONFIRMED while the 'Is this you?' card was still open."""
    store.save_listing(li.model_copy(update={"match_level": MatchLevel.CONFIRMED,
                                             "match_reasons": ["age", "city"]}))


def test_no_wins_over_a_matcher_confirmed_listing(env):  # noqa: F811
    c, store, p, li, t, f, _ = env
    _matcher_confirmed(store, p, li, t)
    r = c.post(f"/todo/{t.id}/review/no", data=f)
    assert r.status_code == 303
    got = _level(store, p, li)
    assert got.match_level == MatchLevel.NO_MATCH and got.match_reasons == ["user_rejected"]


def test_person_answer_still_cannot_be_flipped_by_a_stale_card(env):  # noqa: F811
    """Guard for the SEC-123 fix: a second card for the same listing must not undo a Yes."""
    c, store, p, li, t, f, _ = env
    c.post(f"/todo/{t.id}/review/yes", data=f)
    t2 = Todo(profile_id=p.id, broker_id=li.broker_id, kind=TodoKind.REVIEW_MATCH,
              title="Is this Jane? (Example)", body="b", links=[li.url],
              resume_token=f"review:{li.id}")
    store.save_todo(t2)
    c.post(f"/todo/{t2.id}/review/no", data=f)
    got = _level(store, p, li)
    assert got.match_level == MatchLevel.CONFIRMED and "user_confirmed" in got.match_reasons


def test_other_persons_todo_cannot_touch_this_listing(env):  # noqa: F811
    c, store, p, li, _t, f, person = env
    q = person("Other")
    tq = Todo(profile_id=q.id, broker_id=li.broker_id, kind=TodoKind.REVIEW_MATCH,
              title="Is this Other? (Example)", body="b", links=[li.url],
              resume_token=f"review:{li.id}")      # forged: points at Jane's listing
    store.save_todo(tq)
    assert c.post(f"/todo/{tq.id}/review/yes", data=f).status_code == 400
    assert _level(store, p, li).match_level == MatchLevel.POSSIBLE
