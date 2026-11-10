"""WO-349: a missing or failing OS notifier stays quiet. No real subprocess, no network."""
from __future__ import annotations

import logging
import socket
from datetime import UTC, datetime

import pytest

from freemyid import notify
from freemyid.engine.handoff import GENERIC_HELP

T0 = datetime(2026, 11, 1, tzinfo=UTC)
POISON = (
    "Jane Q Testperson",
    "Springfield IL",
    "peoplesearch.example",
    "https://peoplesearch.example/listing",
    "jane.testperson@example.com",
)
SAFE_BODY = "1 thing needs you"


class _Done:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any accidental socket use fails the test. No real network."""
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise OSError("network blocked by test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture(autouse=True)
def _no_real_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default runner must not reach a real process. Tests pass a fake runner."""
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("real subprocess blocked by test")

    monkeypatch.setattr(notify.subprocess, "run", blocked)
    monkeypatch.setattr(notify.subprocess, "Popen", blocked)


@pytest.fixture(autouse=True)
def _reset_notice_state():
    notify._OsGate.unavailable = False
    notify._OsGate.logged = False
    notify.ThrottledNotifier._shared_started_at = None
    yield
    notify._OsGate.unavailable = False
    notify._OsGate.logged = False
    notify.ThrottledNotifier._shared_started_at = None


def _finder(name: str) -> str:
    return name


def _blob(calls: list[list[str]]) -> str:
    return "\n".join(" ".join(call) for call in calls)


def test_network_is_blocked() -> None:
    sock = socket.socket()
    try:
        with pytest.raises(OSError, match="network blocked by test"):
            sock.connect(("127.0.0.1", 1))
    finally:
        sock.close()
    with pytest.raises(OSError, match="network blocked by test"):
        socket.create_connection(("127.0.0.1", 1))


def test_default_runner_does_not_escape_the_block() -> None:
    with pytest.raises(AssertionError, match="real subprocess blocked"):
        notify._subprocess_runner(["/nonexistent/freemyid-notify-test"])
    with pytest.raises(AssertionError, match="real subprocess blocked"):
        notify.subprocess.Popen(["/nonexistent/freemyid-notify-test"])


