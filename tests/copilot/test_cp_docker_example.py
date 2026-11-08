"""Docker example config checks (WO-155 / GP-10). Offline; reads files only.

- packaging/docker/example-config.yaml must validate against schema/setup-config.schema.json.
- compose.example.yaml must mount the example config from a file that exists, under FREEMYID_HOME.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / "packaging" / "docker"
CONFIG = DOCKER / "example-config.yaml"
COMPOSE = DOCKER / "compose.example.yaml"
SCHEMA = ROOT / "schema" / "setup-config.schema.json"


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _config_mount() -> tuple[Path, PurePosixPath, list[str]]:
    """Return (host source, container target, mount options) of the example-config volume."""
    compose = _load(COMPOSE)
    service = compose["services"]["freemyid"]
    for volume in service["volumes"]:
        if isinstance(volume, str) and "example-config" in volume:
            source, target, *options = volume.split(":")
            return (COMPOSE.parent / source).resolve(), PurePosixPath(target), options
    pytest.fail("compose.example.yaml does not mount example-config.yaml")


def test_example_config_is_a_yaml_mapping() -> None:
    assert isinstance(_load(CONFIG), dict)


def test_example_config_validates_against_setup_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(_load(CONFIG), schema)


def test_example_config_uses_fake_data_only() -> None:
    text = CONFIG.read_text(encoding="utf-8")
    assert "Testperson" in text
    assert ".invalid" in text or "example." in text


def test_compose_mounts_an_existing_example_config() -> None:
    source, _target, _options = _config_mount()
    assert source == CONFIG.resolve()
    assert source.is_file()


def test_compose_mount_is_read_only_and_under_freemyid_home() -> None:
    _source, target, options = _config_mount()
    service = _load(COMPOSE)["services"]["freemyid"]
    home = PurePosixPath(service["environment"]["FREEMYID_HOME"])
    assert target.is_relative_to(home)
    assert target.name == CONFIG.name
    assert "ro" in options
