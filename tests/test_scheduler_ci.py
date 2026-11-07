"""OS markers, the real-scheduler guard, and real scheduler round-trips on CI runners only.

Real tests carry `real_scheduler` plus an OS marker: conftest skips them unless CI=true, so a
developer's own scheduled tasks/timers are never touched. Everything else gets a
`scheduler._run` that refuses to start a process."""
from __future__ import annotations

import sys

import pytest

from freemyid import scheduler
from tests.conftest import OS_MARKERS


def test_os_markers_match_exactly_one_family():
    assert OS_MARKERS["windows_only"][0] != OS_MARKERS["posix_only"][0]
    if sys.platform == "darwin":
        assert OS_MARKERS["macos_only"][0] and not OS_MARKERS["linux_only"][0]
    if sys.platform.startswith("linux"):
        assert OS_MARKERS["linux_only"][0] and not OS_MARKERS["macos_only"][0]


@pytest.mark.windows_only
def test_windows_only_runs_on_windows():
    assert sys.platform == "win32"


@pytest.mark.posix_only
def test_posix_only_runs_on_posix():
    assert sys.platform != "win32"


def test_unmarked_tests_cannot_reach_the_real_scheduler():
    for args in (scheduler.windows_query_args(), ["systemctl", "--user", "list-timers"],
                 ["launchctl", "list"], ["crontab", "-l"]):
        with pytest.raises(RuntimeError, match="real scheduler blocked"):
            scheduler._run(args)


@pytest.mark.windows_only
@pytest.mark.real_scheduler
def test_windows_task_install_status_remove():
    """Per-user task, no admin: install twice (/F), query, remove, query again."""
    try:
        scheduler.install()
        scheduler.install()
        assert scheduler.status() == "scheduled task installed"
    finally:
        scheduler.remove()
    assert scheduler.status() == "not installed"