@pytest.mark.parametrize(("platform", "tool"), [
    ("linux", "notify-send"),
    ("darwin", "osascript"),
    ("win32", "powershell"),
])
def test_missing_executable_is_a_quiet_noop(platform: str, tool: str,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    asked: list[str] = []
    calls: list[list[str]] = []

    def finder(name: str) -> str | None:
        asked.append(name)
        return None

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    first = notify._deliver_os_notice(
        "Free My ID", SAFE_BODY, platform=platform, finder=finder, runner=runner)
    second = notify._deliver_os_notice(
        "Free My ID", SAFE_BODY, platform=platform, finder=finder, runner=runner)
    assert first is False and second is False
    assert calls == []
    assert asked == [tool, tool]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(("platform", "tool"), [
    ("linux", "notify-send"),
    ("darwin", "osascript"),
    ("win32", "powershell"),
])
def test_desktop_notifier_missing_tool_is_a_noop(platform: str, tool: str,
                                                 monkeypatch: pytest.MonkeyPatch,
                                                 capsys: pytest.CaptureFixture[str]) -> None:
    asked: list[str] = []
    calls: list[list[str]] = []

    def finder(name: str) -> str | None:
        asked.append(name)
        return None

    monkeypatch.setattr(notify.sys, "platform", platform)
    monkeypatch.setattr(notify, "_finder", finder)
    monkeypatch.setattr(notify, "_runner", lambda argv: calls.append(list(argv)) or 0)
    note = notify.DesktopNotifier()
    assert note.notify("Free My ID", SAFE_BODY) is None
    assert note.notify("Free My ID", SAFE_BODY) is None
    assert calls == []
    assert asked == [tool, tool]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err


def test_unknown_platform_does_nothing() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    sent = notify._deliver_os_notice(
        "Free My ID", SAFE_BODY, platform="freebsd", finder=_finder, runner=runner)
    assert sent is False
    assert calls == []


def test_nonzero_exit_is_not_retried() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> _Done:
        calls.append(list(argv))
        return _Done(1)

    assert notify._deliver_os_notice(
        "Free My ID", SAFE_BODY, platform="linux", finder=_finder, runner=runner) is False
    for platform in ("linux", "darwin", "win32"):
        assert notify._deliver_os_notice(
            "Free My ID", SAFE_BODY, platform=platform, finder=_finder, runner=runner) is False
    assert len(calls) == 1
    assert calls[0][0] == "notify-send"
    blob = _blob(calls)
    assert SAFE_BODY in blob
    for poison in POISON:
        assert poison not in blob


def test_runner_error_stays_quiet(capsys: pytest.CaptureFixture[str],
                                  caplog: pytest.LogCaptureFixture) -> None:
    calls = {"n": 0}

    def runner(_argv: list[str]) -> int:
        calls["n"] += 1
        raise OSError("notify-send failed: Springfield IL")

    with caplog.at_level(logging.DEBUG, logger="freemyid.notify"):
        first = notify._deliver_os_notice(
            "Free My ID", SAFE_BODY, platform="darwin", finder=_finder, runner=runner)
        second = notify._deliver_os_notice(
            "Free My ID", SAFE_BODY, platform="win32", finder=_finder, runner=runner)
    assert first is False and second is False
    assert calls["n"] == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert "Springfield" not in captured.err
    assert "Traceback" not in caplog.text
    assert "Springfield" not in caplog.text
    assert "OSError" in caplog.text


def test_a_link_is_dropped_and_a_later_safe_notice_still_sends() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    dropped = notify._deliver_os_notice(
        "Free My ID", POISON[3], platform="linux", finder=_finder, runner=runner)
    mailed = notify._deliver_os_notice(
        "Jane Q Testperson", "jane.testperson@example.com",
        platform="linux", finder=_finder, runner=runner)
    sent = notify._deliver_os_notice(
        "Free My ID", SAFE_BODY, platform="linux", finder=_finder, runner=runner)
    assert dropped is False and mailed is False and sent is True
    assert len(calls) == 1
    blob = _blob(calls)
    assert SAFE_BODY in blob
    for poison in POISON:
        assert poison not in blob


def test_url_argument_is_not_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    monkeypatch.setattr(notify.sys, "platform", "linux")
    monkeypatch.setattr(notify, "_app_icon", lambda: None)
    monkeypatch.setattr(notify, "_finder", _finder)
    monkeypatch.setattr(notify, "_runner", runner)
    assert notify.DesktopNotifier().notify(
        "Free My ID", "2 things need you", POISON[3]) is None
    assert len(calls) == 1
    blob = _blob(calls)
    assert calls[0][0] == "notify-send"
    assert "2 things need you" in blob
    for poison in POISON:
        assert poison not in blob


def test_held_details_never_reach_the_tool() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    class Inner:
        def notify(self, title: str, body: str, url: str | None = None) -> None:
            notify._deliver_os_notice(
                title, body, platform="linux", finder=_finder, runner=runner)
            assert url is None or url == ""

    wrapped = notify.ThrottledNotifier(Inner(), now=lambda: T0)
    wrapped.notify("Free My ID needs you", GENERIC_HELP)
    wrapped.notify(POISON[0], POISON[1])
    wrapped.notify(POISON[2], POISON[3])
    wrapped.notify(POISON[4], "still held")
    wrapped.flush()
    assert len(calls) == 2
    assert calls[0][-2:] == ["Free My ID needs you", GENERIC_HELP]
    assert calls[1][-2:] == [
        "Free My ID: 3 things need you",
        "3 things need you. Open Free My ID to see them.",
    ]
    blob = _blob(calls)
    for poison in POISON:
        assert poison not in blob


def test_failed_tool_is_not_called_again_for_a_burst() -> None:
    calls = {"n": 0}

    def runner(argv: list[str]) -> _Done:
        calls["n"] += 1
        assert "Jane" not in " ".join(argv)
        assert "Springfield" not in " ".join(argv)
        return _Done(2)

    class Inner:
        def notify(self, title: str, body: str, url: str | None = None) -> None:
            notify._deliver_os_notice(
                title, body, platform="win32", finder=_finder, runner=runner)

    wrapped = notify.ThrottledNotifier(Inner(), now=lambda: T0)
    wrapped.notify("Free My ID needs you", GENERIC_HELP)
    for _ in range(6):
        wrapped.notify(POISON[0], POISON[1])
    wrapped.flush()
    assert calls["n"] == 1


@pytest.mark.parametrize(("platform", "tool"), [
    ("linux", "notify-send"),
    ("darwin", "osascript"),
    ("win32", "powershell"),
])
def test_monthly_wording_is_what_the_tool_sees(platform: str, tool: str) -> None:
    body = notify.progress_body({"sent": 1, "confirmed": 2, "need_you": 3})
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> _Done:
        calls.append(list(argv))
        return _Done(0)

    sent = notify._deliver_os_notice(
        "Free My ID: your monthly update", body, platform=platform, finder=_finder, runner=runner)
    assert sent is True
    assert len(calls) == 1
    assert calls[0][0] == tool
    blob = _blob(calls)
    assert body in blob
    assert "1 request sent" in blob
    assert "2 sites confirmed" in blob
    assert "3 need you" in blob
    for poison in (*POISON, "http://", "https://", "www."):
        assert poison not in blob


def test_a_successful_notice_can_run_again() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    assert notify._deliver_os_notice(
        "Free My ID", SAFE_BODY, platform="darwin", finder=_finder, runner=runner) is True
    assert notify._deliver_os_notice(
        "Free My ID", "2 things need you", platform="darwin", finder=_finder, runner=runner) is True
    assert len(calls) == 2
    assert calls[0][0] == "osascript"
    assert calls[0][-1] == SAFE_BODY
    assert calls[1][-1] == "2 things need you"
