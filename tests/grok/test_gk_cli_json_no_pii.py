"""WO-340: every CLI JSON document stays free of personal details.

One documented exception: exposure/1 ``check_url`` and listing ``url`` carry the search
link the text output also shows, which the engine builds from the name, city, state and
ZIP. The last test pins that those keys are the only place a profile detail can appear.

Existing guards, left unchanged:
* ``tests/test_cli_json_serialization_edges.py`` covers status, todos, outbox and reports
  with the stock fake profile, not these markers, and not exposure, registry, schedule,
  run, secrets or error.
* ``tests/test_cli_json_headless.py`` checks profiles and todos through the CLI.
* ``tests/codex/test_cx_cli_json_contract.py`` checks one JSON object and a schema name.

Gap: build every ``*_doc`` in ``cli_json.py`` from one fake person (Jane Q Testperson,
Springfield IL) whose street, mailbox, password, copy-fields, letter and date of birth
are markers, then walk the JSON at every depth.
"""
from __future__ import annotations

import json
import socket
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from freemyid import cli_json as cj
from freemyid.engine.exposure import Trend, TrendPoint
from freemyid.engine.runner import RunReport
from freemyid.exposure_models import (
    ExposureEntry,
    ExposureListing,
    ExposureResult,
    ScoreDriver,
    ScoreLine,
)
from freemyid.models import (
    Address,
    Broker,
    BrokerCategory,
    BrokerStatus,
    Consent,
    ConsentBasis,
    FormStep,
    ListingState,
    MailboxConfig,
    MatchLevel,
    Method,
    PersonName,
    PostalContact,
    Profile,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    Tier,
    Todo,
    TodoKind,
    VerificationStatus,
)

# Fixed ids: a random hex id could contain "1980" or "62704" by chance.
_PROFILE_ID = "a" * 32
_TODO_ID = "b" * 32
_REQUEST_ID = "c" * 32
_STAMP = datetime(2026, 11, 7, 12, 34, 56, tzinfo=UTC)
_DOB = date(1980, 4, 1)
_STREET = "MARKER-STREET-1"
_MAILBOX = "jane.testperson@example.com"
_PASSWORD = "MARKER-PASSWORD"
_LETTER = "MARKER-LETTER-BODY"
_COPY = "MARKER-COPY-FIELD"
_MARKERS: tuple[str, ...] = (
    _STREET,
    _MAILBOX,
    _PASSWORD,
    _LETTER,
    _COPY,
    "MARKER-NICKNAME",
    "MARKER-IMAP-HOST",
    "MARKER-SMTP-HOST",
    _DOB.isoformat(),
    "Testperson",
    "Jane Q",
    "217-555-0142",
    "62704",
    "Springfield",
    "freemyid-mailbox",
)
# Top-level documents only. ``trend_doc`` is a nested fragment of exposure/1 (no schema of
# its own); ``skipped_entry`` is one row inside ``skipped``.
_SCHEMAS: dict[str, str] = {
    "status": "status/1",
    "profiles": "profiles/1",
    "todos": "todos/1",
    "outbox": "outbox/1",
    "registry": "registry/1",
    "registry_source": "registry-source/1",
    "schedule": "schedule/1",
    "reports": "reports/1",
    "run": "run/1",
    "secrets": "secrets/1",
    "error": "error/1",
    "exposure": "exposure/1",
}


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: object) -> None:
    """Fail the test on any socket use. Depends on ``freemyid_env`` so this patch wins."""
    assert freemyid_env is not None

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _walk(node: Any, path: str, hits: list[str]) -> None:
    if isinstance(node, str):
        for marker in _MARKERS:
            if marker in node:
                hits.append(f"{path} contains {marker}")
        return
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}"
            if isinstance(key, str):
                for marker in _MARKERS:
                    if marker in key:
                        hits.append(f"{here} key contains {marker}")
            _walk(value, here, hits)
        return
    if isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, f"{path}[{index}]", hits)


