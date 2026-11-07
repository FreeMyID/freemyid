"""'Protect yourself' checklists: ticks kept per person in the encrypted store.

A tick is an append-only, encrypted audit Event (actor USER, action checklist_done or
checklist_undone, detail = {"checklist": id}). The latest event per checklist wins. No new table,
no PII. Checklist ids are public (brokers/checklists.yaml), never user text.
"""
from __future__ import annotations

import logging

from ..models import Actor, ChecklistFile, Event

log = logging.getLogger(__name__)
DONE, UNDONE = "checklist_done", "checklist_undone"
_SCAN = 5000   # newest events to replay; ticks are rare so this covers a long history


def load_checklists() -> ChecklistFile | None:
    from .. import checklists
    try:
        return checklists.load()
    except Exception as e:  # noqa: BLE001  missing or invalid file must not break the app
        log.warning("checklists unavailable: %s", type(e).__name__)
        return None


def progress(store, profile_id: str) -> dict[str, bool]:
    """checklist id -> done, from the newest event per id."""
    seen: dict[str, bool] = {}
    for ev in store.events(profile_id, limit=_SCAN):      # newest first
        if ev.action not in (DONE, UNDONE):
            continue
        cid = str(ev.detail.get("checklist", ""))
        if cid and cid not in seen:
            seen[cid] = ev.action == DONE
    return seen


def set_done(store, profile_id: str, checklist_id: str, done: bool) -> bool:
    """Record a tick. Returns False for an unknown checklist id (nothing is written)."""
    cf = load_checklists()
    if cf is None or checklist_id not in {c.id for c in cf.checklists}:
        return False
    store.log(Event(profile_id=profile_id, actor=Actor.USER, action=DONE if done else UNDONE,
                    detail={"checklist": checklist_id}))
    return True


def counts(store, profile_id: str) -> tuple[int, int]:
    """(done, total) over the current checklist file."""
    cf = load_checklists()
    if cf is None:
        return 0, 0
    prog = progress(store, profile_id)
    return sum(1 for c in cf.checklists if prog.get(c.id)), len(cf.checklists)
