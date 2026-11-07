"""Pure serializer edge cases for the additive schemas documented in docs/CLI.md."""
from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from itertools import permutations
from typing import Any

import pytest

from freemyid import cli_json as cj
from freemyid.models import (
    BrokerStatus,
    ListingState,
    Method,
    Profile,
    Request,
    RequestKind,
    RequestStatus,
    Tier,
    Todo,
    TodoKind,
)

STAMP = datetime(2026, 11, 7, 12, 34, 56, tzinfo=UTC)
STAMP_TEXT = "2026-11-07T12:34:56+00:00"
LABEL = 'Pat Testperson — 雪 "fake" \\ label\nSpringfield IL'
TITLE = 'Review fake "listing" \\ café\n次'
PROFILE_ID = "11111111111111111111111111111111"


@pytest.fixture
def person() -> Profile:
    # Only the two fields these serializers consume; no consent or store machinery.
    return Profile.model_construct(id=PROFILE_ID, label=LABEL, created_at=STAMP,
                                   updated_at=STAMP)


def _required(actual: Any, expected: Any) -> None:
    """Check documented values and JSON types while permitting additive object fields."""
    assert type(actual) is type(expected)
    if isinstance(expected, dict):
        assert expected.keys() <= actual.keys()
        for key, value in expected.items():
            _required(actual[key], value)
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for item, value in zip(actual, expected, strict=True):
            _required(item, value)
    else:
        assert actual == expected


