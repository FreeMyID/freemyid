"""'Protect yourself' checklists: ticks kept per person in the encrypted store.

Delegates to freemyid.checklist_state, which tags ticks with the reserved
broker_id '_checklist' and reads both tagged and legacy untagged ticks.
Checklist ids are public (brokers/checklists.yaml), never user text.
"""
from __future__ import annotations

from .. import checklist_state as cs
from ..models import ChecklistFile

DONE, UNDONE = cs.DONE, cs.UNDONE
TAG = cs.TAG


def load_checklists() -> ChecklistFile | None:
    """The checklist file, or None if it is missing or invalid (logged, never raised)."""
    return cs.load_checklists()


def progress(store, profile_id: str) -> dict[str, bool]:
    """checklist id -> done (same shape as checklist_state.progress)."""
    return cs.progress(store, profile_id)


def set_done(store, profile_id: str, checklist_id: str, done: bool) -> bool:
    """Record a tick. Returns False for an unknown checklist id (nothing is written)."""
    return cs.set_done(store, profile_id, checklist_id, done)


def counts(store, profile_id: str) -> tuple[int, int]:
    """(done, total) over the current checklist file."""
    return cs.counts(store, profile_id)

