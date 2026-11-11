"""Checklist loader errors identify the file/item without echoing untrusted values."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from freemyid import checklists
from freemyid.models import ChecklistFile


def document() -> dict[str, Any]:
    return {"version": "test", "updated": "2026-01-01", "checklists": [{
        "id": "example_item", "title": "Example checklist", "why": "Example reason",
        "url": "https://example.org/list", "cost": "Free", "time_needed": "5 minutes",
        "steps": ["Read the example instructions"], "how_to_undo": "No action needed",
        "source_urls": ["https://example.org/source"], "date_checked": "2026-01-01",
        "verification": "official_page",
    }]}


def write_document(tmp_path: Path, raw: Any) -> Path:
    path = tmp_path / "example_checklists.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


@pytest.mark.parametrize("problem,reason", [
    ("missing_title", "title is missing"),
    ("duplicate", "duplicate checklist id"),
    ("empty_steps", "steps needs at least one item"),
    ("scheme", "url must use http or https"),
    ("long_title", "title is too long"),
])
def test_error_names_file_item_and_plain_reason(
    tmp_path: Path, problem: str, reason: str,
) -> None:
    raw = document()
    item = raw["checklists"][0]
    if problem == "missing_title":
        del item["title"]
    elif problem == "duplicate":
        raw["checklists"].append(deepcopy(item))
    elif problem == "empty_steps":
        item["steps"] = []
    elif problem == "scheme":
        item["url"] = "javascript:synthetic_private_marker"
    else:
        item["title"] = "synthetic_private_marker" * 20
    path = write_document(tmp_path, raw)
    with pytest.raises(ValueError) as caught:
        checklists.load(path)
    assert str(caught.value) == f"{path.name}: example_item: {reason}"
    assert str(tmp_path) not in str(caught.value)
    assert "synthetic_private_marker" not in str(caught.value)
    assert "input_value" not in str(caught.value)


def test_only_first_validation_problem_is_reported(tmp_path: Path) -> None:
    raw = document()
    del raw["checklists"][0]["title"]
    raw["checklists"][0]["steps"] = []
    with pytest.raises(ValueError) as caught:
        checklists.load(write_document(tmp_path, raw))
    assert str(caught.value).endswith("example_item: title is missing")
    assert "steps" not in str(caught.value)


@pytest.mark.parametrize("bad_id", [None, "../synthetic_private_marker", 123])
def test_invalid_id_not_echoed(tmp_path: Path, bad_id: Any) -> None:
    raw = document()
    raw["checklists"][0]["id"] = bad_id
    with pytest.raises(ValueError) as caught:
        checklists.load(write_document(tmp_path, raw))
    message = str(caught.value)
    assert "item 1" in message
    assert "synthetic_private_marker" not in message
    assert str(tmp_path) not in message


@pytest.mark.parametrize("raw", [None, [], {"version": "test"}])
def test_document_errors_have_safe_context(tmp_path: Path, raw: Any) -> None:
    path = write_document(tmp_path, raw)
    with pytest.raises(ValueError) as caught:
        checklists.load(path)
    assert str(caught.value).startswith(f"{path.name}: document:")
    assert str(tmp_path) not in str(caught.value)


def test_valid_document_keeps_model_behavior(tmp_path: Path) -> None:
    raw = document()
    assert checklists.load(write_document(tmp_path, raw)) == ChecklistFile.model_validate(raw)


def test_every_shipped_checklist_file_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    candidates = set(checklists._candidates())
    candidates.update(root.glob("src/**/brokers/checklists.yaml"))
    existing = sorted(path for path in candidates if path.is_file())
    assert existing
    for path in existing:
        loaded = checklists.load(path)
        assert loaded.checklists
        for item in loaded.checklists:
            assert item.title and item.steps


def test_bom_and_crlf_still_load(tmp_path: Path) -> None:
    raw = document()
    path = tmp_path / "windows.yaml"
    text = yaml.safe_dump(raw).replace("\n", "\r\n")
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert checklists.load(path) == ChecklistFile.model_validate(raw)


def test_collection_aliases_still_rejected(tmp_path: Path) -> None:
    path = tmp_path / "aliases.yaml"
    path.write_text("shared: &shared [one, two]\nchecklists: *shared\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        checklists.load(path)


@pytest.mark.parametrize("item_level", [True, False])
def test_unknown_field_names_are_not_echoed(tmp_path: Path, item_level: bool) -> None:
    raw = document()
    target = raw["checklists"][0] if item_level else raw
    target["synthetic_private_marker"] = "another_private_marker"
    with pytest.raises(ValueError) as caught:
        checklists.load(write_document(tmp_path, raw))
    assert "private_marker" not in str(caught.value)
