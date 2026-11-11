"""WO-333: one summary instead of a burst, and a monthly marker that survives a bad home."""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
from datetime import UTC, datetime, timedelta

import pytest

from freemyid import notify
from freemyid.engine.handoff import GENERIC_HELP, QueuedHandoff
from freemyid.engine.handoff import get_notifier as handoff_notifier
from freemyid.models import Todo, TodoKind, new_id

T0 = datetime(2026, 11, 1, tzinfo=UTC)
POISON = (
    "Jane Q Testperson",
    "Springfield",
    "peoplesearch.example",
    "https://peoplesearch.example/listing",
    "jane.testperson@example.com",
)


class Rec:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.calls.append((title, body, url))


class Clock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **delta: int) -> None:
        self.moment += timedelta(**delta)


class EmptyStore:
    def list_requests(self, status: object = None) -> list[object]:
        return []

    def list_statuses(self) -> list[object]:
        return []

    def list_todos(self) -> list[object]:
        return []


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any accidental socket use fails the test. No real network."""
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise OSError("network blocked by test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture(autouse=True)
def _reset_notice_window():
    notify.ThrottledNotifier._shared_started_at = None
    yield
    notify.ThrottledNotifier._shared_started_at = None


def test_network_is_blocked() -> None:
    sock = socket.socket()
    try:
        with pytest.raises(OSError, match="network blocked by test"):
            sock.connect(("127.0.0.1", 1))
    finally:
        sock.close()
    with pytest.raises(OSError, match="network blocked by test"):
        socket.create_connection(("127.0.0.1", 1))


def test_first_goes_out_and_four_later_ones_become_one_summary() -> None:
    rec = Rec()
    wrapper = notify.ThrottledNotifier(rec, now=Clock(T0))
    wrapper.notify("Free My ID needs you", "Free My ID needs your help with 1 site.", None)
    # Four held notices, together carrying every poisoned detail. The summary must drop them.
    wrapper.notify(POISON[0], POISON[1])
    wrapper.notify(POISON[2], POISON[3])
    wrapper.notify(POISON[4], "still held")
    wrapper.notify("one more", "still held")
    assert rec.calls == [("Free My ID needs you", "Free My ID needs your help with 1 site.", None)]
    wrapper.flush()
    assert len(rec.calls) == 2
    title, body, url = rec.calls[1]
    assert title == "Free My ID: 4 things need you"
    assert body == "4 things need you. Open Free My ID to see them."
    assert url is None
    for poison in POISON:
        assert poison not in title and poison not in body
    wrapper.flush()
    assert len(rec.calls) == 2


def test_one_held_notice_is_singular_and_has_no_site() -> None:
    rec = Rec()
    wrapper = notify.ThrottledNotifier(rec, now=Clock(T0))
    wrapper.notify("Free My ID needs you", GENERIC_HELP)
    wrapper.notify("peoplesearch.example", "Jane Q Testperson in Springfield")
    wrapper.flush()
    title, body, url = rec.calls[1]
    assert title == "Free My ID: 1 thing needs you"
    assert body == "1 thing needs you. Open Free My ID to see it."
    assert url is None
    assert "peoplesearch.example" not in title + body
    assert "Jane" not in title + body
    assert "Springfield" not in title + body


def test_flush_with_nothing_held_sends_nothing() -> None:
    rec = Rec()
    wrapper = notify.ThrottledNotifier(rec, now=Clock(T0))
    wrapper.flush()
    wrapper.notify("Free My ID needs you", GENERIC_HELP)
    wrapper.flush()
    assert rec.calls == [("Free My ID needs you", GENERIC_HELP, None)]


def test_same_run_still_counts_after_the_window() -> None:
    assert notify.ThrottledNotifier.window == timedelta(minutes=10)
    rec = Rec()
    clock = Clock(T0)
    wrapper = notify.ThrottledNotifier(rec, now=clock)
    wrapper.notify("Free My ID needs you", GENERIC_HELP)
    clock.advance(minutes=30)
    wrapper.notify("peoplesearch.example", "still this run")
    assert len(rec.calls) == 1
    wrapper.flush()
    assert rec.calls[1][0] == "Free My ID: 1 thing needs you"
    assert "peoplesearch.example" not in rec.calls[1][1]


def test_within_10_minutes_after_flush_still_counts() -> None:
    rec = Rec()
    clock = Clock(T0)
    wrapper = notify.ThrottledNotifier(rec, now=clock)
    wrapper.notify("Free My ID needs you", GENERIC_HELP)
    wrapper.flush()
    clock.advance(minutes=9, seconds=59)
    wrapper.notify("peoplesearch.example", "too soon")
    assert len(rec.calls) == 1
    wrapper.flush()
    assert rec.calls[1][0] == "Free My ID: 1 thing needs you"


def test_at_10_minutes_a_closed_run_sends_the_next_notice() -> None:
    rec = Rec()
    clock = Clock(T0)
    wrapper = notify.ThrottledNotifier(rec, now=clock)
    wrapper.notify("first", "body")
    wrapper.flush()
    clock.advance(minutes=10)
    wrapper.notify("second", "body")
    assert [call[0] for call in rec.calls] == ["first", "second"]


def test_a_new_wrapper_within_10_minutes_counts() -> None:
    rec = Rec()
    clock = Clock(T0)
    first = notify.ThrottledNotifier(rec, now=clock)
    first.notify("first", "body")
    clock.advance(minutes=9)
    second = notify.ThrottledNotifier(rec, now=clock)
    second.notify("peoplesearch.example", "held")
    assert [call[0] for call in rec.calls] == ["first"]
    second.flush()
    assert rec.calls[1][0] == "Free My ID: 1 thing needs you"
    assert "peoplesearch.example" not in rec.calls[1][0] + rec.calls[1][1]


def test_handoff_get_notifier_returns_the_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = Rec()
    monkeypatch.setattr(notify, "get_notifier", lambda: inner)
    wrapped = handoff_notifier()
    assert isinstance(wrapped, notify.ThrottledNotifier)
    wrapped.notify("Free My ID needs you", GENERIC_HELP)
    wrapped.notify("peoplesearch.example", "held")
    assert len(inner.calls) == 1
    wrapped.flush()
    assert inner.calls[1][0] == "Free My ID: 1 thing needs you"


def test_queued_handoff_burst_is_one_notice_plus_a_summary(store) -> None:
    rec = Rec()
    wrapped = notify.ThrottledNotifier(rec, now=Clock(T0))
    profile_id = new_id()
    for broker_id in ("fakea", "fakeb", "fakec", "faked"):
        todo = Todo(profile_id=profile_id, broker_id=broker_id, kind=TodoKind.ASSISTED_OPT_OUT,
                    title="t", body="b")
        asyncio.run(QueuedHandoff(store, wrapped, "Jane").request(todo, None))
    assert rec.calls == [("Free My ID needs you", GENERIC_HELP, None)]
    wrapped.flush()
    title, body, _url = rec.calls[1]
    assert title == "Free My ID: 3 things need you"
    for broker_id in ("fakea", "fakeb", "fakec", "faked"):
        assert broker_id not in title + body
    assert "Jane" not in title + body


def test_missing_home_does_not_raise(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    missing = tmp_path / "missing-home"
    rec = Rec()
    with caplog.at_level(logging.INFO, logger="freemyid.notify"):
        sent = notify.maybe_monthly_progress(object(), rec, T0, home=missing)
    assert sent is False
    assert rec.calls == []
    assert not missing.exists()
    assert "missing-home" not in caplog.text
    assert "marker not written" in caplog.text


def test_home_helper_oserror_does_not_raise(monkeypatch: pytest.MonkeyPatch,
                                            caplog: pytest.LogCaptureFixture) -> None:
    def boom() -> object:
        raise OSError("denied")

    monkeypatch.setattr("freemyid.paths.home", boom)
    rec = Rec()
    with caplog.at_level(logging.INFO, logger="freemyid.notify"):
        sent = notify.maybe_monthly_progress(object(), rec, T0)
    assert sent is False
    assert rec.calls == []
    assert "denied" not in caplog.text
    assert "home unavailable" in caplog.text


@pytest.mark.skipif(sys.platform == "win32", reason="directory mode bits do not block writes")
def test_unwritable_home_does_not_raise(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    home = tmp_path / "ro-home-marker"
    home.mkdir()
    home.chmod(0o500)
    rec = Rec()
    try:
        probe = home / ".probe"
        try:
            probe.write_text("x", encoding="utf-8")
        except OSError:
            probe_wrote = False
        else:
            probe.unlink()
            probe_wrote = True
        if probe_wrote:
            pytest.skip("this user can still write the directory")
        with caplog.at_level(logging.INFO, logger="freemyid.notify"):
            sent = notify.maybe_monthly_progress(object(), rec, T0, home=home)
        assert sent is False
        assert rec.calls == []
        assert not (home / notify.PROGRESS_MARKER).exists()
        assert "ro-home-marker" not in caplog.text
    finally:
        home.chmod(0o700)


def test_marker_is_replaced_and_a_failed_replace_keeps_the_old_bytes(tmp_path,
                                                                    monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    replaced: list[str] = []
    real_replace = os.replace

    def spy(src: str, dst: str) -> None:
        replaced.append(os.path.basename(dst))
        real_replace(src, dst)

    monkeypatch.setattr(notify.os, "replace", spy)
    assert notify.maybe_monthly_progress(object(), Rec(), T0, home=home) is False
    marker = home / notify.PROGRESS_MARKER
    assert marker.read_text(encoding="utf-8") == T0.isoformat()
    assert replaced == [marker.name]
    assert [path.name for path in home.iterdir()] == [marker.name]

    marker.write_text("keep-this", encoding="utf-8")

    def fail(_src: str, _dst: str) -> None:
        raise OSError("full")

    monkeypatch.setattr(notify.os, "replace", fail)
    rec = Rec()
    assert notify.maybe_monthly_progress(object(), rec, T0, home=home) is False
    assert rec.calls == []
    assert marker.read_text(encoding="utf-8") == "keep-this"
    assert list(home.glob("*.tmp")) == []


def test_failed_refresh_does_not_send(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    marker = home / notify.PROGRESS_MARKER
    marker.write_text(T0.isoformat(), encoding="utf-8")

    def fail(_src: str, _dst: str) -> None:
        raise OSError("full")

    monkeypatch.setattr(notify.os, "replace", fail)
    rec = Rec()
    sent = notify.maybe_monthly_progress(EmptyStore(), rec, T0 + timedelta(days=31), home=home)
    assert sent is False
    assert rec.calls == []
    assert marker.read_text(encoding="utf-8") == T0.isoformat()
    assert list(home.glob("*.tmp")) == []
