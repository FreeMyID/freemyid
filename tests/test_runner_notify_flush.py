"""PR #110 (WO-333) follow-up: the runner closes the throttled notifier at the end of a run.

Without this, the end-of-run notice was swallowed by the throttle on an interactive run, and a
held count could claim things "need you" after the person had finished them. Fake people only.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from freemyid import notify
from freemyid.engine.runner import Runner
from freemyid.models import Todo, TodoKind

T0 = datetime(2026, 11, 1, tzinfo=UTC)


class Rec:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.calls.append((title, body, url))


@pytest.fixture(autouse=True)
def _reset_window():
    notify.ThrottledNotifier._shared_started_at = None
    yield
    notify.ThrottledNotifier._shared_started_at = None


def _runner(store, fake_registry, notifier) -> Runner:
    return Runner(store, fake_registry, scan_only=False, dry_run=True, interactive=True,
                  broker_ids=None, only_due=False, notifier=notifier, now=T0)


def _todo(profile, broker_id: str) -> Todo:
    return Todo(profile_id=profile.id, broker_id=broker_id, kind=TodoKind.ASSISTED_OPT_OUT,
                title="t", body="b")


def test_end_of_run_notice_is_not_swallowed(store, fake_registry, profile) -> None:
    store.save_profile(profile)
    for broker_id in ("fakea", "fakeb", "fakec"):
        store.save_todo(_todo(profile, broker_id))
    rec = Rec()
    wrapped = notify.ThrottledNotifier(rec, now=lambda: T0)
    # Per-to-do notices during the run: first goes out, the rest are held.
    wrapped.notify("Free My ID needs you", "first")
    wrapped.notify("Free My ID needs you", "held")
    runner = _runner(store, fake_registry, wrapped)
    runner._finish([profile])
    assert len(rec.calls) == 2
    title, body, url = rec.calls[1]
    assert title == "Free My ID needs 5 minutes of your help"
    assert body == "3 things need you. Open Free My ID to see them."   # the real count
    assert url is None
    assert "Jane" not in title + body and "fakea" not in title + body
    wrapped.flush()                                                   # nothing left held
    assert len(rec.calls) == 2


def test_nothing_left_open_drops_the_held_count(store, fake_registry, profile) -> None:
    store.save_profile(profile)
    rec = Rec()
    wrapped = notify.ThrottledNotifier(rec, now=lambda: T0)
    wrapped.notify("Free My ID needs you", "first")
    wrapped.notify("Free My ID needs you", "held")                    # done during the run
    _runner(store, fake_registry, wrapped)._finish([profile])
    wrapped.flush()
    assert [c[1] for c in rec.calls] == ["first"]                     # no stale "1 thing"


def test_failed_run_still_shows_the_held_count(store, fake_registry, profile,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    store.save_profile(profile)
    rec = Rec()
    wrapped = notify.ThrottledNotifier(rec, now=lambda: T0)
    runner = _runner(store, fake_registry, wrapped)

    async def boom(_p) -> None:
        wrapped.notify("Free My ID needs you", "first")
        wrapped.notify("Free My ID needs you", "held")
        raise RuntimeError("profile failed")

    monkeypatch.setattr(runner, "run_profile", boom)
    monkeypatch.setattr("freemyid.engine.runner.consent_ok", lambda p, s: (True, ""))
    with pytest.raises(RuntimeError):
        asyncio.run(runner.run([profile]))
    assert [c[0] for c in rec.calls] == ["Free My ID needs you", "Free My ID: 1 thing needs you"]


def test_plain_notifier_still_gets_the_end_of_run_notice(store, fake_registry, profile) -> None:
    store.save_profile(profile)
    store.save_todo(_todo(profile, "fakea"))
    rec = Rec()
    _runner(store, fake_registry, rec)._finish([profile])
    assert rec.calls == [("Free My ID needs 5 minutes of your help",
                          "1 thing needs you. Open Free My ID to see it.", None)]


def test_no_notifier_is_built_when_nothing_was_said(store, fake_registry, profile,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    store.save_profile(profile)

    def no_build():
        raise AssertionError("a notifier was built for an empty run")

    monkeypatch.setattr("freemyid.engine.handoff.get_notifier", no_build)
    _runner(store, fake_registry, None)._finish([profile])
