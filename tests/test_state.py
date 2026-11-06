"""State machine + escalation ladder (pure functions)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vanish import state
from vanish.models import Broker, BrokerStatus
from vanish.models import ListingState as S
from vanish.state import Escalation

NOW = datetime(2026, 11, 5, 12, tzinfo=UTC)


def _broker(days=30):
    return Broker(id="fakeb", name="F", url="https://fakeb.example/", category="people_search",
                  domains=["fakeb.example"], method="web_form",
                  opt_out_url="https://fakeb.example/o", typical_processing_days=days)


def _st(s=S.UNKNOWN, **kw):
    return BrokerStatus(profile_id="a" * 32, broker_id="fakeb", state=s, **kw)


@pytest.mark.parametrize("src,dst,ok", [
    (S.UNKNOWN, S.FOUND, True), (S.UNKNOWN, S.SUBMITTED, False),
    (S.FOUND, S.SUBMITTED, True), (S.NOT_FOUND, S.SUBMITTED, False),
    (S.REMOVED, S.REAPPEARED, True), (S.REMOVED, S.SUBMITTED, False),
    (S.REAPPEARED, S.SUBMITTED, True), (S.CONFIRMED, S.REMOVED, True),
    (S.FOUND, S.NEEDS_HUMAN, True), (S.REMOVED, S.ERROR, True),
    (S.NEEDS_HUMAN, S.FOUND, True), (S.ERROR, S.UNKNOWN, False),
])
def test_can_transition(src, dst, ok):
    assert state.can_transition(src, dst) is ok


def test_transition_rejects_illegal():
    with pytest.raises(state.TransitionError):
        state.transition(_st(S.UNKNOWN), S.SUBMITTED, NOW)


def test_submit_sets_attempts_and_timestamp():
    st = state.transition(_st(S.FOUND), S.SUBMITTED, NOW)
    assert st.attempts == 1 and st.last_submitted_at == NOW and st.updated_at == NOW


def test_removed_resets_ladder_and_needs_human_reason():
    st = _st(S.SUBMITTED, escalation_level=3, last_escalated_at=NOW,
             needs_human_reason="captcha", last_submitted_at=NOW)
    out = state.transition(st, S.REMOVED, NOW)
    assert out.escalation_level == 0 and out.last_escalated_at is None
    assert out.needs_human_reason is None


@pytest.mark.parametrize("src,found,expect", [
    (S.UNKNOWN, True, S.FOUND), (S.UNKNOWN, False, S.NOT_FOUND),
    (S.REMOVED, True, S.REAPPEARED), (S.REMOVED, False, S.REMOVED),
    (S.SUBMITTED, False, S.REMOVED), (S.CONFIRMED, False, S.REMOVED),
    (S.FOUND, False, S.NOT_FOUND), (S.REAPPEARED, False, S.REMOVED),
])
def test_after_scan(src, found, expect):
    assert state.after_scan(_st(src), found, NOW) == expect


def test_should_submit():
    assert state.should_submit(S.FOUND) and state.should_submit(S.REAPPEARED)
    assert not state.should_submit(S.SUBMITTED) and not state.should_submit(S.NEEDS_HUMAN)


def test_escalation_ladder_walk():
    b = _broker(30)
    win = state.escalation_window(b)
    assert win == timedelta(days=45)
    st = _st(S.SUBMITTED, last_submitted_at=NOW)
    assert state.next_escalation(st, b, NOW + win - timedelta(seconds=1)).action == Escalation.NONE
    t = NOW + win
    seen = []
    for _ in range(4):
        d = state.next_escalation(st, b, t)
        seen.append(d.action)
        assert d.due_at == t
        st = st.model_copy(update={"escalation_level": d.new_level, "last_escalated_at": t})
        t = t + win
    assert seen == [Escalation.RESUBMIT, Escalation.FOLLOW_UP, Escalation.LEGAL_DEMAND,
                    Escalation.COMPLAINT]
    assert state.next_escalation(st, b, t + win * 10).action == Escalation.NONE


@pytest.mark.parametrize("s", [S.FOUND, S.REMOVED, S.NEEDS_HUMAN, S.NOT_FOUND])
def test_no_escalation_outside_submitted_states(s):
    st = _st(s, last_submitted_at=NOW - timedelta(days=400))
    assert state.next_escalation(st, _broker(), NOW).action == Escalation.NONE


def test_next_check_at_bounds():
    b = _broker(30)
    assert state.next_check_at(b, S.SUBMITTED, NOW) == NOW + timedelta(days=14)
    assert state.next_check_at(_broker(1), S.SUBMITTED, NOW) == NOW + timedelta(days=3)
    assert state.next_check_at(b, S.REMOVED, NOW) == NOW + timedelta(days=30)
    assert state.next_check_at(b, S.FOUND, NOW) == NOW + timedelta(days=7)


# ---- findings ----

def test_rescan_does_not_reset_escalation_anchor():
    b = _broker(30)
    st = _st(S.SUBMITTED, last_submitted_at=NOW, attempts=1)
    t = NOW
    for _ in range(10):                    # weekly-ish rescans, listing still visible
        t += timedelta(days=7)
        dst = state.after_scan(st, True, t)
        st = state.transition(st, dst, t)
    assert st.attempts == 1
    assert state.next_escalation(st, b, t).action == Escalation.RESUBMIT


def test_needs_human_rescan_reenters_submit_path():
    st = _st(S.NEEDS_HUMAN, last_submitted_at=NOW - timedelta(days=60))
    assert state.should_submit(state.after_scan(st, True, NOW))


def test_not_found_after_prior_submission_is_legal():
    st = _st(S.NOT_FOUND, last_submitted_at=NOW - timedelta(days=60))
    dst = state.after_scan(st, True, NOW)
    state.transition(st, dst, NOW)
