"""PR #128 review: the OS notice path cannot be broken out of, a slow start does not switch
notices off for good, and a notice sent from async code does not block the event loop.

Fake runners only. No real subprocess.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from freemyid import notify

# PowerShell ends a single-quoted literal at any of these, not only the ASCII one.
_PS_SINGLE_QUOTES = "'\u2018\u2019\u201a\u201b"


@pytest.fixture(autouse=True)
def _reset_gate():
    notify._OsGate.unavailable = False
    notify._OsGate.logged = False
    yield
    notify._OsGate.unavailable = False
    notify._OsGate.logged = False


def _ps_literal(src: str) -> tuple[str, str]:
    """Read one PowerShell single-quoted literal from the start of src: (value, rest)."""
    assert src[0] in _PS_SINGLE_QUOTES
    out: list[str] = []
    i = 1
    while i < len(src):
        c = src[i]
        if c in _PS_SINGLE_QUOTES:
            if i + 1 < len(src) and src[i + 1] in _PS_SINGLE_QUOTES:
                out.append(c)
                i += 2
                continue
            return "".join(out), src[i + 1:]
        out.append(c)
        i += 1
    raise AssertionError("unterminated literal")


@pytest.mark.parametrize("quote", list(_PS_SINGLE_QUOTES))
def test_powershell_title_cannot_end_the_literal(quote: str) -> None:
    hostile = f"Sam{quote}; Remove-Item -Recurse C:\\x; {quote}"
    for line in notify._powershell_script(hostile, hostile).splitlines():
        for var in ("$title = ", "$body = "):
            if line.startswith(var):
                value, rest = _ps_literal(line[len(var):])
                assert rest == ""          # nothing after the literal runs as code
                assert value == notify._xml_escape(hostile)


def test_a_timeout_skips_one_notice_but_does_not_switch_notices_off() -> None:
    calls: list[list[str]] = []
    codes = iter([124, 0])

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return next(codes)

    kw = {"platform": "linux", "finder": lambda name: name, "runner": runner}
    assert notify._deliver_os_notice("Free My ID", "1 thing needs you", **kw) is False
    assert notify._OsGate.unavailable is False
    assert notify._deliver_os_notice("Free My ID", "1 thing needs you", **kw) is True
    assert len(calls) == 2


def test_other_bad_exits_still_switch_notices_off() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        calls.append(list(argv))
        return 1

    kw = {"platform": "linux", "finder": lambda name: name, "runner": runner}
    notify._deliver_os_notice("Free My ID", "1 thing needs you", **kw)
    notify._deliver_os_notice("Free My ID", "1 thing needs you", **kw)
    assert len(calls) == 1


def test_notice_from_async_code_does_not_block_the_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    started = threading.Event()
    release = threading.Event()
    calls: list[list[str]] = []

    def slow_runner(argv: list[str]) -> int:
        started.set()
        release.wait(2)
        calls.append(list(argv))
        return 0

    monkeypatch.setattr(notify.sys, "platform", "linux")
    monkeypatch.setattr(notify, "_app_icon", lambda: None)
    monkeypatch.setattr(notify, "_finder", lambda name: name)
    monkeypatch.setattr(notify, "_runner", slow_runner)

    async def main() -> int:
        notify.DesktopNotifier().notify("Free My ID", "1 thing needs you")
        # notify() returned while the tool is still running: the loop was not blocked.
        await asyncio.sleep(0)
        return len(calls)

    assert asyncio.run(main()) == 0
    assert started.wait(5)
    release.set()
    for t in threading.enumerate():
        if t.name == "freemyid-notice":
            t.join(5)
    assert len(calls) == 1


def test_notice_outside_a_loop_is_delivered_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(notify.sys, "platform", "linux")
    monkeypatch.setattr(notify, "_app_icon", lambda: None)
    monkeypatch.setattr(notify, "_finder", lambda name: name)
    monkeypatch.setattr(notify, "_runner", lambda argv: calls.append(list(argv)) or 0)
    notify.DesktopNotifier().notify("Free My ID", "1 thing needs you")
    assert len(calls) == 1
