"""Exhaustive, deterministic properties for the listing state machine."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from freemyid import state
from freemyid.models import Broker, BrokerStatus
from freemyid.models import ListingState as S
from freemyid.state import Escalation

NOW = datetime(2026, 11, 9, 12, tzinfo=UTC)
SUBMISSION_VALUES = (None, NOW - timedelta(days=30))
AFTER_SCAN_CASES = [
    pytest.param(
        current,
        found,
        last_submitted_at,
        marks=(
            pytest.mark.xfail(
                strict=True,
                reason="SEC finding, fix owner: orchestrator (state.py contract): an UNKNOWN status "
                       "that has a last_submitted_at makes after_scan return REAPPEARED or "
                       "REMOVED (src/freemyid/state.py:87-91), which UNKNOWN may not enter "
                       "(src/freemyid/state.py:19,35-39)",
            ),
        )
        if current == S.UNKNOWN and last_submitted_at is not None
        else (),
        id=f"{current.value}-found-{found}-submitted-{last_submitted_at is not None}",
    )
    for current in S
    for found in (False, True)
    for last_submitted_at in SUBMISSION_VALUES
]


def _broker(processing_days: int = 30, recheck_days: int = 30) -> Broker:
    return Broker(
        id="fakeb",
        name="Example Broker",
        url="https://fakeb.example/",
        category="people_search",
        domains=["fakeb.example"],
        method="web_form",
        opt_out_url="https://fakeb.example/opt-out",
        typical_processing_days=processing_days,
        recheck_interval_days=recheck_days,
    )


def _status(current: S, **updates: object) -> BrokerStatus:
    return BrokerStatus(
        profile_id="a" * 32,
        broker_id="fakeb",
        state=current,
        **updates,
    )


@pytest.mark.parametrize("current,found,last_submitted_at", AFTER_SCAN_CASES)
def test_after_scan_result_is_a_legal_transition(
    current: S, found: bool, last_submitted_at: datetime | None
) -> None:
    status = _status(current, last_submitted_at=last_submitted_at)
    destination = state.after_scan(status, found, NOW)
    assert state.can_transition(current, destination)
    assert state.transition(status, destination, NOW).state == destination


@pytest.mark.parametrize(
    "source", (S.FOUND, S.AWAITING_VERIFICATION, S.CONFIRMED, S.REAPPEARED, S.NEEDS_HUMAN, S.ERROR)
)
def test_entering_submitted_increments_and_stamps_once(source: S) -> None:
    prior = NOW - timedelta(days=4)
    result = state.transition(
        _status(source, attempts=3, last_submitted_at=prior), S.SUBMITTED, NOW
    )
    assert result.attempts == 4
    assert result.last_submitted_at == NOW


def test_transition_to_same_submitted_preserves_submission_fields() -> None:
    prior = NOW - timedelta(days=4)
    result = state.transition(
        _status(S.SUBMITTED, attempts=3, last_submitted_at=prior), S.SUBMITTED, NOW
    )
    assert result.attempts == 3
    assert result.last_submitted_at == prior


@pytest.mark.parametrize(
    "source", (S.AWAITING_VERIFICATION, S.CONFIRMED, S.REMOVED, S.NEEDS_HUMAN, S.ERROR)
)
def test_non_submission_transition_preserves_submission_fields(source: S) -> None:
    destination = S.NEEDS_HUMAN if source != S.NEEDS_HUMAN else S.ERROR
    prior = NOW - timedelta(days=4)
    result = state.transition(
        _status(source, attempts=3, last_submitted_at=prior), destination, NOW
    )
    assert result.attempts == 3
    assert result.last_submitted_at == prior


@pytest.mark.parametrize(
    "destination",
    (S.AWAITING_VERIFICATION, S.CONFIRMED, S.REMOVED, S.NEEDS_HUMAN, S.ERROR),
)
def test_submitted_state_transitions_preserve_submission_fields(destination: S) -> None:
    prior = NOW - timedelta(days=4)
    result = state.transition(
        _status(S.SUBMITTED, attempts=3, last_submitted_at=prior), destination, NOW
    )
    assert result.attempts == 3
    assert result.last_submitted_at == prior


@pytest.mark.parametrize("destination", [s for s in S if s not in (S.NEEDS_HUMAN, S.UNKNOWN)])
def test_leaving_needs_human_clears_reason(destination: S) -> None:
    result = state.transition(
        _status(S.NEEDS_HUMAN, needs_human_reason="synthetic review required"),
        destination,
        NOW,
    )
    assert result.needs_human_reason is None


def test_remaining_needs_human_preserves_reason() -> None:
    result = state.transition(
        _status(S.NEEDS_HUMAN, needs_human_reason="synthetic review required"),
        S.NEEDS_HUMAN,
        NOW,
    )
    assert result.needs_human_reason == "synthetic review required"


@pytest.mark.parametrize("destination", (S.REMOVED, S.NOT_FOUND))
def test_terminal_absence_resets_escalation_fields(destination: S) -> None:
    source = S.SUBMITTED if destination == S.REMOVED else S.FOUND
    result = state.transition(
        _status(source, escalation_level=3, last_escalated_at=NOW - timedelta(days=2)),
        destination,
        NOW,
    )
    assert result.escalation_level == 0
    assert result.last_escalated_at is None


@pytest.mark.parametrize("current", (S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED))
@pytest.mark.parametrize("level", range(5))
@pytest.mark.parametrize("processing_days", (0, 1, 14, 365))
def test_escalation_ladder_is_bounded_and_due_at_anchor_window(
    current: S, level: int, processing_days: int
) -> None:
    submitted = NOW - timedelta(days=500)
    escalated = submitted + timedelta(days=3) if level else None
    anchor = max(value for value in (submitted, escalated) if value is not None)
    broker = _broker(processing_days)
    due = anchor + state.escalation_window(broker)
    status = _status(
        current,
        last_submitted_at=submitted,
        escalation_level=level,
        last_escalated_at=escalated,
    )
    before = state.next_escalation(status, broker, due - timedelta(microseconds=1))
    assert before.action == Escalation.NONE
    decision = state.next_escalation(status, broker, due)
    assert decision.new_level >= status.escalation_level
    assert decision.new_level <= 4
    if decision.action != Escalation.NONE:
        assert decision.due_at is not None and decision.due_at >= due


@pytest.mark.parametrize(
    "current", [s for s in S if s not in (S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED)]
)
def test_no_escalation_action_outside_submitted_states(current: S) -> None:
    result = state.next_escalation(
        _status(
            current,
            last_submitted_at=NOW - timedelta(days=500),
            escalation_level=0,
        ),
        _broker(),
        NOW,
    )
    assert result.action == Escalation.NONE


@pytest.mark.parametrize("current", list(S))
@pytest.mark.parametrize("weekly", (False, True))
@pytest.mark.parametrize("processing_days", (0, 1, 3, 7, 14, 365))
@pytest.mark.parametrize("recheck_days", (1, 2, 7, 14, 365))
def test_next_check_is_future_and_weekly_states_are_capped(
    current: S, weekly: bool, processing_days: int, recheck_days: int
) -> None:
    result = state.next_check_at(
        _broker(processing_days, recheck_days), current, NOW, weekly=weekly
    )
    assert result > NOW
    if weekly and current in (S.FOUND, S.REAPPEARED, S.NEEDS_HUMAN):
        assert result <= NOW + timedelta(days=7)


@pytest.mark.parametrize("current", list(S))
def test_should_submit_only_for_found_and_reappeared(current: S) -> None:
    assert state.should_submit(current) is (current in (S.FOUND, S.REAPPEARED))
