"""Keep the developer YAML reference aligned with the checked-in setup schema."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/src/pages/developers/config/index.astro"
SCHEMA = ROOT / "schema/setup-config.schema.json"


def _property_names(schema: dict[str, object]) -> set[str]:
    definitions = schema.get("$defs", {})

    def walk(node: dict[str, object]) -> set[str]:
        names: set[str] = set()
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/") and isinstance(definitions, dict):
            target = definitions.get(ref.removeprefix("#/$defs/"))
            if isinstance(target, dict):
                names.update(walk(target))

        properties = node.get("properties", {})
        if isinstance(properties, dict):
            for name, child in properties.items():
                names.add(name)
                if isinstance(child, dict):
                    names.update(walk(child))

        items = node.get("items")
        if isinstance(items, dict):
            names.update(walk(items))
        for branch in node.get("anyOf", []):
            if isinstance(branch, dict):
                names.update(walk(branch))
        return names

    return walk(schema)


def test_reference_mentions_every_schema_property_and_version() -> None:
    page = PAGE.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["properties"]["version"]["const"] == 1
    for name in _property_names(schema):
        assert name in page

    assert "schema/setup-config.schema.json" in page
    assert "docs/CLI.md" in page


def test_example_is_fake_and_keeps_mailbox_password_out_of_yaml() -> None:
    page = PAGE.read_text(encoding="utf-8")
    match = re.search(r"const example = `(?P<yaml>.*?)`;", page, flags=re.DOTALL)

    assert match is not None
    sample = match.group("yaml")
    assert "Jane Q Testperson" in sample
    assert "Springfield" in sample
    assert "jane.removals@example.com" in sample
    assert "password_env:" in sample
    assert "password:" not in sample


def test_page_has_no_client_script_or_interactive_directive() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "<script" not in page.lower()
    assert not re.search(r"\bclient:(?:load|idle|visible|media|only)\b", page)
    assert 'freemyid setup --from setup.yaml --check' in page
    assert 'freemyid setup --from setup.yaml' in page
