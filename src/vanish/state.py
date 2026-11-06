"""Per (profile, broker) state machine and escalation policy.

OWNER: orchestrator. Pure functions only: no I/O, fully deterministic, easy to test.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from .models import Broker, BrokerStatus
from .models import ListingState as S

GRACE_DAYS = 15

# Allowed transitions. NEEDS_HUMAN and ERROR are reachable from anywhere and can return to
# any non-terminal state once resolved, so they are handled in `can_transition`.
TRANSITIONS: dict[S, set[S]] = {
    S.UNKNOWN: {S.NOT_FOUND, S.FOUND},
    S.NOT_FOUND: {S.NOT_FOUND, S.FOUND, S.REAPPEARED},
    S.FOUND: {S.FOUND, S.SUBMITTED, S.NOT_FOUND},
    S.SUBMITTED: {S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED, S.REMOVED},
    S.AWAITING_VERIFICATION: {S.AWAITING_VERIFICATION, S.CONFIRMED, S.SUBMITTED, S.REMOVED},
    S.CONFIRMED: {S.CONFIRMED, S.REMOVED, S.SUBMITTED},
    S.REMOVED: {S.REMOVED, S.REAPPEARED},
    S.REAPPEARED: {S.REAPPEARED, S.SUBMITTED, S.REMOVED},
}
_ANYWHERE = {S.NEEDS_HUMAN, S.ERROR}


class TransitionError(ValueError):
    pass


def can_transition(src: S, dst: S) -> bool:
    if dst in _ANYWHERE:
        return True
    if src in _ANYWHERE:
        return dst != S.UNKNOWN
    return dst in TRANSITIONS.get(src, set())


def transition(status: BrokerStatus, dst: S, now: datetime) -> BrokerStatus:
    """Move to `dst`. Entering SUBMITTED from another state counts as a send.

    A rescan that leaves the state unchanged (SUBMITTED -> SUBMITTED) does NOT re-stamp
    `last_submitted_at`/`attempts`, otherwise escalation would never become due (SEC-01).
    A real resubmission of an already-SUBMITTED listing must call `mark_submitted`.
    """
    if not can_transition(status.state, dst):
        raise TransitionError(f"{status.state} -> {dst} not allowed")
    upd = status.model_copy(update={"state": dst, "updated_at": now})
    if dst == S.SUBMITTED and status.state != S.SUBMITTED:
        upd.last_submitted_at = now
        upd.attempts = status.attempts + 1
    if dst != S.NEEDS_HUMAN:
        upd.needs_human_reason = None
    if dst in (S.REMOVED, S.NOT_FOUND):
        upd.escalation_level = 0
        upd.last_escalated_at = None
    return upd


def mark_submitted(status: BrokerStatus, now: datetime) -> BrokerStatus:
    """Record a real send (first submission or resubmission). Call only after a send succeeded."""
    if not can_transition(status.state, S.SUBMITTED):
        raise TransitionError(f"{status.state} -> {S.SUBMITTED} not allowed")
    return status.model_copy(update={
        "state": S.SUBMITTED, "updated_at": now, "last_submitted_at": now,
        "attempts": status.attempts + 1, "needs_human_reason": None,
    })


def after_scan(status: BrokerStatus, found: bool, now: datetime) -> S:
    """Which state a scan result moves us to (caller then calls `transition`)."""
    st = status.state
    if st in (S.UNKNOWN, S.NOT_FOUND, S.ERROR, S.NEEDS_HUMAN) and status.last_submitted_at is None:
        return S.FOUND if found else S.NOT_FOUND
    if st == S.REMOVED:
        return S.REAPPEARED if found else S.REMOVED
    if st in (S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED):
        return st if found else S.REMOVED
    if st == S.REAPPEARED:
        return S.REAPPEARED if found else S.REMOVED
    if st == S.FOUND:
        return S.FOUND if found else S.NOT_FOUND
    # NOT_FOUND / NEEDS_HUMAN / ERROR after a prior submission: a listing that is visible
    # again goes back on the submit path (nothing was sent from these states).
    if found:
        return S.REAPPEARED
    return S.NOT_FOUND if st == S.NOT_FOUND else S.REMOVED


def should_submit(state: S) -> bool:
    return state in (S.FOUND, S.REAPPEARED)


# --------------------------------------------------------------------------- escalation


class Escalation(StrEnum):
    NONE = "none"
    RESUBMIT = "resubmit"            # level 1
    FOLLOW_UP = "follow_up"          # level 2 (state-law follow-up email)
    LEGAL_DEMAND = "legal_demand"    # level 3 (formal demand email, always needs approval)
    COMPLAINT = "complaint"          # level 4 (todo with AG / CPPA links)


_LADDER = [Escalation.RESUBMIT, Escalation.FOLLOW_UP, Escalation.LEGAL_DEMAND, Escalation.COMPLAINT]


@dataclass(frozen=True)
class EscalationDecision:
    action: Escalation
    new_level: int
    due_at: datetime | None   # when this step became due (None if nothing to do)


def escalation_window(broker: Broker) -> timedelta:
    return timedelta(days=broker.typical_processing_days + GRACE_DAYS)


def next_escalation(status: BrokerStatus, broker: Broker, now: datetime) -> EscalationDecision:
    """If a submitted request has been ignored, decide the next step.

    Rung n+1 becomes due one window (processing days + 15) after the later of the last
    submission and the last escalation. Caller applies the decision and sets
    `escalation_level=new_level, last_escalated_at=now`. Removal resets the ladder.
    """
    if status.state not in (S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED):
        return EscalationDecision(Escalation.NONE, status.escalation_level, None)
    if status.last_submitted_at is None or status.escalation_level >= len(_LADDER):
        return EscalationDecision(Escalation.NONE, status.escalation_level, None)
    anchor = max(t for t in (status.last_submitted_at, status.last_escalated_at) if t)
    due = anchor + escalation_window(broker)
    if now < due:
        return EscalationDecision(Escalation.NONE, status.escalation_level, None)
    return EscalationDecision(_LADDER[status.escalation_level], status.escalation_level + 1, due)


def next_check_at(broker: Broker, state: S, now: datetime, weekly: bool = True) -> datetime:
    """When this broker should next be scanned for this profile."""
    if state in (S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED):
        days = max(3, min(broker.typical_processing_days, 14))
    elif state in (S.REMOVED, S.NOT_FOUND):
        days = broker.recheck_interval_days
    else:
        days = 7
    if weekly:
        days = min(days, 7) if state in (S.FOUND, S.REAPPEARED, S.NEEDS_HUMAN) else days
    return now + timedelta(days=days)
