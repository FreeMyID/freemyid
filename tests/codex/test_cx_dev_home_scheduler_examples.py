"""Compare the developer page's scheduler snippets with pure public renderers."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from freemyid import scheduler
from freemyid.scheduler import render

PAGE = Path(__file__).resolve().parents[2] / "web/src/pages/developers/index.astro"


def _snippet(name: str) -> str:
    page = PAGE.read_text(encoding="utf-8")
    matches = re.findall(rf"^const {re.escape(name)} = `([^`]*)`;", page, re.MULTILINE)
    assert len(matches) == 1, f"Expected one literal {name} snippet in {PAGE}"
    assert "${" not in matches[0], f"Unexpected interpolation in {name} snippet"
    return matches[0]


def test_cron_example_matches_daily_and_reboot_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fix executable discovery without consulting the host PATH or running a job.
    monkeypatch.setattr(scheduler.shutil, "which", lambda _name: "freemyid")
    command = scheduler.job_command(frozen=False, platform="linux")
    rendered = render.cron_lines(command).splitlines()
    example = _snippet("cron").splitlines()
    assert len(example) == len(rendered) == 2

    for shown, actual in zip(example, rendered, strict=True):
        # The page intentionally omits only the renderer's maintenance comment.
        assert actual.endswith(" " + render.CRON_MARK)
        assert shlex.split(shown) == shlex.split(actual.removesuffix(" " + render.CRON_MARK))

    daily = shlex.split(example[0])
    assert daily[:5] == ["0", str(render.DAILY_HOUR), "*", "*", "*"]
    assert daily[5:] == command


def test_systemd_example_matches_timer_settings_and_unit_name() -> None:
    snippet = _snippet("timer")
    assert re.findall(r"^#\s+(\S+\.timer)$", snippet, re.MULTILINE) == [
        f"{render.UNIT}.timer"
    ]
    assert "[Timer]" in snippet.splitlines()
    expected = dict(
        line.split("=", 1) for line in render.systemd_timer().splitlines() if "=" in line
    )
    shown = dict(line.split("=", 1) for line in snippet.splitlines() if "=" in line)
    assert set(shown) == {"OnCalendar", "Persistent", "RandomizedDelaySec"}
    for setting, value in shown.items():
        assert value == expected[setting], f"Developer timer example disagrees on {setting}"
