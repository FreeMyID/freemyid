"""Cross-platform guards for Free My ID's home and wipe-target helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from freemyid import paths


def _fake_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Keep Path.home() inside the test's temporary directory."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))


def test_home_uses_windows_appdata_and_creates_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FREEMYID_HOME", raising=False)
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(paths.sys, "platform", "win32")

    result = paths.home()

    assert result == appdata / "FreeMyID"
    assert result.is_dir()
    assert (result / paths.MARKER).is_file()


def test_windows_appdata_fallback_uses_path_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FREEMYID_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    user_home = tmp_path / "fake-user-home"
    _fake_home(monkeypatch, user_home)
    monkeypatch.setattr(paths.sys, "platform", "win32")

    result = paths.home()

    assert result == user_home / "AppData" / "Roaming" / "FreeMyID"
    assert result.is_dir()
    assert (result / paths.MARKER).is_file()


def test_freemyid_home_override_wins_over_platform_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "override"
    monkeypatch.setenv("FREEMYID_HOME", str(override))
    monkeypatch.setenv("APPDATA", str(tmp_path / "unused-appdata"))
    monkeypatch.setattr(paths.sys, "platform", "win32")

    assert paths.home() == override
    assert (override / paths.MARKER).is_file()
    assert not (tmp_path / "unused-appdata").exists()


def test_existing_unrelated_home_does_not_get_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unrelated = tmp_path / "existing-folder"
    unrelated.mkdir()
    monkeypatch.setenv("FREEMYID_HOME", str(unrelated))

    assert paths.home() == unrelated
    assert not (unrelated / paths.MARKER).exists()


def test_existing_home_with_database_gets_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "existing-home"
    existing.mkdir()
    (existing / "freemyid.db").write_bytes(b"synthetic database marker")
    monkeypatch.setenv("FREEMYID_HOME", str(existing))

    paths.home()

    assert (existing / paths.MARKER).is_file()


def test_owned_entries_include_names_created_by_path_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "owned-home"
    monkeypatch.setenv("FREEMYID_HOME", str(home))

    for helper in (
        paths.db_path,
        paths.config_path,
        paths.registry_cache_path,
        paths.evidence_dir,
        paths.artifacts_dir,
        paths.logs_dir,
    ):
        result = helper()
        assert result.parent == home
        assert result.name in paths.OWNED_ENTRIES, helper.__name__

    created = {path.name for path in home.iterdir()}
    assert paths.MARKER in paths.OWNED_ENTRIES
    assert created <= set(paths.OWNED_ENTRIES)


def test_is_safe_wipe_target_refuses_user_home_and_its_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_home = tmp_path / "users" / "nested" / "fake-user"
    user_home.mkdir(parents=True)
    _fake_home(monkeypatch, user_home)
    protected = (user_home, *(parent for parent in user_home.parents if parent.is_relative_to(tmp_path)))
    for folder in protected:
        (folder / paths.MARKER).write_text("synthetic marker", encoding="utf-8")
        assert not paths.is_safe_wipe_target(folder)


def test_is_safe_wipe_target_refuses_filesystem_anchor_and_shallow_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_home(monkeypatch, tmp_path / "fake-user-home")
    anchor = Path(tmp_path.anchor)
    # Pretend a marker exists everywhere, so only the depth/anchor guards can refuse.
    real_exists = Path.exists
    monkeypatch.setattr(
        Path, "exists", lambda p: p.name in {paths.MARKER, "freemyid.db"} or real_exists(p)
    )

    assert not paths.is_safe_wipe_target(anchor)
    assert not paths.is_safe_wipe_target(anchor / "one")
    # Control: the same fake marker is accepted one level deeper than the guard.
    assert paths.is_safe_wipe_target(anchor / "one" / "two")


def test_is_safe_wipe_target_refuses_unmarked_folder_and_accepts_marked_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_home(monkeypatch, tmp_path / "fake-user-home")
    unmarked = tmp_path / "unmarked" / "folder"
    marked = tmp_path / "marked" / "folder"
    unmarked.mkdir(parents=True)
    marked.mkdir(parents=True)
    (marked / paths.MARKER).write_text("synthetic marker", encoding="utf-8")

    assert not paths.is_safe_wipe_target(unmarked)
    assert paths.is_safe_wipe_target(marked)


def test_is_safe_wipe_target_accepts_database_without_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_home(monkeypatch, tmp_path / "fake-user-home")
    database_home = tmp_path / "database-home" / "profile"
    database_home.mkdir(parents=True)
    (database_home / "freemyid.db").write_bytes(b"synthetic database marker")

    assert paths.is_safe_wipe_target(database_home)