def _assert_clean(name: str, doc: dict[str, Any]) -> None:
    assert doc["schema"] == _SCHEMAS[name]
    assert isinstance(doc, dict)
    wire = json.dumps(doc, ensure_ascii=False)
    again = json.loads(wire)
    assert again == doc
    hits: list[str] = []
    _walk(again, name, hits)
    assert hits == [], hits
    for marker in _MARKERS:
        assert marker not in wire


def _person() -> Profile:
    return Profile(
        id=_PROFILE_ID,
        label="Mom",
        consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                        attested_at=_STAMP, text_version="2026-11-c"),
        name=PersonName(first="Jane", middle="Q", last="Testperson"),
        nicknames=["MARKER-NICKNAME"],
        previous_names=[PersonName(first="Janet", last="Testperson")],
        addresses=[
            Address(street=_STREET, city="Springfield", state="IL", zip="62704", current=True),
            Address(street=_STREET, city="Springfield", state="IL", zip="62704", current=False,
                    from_year=2001, to_year=2010),
        ],
        dob=_DOB,
        phones=["217-555-0142"],
        emails=[_MAILBOX],
        relatives=["John Testperson"],
        mailbox=MailboxConfig(address=_MAILBOX, imap_host="MARKER-IMAP-HOST",
                              smtp_host="MARKER-SMTP-HOST", username=_MAILBOX,
                              keyring_service="freemyid-mailbox"),
        created_at=_STAMP,
        updated_at=_STAMP,
    )


def _todo(person: Profile) -> Todo:
    return Todo(
        id=_TODO_ID, profile_id=person.id, broker_id="fake_broker",
        kind=TodoKind.POSTAL_LETTER, title="Finish on Fake Broker",
        body=f"{_LETTER} Dear broker, please delete the listing.",
        links=[f"https://fake-broker.example/form?email={_MAILBOX}"],
        request_id=_REQUEST_ID, artifact_relpath=f"letters/{_LETTER}.txt",
        created_at=_STAMP, resume_token=_PASSWORD,
        copy_fields={"Street": _STREET, "Mailbox": _MAILBOX, "Password": _PASSWORD,
                     "Note": _COPY, "Born": _DOB.isoformat()},
    )


def _request(person: Profile) -> Request:
    return Request(
        id=_REQUEST_ID, profile_id=person.id, broker_id="fake_broker",
        kind=RequestKind.OPT_OUT, method=Method.EMAIL,
        status=RequestStatus.QUEUED_FOR_APPROVAL, attempt=1, created_at=_STAMP,
        reference=_PASSWORD,
    )


def _status(person: Profile) -> BrokerStatus:
    return BrokerStatus(
        profile_id=person.id, broker_id="fake_broker", state=ListingState.NEEDS_HUMAN,
        tier=Tier.ASSISTED, updated_at=_STAMP, last_scan_at=_STAMP,
        last_submitted_at=_STAMP, next_check_at=_STAMP, attempts=2, escalation_level=1,
        needs_human_reason=f"{_LETTER} {_STREET} {_PASSWORD} {_MAILBOX}",
    )


def _registry() -> Registry:
    broker = Broker.model_construct(
        id="fake_broker", name="Fake Broker", url="https://fake-broker.example/",
        category=BrokerCategory.PEOPLE_SEARCH, method=Method.EMAIL,
        verification_status=VerificationStatus.UNVERIFIED, has_captcha=True, covered_by=None,
        priority=40, enabled=True,
        postal=PostalContact(recipient="Privacy Office",
                             lines=[_STREET, "Springfield IL 62704"]),
        phone="217-555-0142", opt_out_email=_MAILBOX,
        search_url_pattern=f"https://fake-broker.example/{_STREET}/{{first}}",
        phone_search_url_pattern="https://fake-broker.example/217-555-0142",
        email_search_url_pattern=f"https://fake-broker.example/{_MAILBOX}",
        steps=[_LETTER], legal_basis_notes=_STREET, verification_notes=_PASSWORD,
        form=[FormStep(action="fill", value=f"{_STREET} {_MAILBOX} {_PASSWORD}")],
    )
    return Registry.model_construct(version="2026.11.10", updated=date(2026, 11, 10),
                                    brokers=[broker])


