"""engine/todo_cache.py: the runner's per-run to-do cache stays equal to the store.

Roadmap 0.7 (registry at scale): the run loop used to decrypt every to-do of the person once
per broker check. The cache must give exactly what `Store.list_todos` gives after any mix of
writes made through it. Fake people only.
"""
from __future__ import annotations

from datetime import timedelta

from freemyid.engine.todo_cache import TodoCachingStore
from freemyid.models import Todo, TodoKind, utcnow
from tests.conftest import make_profile


def _ids(todos: list[Todo]) -> list[str]:
    return [t.id for t in todos]


def _same(cache: TodoCachingStore, store, pid) -> None:
    for open_only in (True, False):
        assert _ids(cache.list_todos(pid, open_only=open_only)) == \
            _ids(store.list_todos(pid, open_only=open_only))


def test_cache_reads_once_then_tracks_writes(store, monkeypatch):
    a, b = make_profile(label="A"), make_profile(label="B")
    store.save_profile(a)
    store.save_profile(b)
    t0 = utcnow()
    first = Todo(profile_id=a.id, broker_id="fakee00001", kind=TodoKind.CAPTCHA,
                 title="Opt out", created_at=t0)
    store.save_todo(first)
    cache = TodoCachingStore(store)
    for pid in (a.id, b.id, None):
        _same(cache, store, pid)

    calls = []
    real = store.list_todos
    monkeypatch.setattr(store, "list_todos",
                        lambda *a, **k: calls.append(1) or real(*a, **k))
    cache.list_todos(a.id)
    cache.list_todos(a.id)
    assert calls == []            # served from memory

    new = Todo(profile_id=a.id, broker_id="fakew00002", kind=TodoKind.SEND_EMAIL_MANUALLY,
               title="Send letter", created_at=t0 + timedelta(seconds=5))
    cache.save_todo(new)
    other = Todo(profile_id=b.id, broker_id="fakew00002", kind=TodoKind.CAPTCHA,
                 title="Opt out", created_at=t0 + timedelta(seconds=6))
    cache.save_todo(other)
    older = Todo(profile_id=a.id, broker_id="fakew00003", kind=TodoKind.CAPTCHA,
                 title="Older", created_at=t0 - timedelta(hours=1))
    cache.save_todo(older)        # written out of order: the cache keeps created_at order
    done = cache.complete_todo(first.id)
    assert done is not None and done.done_at is not None
    cache.save_todo(new.model_copy(update={"title": "Send letter (edited)"}))
    assert cache.complete_todo("0" * 32) is None
    monkeypatch.setattr(store, "list_todos", real)
    for pid in (a.id, b.id, None):
        _same(cache, store, pid)
    assert [t.title for t in cache.list_todos(a.id)] == ["Older", "Send letter (edited)"]


def test_cache_passes_everything_else_through(store):
    cache = TodoCachingStore(store)
    p = make_profile()
    cache.save_profile(p)
    assert cache.get_profile(p.id) is not None
    assert cache.wrapped is store


def test_runner_uses_one_policy_and_cached_todos(store, fake_registry):
    from freemyid.engine.runner import Runner
    r = Runner(store, fake_registry, scan_only=True, dry_run=True, interactive=False,
               broker_ids=None, only_due=False, state_laws={})
    assert isinstance(r.store, TodoCachingStore)
    assert r.netpolicy() is r.netpolicy()
    p = make_profile()
    b = fake_registry.brokers[0]
    assert r._ctx(p, b).netpolicy is r._ctx(p, b).netpolicy
