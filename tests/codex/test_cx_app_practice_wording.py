"""Offline guard against overbroad practice-mode promises in app copy."""
from __future__ import annotations

import ast
import html
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRACTICE = re.compile(r"\bpractice[\s-]+mode\b", re.IGNORECASE)
BAD = re.compile(
    r"\bnothing\s+(?:is\s+sent|goes\s+out)\b(?!\s+to\s+us\b)"
    r"|\bsends\s+nothing\b(?!\s+to\s+us\b)"
    # 0.3.1: dashboard banner said "is looking but is not sending anything yet".
    r"|\b(?:is\s+not|isn't|not)\s+sending\s+anything\b(?!\s+to\s+us\b)"
    r"|\b(?:does\s+not|doesn't|will\s+not|won't)\s+send\s+anything\b(?!\s+to\s+us\b)",
    re.IGNORECASE,
)
# Preserve quoted JS strings while discarding comments.
COMMENTS = re.compile(
    r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)'''
    r"|<!--.*?-->|\{#.*?#\}|/\*.*?\*/|//[^\n]*", re.DOTALL,
)
SUFFIXES = {".py", ".html", ".htm", ".js", ".jinja", ".jinja2", ".j2"}


def misleading(text: str) -> bool:
    """Require practice context and an unqualified promise in the same copy unit."""
    text = html.unescape(re.sub(r"<[^>]*>", " ", text))
    text = re.sub(r"\s+", " ", text)
    return bool(PRACTICE.search(text) and BAD.search(text))


def copy_units(source: str, suffix: str) -> list[tuple[int, str]]:
    if suffix != ".py":
        def strip_comment(match: re.Match[str]) -> str:
            return match[0] if match[1] else "\n" * match[0].count("\n")

        clean = COMMENTS.sub(strip_comment, source)
        units = []
        for match in re.finditer(r"[^\n]*(?:\n(?!\s*\n)[^\n]*)*", clean):
            if match[0].strip():
                leading = match[0][:len(match[0]) - len(match[0].lstrip())]
                line = clean.count("\n", 0, match.start()) + leading.count("\n") + 1
                units.append((line, match[0]))
        return units
    tree = ast.parse(source)
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    units: list[tuple[int, str]] = []
    # Adjacent literals ("a" "b") are already one Constant in the ast. Join explicit
    # "a" + "b" chains too, so a sentence split that way is still one copy unit.
    concat_parts: set[int] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)
                and id(node) not in concat_parts):
            parts: list[ast.expr] = []
            stack: list[ast.expr] = [node]
            while stack:
                cur = stack.pop()
                if isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Add):
                    concat_parts.add(id(cur))
                    stack += [cur.right, cur.left]
                else:
                    parts.append(cur)
            strs = [p.value for p in parts
                    if isinstance(p, ast.Constant) and isinstance(p.value, str)]
            if len(strs) > 1:
                units.append((node.lineno, " ".join(strs)))
    joined_constants = {id(value) for node in ast.walk(tree)
                        if isinstance(node, ast.JoinedStr) for value in node.values}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings | joined_constants):
            units.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):
            text = " ".join(n.value for n in node.values
                            if isinstance(n, ast.Constant) and isinstance(n.value, str))
            units.append((node.lineno, text))
    return units


def findings(path: Path) -> list[tuple[int, str]]:
    return [(line, text) for line, text in copy_units(path.read_text(), path.suffix)
            if misleading(text)]


def app_paths(root: Path) -> list[Path]:
    return sorted({
        *(p for p in (root / "src/freemyid/wizard").rglob("*")
          if p.is_file() and p.suffix in SUFFIXES),
        root / "src/freemyid/cli.py", root / "src/freemyid/setup_config.py",
    })


@pytest.mark.parametrize("text", [
    "Practice mode: nothing is sent.", "In practice mode nothing goes out until you say so.",
    "Practice mode sends nothing.", "PRACTICE MODE. Nothing IS sent.",
])
def test_rejects_overbroad_practice_promises(text: str) -> None:
    assert misleading(text)


@pytest.mark.parametrize("text", [
    "In practice mode nothing is sent to us.",
    "Practice mode sends nothing to us, but searches sites.",
    "Practice mode: no removal requests go out until you say so.",
    "Practice mode still searches sites; no removal requests are sent.",
    "Nothing is sent until you approve this email.",
    "If you press No, nothing will be sent for this listing.",
])
def test_allows_qualified_and_unrelated_copy(text: str) -> None:
    assert not misleading(text)


@pytest.mark.parametrize("suffix,source", [
    (".py", ('# Practice mode sends nothing.\n"""Practice mode sends nothing."""\n'
     'def example():\n    """Practice mode sends nothing."""\n'
     '    print("Practice mode sends nothing.")\n')),
    (".html", '<!-- Practice mode sends nothing. -->\n<p>Practice mode sends nothing.</p>'),
    (".j2", '{# Practice mode sends nothing. #}\n<p>Practice mode sends nothing.</p>'),
    (".js", ('// Practice mode sends nothing.\n'
     '/* Practice mode sends nothing. */\nalert("Practice mode sends nothing.");')),
])
def test_temp_sources_ignore_comments_and_docstrings_but_flag_copy(
    tmp_path: Path, suffix: str, source: str,
) -> None:
    path = tmp_path / ("synthetic" + suffix)
    path.write_text(source)
    hits = findings(path)
    assert len(hits) == 1
    assert hits[0][0] == len(source.splitlines())
    path.write_text('print("In practice mode no removal requests go out.")'
                    if suffix == ".py" else "In practice mode nothing is sent to us.")
    assert findings(path) == []


def test_python_adjacent_literals_and_fstrings_are_checked(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.py"
    path.write_text('print("Practice mode " "sends nothing.")\n'
                    'print(f"Practice mode {label}: nothing goes out.")\n')
    assert {line for line, _ in findings(path)} == {1, 2}


def test_split_sentence_with_not_sending_anything_is_flagged(tmp_path: Path) -> None:
    """0.3.1 gap: the dashboard banner split this sentence over adjacent literals."""
    path = tmp_path / "synthetic.py"
    path.write_text("body = ('<div class=banner><b>Practice mode.</b> Free My ID is looking'\n"
                    "        ' but is not sending '\n"
                    "        'anything yet.</div>')\n"
                    'msg = "Practice mode: Free My ID " + "does not send anything."\n'
                    'ok = ("Practice mode: Free My ID is looking for your listings, but no "\n'
                    '      "removal requests go out until you say so.")\n')
    assert {line for line, _ in findings(path)} == {1, 4}


KNOWN = "src/freemyid/setup_config.py"


@pytest.mark.parametrize("path", app_paths(ROOT), ids=lambda p: str(p.relative_to(ROOT)))
def test_app_practice_copy_has_no_unqualified_no_sending_claims(path: Path) -> None:
    hits = findings(path)
    assert not hits, f"{path.relative_to(ROOT)}: {hits}"


# WO-218 finding fixed in-house: setup_config.py:300 no longer promises nothing is sent.
def test_setup_practice_copy_does_not_promise_nothing_is_sent() -> None:
    hits = findings(ROOT / KNOWN)
    assert not [(line, text) for line, text in hits if line == 300], hits
