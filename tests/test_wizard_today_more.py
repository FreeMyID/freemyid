"""Today is one card; the rest is one click away on /more; broker page answers four questions."""
from __future__ import annotations

import re

from freemyid.models import BrokerStatus, ListingState
from tests.test_wizard_dashboard import _assisted, env  # noqa: F401


def test_today_has_one_card_and_a_link_to_the_rest(env):  # noqa: F811
    c, store, p, _, _ = env
    for i in range(3):
        store.save_todo(_assisted(p).model_copy(update={"id": f"{i}" * 32, "title": f"Item {i}"}))
    t = c.get("/").text
    assert t.count('class="card todo"') == 0 and t.count("hero-card") >= 1
    assert t.count("<h1") == 1 and "Protect yourself</h2>" not in t
    assert 'href="/more#waiting-h"' in t and "(3 waiting)" in t
    m = c.get("/more")
    assert m.status_code == 200 and m.text.count('class="card todo"') == 3
    assert 'id="waiting-h"' in m.text and m.text.count("<h1") == 1


def test_single_todo_shows_no_full_list_link(env):  # noqa: F811
    c, store, p, _, _ = env
    store.save_todo(_assisted(p))
    t = c.get("/").text
    assert "See the full list" not in t and 'href="/more"' in t


def test_more_needs_session_and_has_no_nested_forms(env):  # noqa: F811
    c, store, p, _, _ = env
    store.save_todo(_assisted(p))
    html = c.get("/more").text
    for m in re.finditer(r"<form[^>]*>(.*?)</form>", html, re.DOTALL):
        assert "<form" not in m.group(1)
    c.cookies.clear()
    assert c.get("/more").status_code in (401, 403)


def test_broker_page_four_questions_in_plain_words(env):  # noqa: F811
    c, store, p, _, _ = env
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.SUBMITTED))
    t = c.get(f"/profile/{p.id}/site/examplebroker").text
    for h in ("What this site shows about you", "What we sent", "What came back", "Next check"):
        assert f"<h2>{h}</h2>" in t
    assert t.count("<h1") == 1
