"""WO-603: the progress report only says a site was "asked" when a request really went out.

Fake people and fake sites only. Covers: dry-run-only data (asked 0), NEEDS_HUMAN never counted
as asked, one real send plus one site waiting on a person, the "data broker" / "people-search"
wording, no profile PII beyond the label, and HTML/PDF sharing the same sentences.
"""
from __future__ import annotations

import html
import re
import sys
import types
from datetime import UTC, date, datetime

import pytest

from freemyid.models import (
    Broker,
    BrokerStatus,
    ListingState,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    Todo,
    TodoKind,
)
from freemyid.registry import Registry
from freemyid.state import mark_submitted
from freemyid.wizard.report import build_report, report_counts
from tests.conftest import make_profile

S = ListingState
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def _broker(bid: str, category: str = "data_broker", **over) -> Broker:
    return Broker.model_validate({
        "id": bid, "name": bid.title(), "url": f"https://{bid}.example/",
        "category": category, "domains": [f"{bid}.example"], "method": "email",
        "opt_out_email": f"privacy@{bid}.example", **over})


def _registry(*brokers: Broker) -> Registry:
    return Registry(version="t", updated=date(2026, 11, 7), brokers=list(brokers))


MIXED = _registry(_broker("fakeone", "people_search"), _broker("faketwo"),
                  _broker("fakethree"), _broker("fakefour", "people_search"))
PEOPLE = _registry(_broker("fakeone", "people_search"), _broker("fakefour", "people_search"))


@pytest.fixture
def person(store):
    p = make_profile(label="Gran")
    store.save_profile(p)
    return p


def _status(store, p, bid: str, state: S, **over) -> BrokerStatus:
    st = BrokerStatus(profile_id=p.id, broker_id=bid, state=state, **over)
    store.save_status(st)
    return st


def _request(store, p, bid: str, **over) -> Request:
    r = Request(profile_id=p.id, broker_id=bid, kind=RequestKind.OPT_OUT, method=Method.EMAIL,
                **over)
    store.save_request(r)
    return r


def _todo(store, p, bid: str | None, kind: TodoKind = TodoKind.ASSISTED_OPT_OUT, **over) -> Todo:
    t = Todo(profile_id=p.id, broker_id=bid, kind=kind, title="Remove your listing", **over)
    store.save_todo(t)
    return t


def _text(store, reg, p) -> str:
    return html.unescape(build_report(store, reg, p.id, "html").read_text(encoding="utf-8"))


def _lead(text: str) -> str:
    m = re.search(r'<p class="lead">(.*?)</p>', text, re.DOTALL)
    assert m, "report has no opening paragraph"
    return m.group(1)


def _row(text: str, site: str) -> str:
    m = re.search(rf"<tr><td>{site}.*?</tr>", text, re.DOTALL)
    assert m, f"no row for {site}"
    return m.group(0)


ASKED_CLAIM = re.compile(r"\d+ [a-z\- ]*sites? ha(s|ve) been asked")


# ------------------------------------------------------------------ (a) dry run only: asked 0

def test_dry_run_only_counts_nothing_as_asked(store, person):
    """The owner test in small: scan + `run --dry-run`. Draft letters, sites that need a person."""
    for bid in ("fakeone", "faketwo", "fakethree"):
        _status(store, person, bid, S.NEEDS_HUMAN)
        _request(store, person, bid, status=RequestStatus.DRAFT, dry_run=True)
        _todo(store, person, bid, TodoKind.SEND_EMAIL_MANUALLY)
    c = report_counts(store, MIXED, person.id)
    assert (c.asked, c.good, c.waiting, c.need_you) == (0, 0, 0, 3)
    text = _text(store, MIXED, person)
    assert _lead(text) == "Nothing has been sent yet. 3 data broker sites need a step from you."
    assert not ASKED_CLAIM.search(text)
    assert "no site has received a request" in text


def test_dry_run_request_marked_sent_is_still_not_asked(store, person):
    """Belt and braces: a practice request never counts, whatever its status says."""
    _status(store, person, "fakeone", S.FOUND, last_scan_at=NOW)
    _request(store, person, "fakeone", status=RequestStatus.SENT, sent_at=NOW, dry_run=True)
    c = report_counts(store, MIXED, person.id)
    assert (c.asked, c.need_you) == (0, 0)
    text = _text(store, MIXED, person)
    assert _lead(text) == "Nothing has been sent yet."
    assert _row(text, "Fakeone").endswith("<td class='d'>-</td></tr>")   # no "last request" date


