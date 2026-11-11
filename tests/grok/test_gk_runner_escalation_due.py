"""When a sent removal request is overdue: calendar days, not elapsed hours.

45 days for a standard state-law request, 15 for a stated shorter deadline, plus any
extension the broker claimed. Jane Q Testperson of Springfield IL only. No network.
"""
from __future__ import annotations

import asyncio
import socket
from datetime import UTC, datetime, timedelta, tzinfo
from pathlib import Path

import pytest

from freemyid import config as cfgmod
from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import outbox
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import (
    EXTENSION_EVENT,
    LEGAL_EXTENSION_DAYS,
    LEGAL_WINDOW_DAYS,
    SHORT_DEADLINE_DAYS,
    RequestDeadline,
    Runner,
    request_deadline,
)
from freemyid.models import (
    Actor,
    Broker,
    BrokerStatus,
    Consent,
    ConsentBasis,
    EmailMode,
    Event,
    ListingState,
    MailboxConfig,
    Method,
    Profile,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    StateLaw,
    Tier,
    TodoKind,
)
from freemyid.storage import Store
from tests.conftest import make_profile

# Fixed clock. The send time is 23:00 on an earlier date, so 01:00 on the due day is
# still short of N * 24 hours. A calendar due day is overdue anyway.
NOW = datetime(2026, 8, 1, 1, 0, tzinfo=UTC)
B = Broker.model_validate({
    "id": "fakeb", "name": "Fake B", "url": "https://fakeb.example/",
    "category": "data_broker", "domains": ["fakeb.example"], "method": "email",
    "opt_out_email": "privacy@fakeb.example", "typical_processing_days": 3})
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")
LADDER = timedelta(days=3 + 15)


class _SpringForward(tzinfo):
    """UTC-6 before 2026-03-08 02:00 wall time, UTC-5 after (one hour disappears)."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        if dt is None or dt.replace(tzinfo=None) < datetime(2026, 3, 8, 2, 0):
            return timedelta(hours=-6)
        return timedelta(hours=-5)

    def dst(self, dt: datetime | None) -> timedelta:
        if dt is None or dt.replace(tzinfo=None) < datetime(2026, 3, 8, 2, 0):
            return timedelta(hours=1)
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "SPR"


class _FallBack(tzinfo):
    """UTC-5 before 2026-11-01 01:30 wall time, UTC-6 after (one hour repeats)."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        if dt is None or dt.replace(tzinfo=None) < datetime(2026, 11, 1, 1, 30):
            return timedelta(hours=-5)
        return timedelta(hours=-6)

    def dst(self, dt: datetime | None) -> timedelta:
        if dt is None or dt.replace(tzinfo=None) < datetime(2026, 11, 1, 1, 30):
            return timedelta(hours=1)
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "FLB"


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    """socket.connect and create_connection always raise, including localhost.

    Depending on freemyid_env runs this after that fixture's own connect patch.
    """
    del freemyid_env

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_socket_helpers_raise() -> None:
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="network blocked"):
        socket.create_connection(("127.0.0.1", 9))


def _sent(days_before: int) -> datetime:
    day = NOW.date() - timedelta(days=days_before)
    return datetime(day.year, day.month, day.day, 23, 0, tzinfo=UTC)


# ---------------------------------------------------------------- table


@pytest.mark.parametrize(
    ("days", "shorter", "extension", "overdue"),
    [
        (14, True, 0, False),
        (15, True, 0, True),
        (44, False, 0, False),
        (45, False, 0, True),
        (46, False, 0, True),
        (14, False, 0, False),
        (15, False, 0, False),
        (44, True, 0, True),
        (45, True, 0, True),
        (46, True, 0, True),
        # an extension claim moves the due day by that many days, not a fixed 45
        (45, False, 20, False),
        (64, False, 20, False),
        (65, False, 20, True),
        (15, True, 10, False),
        (24, True, 10, False),
        (25, True, 10, True),
    ],
)
def test_due_day_table(days: int, shorter: bool, extension: int, overdue: bool) -> None:
    sent = _sent(days)
    limit = (SHORT_DEADLINE_DAYS if shorter else LEGAL_WINDOW_DAYS) + extension
    got = request_deadline(sent, NOW, shorter_deadline=shorter, extension_days=extension)
    assert got == RequestDeadline(overdue, sent.date() + timedelta(days=limit))
    # 01:00 on the due day is not yet N * 24 hours after a 23:00 send
    if days == limit and extension == 0:
        assert NOW - sent < timedelta(days=limit)


