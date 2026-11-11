"""Offline render checks for the Today screen's single-card states."""
from __future__ import annotations

from html.parser import HTMLParser

import pytest

from freemyid.models import Listing, MatchLevel, Profile, Todo, TodoKind
from freemyid.storage import Store
from freemyid.wizard import dashboard
from tests.conftest import make_profile

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

FAKE_REVIEW_VALUES = (
    "SYNTHETIC-NAME-235",
    "SYNTHETIC-LOCATION-235",
    "SYNTHETIC-RELATIVE-235",
    "SYNTHETIC-BODY-235",
    "83",
    "https://example.invalid/SYNTHETIC-URL-235",
)


@pytest.mark.parametrize("todo_count", [0, 1, 3], ids=["none", "one", "many"])
def test_today_has_one_next_step_card_and_more_link(store: Store, todo_count: int) -> None:
    person = make_profile(label="Jane Q Testperson")
    store.save_profile(person)
    for index in range(todo_count):
        todo = Todo(
            id=f"{index + 1:032x}",
            profile_id=person.id,
            broker_id="samplebroker",
            kind=TodoKind.ASSISTED_OPT_OUT,
            title=f"Sample task {index + 1}",
            body="Follow the sample steps.",
        )
        store.save_todo(todo)

    html = _render_today(store, person)

    assert html.count('class="card hero-card') == 1
    assert 'href="/more"' in html
    if todo_count > 1:
        assert f'href="/more#waiting-h">See the full list ({todo_count} waiting)' in html
    else:
        assert "See the full list" not in html
    if todo_count == 0:
        assert "Nothing needs you today" in html
    elif todo_count == 1:
        assert "Sample task 1" in html
    else:
        assert "Sample task 1" in html
        assert "Sample task 2" not in html
        assert "Sample task 3" not in html


@pytest.mark.parametrize("real_submissions", [False, True], ids=["practice", "real"])
def test_practice_banner_matches_submission_mode(store: Store, real_submissions: bool) -> None:
    person = make_profile(label="Jane Q Testperson")
    store.save_profile(person)
    html = _render_today(store, person, practice=not real_submissions)

    expected = "Practice mode:</b> Free My ID is looking for your listings, but no removal " \
        "requests go out until you say so."
    if real_submissions:
        assert expected not in html
        assert "Practice mode:" not in html
    else:
        assert expected in html


def test_pending_possible_match_is_private_on_today(store: Store) -> None:
    person = make_profile(label="Jane Q Testperson")
    store.save_profile(person)
    listing = Listing(
        profile_id=person.id,
        broker_id="examplebroker",
        url=FAKE_REVIEW_VALUES[5],
        name_shown=FAKE_REVIEW_VALUES[0],
        age_shown=83,
        locations_shown=[FAKE_REVIEW_VALUES[1]],
        relatives_shown=[FAKE_REVIEW_VALUES[2]],
        match_score=72,
        match_level=MatchLevel.POSSIBLE,
        match_reasons=["city", "age"],
    )
    store.save_listing(listing)
    store.save_todo(Todo(
        profile_id=person.id,
        broker_id="examplebroker",
        kind=TodoKind.REVIEW_MATCH,
        title="Possible match for Jane",
        body=FAKE_REVIEW_VALUES[3],
        links=[FAKE_REVIEW_VALUES[5]],
        resume_token=f"review:{listing.id}",
    ))

    html = _render_today(store, person, reasons={listing.id: ["city", "age"]})

    assert html.count('class="card hero-card') == 1
    assert html.count('data-kind="review_match"') == 1
    assert "Possible match for Jane" in html
    visible = _visible_text(html)
    for value in FAKE_REVIEW_VALUES:
        assert value not in visible
    assert "Testperson" not in visible
    assert "Springfield" not in visible
    assert "Q Testperson" not in visible


def _render_today(store: Store, person: Profile, *, practice: bool = True,
                  reasons: dict[str, list[str]] | None = None) -> str:
    todos = [(todo, person.label, "Sample broker") for todo in store.list_todos(person.id)]
    return dashboard.home_page(
        statuses=store.list_statuses(person.id),
        todos=todos,
        people=[{"profile": person, "consent_problem": None}],
        outbox_count=0,
        csrf="SYNTHETIC-CSRF-TOKEN",
        practice=practice,
        reasons=reasons,
    )


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"style", "script"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def _visible_text(markup: str) -> str:
    parser = _VisibleText()
    parser.feed(markup)
    return " ".join(parser.parts)