def _serialize(fn: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    """Check fixed inputs remain unchanged and produce equal JSON-native documents."""
    before = deepcopy(args)
    first = fn(*args)
    snapshot = deepcopy(first)
    second = fn(*args)
    assert first == second == snapshot
    assert args == before
    decoded = json.loads(json.dumps(first, ensure_ascii=False))
    assert decoded == first
    return decoded


def _skipped() -> list[dict[str, Any]]:
    return [
        {"profile_id": "fake-skipped-z", "label": LABEL, "reason": "Fake reason Z"},
        {"profile_id": "fake-skipped-a", "label": "Fake A", "reason": "Fake reason A"},
    ]


@pytest.mark.parametrize("name", ["status", "todos", "outbox", "reports"])
def test_empty_collections(name: str) -> None:
    if name == "status":
        doc = _serialize(cj.status_doc, [], {}, [])
        collection = "profiles"
    elif name == "todos":
        doc = _serialize(cj.todos_doc, [], [])
        collection = "todos"
    elif name == "outbox":
        doc = _serialize(cj.outbox_doc, [])
        collection = "requests"
    else:
        doc = _serialize(cj.reports_doc, [], [])
        collection = "reports"
    expected: dict[str, Any] = {"schema": f"{name}/1", collection: []}
    if name != "outbox":
        expected["skipped"] = []
    _required(doc, expected)


@pytest.mark.parametrize("order", list(permutations(["fake_z", "fake_a", "fake_m"])))
def test_status_broker_order_fallback_and_nullable_fields(
    person: Profile, order: tuple[str, ...],
) -> None:
    statuses = [BrokerStatus(profile_id=person.id, broker_id=bid, updated_at=STAMP)
                for bid in order]
    skipped = _skipped()
    doc = _serialize(cj.status_doc, [(person, statuses, 0)], {"fake_a": TITLE}, skipped)
    _required(doc, {"schema": "status/1", "skipped": skipped})
    [profile] = doc["profiles"]
    _required(profile, {"profile_id": PROFILE_ID, "label": LABEL, "open_todos": 0})
    assert [b["broker_id"] for b in profile["brokers"]] == ["fake_a", "fake_m", "fake_z"]
    for broker in profile["brokers"]:
        bid = broker["broker_id"]
        _required(broker, {
            "broker_id": bid, "broker_name": TITLE if bid == "fake_a" else bid,
            "state": "unknown", "tier": None, "updated_at": STAMP_TEXT,
            "last_scan_at": None, "last_submitted_at": None, "next_check_at": None,
            "attempts": 0, "escalation_level": 0,
        })


@pytest.mark.parametrize("tier", [Tier.EMAIL, Tier.ASSISTED, Tier.AUTOMATIC])
def test_status_populated_dates_and_tiers(person: Profile, tier: Tier) -> None:
    status = BrokerStatus(profile_id=person.id, broker_id="fake_broker",
                          state=ListingState.SUBMITTED, tier=tier, updated_at=STAMP,
                          last_scan_at=STAMP, last_submitted_at=STAMP, next_check_at=STAMP,
                          attempts=2, escalation_level=1)
    doc = _serialize(cj.status_doc, [(person, [status], 3)], {}, [])
    [profile] = doc["profiles"]
    _required(profile, {"open_todos": 3})
    [broker] = profile["brokers"]
    _required(broker, {"state": "submitted", "tier": str(tier), "attempts": 2,
                       "escalation_level": 1, "updated_at": STAMP_TEXT,
                       "last_scan_at": STAMP_TEXT, "last_submitted_at": STAMP_TEXT,
                       "next_check_at": STAMP_TEXT})


def test_status_profile_without_brokers(person: Profile) -> None:
    doc = _serialize(cj.status_doc, [(person, [], 0)], {}, _skipped())
    _required(doc, {"profiles": [{"profile_id": PROFILE_ID, "label": LABEL,
                                 "open_todos": 0, "brokers": []}]})


@pytest.mark.parametrize("request_id", [None, "22222222222222222222222222222222"])
def test_todos_required_fields_and_optional_ids(person: Profile, request_id: str | None) -> None:
    todo = Todo(id="33333333333333333333333333333333", profile_id=person.id, broker_id=None,
                kind=TodoKind.CAPTCHA, title=TITLE, request_id=request_id, created_at=STAMP)
    doc = _serialize(cj.todos_doc, [(person, todo)], _skipped())
    _required(doc, {"schema": "todos/1", "skipped": _skipped(), "todos": [{
        "id": "33333333333333333333333333333333", "profile_id": PROFILE_ID, "label": LABEL,
        "broker_id": None, "kind": "captcha", "title": TITLE,
        "request_id": request_id, "created_at": STAMP_TEXT,
    }]})


def test_outbox_required_fields(person: Profile) -> None:
    request = Request(id="22222222222222222222222222222222", profile_id=person.id,
                      broker_id="fake_broker", kind=RequestKind.OPT_OUT, method=Method.EMAIL,
                      status=RequestStatus.QUEUED_FOR_APPROVAL, attempt=2, created_at=STAMP)
    doc = _serialize(cj.outbox_doc, [request])
    _required(doc, {"schema": "outbox/1", "requests": [{
        "id": "22222222222222222222222222222222", "profile_id": PROFILE_ID,
        "broker_id": "fake_broker", "kind": "opt_out", "method": "email",
        "status": "queued_for_approval", "attempt": 2, "created_at": STAMP_TEXT,
    }]})


@pytest.mark.parametrize("fmt", ["html", "pdf"])
def test_reports_required_fields(person: Profile, fmt: str) -> None:
    path = f'fake-reports/雪 "report" \\ file\n.{fmt}'
    doc = _serialize(cj.reports_doc, [(person, fmt, path)], _skipped())
    _required(doc, {"schema": "reports/1", "skipped": _skipped(), "reports": [{
        "profile_id": PROFILE_ID, "label": LABEL, "format": fmt, "path": path,
    }]})


@pytest.mark.parametrize("length", [1, 10000])
def test_emit_one_unwrapped_json_object(
    person: Profile, capsys: pytest.CaptureFixture[str], length: int,
) -> None:
    title = TITLE * length
    todo = Todo(id="33333333333333333333333333333333", profile_id=person.id, kind=TodoKind.OTHER,
                title=title, created_at=STAMP)
    doc = cj.todos_doc([(person, todo)], _skipped())
    before = deepcopy(doc)
    cj.emit(doc)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert captured.out.count("\n") == 1
    assert captured.out.startswith("{")
    decoded = json.loads(captured.out)
    assert type(decoded) is dict
    assert decoded == before
    assert decoded["todos"][0]["label"] == LABEL
    assert decoded["todos"][0]["title"] == title
    assert doc == before