def test_no_sent_date_is_never_overdue() -> None:
    for shorter in (False, True):
        for extra in (0, LEGAL_EXTENSION_DAYS):
            got = request_deadline(None, NOW, shorter_deadline=shorter, extension_days=extra)
            assert got == RequestDeadline(False, None)


# ---------------------------------------------------------------- leap year and DST


def test_leap_day_counts_and_hours_do_not() -> None:
    sent = datetime(2024, 2, 28, 23, 0, tzinfo=UTC)
    morning = datetime(2024, 4, 13, 1, 0, tzinfo=UTC)
    assert (morning.date() - sent.date()).days == 45
    assert morning - sent < timedelta(days=45)
    assert request_deadline(sent, morning) == RequestDeadline(True, morning.date())
    day_before = datetime(2024, 4, 12, 23, 0, tzinfo=UTC)
    assert request_deadline(sent, day_before).overdue is False

    # the same month-day span is 44 days when February has no 29th
    common = datetime(2023, 2, 28, 23, 0, tzinfo=UTC)
    common_morning = datetime(2023, 4, 13, 1, 0, tzinfo=UTC)
    assert (common_morning.date() - common.date()).days == 44
    assert request_deadline(common, common_morning).overdue is False
    next_morning = datetime(2023, 4, 14, 1, 0, tzinfo=UTC)
    assert request_deadline(common, next_morning).overdue is True


def test_dst_spring_forward_does_not_delay_the_due_day() -> None:
    zone = _SpringForward()
    sent = datetime(2026, 3, 7, 12, 0, tzinfo=zone)
    now = datetime(2026, 3, 22, 12, 0, tzinfo=zone)
    assert (now.date() - sent.date()).days == SHORT_DEADLINE_DAYS
    # UTC elapsed hours are one short; the due day does not move with them
    utc_elapsed = now.astimezone(UTC) - sent.astimezone(UTC)
    assert utc_elapsed < timedelta(days=SHORT_DEADLINE_DAYS)
    got = request_deadline(sent, now, shorter_deadline=True)
    assert got.overdue is True
    assert got.due_on == sent.date() + timedelta(days=SHORT_DEADLINE_DAYS)


def test_dst_fall_back_does_not_advance_the_due_day() -> None:
    zone = _FallBack()
    sent = datetime(2026, 10, 31, 0, 30, tzinfo=zone)
    now = datetime(2026, 11, 14, 23, 59, tzinfo=zone)
    assert (now.date() - sent.date()).days == SHORT_DEADLINE_DAYS - 1
    # the repeated hour makes UTC elapsed time a day long; the due day stays put
    utc_elapsed = now.astimezone(UTC) - sent.astimezone(UTC)
    assert utc_elapsed >= timedelta(days=SHORT_DEADLINE_DAYS)
    got = request_deadline(sent, now, shorter_deadline=True)
    assert got.overdue is False
    assert got.due_on == sent.date() + timedelta(days=SHORT_DEADLINE_DAYS)


# ---------------------------------------------------------------- runner uses the helper


def _person(store: Store) -> Profile:
    consent = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                      text_version=CURRENT_TEXT_VERSION)
    profile = make_profile(consent=consent, mailbox=MB, email_mode=EmailMode.AUTO)
    store.save_profile(profile)
    return profile


