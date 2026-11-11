"""Hardening for bundled YAML data files; all fixtures use synthetic values."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from freemyid import checklists
from freemyid.engine import law_matrix

CHECKLIST_YAML = '''\
version: "test"
updated: 2026-01-01
checklists:
  - id: test_list
    title: "Example checklist"
    why: "Example reason"
    url: "https://example.org/list"
    cost: "Free"
    time_needed: "5 minutes"
    steps: ["Read the example instructions"]
    how_to_undo: "No action needed"
    source_urls: ["https://example.org/source"]
    date_checked: 2026-01-01
    verification: official_page
'''

MATRIX_YAML = '''\
version: "test"
states:
  - state: VA
    in_force: true
    deletion_right: yes
    citation: "Example Code 1"
    evidence: statute_text
'''


@pytest.mark.parametrize("loader_kind", ["checklists", "matrix"])
@pytest.mark.parametrize("alias_value", ["[one, two]", "{key: value}"])
def test_yaml_loaders_reject_aliases_to_collections(
    tmp_path: Path, loader_kind: str, alias_value: str,
) -> None:
    alias_yaml = f"shared: &shared {alias_value}\n"
    if loader_kind == "checklists":
        contents = alias_yaml + "version: test\nupdated: 2026-01-01\nchecklists: *shared\n"
        path = tmp_path / "checklists.yaml"
        path.write_text(contents, encoding="utf-8")
        with pytest.raises(yaml.YAMLError):
            checklists.load(path)
    else:
        contents = alias_yaml + "version: test\nstates: *shared\n"
        path = tmp_path / "matrix.yaml"
        path.write_text(contents, encoding="utf-8")
        assert law_matrix.load(path) == law_matrix.EMPTY


@pytest.mark.parametrize("loader_kind", ["checklists", "matrix"])
def test_yaml_loaders_allow_aliases_to_scalars(
    tmp_path: Path, loader_kind: str,
) -> None:
    if loader_kind == "checklists":
        contents = CHECKLIST_YAML.replace(
            'version: "test"', 'version: &shared "test"'
        ).replace('title: "Example checklist"', 'title: *shared')
        path = tmp_path / "checklists.yaml"
        path.write_text(contents, encoding="utf-8")
        assert checklists.load(path).checklists[0].title == "test"
    else:
        contents = MATRIX_YAML.replace(
            'version: "test"', 'version: &shared "test"\nother: *shared'
        )
        path = tmp_path / "matrix.yaml"
        path.write_text(contents, encoding="utf-8")
        assert law_matrix.load(path).get("VA") is not None


@pytest.mark.parametrize("loader_kind", ["checklists", "matrix"])
def test_utf8_bom_and_crlf_load_same_as_plain_yaml(
    tmp_path: Path, loader_kind: str,
) -> None:
    contents = CHECKLIST_YAML if loader_kind == "checklists" else MATRIX_YAML
    plain_path = tmp_path / "plain.yaml"
    windows_path = tmp_path / "windows.yaml"
    plain_path.write_text(contents, encoding="utf-8", newline="")
    windows_path.write_bytes(b"\xef\xbb\xbf" + contents.replace("\n", "\r\n").encode("utf-8"))

    if loader_kind == "checklists":
        assert checklists.load(windows_path) == checklists.load(plain_path)
    else:
        assert law_matrix.load(windows_path) == law_matrix.load(plain_path)


def test_invalid_state_and_evidence_rows_are_dropped_with_code_only_warnings(
    caplog: pytest.LogCaptureFixture,
) -> None:
    matrix = law_matrix.parse({"version": "test", "states": [
        {"state": "ZZ", "in_force": True, "deletion_right": "yes",
         "citation": "Example Code", "evidence": "statute_text"},
        {"state": "VA", "in_force": True, "deletion_right": "yes",
         "citation": "Example Code", "evidence": "statute_texxt"},
        {"state": "CA", "in_force": True, "deletion_right": "yes",
         "citation": "Example Code", "evidence": "statute_text",
         "response_days": 45, "response_days_evidence": "statute_texxt"},
        {"state": "MN", "in_force": True, "deletion_right": "yes",
         "citation": "Example Code", "evidence": "statute_text"},
    ]})

    assert set(matrix.states) == {"MN"}
    assert matrix.states["MN"].citable()
    assert not matrix.states["MN"].deadline_verified()
    warnings = [record.getMessage() for record in caplog.records]
    assert warnings == [
        "dropping state-law matrix entry for state code ZZ",
        "dropping state-law matrix entry for state code VA",
        "dropping state-law matrix entry for state code CA",
    ]


def test_invalid_state_code_does_not_enter_matrix() -> None:
    matrix = law_matrix.parse({"version": "test", "states": [
        {"state": "VAX", "in_force": True, "deletion_right": "yes",
         "citation": "Example Code", "evidence": "statute_text"},
    ]})
    assert matrix.states == {}


def test_missing_checklist_file_still_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        checklists.load(tmp_path / "missing.yaml")


def test_matrix_alias_to_a_valid_states_list_is_refused(tmp_path: Path) -> None:
    # In-house review: the collection-alias case above would also return EMPTY with
    # safe_load (the aliased value is not a valid states list). Alias a VALID list so
    # only the alias refusal can make the loader fall back to EMPTY.
    contents = (
        "shared: &shared\n"
        "  - {state: VA, in_force: true, deletion_right: yes,"
        ' citation: "Example Code 1", evidence: statute_text}\n'
        "version: test\nstates: *shared\n"
    )
    path = tmp_path / "matrix.yaml"
    path.write_text(contents, encoding="utf-8")
    assert law_matrix.load(path) == law_matrix.EMPTY
