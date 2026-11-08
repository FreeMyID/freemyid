"""The documented `freemyid` spellings match the commands registered in the Typer app (GP-02).

Walks `freemyid.cli.app` with Click introspection (no subprocess, no network) and checks:
- every visible command/subcommand is in the docs/CLI.md command table;
- every `freemyid <words>` example in docs/CLI.md, README.md and docs/USER_GUIDE.md resolves
  to a real command or subcommand.
Hidden commands (for example `run --scheduled`) are exempt.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import typer.main

from freemyid.cli import app

ROOT = Path(__file__).resolve().parents[1]
DOC_FILES = ("docs/CLI.md", "README.md", "docs/USER_GUIDE.md")

WORD = re.compile(r"^[a-z][a-z0-9-]*$")
START = re.compile(r"^(?:\S*[/=])?freemyid[ \t]+(.*)$")
SPAN = re.compile(r"`([^`\n]+)`")

_root = typer.main.get_command(app)


def _is_group(cmd: object) -> bool:
    # Typer bundles its own click, so duck-type instead of isinstance.
    return hasattr(cmd, "commands") and hasattr(cmd, "list_commands")


def _visible(group: Any) -> dict[str, Any]:
    return {n: c for n, c in group.commands.items() if not getattr(c, "hidden", False)}


def _registered() -> list[tuple[str, ...]]:
    paths: list[tuple[str, ...]] = []
    for name, cmd in _visible(_root).items():
        if _is_group(cmd):
            paths += [(name, sub) for sub in _visible(cmd)]
        else:
            paths.append((name,))
    return paths


def _clean(token: str) -> str:
    return token.rstrip(",.;:)")


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert m, f"docs/CLI.md has no '## {heading}' section"
    return m.group(1)


def _documented() -> tuple[set[str], set[tuple[str, str]]]:
    """Command names and (group, sub) pairs from the first column of the Commands table."""
    names: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    table = _section((ROOT / "docs/CLI.md").read_text(encoding="utf-8"), "Commands")
    for line in table.splitlines():
        if not line.startswith("|"):
            continue
        for span in SPAN.findall(line.split("|")[1]):
            tokens = span.split()
            if not tokens or not WORD.match(tokens[0]):
                continue
            names.add(tokens[0])
            for tok in tokens[1:]:
                if tok == "/":
                    continue
                if not WORD.match(tok):
                    break
                pairs.add((tokens[0], tok))
    return names, pairs


def _examples(rel: str) -> list[str]:
    """`freemyid ...` examples: fenced code lines and inline code spans that start with it."""
    found: list[str] = []
    fenced = False
    for raw in (ROOT / rel).read_text(encoding="utf-8").splitlines():
        if raw.lstrip().startswith("```"):
            fenced = not fenced
            continue
        candidates = [raw.strip().removeprefix("$ ")] if fenced else SPAN.findall(raw)
        for cand in candidates:
            m = START.match(cand.strip())
            if m:
                found.append("freemyid " + m.group(1).strip())
    return list(dict.fromkeys(found))


def _resolve(example: str) -> str | None:
    """None when the leading words resolve to real commands, else a plain reason."""
    tokens = [_clean(t) for t in example.split()[1:]]
    if not tokens or not WORD.match(tokens[0]):
        return None
    top = _visible(_root)
    cmd = top.get(tokens[0])
    if cmd is None:
        return f"'{tokens[0]}' is not a command"
    if (
        _is_group(cmd)
        and len(tokens) > 1
        and WORD.match(tokens[1])
        and tokens[1] not in _visible(cmd)
    ):
        return f"'{tokens[0]} {tokens[1]}' is not a subcommand"
    return None


def test_cli_app_has_commands() -> None:
    assert _registered()


@pytest.mark.parametrize("path", _registered(), ids=lambda p: " ".join(p))
def test_registered_command_is_in_cli_md_table(path: tuple[str, ...]) -> None:
    names, pairs = _documented()
    assert path[0] in names, f"`{path[0]}` is not in the docs/CLI.md command table"
    if len(path) == 2:
        assert (path[0], path[1]) in pairs, (
            f"`{' '.join(path)}` is not in the docs/CLI.md command table")


@pytest.mark.parametrize(
    ("rel", "example"),
    [(rel, ex) for rel in DOC_FILES for ex in _examples(rel)],
    ids=lambda v: v if isinstance(v, str) else repr(v),
)
def test_documented_example_resolves(rel: str, example: str) -> None:
    problem = _resolve(example)
    assert problem is None, f"{rel}: `{example}`: {problem}"


@pytest.mark.parametrize("rel", DOC_FILES)
def test_docs_have_examples(rel: str) -> None:
    assert _examples(rel), f"no `freemyid ...` examples found in {rel}; is the scanner broken?"