def _runner(store: Store, now: datetime, laws: dict[str, StateLaw] | None = None) -> Runner:
    reg = Registry(version="t", updated=now.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    return Runner(store, reg, scan_only=False, dry_run=False, interactive=False,
                  broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
                  state_laws=laws or {}, now=now)


def _status(profile: Profile, level: int, sent: datetime, escalated: datetime) -> BrokerStatus:
    return BrokerStatus(profile_id=profile.id, broker_id=B.id, state=ListingState.SUBMITTED,
                        last_submitted_at=sent, escalation_level=level,
                        last_escalated_at=escalated)


def _save_sent(store: Store, profile: Profile, at: datetime) -> None:
    store.save_request(Request(
        profile_id=profile.id, broker_id=B.id, kind=RequestKind.OPT_OUT, method=Method.EMAIL,
        status=RequestStatus.SENT, created_at=at, sent_at=at))


def _escalate(runner: Runner, profile: Profile, status: BrokerStatus) -> BrokerStatus:
    return asyncio.run(runner._escalate(profile, B, B, status, Tier.EMAIL, scanned=False))


def test_runner_legal_demand_follows_the_calendar_day(store: Store) -> None:
    profile = _person(store)
    sent = datetime(2026, 6, 1, 23, 0, tzinfo=UTC)
    _save_sent(store, profile, sent)
    # Day 44, late: still inside the window. Checked before a demand is queued.
    waiting_now = datetime(2026, 7, 15, 23, 0, tzinfo=UTC)
    assert (waiting_now.date() - sent.date()).days == LEGAL_WINDOW_DAYS - 1
    held = _escalate(_runner(store, waiting_now), profile,
                     _status(profile, 2, sent, waiting_now - LADDER))
    assert held.escalation_level == 2
    waiting = [e for e in store.events(profile.id, B.id) if e.action == "escalation_waiting"]
    assert waiting and waiting[-1].detail["why"] == "legal_window"
    assert waiting[-1].detail["until"] == (sent.date() + timedelta(days=45)).isoformat()
    assert set(waiting[-1].detail) <= {"rung", "why", "until"}

    # 01:00 on day 45 is before sent + 45 * 24 hours; the demand still goes out
    due_morning = datetime(2026, 7, 16, 1, 0, tzinfo=UTC)
    assert (due_morning.date() - sent.date()).days == LEGAL_WINDOW_DAYS
    assert due_morning < sent + timedelta(days=LEGAL_WINDOW_DAYS)
    new = _escalate(_runner(store, due_morning), profile,
                    _status(profile, 2, sent, due_morning - LADDER))
    assert new.escalation_level == 3
    demands = [r for r in store.list_requests(profile.id, B.id)
               if r.kind == RequestKind.LEGAL_DEMAND]
    assert len(demands) == 1


def test_runner_extension_moves_the_demand(store: Store) -> None:
    profile = _person(store)
    sent = datetime(2026, 6, 1, 23, 0, tzinfo=UTC)
    _save_sent(store, profile, sent)
    store.log(Event(profile_id=profile.id, broker_id=B.id, actor=Actor.ENGINE,
                    action=EXTENSION_EVENT))
    now = datetime(2026, 7, 16, 1, 0, tzinfo=UTC)
    status = _status(profile, 2, sent, now - LADDER)
    new = _escalate(_runner(store, now), profile, status)
    assert new.escalation_level == 2
    assert not any(r.kind == RequestKind.LEGAL_DEMAND
                   for r in store.list_requests(profile.id, B.id))


def test_runner_complaint_handoff_uses_the_same_due_day(store: Store) -> None:
    profile = _person(store)
    sent = datetime(2026, 6, 1, 23, 0, tzinfo=UTC)
    _save_sent(store, profile, sent)
    early = datetime(2026, 7, 15, 23, 0, tzinfo=UTC)
    _escalate(_runner(store, early), profile, _status(profile, 3, sent, early - LADDER))
    assert not [t for t in store.list_todos(profile.id) if t.kind == TodoKind.COMPLAINT]

    due = datetime(2026, 7, 16, 1, 0, tzinfo=UTC)
    _escalate(_runner(store, due), profile, _status(profile, 3, sent, due - LADDER))
    complaints = [t for t in store.list_todos(profile.id) if t.kind == TodoKind.COMPLAINT]
    assert len(complaints) == 1
    assert complaints[0].broker_id == B.id
    assert "Jane" not in (complaints[0].body or "")
    assert "Springfield" not in (complaints[0].body or "")


def test_stated_shorter_deadline_is_fifteen_days(
    store: Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    law = StateLaw(state="IL", statute_name="Fake Act", citation="Fake 1", response_days=30,
                   rights=["deletion"])

    def fake_effective(*_args: object, **_kwargs: object) -> StateLaw:
        return law

    monkeypatch.setattr(outbox, "effective_law", fake_effective)
    seen: list[object] = []
    real = outbox.queue_email

    def spy(*args: object, **kwargs: object) -> object:
        seen.append(kwargs.get("state_law"))
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(outbox, "queue_email", spy)
    profile = _person(store)
    sent_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    _save_sent(store, profile, sent_at)
    now = sent_at + timedelta(days=20)
    # raw 30-day window would still be a reminder; the stated shorter clock is 15
    status = _status(profile, 1, sent_at, now - LADDER)
    new = _escalate(_runner(store, now, {"IL": law}), profile, status)
    assert new.escalation_level == 2
    assert seen == [law]
    events = [e for e in store.events(profile.id, B.id) if e.action == "escalated"]
    assert events and events[0].detail["reminder"] is False


def _fixed_law(monkeypatch: pytest.MonkeyPatch, days: int) -> StateLaw:
    law = StateLaw(state="IL", statute_name="Fake Act", citation="Fake 1", response_days=days,
                   rights=["deletion"])

    def fake_effective(*_args: object, **_kwargs: object) -> StateLaw:
        return law

    monkeypatch.setattr(outbox, "effective_law", fake_effective)
    return law


@pytest.mark.parametrize("level,kind", [(2, "demand"), (3, "complaint")])
def test_shorter_clock_never_brings_legal_rungs_before_the_statute(
    store: Store, monkeypatch: pytest.MonkeyPatch, level: int, kind: str,
) -> None:
    """CodeRabbit #106: the 15-day clock is for the follow-up only. A legal demand or a
    complaint hand-off still waits out the full verified window (30 days here)."""
    law = _fixed_law(monkeypatch, 30)
    profile = _person(store)
    sent = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    _save_sent(store, profile, sent)
    day20 = sent + timedelta(days=20)
    held = _escalate(_runner(store, day20, {"IL": law}), profile,
                     _status(profile, level, sent, day20 - LADDER))
    assert held.escalation_level == level
    assert not any(r.kind == RequestKind.LEGAL_DEMAND
                   for r in store.list_requests(profile.id, B.id))
    assert not [t for t in store.list_todos(profile.id) if t.kind == TodoKind.COMPLAINT]
    waiting = [e for e in store.events(profile.id, B.id) if e.action == "escalation_waiting"]
    assert waiting[-1].detail["until"] == (sent.date() + timedelta(days=30)).isoformat()

    day30 = sent + timedelta(days=30)
    new = _escalate(_runner(store, day30, {"IL": law}), profile,
                    _status(profile, level, sent, day30 - LADDER))
    assert new.escalation_level == level + 1
    if kind == "demand":
        assert [r for r in store.list_requests(profile.id, B.id)
                if r.kind == RequestKind.LEGAL_DEMAND]
    else:
        assert [t for t in store.list_todos(profile.id) if t.kind == TodoKind.COMPLAINT]


def test_runner_waits_out_a_verified_window_over_45_days(
    store: Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CodeRabbit #140: a 90-day verified window holds the demand past day 45."""
    law = _fixed_law(monkeypatch, 90)
    profile = _person(store)
    sent = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    _save_sent(store, profile, sent)
    day60 = sent + timedelta(days=60)
    held = _escalate(_runner(store, day60, {"IL": law}), profile,
                     _status(profile, 2, sent, day60 - LADDER))
    assert held.escalation_level == 2
    waiting = [e for e in store.events(profile.id, B.id) if e.action == "escalation_waiting"]
    assert waiting[-1].detail["until"] == (sent.date() + timedelta(days=90)).isoformat()
    day90 = sent + timedelta(days=90)
    new = _escalate(_runner(store, day90, {"IL": law}), profile,
                    _status(profile, 2, sent, day90 - LADDER))
    assert new.escalation_level == 3
