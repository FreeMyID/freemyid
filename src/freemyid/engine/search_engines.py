"""Search-engine exposure: a guided step, never a scraper (ROADMAP 3.2, docs/EXPOSURE.md).

Google and Bing can keep showing pages about a person, even after a people-search site has
removed the listing. Their terms forbid automated searching, and it would be blocked anyway,
so Free My ID never queries them. Instead this module:

* names the search-engine checklists (public entries in brokers/checklists.yaml, loaded
  with `checklists.load` through `checklist_state`), in a fixed order;
* opens the official page for the user (`open_step`), only if the checklist URL is https
  and on that engine's own hosts, and records WHEN it was opened;
* records WHEN the user says they did it, with the normal checklist tick
  (`checklist_state.set_done`), so the Protect page and `freemyid checklist` show it too;
* says "do it again" for Bing when a broker listing was removed after the last tick, because
  Bing may still show the old copy of the removed page.

Storage: append-only USER Events under the reserved broker_id `_checklist`
(`checklist_state.TAG`), detail {"checklist": <public id>} only. No search terms, no URLs
typed by the user, nothing about what Google or Bing showed.
"""
from __future__ import annotations

import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from .. import checklist_state as cs
from ..models import Actor, Checklist, ChecklistFile, Event, ListingState

OPENED = "search_step_opened"

INTRO = ("Google and Bing can show pages about you, even after a people-search site removes "
         "your listing. Free My ID does not search Google or Bing for you: their rules do not "
         "allow automatic searches. We open their own official page, and you do the steps "
         "there. When you have finished, tick \"I did this\" so we remember the date.")


@dataclass(frozen=True)
class EngineStep:
    checklist_id: str            # id in brokers/checklists.yaml
    engine: str                  # shown to the user
    hosts: frozenset[str]        # the checklist URL must be on one of these (https)
    why_now: str                 # one plain sentence, shown above the checklist steps
    redo_after_removal: bool     # "do it again" when a listing was removed after the tick


STEPS: tuple[EngineStep, ...] = (
    EngineStep(
        "google_results_about_you", "Google",
        frozenset({"goo.gle", "myactivity.google.com", "support.google.com"}),
        "Google's free tool watches for your phone number, home address and email, and lets "
        "you ask Google to stop showing those results.",
        redo_after_removal=False),       # Google's tool keeps watching on its own
    EngineStep(
        "bing_content_removal", "Bing",
        frozenset({"www.bing.com", "bing.com", "www.microsoft.com"}),
        "After a people-search site removes your page, Bing can keep showing the old copy for "
        "a while. Bing's form asks Bing to look at the page again and drop the old copy.",
        redo_after_removal=True),
)
_BY_ID = {s.checklist_id: s for s in STEPS}

StepStatus = Literal["not_started", "opened", "done", "do_again"]
STATUS_TEXT: dict[str, str] = {
    "not_started": "Not done yet.",
    "opened": "You opened the page. Tick \"I did this\" when you have finished.",
    "done": "Done.",
    "do_again": "A site removed your listing since you last did this. Please do it again "
                "so the search engine drops the old page.",
}


@dataclass(frozen=True)
class GuidedStep:
    step: EngineStep
    checklist: Checklist
    status: StepStatus
    opened_at: datetime | None
    done_at: datetime | None


def is_search_step(checklist_id: str) -> bool:
    return checklist_id in _BY_ID


def official_url(step: EngineStep, c: Checklist) -> str | None:
    """The checklist URL if it is https on the engine's own hosts, else None (never opened)."""
    from ..netpolicy import host_of
    url = str(c.url)
    host = host_of(url)
    if not url.lower().startswith("https://") or host is None or host not in step.hosts:
        return None
    return url


def _opened_times(store: Any, profile_id: str) -> dict[str, datetime]:
    out: dict[str, datetime] = {}
    for ev in store.events(profile_id, cs.TAG, limit=10_000):      # newest first
        cid = ev.detail.get("checklist")
        if ev.action == OPENED and isinstance(cid, str) and cid not in out:
            out[cid] = ev.ts
    return out


def _last_removal(store: Any, profile_id: str) -> datetime | None:
    times = [st.updated_at for st in store.list_statuses(profile_id)
             if st.state == ListingState.REMOVED]
    return max(times) if times else None


def guided_steps(store: Any, profile_id: str,
                 cf: ChecklistFile | None = None) -> list[GuidedStep]:
    """The search-engine steps that exist in the checklist file, in STEPS order, with when
    they were opened and done. Missing or invalid file: an empty list (never raises)."""
    cf = cf if cf is not None else cs.load_checklists()
    if cf is None:
        return []
    by_id = {c.id: c for c in cf.checklists}
    ticks = cs.ticks(store, profile_id)
    opened = _opened_times(store, profile_id)
    removed = _last_removal(store, profile_id)
    out: list[GuidedStep] = []
    for s in STEPS:
        c = by_id.get(s.checklist_id)
        if c is None or official_url(s, c) is None:
            continue
        tick = ticks.get(s.checklist_id)
        done_at = tick.at if tick and tick.done else None
        o = opened.get(s.checklist_id)
        status: StepStatus
        if done_at is not None:
            status = ("do_again" if s.redo_after_removal and removed and removed > done_at
                      else "done")
        else:
            status = "opened" if o is not None else "not_started"
        out.append(GuidedStep(s, c, status, o, done_at))
    return out


def open_step(store: Any, profile_id: str, checklist_id: str,
              opener: Callable[[str], Any] = webbrowser.open,
              cf: ChecklistFile | None = None) -> bool:
    """Open the official page in the user's browser and record when. False (nothing opened,
    nothing written) for an unknown id, a missing entry or a URL off the engine's hosts."""
    step = _BY_ID.get(checklist_id)
    cf = cf if cf is not None else cs.load_checklists()
    if step is None or cf is None:
        return False
    c = next((c for c in cf.checklists if c.id == checklist_id), None)
    url = official_url(step, c) if c is not None else None
    if url is None:
        return False
    opener(url)
    store.log(Event(profile_id=profile_id, broker_id=cs.TAG, actor=Actor.USER,
                    action=OPENED, detail={"checklist": checklist_id}))
    return True


def mark_done(store: Any, profile_id: str, checklist_id: str, done: bool = True,
              cf: ChecklistFile | None = None) -> bool:
    """Record that the user did (or undid) the step: the normal checklist tick."""
    if not is_search_step(checklist_id):
        return False
    return cs.set_done(store, profile_id, checklist_id, done, checklists=cf)


def pending(steps: list[GuidedStep]) -> int:
    """How many steps still need the user (not started, opened only, or do again)."""
    return sum(1 for g in steps if g.status != "done")


def doc(steps: list[GuidedStep], profile_id: str) -> dict[str, Any]:
    """JSON document `search_engines/1` (docs/CLI.md style). Public data and dates only."""
    return {
        "schema": "search_engines/1", "profile_id": profile_id, "intro": INTRO,
        "pending": pending(steps),
        "steps": [{
            "id": g.checklist.id, "engine": g.step.engine, "title": g.checklist.title,
            "why_now": g.step.why_now, "url": str(g.checklist.url),
            "status": g.status, "status_text": STATUS_TEXT[g.status],
            "opened_at": g.opened_at.isoformat() if g.opened_at else None,
            "done_at": g.done_at.isoformat() if g.done_at else None,
            "steps": list(g.checklist.steps), "tips": list(g.checklist.tips),
        } for g in steps],
    }