def _report(person: Profile) -> RunReport:
    return RunReport(
        per_profile={person.id: {ListingState.NOT_FOUND: 2, ListingState.FOUND: 1}},
        needs_human=1, errors=0, tiers={person.id: {Tier.EMAIL: 2, Tier.ASSISTED: 1}},
        skipped_not_due=3, queued_emails=1, drafted_emails=0, submitted=0, open_todos=1,
        skipped_profiles=1, labels={person.id: "Mom"}, dry_run=True,
    )


def _exposure(person: Profile) -> ExposureResult:
    # check_url and listing urls are copied on purpose (the text output shows them).
    # They are not filled from the profile here: a marker already inside one would be
    # the caller putting it in a public field, not this serializer copying the profile.
    entry = ExposureEntry(
        broker_id="fake_broker", broker_name="Fake Broker", status="found",
        category=BrokerCategory.PEOPLE_SEARCH, match_level=MatchLevel.CONFIRMED,
        signals=["city", "age"], checked_at=_STAMP,
        check_url="https://fake-broker.example/search",
        listings=[ExposureListing(url="https://fake-broker.example/listing/1",
                                  match_level=MatchLevel.CONFIRMED, signals=["city", "age"],
                                  contact_shown=True, relatives_shown=1)],
    )
    hand = ExposureEntry(
        broker_id="fake_manual", broker_name="Fake Manual", status="check_by_hand",
        reason="bot_blocked", checked_at=_STAMP,
        check_url="https://fake-manual.example/search",
    )
    return ExposureResult(
        profile_id=person.id, created_at=_STAMP, offline=True, practice_mode=True, score=22,
        explanation=[ScoreLine(points=15, text="1 site shows a listing that is you")],
        entries=[entry, hand], drop_first=False,
        drivers=[ScoreDriver(points=15, text="Fake Broker shows a listing of you",
                             broker_id="fake_broker")],
    )


def _trend() -> Trend:
    return Trend(
        points=[
            TrendPoint(day=date(2026, 10, 1), score=40, sites_total=2, sites_checked=1,
                       found=1),
            TrendPoint(day=date(2026, 10, 31), score=28, sites_total=2, sites_checked=1,
                       found=1),
        ],
        change=-12, since=date(2026, 10, 1),
        note="Your score went down 12 points since 2026-10-01.",
    )


def _documents(report_path: Path) -> dict[str, dict[str, Any]]:
    person = _person()
    todo = _todo(person)
    skipped = [cj.skipped_entry(person, "minor profile requires parent/guardian consent")]
    assert person.addresses[0].street == _STREET
    assert person.mailbox is not None and person.mailbox.address == _MAILBOX
    assert person.dob == _DOB
    assert todo.copy_fields["Password"] == _PASSWORD
    assert _LETTER in todo.body
    trend = _trend()
    docs = {
        "status": cj.status_doc([(person, [_status(person)], 1)],
                                {"fake_broker": "Fake Broker"}, skipped),
        "profiles": cj.profiles_doc([(person, True)]),
        "todos": cj.todos_doc([(person, todo)], skipped),
        "outbox": cj.outbox_doc([_request(person)]),
        "registry": cj.registry_doc(_registry(), "full", ["unverified fixture broker"]),
        "registry_source": cj.registry_source_doc(_registry(), "full",
                                                  ["unverified fixture broker"]),
        "schedule": cj.schedule_doc("linux", "systemd timer: active"),
        "reports": cj.reports_doc([(person, "html", str(report_path))], skipped),
        "run": cj.run_doc(_report(person), scan_only=False, headless=True, exit_code=0,
                          skipped=skipped),
        "secrets": cj.secrets_doc("keyring", None, True, True),
        "error": cj.failure_doc(cj.EXIT_NOT_CONFIGURED,
                                "not configured: nobody is set up yet"),
        "exposure": cj.exposure_doc([(person, _exposure(person))], offline=True,
                                    headless=True, exit_code=cj.EXIT_OK, skipped=skipped,
                                    trends={person.id: trend}),
    }
    assert cj.trend_doc(None) is None
    nested = cj.trend_doc(trend)
    assert nested is not None
    hits: list[str] = []
    _walk(nested, "trend", hits)
    assert hits == []
    assert nested["since"] == "2026-10-01"
    return docs


