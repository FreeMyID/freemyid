"""Printable-summary contracts; fake profiles, fixed dates, no store or browser."""
from __future__ import annotations

from datetime import UTC, date, datetime
from html.parser import HTMLParser

import pytest

from freemyid.models import (
    Address,
    BrokerStatus,
    Consent,
    ConsentBasis,
    ListingState,
    PersonName,
    Profile,
)
from freemyid.wizard import views

NOW = datetime(2026, 11, 7, 12, tzinfo=UTC)
SUBMITTED = datetime(2026, 10, 2, 12, tzinfo=UTC)


class SummaryHTML(HTMLParser):
    """Collect actual cells and elements, decoding text without executing markup."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.rows: list[list[str]] = []
        self.text: list[str] = []
        self.cell: str | None = None
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))
        if tag == "tr":
            self.rows.append([])
        if tag in ("td", "th"):
            self.cell = ""

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self.cell is not None:
            self.rows[-1].append(self.cell)
            self.cell = None


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(views, "utcnow", lambda: NOW)


@pytest.fixture
def fake_profile() -> Profile:
    return Profile(
        id="a" * 32, label="Pat Testperson (test profile)",
        name=PersonName(first="Pat", last="PrivateTestperson"),
        consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                        text_version="test-only"),
        addresses=[Address(street="987 Fictional Test Lane", city="Springfield",
                           state="IL", zip="62704", current=True)],
        phones=["217-555-0198"], emails=["pat.summary-test@example.invalid"],
        dob=date(1943, 2, 19), created_at=NOW, updated_at=NOW,
    )


def status(p: Profile, bid: str, state: ListingState) -> BrokerStatus:
    return BrokerStatus(profile_id=p.id, broker_id=bid, state=state, updated_at=NOW)


# Expected user wording is deliberately independent of views.PLAIN.
STATE_CASES = [
    (ListingState.UNKNOWN, None, 0, 0, 0),
    (ListingState.NOT_FOUND, None, 0, 0, 1),
    (ListingState.FOUND, "Listed. A request has not gone out yet", 0, 0, 0),
    (ListingState.SUBMITTED, "We asked them to delete it", 0, 1, 0),
    (ListingState.AWAITING_VERIFICATION, "We asked. They need to confirm", 0, 1, 0),
    (ListingState.CONFIRMED, "They confirmed", 1, 0, 0),
    (ListingState.REMOVED, "No longer listed", 1, 0, 0),
    (ListingState.REAPPEARED, "It came back. We are asking again", 0, 0, 0),
    (ListingState.NEEDS_HUMAN, "Needs a step from you", 0, 0, 0),
    (ListingState.ERROR, "We hit a problem. We will try again", 0, 0, 0),
]


def test_state_matrix_is_exhaustive() -> None:
    assert {case[0] for case in STATE_CASES} == set(ListingState)


@pytest.mark.parametrize("state,wording,good,waiting,clean", STATE_CASES)
def test_each_state_wording_and_counts(
    fake_profile: Profile, state: ListingState, wording: str | None,
    good: int, waiting: int, clean: int,
) -> None:
    html = views.summary_page(fake_profile, [status(fake_profile, "fake_site", state)],
                              {"fake_site": "Fake Site"}, 0, 0)
    parsed = SummaryHTML(html)
    assert f"{good} site{' has' if good == 1 else 's have'} confirmed" in html
    assert f"{waiting} {'is' if waiting == 1 else 'are'} still waiting to reply" in html
    assert f"{clean} site{' was' if clean == 1 else 's were'} checked and did not list" in html
    if wording is None:
        assert parsed.rows == []
        assert "Fake Site" not in html
        assert "No site has needed a request so far." in html
    else:
        assert parsed.rows == [["Site", "What happened", "Date"],
                               ["Fake Site", wording, "2026-11-07"]]


@pytest.mark.parametrize("count", [0, 1, 2])
def test_counts_and_grammar(fake_profile: Profile, count: int) -> None:
    states = (ListingState.REMOVED, ListingState.SUBMITTED, ListingState.NOT_FOUND)
    statuses = [status(fake_profile, f"fake_{state.value}_{i}", state)
                for state in states for i in range(count)]
    html = views.summary_page(fake_profile, statuses, {}, count, count)
    assert f"sent {count} request{'' if count == 1 else 's'} asking" in html
    assert f"{count} site{' has' if count == 1 else 's have'} confirmed" in html
    assert f"{count} {'is' if count == 1 else 'are'} still waiting" in html
    assert f"{count} {'needs' if count == 1 else 'need'} a step" in html
    assert f"{count} site{' was' if count == 1 else 's were'} checked" in html
    assert len(SummaryHTML(html).rows) == (1 + 2 * count if count else 0)


@pytest.mark.parametrize("bid", ["_consent", "_checklist", "_future_internal"])
@pytest.mark.parametrize("state", list(ListingState))
def test_internal_statuses_do_not_change_summary(
    fake_profile: Profile, bid: str, state: ListingState,
) -> None:
    visible = [status(fake_profile, "fake_site", ListingState.CONFIRMED)]
    names = {"fake_site": "Fake Site", bid: "Internal Fake Sentinel"}
    baseline = views.summary_page(fake_profile, visible, names, 1, 2)
    assert views.summary_page(fake_profile, visible + [status(fake_profile, bid, state)],
                              names, 1, 2) == baseline


def test_order_dates_repeatability_and_inputs(fake_profile: Profile) -> None:
    statuses = [status(fake_profile, bid, ListingState.SUBMITTED)
                for bid in ("z", "fallback_site", "a", "b")]
    statuses[0].last_submitted_at = SUBMITTED
    names = {"z": "Zulu Fake (regional)", "a": "alpha Fake", "b": "Beta Fake"}
    before = [s.model_dump() for s in statuses]
    original_names = names.copy()
    html = views.summary_page(fake_profile, statuses, names, 2, 4)
    assert html == views.summary_page(fake_profile, statuses, names, 2, 4)
    assert html == views.summary_page(fake_profile, list(reversed(statuses)), names, 2, 4)
    assert [row[0] for row in SummaryHTML(html).rows[1:]] == [
        "alpha Fake", "Beta Fake", "fallback_site", "Zulu Fake"]
    assert SummaryHTML(html).rows[-1][-1] == "2026-10-02"
    assert "Written on 2026-11-07." in html
    assert [s.model_dump() for s in statuses] == before
    assert names == original_names


def test_personal_details_are_absent(fake_profile: Profile) -> None:
    html = views.summary_page(fake_profile,
                              [status(fake_profile, "fake_site", ListingState.REMOVED)],
                              {"fake_site": "Fake Site"}, 0, 1)
    assert fake_profile.label in html
    assert "Fake Site" in html
    for private in ("987 Fictional Test Lane", "Springfield", "62704", "217-555-0198",
                    "pat.summary-test@example.invalid", "1943-02-19", "02/19/1943",
                    "19/02/1943", "PrivateTestperson"):
        assert private not in html


def test_hostile_labels_are_text(fake_profile: Profile) -> None:
    label = '<img src=x onerror="fake()"> & Pat Testperson'
    name = '<script>fake()</script> & "Fake Site"'
    fake_profile.label = label
    html = views.summary_page(fake_profile,
                              [status(fake_profile, "fake_site", ListingState.FOUND)],
                              {"fake_site": name}, 0, 0)
    parsed = SummaryHTML(html)
    assert label in "".join(parsed.text)
    assert parsed.rows[1][0] == name
    assert label not in html and name not in html
    assert not any(attrs.get("src") == "x" or "onerror" in attrs for tag, attrs in parsed.elements)
    assert not any(tag == "script" and "src" not in attrs for tag, attrs in parsed.elements)


def test_print_control_and_column_headings(fake_profile: Profile) -> None:
    parsed = SummaryHTML(views.summary_page(
        fake_profile, [status(fake_profile, "fake_site", ListingState.REMOVED)], {}, 0, 1))
    buttons = [attrs for tag, attrs in parsed.elements
               if tag == "button" and attrs.get("data-print") == "1"]
    assert len(buttons) == 1
    assert buttons[0].get("type") == "button"
    assert "Print this page" in "".join(parsed.text)
    assert any(tag == "div" and "noprint" in (attrs.get("class") or "").split()
               for tag, attrs in parsed.elements)
    assert parsed.rows[0] == ["Site", "What happened", "Date"]
    assert [attrs.get("scope") for tag, attrs in parsed.elements if tag == "th"] == [
        "col", "col", "col"]