def test_one_site_needing_you_is_singular(store, person):
    _status(store, person, "fakeone", S.NEEDS_HUMAN)
    assert _lead(_text(store, PEOPLE, person)) == \
        "Nothing has been sent yet. 1 people-search site needs a step from you."


# ------------------------------------------------- (b) one real send + one site that needs you

def test_one_real_submission_and_one_needs_human(store, person):
    sent = mark_submitted(_status(store, person, "fakeone", S.FOUND, last_scan_at=NOW), NOW)
    store.save_status(sent)
    _request(store, person, "fakeone", status=RequestStatus.SENT, sent_at=NOW)
    _status(store, person, "faketwo", S.NEEDS_HUMAN)
    _todo(store, person, "faketwo")
    c = report_counts(store, MIXED, person.id)
    assert (c.asked, c.need_you, c.waiting, c.good) == (1, 1, 1, 0)
    text = _text(store, MIXED, person)
    assert _lead(text) == (
        "1 data broker site has been asked to delete this person's details. So far 0 have "
        "confirmed or no longer list them, and 1 has not replied yet. 1 site needs a step "
        "from you.")
    assert "Nothing has been sent yet" not in text
    assert "2026-11-10" in _row(text, "Fakeone")
    assert _row(text, "Faketwo").endswith("<td class='d'>-</td></tr>")


def test_real_sent_request_counts_even_without_a_submission_time(store, person):
    """A site can be asked AND need you (asked, then it wants a step from a person)."""
    _status(store, person, "fakeone", S.NEEDS_HUMAN)
    _request(store, person, "fakeone", status=RequestStatus.SENT, sent_at=NOW)
    _request(store, person, "fakeone", status=RequestStatus.DRAFT)   # a later draft: not a send
    c = report_counts(store, MIXED, person.id)
    assert (c.asked, c.need_you, c.waiting) == (1, 1, 0)
    assert "2026-11-10" in _row(_text(store, MIXED, person), "Fakeone")


@pytest.mark.parametrize("status", [RequestStatus.DRAFT, RequestStatus.QUEUED_FOR_APPROVAL,
                                    RequestStatus.FAILED, RequestStatus.CANCELLED])
def test_unsent_request_is_not_asked(store, person, status):
    _status(store, person, "fakeone", S.FOUND, last_scan_at=NOW)
    _request(store, person, "fakeone", status=status)
    assert report_counts(store, MIXED, person.id).asked == 0


def test_good_and_waiting_count_only_sites_that_were_asked(store, person):
    for bid, state in (("fakeone", S.CONFIRMED), ("faketwo", S.REMOVED),
                       ("fakethree", S.AWAITING_VERIFICATION)):
        _status(store, person, bid, state, last_submitted_at=NOW)
    _status(store, person, "fakefour", S.REAPPEARED, last_submitted_at=NOW)
    c = report_counts(store, MIXED, person.id)
    assert (c.asked, c.good, c.waiting, c.reappeared, c.need_you) == (4, 2, 1, 1, 0)
    assert _lead(_text(store, MIXED, person)) == (
        "4 data broker sites have been asked to delete this person's details. So far 2 have "
        "confirmed or no longer list them, and 1 has not replied yet. 1 put the details back "
        "up after taking them down.")


def test_site_with_an_open_todo_needs_you_and_the_row_says_so(store, person):
    _status(store, person, "fakeone", S.FOUND, last_scan_at=NOW)
    _todo(store, person, "fakeone", TodoKind.REVIEW_MATCH)
    _todo(store, person, None, TodoKind.OTHER)            # not about a site
    c = report_counts(store, MIXED, person.id)
    assert (c.asked, c.need_you, c.other_steps) == (0, 1, 1)
    text = _text(store, MIXED, person)
    assert "your details are listed (needs you)" in _row(text, "Fakeone")
    assert "1 more step is waiting for you in Free My ID." in text


def test_shared_step_is_explained_once(store, person):
    _status(store, person, "fakeone", S.NEEDS_HUMAN)
    _status(store, person, "faketwo", S.NEEDS_HUMAN, needs_human_reason="via:fakeone")
    assert "One step can cover several sites." in _text(store, MIXED, person)


