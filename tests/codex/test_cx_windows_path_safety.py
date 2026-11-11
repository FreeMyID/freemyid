"""Keep Codex and Grok test suites portable across Windows and POSIX."""
from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_TEST_DIRS = (Path("tests/codex"), Path("tests/grok"))
URL_BASE_NAMES = {"origin", "url", "uri", "href", "endpoint", "base_url", "host"}
PATH_BASE_NAMES = {
    "p", "root", "base", "tmp_path", "home", "directory", "folder", "file_path",
    "root_path", "base_path",
}


def _is_os_sep(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "sep"
            and isinstance(node.value, ast.Name) and node.value.id == "os")


def _contains_os_sep(node: ast.AST) -> bool:
    return any(_is_os_sep(child) for child in ast.walk(node))


def _is_leading_slash_check(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "startswith" and node.args
            and isinstance(node.args[0], ast.Constant) and node.args[0].value == "/")


def _scope_for(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return current
    return next((ancestor for ancestor in parents.values() if isinstance(ancestor, ast.Module)), node)


def _has_path_constructor_parent(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> bool:
    current = node
    for _ in range(5):
        if current not in parents:
            return False
        current = parents[current]
        if isinstance(current, ast.Call):
            func = current.func
            if isinstance(func, ast.Name) and func.id in {"Path", "PurePath", "open"}:
                return True
            if isinstance(func, ast.Attribute) and func.attr == "open":
                return True
    return False


def _has_tmp_filesystem_path(
    node: ast.Constant, parents: dict[ast.AST, ast.AST]
) -> bool:
    value = node.value
    if not isinstance(value, str) or not value.startswith("/tmp/"):
        return False
    return _has_path_constructor_parent(node, parents)


def _root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id.lower()
    if isinstance(node, ast.Call) and node.args:
        return _root_name(node.args[0])
    if isinstance(node, ast.BinOp):
        return _root_name(node.left)
    if isinstance(node, ast.Attribute):
        return _root_name(node.value)
    return None


def _looks_like_path_segment(value: str) -> bool:
    return (value.startswith("/") and not any(char.isspace() for char in value)
            and not value.startswith("//") and bool(Path(value).suffix))


def _has_separator(value: object) -> bool:
    return isinstance(value, str) and ("/" in value or "\\" in value)


def _is_dynamic_string_join(node: ast.BinOp) -> bool:
    if not isinstance(node.op, ast.Add):
        return False
    if _root_name(node.left) in URL_BASE_NAMES or _root_name(node.right) in URL_BASE_NAMES:
        return False
    sides = (node.left, node.right)
    # A path-like variable alone is not enough ("base + pad" is not a path): the other
    # side must also carry a separator.
    has_path_base = any(_root_name(side) in PATH_BASE_NAMES for side in sides) and any(
        isinstance(side, ast.Constant) and _has_separator(side.value) for side in sides
    )
    has_slash_literal = any(
        isinstance(side, ast.Constant) and isinstance(side.value, str)
        and _looks_like_path_segment(side.value)
        for side in sides
    )
    has_dynamic_side = any(not isinstance(side, ast.Constant) for side in sides)
    return has_dynamic_side and (has_slash_literal or has_path_base)


def _is_dynamic_fstring_join(node: ast.JoinedStr) -> bool:
    if any(isinstance(part, ast.FormattedValue)
           and _root_name(part.value) in URL_BASE_NAMES for part in node.values):
        return False
    has_dynamic_part = any(isinstance(part, ast.FormattedValue) for part in node.values)
    has_path_base = any(
        isinstance(part, ast.FormattedValue)
        and _root_name(part.value) in PATH_BASE_NAMES for part in node.values
    ) and any(
        isinstance(part, ast.Constant) and _has_separator(part.value) for part in node.values
    )
    has_slash_part = any(
        isinstance(part, ast.Constant) and isinstance(part.value, str)
        and _looks_like_path_segment(part.value)
        for part in node.values
    )
    return has_dynamic_part and (has_slash_part or has_path_base)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _path_findings(source: str, file_path: Path, repo_root: Path) -> list[str]:
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as error:
        return [f"{file_path.relative_to(repo_root).as_posix()}:{error.lineno}: cannot parse Python"]

    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    relative_path = file_path.relative_to(repo_root).as_posix()
    findings: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and _has_tmp_filesystem_path(node, parents):
            findings.append(f"{relative_path}:{node.lineno}: hard-coded /tmp filesystem path")
        elif isinstance(node, ast.BinOp) and _is_dynamic_string_join(node):
            findings.append(f"{relative_path}:{node.lineno}: string path joined with '/'")
        elif isinstance(node, ast.JoinedStr) and _is_dynamic_fstring_join(node):
            findings.append(f"{relative_path}:{node.lineno}: f-string path joined with '/'")
        elif isinstance(node, ast.Compare) and _contains_os_sep(node):
            compared = (node.left, *node.comparators)
            if any(isinstance(item, ast.Constant) and item.value in {"/", "\\"}
                   for item in compared):
                findings.append(f"{relative_path}:{node.lineno}: os.sep assumes a path separator")
        elif (isinstance(node, ast.Call) and _call_name(node) in {"split", "startswith"}
              and any(_is_os_sep(arg) for arg in node.args)):
            findings.append(f"{relative_path}:{node.lineno}: os.sep used as a path prefix")

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "is_absolute"):
            continue
        scope = _scope_for(node, parents)
        has_slash_guard = any(_is_leading_slash_check(child) for child in ast.walk(scope))
        if not has_slash_guard:
            findings.append(
                f"{relative_path}:{node.lineno}: is_absolute() lacks a leading '/' check"
            )

    return findings


def _scan_directories(repo_root: Path, directories: Iterable[Path]) -> list[str]:
    findings: list[str] = []
    for relative_dir in directories:
        directory = repo_root / relative_dir
        if not directory.is_dir():
            continue
        for file_path in sorted(directory.rglob("*.py")):
            findings.extend(_path_findings(file_path.read_text(encoding="utf-8"),
                                           file_path, repo_root))
    return findings


def scan_vendor_test_paths(repo_root: Path) -> list[str]:
    """Report Windows-unsafe patterns in the Codex and Grok test lanes."""
    return _scan_directories(repo_root, VENDOR_TEST_DIRS)


def test_current_codex_and_grok_tests_have_windows_safe_paths() -> None:
    findings = scan_vendor_test_paths(REPO_ROOT)
    assert not findings, "Windows-unsafe vendor test paths:\n" + "\n".join(findings)


def test_scanner_finds_unsafe_patterns_in_both_vendor_lanes(tmp_path: Path) -> None:
    codex = tmp_path / "tests" / "codex"
    grok = tmp_path / "tests" / "grok"
    codex.mkdir(parents=True)
    grok.mkdir(parents=True)
    (codex / "bad_paths.py").write_text(
        '''from pathlib import Path
import os

def bad(raw, base):
    temp = Path("/tmp/profile")
    joined = str(base) + "/report.json"
    if os.sep == "/":
        return Path(raw).is_absolute()
    return temp, joined
''',
        encoding="utf-8",
    )
    (grok / "unsafe_absolute_check.py").write_text(
        "from pathlib import Path\n"
        "def bad(raw):\n"
        "    return Path(raw).is_absolute()\n",
        encoding="utf-8",
    )

    findings = scan_vendor_test_paths(tmp_path)

    assert any("tests/codex/bad_paths.py:5: hard-coded /tmp" in item for item in findings)
    assert any("tests/codex/bad_paths.py:6: string path joined" in item for item in findings)
    assert any("tests/codex/bad_paths.py:7: os.sep assumes" in item for item in findings)
    assert any("tests/grok/unsafe_absolute_check.py:3: is_absolute()" in item
               for item in findings)


def test_scanner_accepts_pathlib_and_leading_slash_rejection(tmp_path: Path) -> None:
    codex = tmp_path / "tests" / "codex"
    codex.mkdir(parents=True)
    (codex / "safe_paths.py").write_text(
        '''from pathlib import Path

def safe(raw, tmp_path):
    target = tmp_path / "report.json"
    path = Path(raw)
    if raw.startswith("/") or path.is_absolute():
        return None
    return target

def display_only():
    return "A sample path: /tmp/reference.py:7"
''',
        encoding="utf-8",
    )

    assert scan_vendor_test_paths(tmp_path) == []


def test_scanner_ignores_urls_labels_and_plain_string_math(tmp_path: Path) -> None:
    codex = tmp_path / "tests" / "codex"
    codex.mkdir(parents=True)
    (codex / "not_paths.py").write_text(
        '''HOST = "http://127.0.0.1:1"

def values(base, pad, root, folder, count):
    url = f"{HOST}/error.html"
    name = f"{base}-{count}"
    padded = base + pad
    label = f"{root}:{count}"
    shown = f"Sample {folder}"
    return url, name, padded, label, shown
''',
        encoding="utf-8",
    )

    assert scan_vendor_test_paths(tmp_path) == []
