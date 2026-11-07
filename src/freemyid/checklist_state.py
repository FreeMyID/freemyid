"""Done / not-done state of the identity-safety checklists, per person, in the encrypted store.

Shared by the CLI (`freemyid checklist ...`) and the dashboard ("Protect yourself").

Storage: a tick is an append-only, encrypted audit Event, actor USER, action
`checklist_done` or `checklist_undone`, detail {"checklist": <id>}, tagged with the
reserved broker_id `_checklist` so ticks can be read directly instead of by replaying
the whole event log (a busy log would otherwise push old ticks out of any replay window).
The newest event per checklist id wins. Untagged ticks written by the first dashboard
version (wizard/protect.py, broker_id None) are still read, from a bounded recent window.

No PII: checklist ids are public (brokers/checklists.yaml), never user text.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import Actor, Checklist, ChecklistFile, Event

log = logging.getLogger(__name__)

DONE, UNDONE = "checklist_done", "checklist_undone"
TAG = "_checklist"           # reserved Event.broker_id for ticks (never a real broker id)
_TAGGED_LIMIT = 100_000      # every tick ever made for one person; ticks are rare
_LEGACY_SCAN = 5000          # untagged ticks from the first dashboard version


@dataclass(frozen=True)
class Tick:
    done: bool
    at: datetime


def load_checklists() -> ChecklistFile | None:
    """The checklist file, or None if it is missing or invalid (logged, never raised)."""
    from . import checklists
    try:
        return checklists.load()
    except Exception as e:  # noqa: BLE001  a missing or bad file must not break the app
        log.warning("checklists unavailable: %s", type(e).__name__)
        return None


def ticks(store, profile_id: str) -> dict[str, Tick]:
    """checklist id -> newest Tick for this person."""
    tagged = store.events(profile_id, TAG, limit=_TAGGED_LIMIT)            # newest first
    legacy = [ev for ev in store.events(profile_id, limit=_LEGACY_SCAN) if ev.broker_id is None]
    evs = [ev for ev in [*reversed(legacy), *reversed(tagged)] if ev.action in (DONE, UNDONE)]
    out: dict[str, Tick] = {}
    for ev in sorted(evs, key=lambda e: e.ts):   # stable: oldest first, newest overwrites
        cid = ev.detail.get("checklist")
        if isinstance(cid, str) and cid:
            out[cid] = Tick(ev.action == DONE, ev.ts)
    return out


def progress(store, profile_id: str) -> dict[str, bool]:
    """checklist id -> done (same shape as wizard/protect.progress)."""
    return {cid: t.done for cid, t in ticks(store, profile_id).items()}


def set_done(store, profile_id: str, checklist_id: str, done: bool,
             checklists: ChecklistFile | None = None) -> bool:
    """Record a tick. False (nothing written) for an unknown checklist id or no file."""
    cf = checklists if checklists is not None else load_checklists()
    if cf is None or checklist_id not in {c.id for c in cf.checklists}:
        return False
    store.log(Event(profile_id=profile_id, broker_id=TAG, actor=Actor.USER,
                    action=DONE if done else UNDONE, detail={"checklist": checklist_id}))
    return True


def counts(store, profile_id: str, checklists: ChecklistFile | None = None) -> tuple[int, int]:
    """(done, total) over the current checklist file."""
    cf = checklists if checklists is not None else load_checklists()
    if cf is None:
        return 0, 0
    prog = progress(store, profile_id)
    return sum(1 for c in cf.checklists if prog.get(c.id)), len(cf.checklists)


# --------------------------------------------------------------------------- JSON documents
# docs/CLI.md style: one object per document with "schema": "<name>/1".


def item_doc(c: Checklist, tick: Tick | None, *, full: bool = False) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": c.id, "title": c.title, "done": bool(tick and tick.done),
        "done_at": tick.at.isoformat() if tick and tick.done else None,
        "url": str(c.url), "cost": c.cost, "time_needed": c.time_needed,
    }
    if full:
        d.update({
            "why": c.why, "need_on_hand": list(c.need_on_hand), "steps": list(c.steps),
            "how_to_undo": c.how_to_undo, "source_urls": [str(u) for u in c.source_urls],
            "date_checked": c.date_checked.isoformat(), "verification": c.verification,
            "notes": c.notes, "status_note": c.status_note,
        })
    return d


def list_doc(cf: ChecklistFile, tk: dict[str, Tick], profile_id: str | None) -> dict[str, Any]:
    items = [item_doc(c, tk.get(c.id)) for c in cf.checklists]
    return {"schema": "checklists/1", "version": cf.version, "profile_id": profile_id,
            "done": sum(1 for i in items if i["done"]), "total": len(items),
            "checklists": items}


def show_doc(c: Checklist, tick: Tick | None, profile_id: str | None) -> dict[str, Any]:
    return {"schema": "checklist/1", "profile_id": profile_id,
            **item_doc(c, tick, full=True)}
