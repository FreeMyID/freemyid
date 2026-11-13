"""Per-run to-do cache for the runner (roadmap 0.7 "Registry at scale").

The run loop asks "does this site already have an open to-do?" several times per broker
(`_open_human_todo`, `_open_manual_letter`, `_id_hold`, `_escalation_waiting`,
`handoff.persist_todo`). `Store.list_todos` has no broker filter, so every one of those
calls decrypted every to-do of the person: with 1,000 brokers that was about a million
decrypts per run (measured 11.5 s of a 15.7 s run).

`TodoCachingStore` wraps the store. Only inside `with cache.cached():` (the runner's
broker loop for one person) the first `list_todos(pid, open_only)` reads the table once,
and every to-do written through the wrapper (`save_todo`, `complete_todo`) updates the
cached copy in place, so later reads cost a dict copy instead of a full decrypt. Outside
that block, and for everything else, calls go straight to the real store.

Writers outside the loop (the dashboard completing a to-do while a run is going) are not
seen until the loop ends. That is the cautious direction: the runner may keep a site waiting
on a to-do that was just done, never send a request the person still has to act on.
The real fix is a broker filter on `Store.list_todos` (change request, roadmap 0.7).
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models import Todo
    from ..storage import Store

_Key = tuple[str | None, bool]


class TodoCachingStore:
    """A Store view whose `list_todos` is served from memory after the first read."""

    def __init__(self, store: Store) -> None:
        self._store = store
        # (profile_id or None, open_only) -> todo id -> Todo, in created_at order
        self._cache: dict[_Key, dict[str, Todo]] = {}
        self._depth = 0

    @contextmanager
    def cached(self) -> Iterator[None]:
        """Serve list_todos from memory inside this block; start and end with a clean read."""
        if self._depth == 0:
            self._cache.clear()
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
            if self._depth == 0:
                self._cache.clear()

    @property
    def wrapped(self) -> Store:
        return self._store

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)

    def list_todos(self, pid: str | None = None, open_only: bool = True) -> list[Todo]:
        if not self._depth:
            return self._store.list_todos(pid, open_only=open_only)
        key = (pid, open_only)
        rows = self._cache.get(key)
        if rows is None:
            rows = {t.id: t for t in self._store.list_todos(pid, open_only=open_only)}
            self._cache[key] = rows
        return list(rows.values())

    def save_todo(self, t: Todo) -> None:
        self._store.save_todo(t)
        self._apply(t)

    def complete_todo(self, tid: str) -> Todo | None:
        t = self._store.complete_todo(tid)
        if t is not None:
            self._apply(t)
        return t

    def delete_profile(self, pid: str) -> None:
        self._cache.clear()
        self._store.delete_profile(pid)

    def _apply(self, t: Todo) -> None:
        for (pid, open_only), rows in self._cache.items():
            if pid is not None and pid != t.profile_id:
                continue
            if open_only and t.done_at is not None:
                rows.pop(t.id, None)
                continue
            if t.id in rows:
                rows[t.id] = t          # same key keeps its place in the order
                continue
            last = next(reversed(rows.values()), None)
            rows[t.id] = t
            if last is not None and t.created_at < last.created_at:
                ordered = sorted(rows.values(), key=lambda x: x.created_at)
                rows.clear()
                rows.update((x.id, x) for x in ordered)
