"""qa-security review of PR #112 (WO-336): setup-file errors never echo what was typed.

A misplaced colon in YAML turns a value into a key (``- 100 Example Road, Springfield: IL``).
The unknown key is then typed content, so it must not show up in the problem list.
Fake people only (Jane Q Testperson, Springfield IL). No network.
"""
from __future__ import annotations

import socket
from pathlib import Path

import pytest
import yaml

from freemyid.setup_config import SetupFileError, load


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    del freemyid_env

    def refuse(*_a: object, **_k: object) -> None:
        raise OSError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _base() -> dict:
    return {
        "version": 1,
        "consent": {"agreed": True, "signed_name": "Jane Q Testperson", "basis": "self"},
        "person": {
            "name": {"first": "Jane", "middle": "Q", "last": "Testperson"},
            "addresses": [{"city": "Springfield", "state": "IL", "current": True}],
        },
    }


def _problems(tmp_path: Path, data: object) -> list[str]:
    path = tmp_path / "setup.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(SetupFileError) as caught:
        load(path)
    return list(caught.value.problems)


def test_value_that_became_a_key_is_not_echoed(tmp_path: Path) -> None:
    data = _base()
    data["person"]["addresses"] = [{"100 Example Road, Springfield": "IL"}]
    problems = _problems(tmp_path, data)
    text = "\n".join(problems)
    assert "100 Example Road" not in text
    assert "Springfield" not in text
    assert any(p.startswith("person.addresses.0: ") and "not a setting Free My ID knows" in p
               for p in problems), problems


@pytest.mark.parametrize("key", [
    "jane.testperson@example.com", "217-555-0142", "Jane Q Testperson", "62704",
])
def test_personal_looking_unknown_keys_are_hidden(tmp_path: Path, key: str) -> None:
    data = _base()
    data["person"][key] = "x"
    problems = _problems(tmp_path, data)
    assert all(key not in p for p in problems), problems
    assert problems == [("person: has a line that is not a setting Free My ID knows; "
                         "check the colons and spaces")]


def test_non_text_unknown_key_is_hidden(tmp_path: Path) -> None:
    data = _base()
    data["person"][1980] = "x"
    problems = _problems(tmp_path, data)
    assert all("1980" not in p for p in problems), problems


def test_setting_name_typo_still_named_with_hint(tmp_path: Path) -> None:
    data = _base()
    data["person"]["relatvies"] = []
    assert _problems(tmp_path, data) == [
        "person.relatvies: is not a setting Free My ID knows; did you mean relatives?"]
