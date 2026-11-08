"""Documented `--flag`s exist on the Click command they are written next to (CP-10 / WO-148).

tests/test_cli_docs_match_source.py already checks command and subcommand names. This file goes
further and walks the same Typer/Click tree (no subprocess, no network) to check options:
- every `--flag` in a `freemyid <command> ...` example in docs/CLI.md, README.md and
  docs/USER_GUIDE.md is an option of that command (or its group), or a global option;
- every `--flag` in the first two columns of the docs/CLI.md command table is an option of the
  command in that row;
- every visible top-level command is also shown as `freemyid <command>` somewhere in those docs.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import typer.main

from freemyid.cli import app

ROOT = Path(__file__).resolve().parents[2]
DOC_FILES = ("docs/CLI.md", "README.md", "docs/USER_GUIDE.md")

FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")
SPAN = re.compile(r"`([^`\n]+)`")
START = re.compile(r"^(?:\S*[/=])?freemyid[ \t]+(.*)$")
WORD = re.compile(r"^[a-z][a-z0-9-]*$")

_root = typer.main.get_command(app)


def _options(cmd: Any) -> set[str]:
    opts: set[str] = set()
    for param in getattr(cmd, "params", []):
        opts.update(o for o in (*param.opts, *param.secondary_opts) if o.startswith("--"))
    return opts


def _walk(tokens: list[str]) -> tuple[list[str], set[str]]:
    """Command path named by leading words, and the options valid at that path."""
    cmd: Any = _root
    path: list[str] = []
    valid = _options(cmd) | {"--help"}
    for tok in tokens:
        subs = getattr(cmd, "commands", None)
        if not subs or not WORD.match(tok) or tok not in subs:
            break
        cmd = subs[tok]
        path.append(tok)
        valid |= _options(cmd)
    return path, valid


def _flag_cases(rel: str) -> list[tuple[str, str, str]]:
    """(file, example, flag) for each flag in a `freemyid ...` example."""
    cases: list[tuple[str, str, str]] = []
    fenced = False
    for raw in (ROOT / rel).read_text(encoding="utf-8").splitlines():
        if raw.lstrip().startswith("```"):
            fenced = not fenced
            continue
        candidates = [raw.strip().removeprefix("$ ")] if fenced else SPAN.findall(raw)
        for cand in candidates:
            m = START.match(cand.strip())
            if not m:
                continue
            body = m.group(1).split("#")[0].split("|")[0]
            for flag in FLAG.findall(body):
                cases.append((rel, "freemyid " + body.strip(), flag))
    return list(dict.fromkeys(cases))


def _table_cases() -> list[tuple[str, str]]:
    """(command, flag) for each flag in the Commands table row of docs/CLI.md."""
    text = (ROOT / "docs/CLI.md").read_text(encoding="utf-8")
    m = re.search(r"^## Commands\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert m, "docs/CLI.md has no '## Commands' section"
    cases: list[tuple[str, str]] = []
    for line in m.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cols = line.split("|")
        first = SPAN.findall(cols[1])
        if not first or not WORD.match(first[0].split()[0]):
            continue
        cmd = first[0].split()[0]
        for flag in FLAG.findall(first[0] + " " + cols[2]):
            cases.append((cmd, flag))
    return list(dict.fromkeys(cases))


def test_flag_scanners_find_something() -> None:
    assert all(_flag_cases(rel) for rel in DOC_FILES)
    assert _table_cases()


@pytest.mark.parametrize(
    ("rel", "example", "flag"),
    [c for rel in DOC_FILES for c in _flag_cases(rel)],
    ids=lambda v: v,
)
def test_example_flag_exists_on_command(rel: str, example: str, flag: str) -> None:
    tokens = [t.rstrip(",.;:)") for t in example.split()[1:]]
    path, valid = _walk(tokens)
    where = " ".join(["freemyid", *path])
    assert flag in valid, f"{rel}: `{example}`: `{flag}` is not an option of `{where}`"


@pytest.mark.parametrize(("cmd", "flag"), _table_cases(), ids=lambda v: v)
def test_table_flag_exists_on_row_command(cmd: str, flag: str) -> None:
    _, valid = _walk([cmd])
    top = _root.commands.get(cmd)
    for sub in getattr(top, "commands", {}).values():
        valid |= _options(sub)
    assert flag in valid, (
        f"docs/CLI.md table row `{cmd}`: `{flag}` is not an option of `{cmd}` or its subcommands"
    )


def test_every_visible_top_level_command_is_written_as_freemyid_example() -> None:
    """Beyond the table: each top-level command also appears in some docs `freemyid <cmd>` text."""
    seen: set[str] = set()
    for rel in DOC_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        seen.update(re.findall(r"freemyid[ \t]+([a-z][a-z0-9-]*)", text))
    missing = sorted(
        n for n, c in _root.commands.items() if not getattr(c, "hidden", False) and n not in seen
    )
    assert not missing, f"commands never shown as `freemyid <command>` in the docs: {missing}"
