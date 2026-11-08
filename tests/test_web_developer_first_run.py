"""Guard the v3 developer examples; build web/ before running these tests."""
from __future__ import annotations

import re
from html import unescape
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web/dist/developers/index.html"


@pytest.fixture(scope="module")
def sections() -> dict[str, str]:
    assert PAGE.is_file(), "Run pnpm --dir web build before testing the v3 output"
    html = PAGE.read_text(encoding="utf-8")
    return {
        name: unescape(body)
        for name, body in re.findall(
            r'<section\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</section>', html, re.DOTALL
        )
    }


def text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_setup_reference_links(sections: dict[str, str]) -> None:
    first = sections["first-run"]
    for path, label in (
        ("schema/setup-config.schema.json", "version 1 setup schema"),
        ("docs/examples/setup-config.example.yaml", "fake example YAML"),
    ):
        assert (ROOT / path).is_file()
        assert re.search(
            rf'href="https://[^\s"]+/blob/main/{re.escape(path)}">{label}</a>', first
        )
    assert "format will be published" not in text(first)


def test_validation_precedes_interactive_confirmation(sections: dict[str, str]) -> None:
    first = sections["first-run"]
    commands = re.findall(r"<code>(.*?)</code>", first, re.DOTALL)
    snippet = next(code for code in commands if "--check" in code and "\n" in code)
    assert re.findall(r"^freemyid setup.*$", snippet, re.MULTILINE) == [
        "freemyid setup --from config.yaml --check",
        "freemyid setup --from config.yaml",
    ]
    assert "--yes" not in first
    copy = text(first)
    assert "validation saves nothing" in copy
    assert "review the plan and permission text and confirm" in copy
    assert "Without a terminal, nothing is saved" in copy


def test_json_is_read_only_and_explains_streams(sections: dict[str, str]) -> None:
    body = sections["json"]
    assert re.findall(r"<pre\b[^>]*>\s*<code>(.*?)</code>\s*</pre>", body, re.DOTALL) == [
        "freemyid status --json"
    ]
    copy = text(body)
    for phrase in (
        "without changing it", "one JSON object on stdout", "human messages",
        "stderr", "versioned schema", '"schema": "status/1"',
        "will not be renamed or removed",
    ):
        assert phrase in copy
    assert re.search(r'href="https://[^\s"]+/blob/main/docs/CLI.md"', body)
    assert "exit code reference" in copy


def test_examples_match_shipped_v020(sections: dict[str, str]) -> None:
    for name in ("first-run", "json", "status"):
        copy = text(sections[name])
        assert "Coming in v0.2" not in copy
        assert "Version 0.2 isn't out yet" not in copy
    assert "Version 0.2.0 is out" in text(sections["status"])
    assert "You can open the web wizard" in text(sections["first-run"])
    assert "reads the saved status without changing it" in text(sections["json"])