def test_presumed_site_that_was_never_searched_is_not_called_listed(store, person):
    _status(store, person, "fakeone", S.FOUND)                      # blind: no scan ran
    _status(store, person, "faketwo", S.FOUND, last_scan_at=NOW)    # really seen
    text = _text(store, MIXED, person)
    assert "not checked yet" in _row(text, "Fakeone")
    assert "your details are listed" in _row(text, "Faketwo")


def test_internal_rows_are_not_sites(store, person):
    _status(store, person, "_internal", S.NEEDS_HUMAN)
    c = report_counts(store, MIXED, person.id)
    assert (c.sites, c.need_you) == (0, 0)
    assert "_internal" not in _text(store, MIXED, person)


# ------------------------------------------------------------------ wording: which kind of site

def test_mixed_brokers_are_called_data_broker_sites(store, person):
    _status(store, person, "fakeone", S.SUBMITTED, last_submitted_at=NOW)   # people-search
    _status(store, person, "faketwo", S.NEEDS_HUMAN)                        # marketing data
    text = _text(store, MIXED, person)
    lead = _lead(text)
    assert "data broker site" in lead and "people-search" not in lead
    assert "A data broker is a company that collects details about people" in text
    assert "what Free My ID has asked" not in text      # the old heading claimed asking too


def test_only_people_search_brokers_keep_the_people_search_wording(store, person):
    _status(store, person, "fakeone", S.SUBMITTED, last_submitted_at=NOW)
    _status(store, person, "fakefour", S.NEEDS_HUMAN)
    text = _text(store, PEOPLE, person)
    lead = _lead(text)
    assert lead.startswith("1 people-search site has been asked")
    assert "data broker" not in text


def test_site_missing_from_the_registry_is_not_assumed_people_search(store, person):
    _status(store, person, "fakeone", S.NEEDS_HUMAN)
    _status(store, person, "gonesite", S.NEEDS_HUMAN)
    assert not report_counts(store, PEOPLE, person.id).people_search_only
    assert "2 data broker sites need a step" in _lead(_text(store, PEOPLE, person))


def test_empty_report_makes_no_claim(store, person):
    text = _text(store, MIXED, person)
    assert _lead(text) == "Nothing has been sent yet."
    assert not ASKED_CLAIM.search(text)


# ------------------------------------------------------------------ (c) no PII beyond the label

def test_report_has_the_label_and_no_other_profile_details(store, person):
    _status(store, person, "fakeone", S.SUBMITTED, last_submitted_at=NOW)
    _request(store, person, "fakeone", status=RequestStatus.SENT, sent_at=NOW,
             reference="Jane Q Testperson ticket")
    _status(store, person, "faketwo", S.NEEDS_HUMAN,
            needs_human_reason="call about Jane Testperson")
    _todo(store, person, "faketwo", TodoKind.PHONE_CALL,
          body="Say: I am Jane Q Testperson, 742 Evergreen Terrace, 217-555-0142",
          copy_fields={"Email": "jane.testperson@example.com"})
    raw = build_report(store, MIXED, person.id, "html").read_text(encoding="utf-8")
    assert "Gran" in raw
    for leak in ("Jane", "Testperson", "Evergreen", "Springfield", "62704", "217-555-0142",
                 "555", "jane.testperson", "example.com", "John", "1980", person.id):
        assert leak not in raw, leak


# ------------------------------------------------------------------ PDF shares the same counts

def test_pdf_is_rendered_from_the_same_sentences(store, person, monkeypatch):
    _status(store, person, "faketwo", S.NEEDS_HUMAN)
    _request(store, person, "faketwo", status=RequestStatus.DRAFT, dry_run=True)
    seen: list[str] = []

    class FakeHTML:
        def __init__(self, string: str) -> None:
            seen.append(string)

        def write_pdf(self, target: str) -> None:
            with open(target, "wb") as fh:
                fh.write(b"%PDF-fake")

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=FakeHTML))
    out = build_report(store, MIXED, person.id, "pdf")
    assert out.suffix == ".pdf" and len(seen) == 1
    assert _lead(html.unescape(seen[0])) == \
        "Nothing has been sent yet. 1 data broker site needs a step from you."
