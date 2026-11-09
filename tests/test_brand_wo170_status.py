"""WO-170 OG image: its `freemyid status` lines must match what the CLI prints (CR #66)."""
from __future__ import annotations

import ast
import re

from tests.conftest import ROOT

SCRIPT = ROOT / "brand/src/build_wo170_171.py"
CLI = ROOT / "src/freemyid/cli.py"


def _constants() -> dict[str, str]:
    """Read the script's string constants without running it (it renders on import)."""
    out = {}
    for node in ast.parse(SCRIPT.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = node.value.value
    return out


def test_og_status_panel_matches_the_cli_wording() -> None:
    src, c = CLI.read_text(encoding="utf-8"), _constants()
    todo = re.search(r"\{len\(todos\)\}( item\(s\) need you: [^\[]*)\[/\]", src)
    note = re.search(r"\"\[dim\]('removed' means [^\"]*)\"", src)
    assert todo and note, "freemyid status wording moved: update this test and the image"
    assert c["STATUS_TODO"] == "1" + todo.group(1)
    assert c["STATUS_NOTE"] == note.group(1).strip()