def test_socket_helpers_raise() -> None:
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


def test_every_cli_json_document_omits_personal_markers(tmp_path: Path) -> None:
    docs = _documents(tmp_path / "report.html")
    assert set(docs) == set(_SCHEMAS)
    for name, doc in docs.items():
        _assert_clean(name, doc)
    profiles = docs["profiles"]["profiles"][0]
    assert profiles["label"] == "Mom"
    assert profiles["state_of_residence"] == "IL"
    assert profiles["has_mailbox"] is True
    assert docs["todos"]["todos"][0]["title"] == "Finish on Fake Broker"
    assert docs["todos"]["todos"][0]["kind"] == "postal_letter"
    assert "body" not in docs["todos"]["todos"][0]
    assert "copy_fields" not in docs["todos"]["todos"][0]
    assert docs["schedule"]["installed"] is True
    assert docs["exposure"]["profiles"][0]["label"] == "Mom"
    assert docs["exposure"]["profiles"][0]["entries"][0]["check_url"].startswith("https://")
    for name in ("status", "profiles", "todos", "reports", "run", "exposure"):
        assert "Mom" in json.dumps(docs[name])


def test_emit_writes_one_json_object(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = _documents(tmp_path / "report.html")["exposure"]
    cj.emit(doc)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert captured.out.count("\n") == 1
    assert captured.out.startswith("{")
    parsed = json.loads(captured.out)
    assert type(parsed) is dict
    assert parsed == doc
    assert parsed["schema"] == "exposure/1"
    for marker in _MARKERS:
        assert marker not in captured.out


# qa-security review (CodeRabbit #132): check_url and listing url are the documented
# exception. The engine builds check_url from the name, city, state and ZIP (docs/CLI.md:
# the text output shows the same link). Pin that, with the real builder, those two keys
# are the only places a profile detail can appear, and that the street, mailbox, password,
# copy-fields, letter and date of birth never appear even there.
_URL_KEYS = (".check_url", ".url")
_NEVER_IN_URL: tuple[str, ...] = (_STREET, _MAILBOX, _PASSWORD, _LETTER, _COPY,
                                  "MARKER-NICKNAME", "MARKER-IMAP-HOST", "MARKER-SMTP-HOST",
                                  _DOB.isoformat(), "217-555-0142", "freemyid-mailbox")


def test_exposure_urls_built_by_the_engine_are_the_only_profile_detail() -> None:
    from freemyid.engine.exposure import _hand_check_url

    person = _person()
    broker = Broker.model_construct(
        id="fake_broker", name="Fake Broker", url="https://fake-broker.example/",
        domains=["fake-broker.example"],
        category=BrokerCategory.PEOPLE_SEARCH, method=Method.EMAIL, enabled=True,
        search_url_pattern="https://fake-broker.example/name/{first}-{last}/{city}-{state}"
                           "/{zip}",
        slug_case="title")
    url = _hand_check_url(broker, person)
    assert "Testperson" in url and "62704" in url   # a real, profile-built link
    entry = ExposureEntry(broker_id="fake_broker", broker_name="Fake Broker",
                          status="check_by_hand", reason="bot_blocked", checked_at=_STAMP,
                          check_url=url)
    result = ExposureResult(profile_id=person.id, created_at=_STAMP, offline=True,
                            practice_mode=True, score=0, explanation=[], entries=[entry],
                            drop_first=False, drivers=[])
    doc = cj.exposure_doc([(person, result)], offline=True, headless=True,
                          exit_code=cj.EXIT_OK, skipped=[], trends={})
    assert doc["profiles"][0]["entries"][0]["check_url"] == url
    hits: list[str] = []
    _walk(doc, "exposure", hits)
    assert hits, "the profile-built link should carry name/city/ZIP markers"
    for hit in hits:
        where = hit.split(" contains ")[0]
        assert where.endswith(_URL_KEYS), hit
    wire = json.dumps(doc, ensure_ascii=False)
    for marker in _NEVER_IN_URL:
        assert marker not in wire, marker
