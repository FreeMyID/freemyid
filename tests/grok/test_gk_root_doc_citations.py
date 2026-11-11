"""Guard ``file.py:NNN`` citations in the three root user docs (WO-323).

Reference: ``tests/copilot/test_cp_source_citations.py``. That guard checks
``docs/user/`` only. This file covers the three root user docs it skips:
``docs/USER_GUIDE.md``, ``docs/CLI.md``, and ``FAMILY_QUICK_START.md``.

Also checked, and not duplicated: ``tests/codex/test_cx_dev_source_citations.py``
(``docs/dev/`` and ``docs/i18n/``) and ``tests/codex/test_cx_dev_broker_citations.py``
(``docs/dev/CONTRIBUTING_BROKERS.md``). ``tests/grok/`` had no citation guard.

Rules match the reference. A citation resolves to exactly one file under
``src/freemyid/``, the cited line exists, and quoted text on that line appears
in the file. Python joins of adjacent string literals count; separate
statements do not. A file with no citations passes. A path outside
``src/freemyid/``, including ``packaging/windows/splash_win.py:N``, does not pass.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

import pytest

ROOT = Path(__file__).resolve().parents[2]
ROOT_DOCS: tuple[str, ...] = (
    "docs/USER_GUIDE.md",
    "docs/CLI.md",
    "FAMILY_QUICK_START.md",
)
CITATION = re.compile(
    r"(?P<reference>(?:src/freemyid/)?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py):"
    r"(?P<line>[1-9][0-9]*)(?:-[1-9][0-9]*)?"
)
QUOTED_TEXT = re.compile(r'"([^"\n]+)"|\'([^\'\n]+)\'|`([^`\n]+)`')


class Citation(NamedTuple):
    doc: Path
    doc_line: int
    reference: str
    source_line: int
    text: str


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_under_source(root: Path, path: Path) -> bool:
    """True only for a real file whose resolved path stays under ``src/freemyid``."""
    source = (root / "src" / "freemyid").resolve()
    try:
        resolved = path.resolve()
        resolved.relative_to(source)
    except (OSError, ValueError):
        return False
    return resolved.is_file()


def _source_matches(root: Path, reference: str) -> list[Path]:
    source = root / "src" / "freemyid"
    if reference.startswith("src/freemyid/"):
        candidate = root / reference
        return [candidate] if _is_under_source(root, candidate) else []
    if not source.is_dir():
        return []
    matches = [
        path
        for path in source.rglob("*.py")
        if path.name == reference and _is_under_source(root, path)
    ]
    return sorted(matches)


def _citations_in(doc: Path) -> list[Citation]:
    found: list[Citation] = []
    for doc_line, text in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        for match in CITATION.finditer(text):
            found.append(Citation(doc, doc_line, match["reference"], int(match["line"]), text))
    return found


def _quoted_ui_text(text: str) -> list[str]:
    """Quoted text on a citation line, excluding the citation itself."""
    without_citations = CITATION.sub("", text).replace("``", "")
    found: list[str] = []
    for match in QUOTED_TEXT.finditer(without_citations):
        found.append(next(part for part in match.groups() if part is not None))
    return found


def _python_strings(source: str) -> list[str]:
    """String constants as Python parses them.

    Adjacent literals (``"a " "b"``) are one constant. Two statements stay two,
    including a string on the line after ``return`` (same rule as the reference).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _where(root: Path, case: Citation) -> str:
    return f"{_relative(root, case.doc)}:{case.doc_line}"


def _resolution_problem(root: Path, case: Citation) -> str | None:
    matches = _source_matches(root, case.reference)
    where = _where(root, case)
    label = f"{case.reference}:{case.source_line}"
    if not matches:
        return f"{where}: {label} resolves to no files"
    if len(matches) != 1:
        shown = [_relative(root, path) for path in matches]
        return f"{where}: {label} is ambiguous; matches: {shown}"
    line_count = len(matches[0].read_text(encoding="utf-8").splitlines())
    if case.source_line > line_count:
        return f"{where}: {label} does not exist"
    return None


def _missing_quotes(root: Path, case: Citation) -> list[str]:
    matches = _source_matches(root, case.reference)
    if len(matches) != 1:
        return []
    source_path = matches[0]
    source = source_path.read_text(encoding="utf-8")
    # UI text is often split across adjacent literals. Search those joins too.
    joined = _python_strings(source) if source_path.suffix == ".py" else []
    return [
        phrase
        for phrase in _quoted_ui_text(case.text)
        if phrase not in source and not any(phrase in literal for literal in joined)
    ]


def _citation_id(case: Citation) -> str:
    try:
        relative = _relative(ROOT, case.doc)
    except ValueError:
        relative = case.doc.name
    return f"{relative}:{case.doc_line}->{case.reference}:{case.source_line}"


def _collect_real_cases() -> list[Citation]:
    found: list[Citation] = []
    for relative in ROOT_DOCS:
        found.extend(_citations_in(ROOT / relative))
    return found


CASES = _collect_real_cases()

# Quote mismatches in docs this WO may not edit. Line existence still passes.
KNOWN_BROKEN_QUOTES: dict[tuple[str, int, str, int], str] = {
    ("docs/CLI.md", 83, "cli.py", 168): (
        "docs/CLI.md:83 quotes `--web --prefill`, which is not text in src/freemyid/cli.py"
    ),
    ("docs/CLI.md", 85, "cli.py", 520): (
        "docs/CLI.md:85 quotes `profile add [--prefill]`, which is not text in "
        "src/freemyid/cli.py; cli.py:520 is inside report(), not profile add"
    ),
    ("docs/CLI.md", 93, "cli.py", 761): (
        "docs/CLI.md:93 quotes `-p/--profile`, which is not text in src/freemyid/cli.py"
    ),
    ("docs/CLI.md", 93, "cli.py", 799): (
        "docs/CLI.md:93 quotes `-p/--profile`, which is not text in src/freemyid/cli.py"
    ),
    ("docs/CLI.md", 94, "cli.py", 181): (
        "docs/CLI.md:94 quotes `doctor --offline`, which is not text in src/freemyid/cli.py"
    ),
    ("docs/CLI.md", 94, "src/freemyid/doctor.py", 56): (
        "docs/CLI.md:94 quotes `doctor --offline`, which is not text in "
        "src/freemyid/doctor.py"
    ),
}


def _resolution_params() -> list[object]:
    if not CASES:
        return [pytest.param(None, id="no-citations")]
    return [pytest.param(case, id=_citation_id(case)) for case in CASES]


def _quote_params() -> list[object]:
    if not CASES:
        return [pytest.param(None, id="no-citations")]
    params: list[object] = []
    for case in CASES:
        key = (_relative(ROOT, case.doc), case.doc_line, case.reference, case.source_line)
        reason = KNOWN_BROKEN_QUOTES.get(key)
        if reason:
            params.append(
                pytest.param(
                    case,
                    marks=pytest.mark.xfail(strict=True, reason=reason),
                    id=_citation_id(case),
                )
            )
        else:
            params.append(pytest.param(case, id=_citation_id(case)))
    return params


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_only_literals_python_concatenates_are_joined() -> None:
    joined = _python_strings('msg = ("Do not "\n       "send your password.")\n')
    assert any("Do not send your password." in item for item in joined)
    split = _python_strings('msg = "Do not "\n"send your password."\n')
    assert not any("Do not send your password." in item for item in split)
    returned = _python_strings('def f():\n    return "Please "\n    "try again."\n')
    assert not any("Please try again." in item for item in returned)


@pytest.mark.parametrize("case", _resolution_params())
def test_source_citation_resolves_to_one_current_line(case: Citation | None) -> None:
    if case is None:
        return
    problem = _resolution_problem(ROOT, case)
    assert problem is None, problem


@pytest.mark.parametrize("case", _quote_params())
def test_quoted_ui_text_exists_in_cited_source(case: Citation | None) -> None:
    if case is None:
        return
    problem = _resolution_problem(ROOT, case)
    assert problem is None, problem
    missing = _missing_quotes(ROOT, case)
    assert not missing, (
        f"{_where(ROOT, case)}: {case.reference}:{case.source_line} does not contain "
        f"quoted UI text {missing}"
    )


def test_missing_file_fails(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/present.py", "one\n")
    doc = tmp_path / "notes.md"
    _write(doc, "See `missing.py:1`.\n")
    problem = _resolution_problem(tmp_path, _citations_in(doc)[0])
    assert problem is not None
    assert "resolves to no files" in problem


def test_line_past_the_end_fails(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/short.py", "one\ntwo\n")
    doc = tmp_path / "notes.md"
    _write(doc, "See `short.py:4`.\n")
    problem = _resolution_problem(tmp_path, _citations_in(doc)[0])
    assert problem is not None
    assert "does not exist" in problem


def test_ambiguous_file_name_fails(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/a/widget.py", 'label = "Hello"\n')
    _write(tmp_path / "src/freemyid/b/widget.py", 'label = "Hello"\n')
    doc = tmp_path / "notes.md"
    _write(
        doc,
        "Bare (`widget.py:1`).\n"
        'Full path says "Hello" (`src/freemyid/a/widget.py:1`).\n',
    )
    bare, full = _citations_in(doc)
    problem = _resolution_problem(tmp_path, bare)
    assert problem is not None
    assert "ambiguous" in problem
    assert "src/freemyid/a/widget.py" in problem
    assert "src/freemyid/b/widget.py" in problem
    assert _resolution_problem(tmp_path, full) is None
    assert _missing_quotes(tmp_path, full) == []


def test_quoted_text_not_in_source_fails(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/phrase.py", 'label = "present"\n')
    doc = tmp_path / "notes.md"
    _write(doc, 'The screen says "not in the source" (`phrase.py:1`).\n')
    case = _citations_in(doc)[0]
    assert _resolution_problem(tmp_path, case) is None
    assert _missing_quotes(tmp_path, case) == ["not in the source"]


def test_good_citation_passes(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/phrase.py", 'label = "Hello there"\nsecond\n')
    doc = tmp_path / "notes.md"
    _write(doc, 'See "Hello there" (`phrase.py:1-2`).\n')
    case = _citations_in(doc)[0]
    assert case.source_line == 1
    assert _resolution_problem(tmp_path, case) is None
    assert _missing_quotes(tmp_path, case) == []


def test_adjacent_string_literals_pass(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/phrase.py", 'label = ("Hello "\n        "there")\n')
    doc = tmp_path / "notes.md"
    _write(doc, 'See "Hello there" (`phrase.py:1`).\n')
    source = (tmp_path / "src/freemyid/phrase.py").read_text(encoding="utf-8")
    case = _citations_in(doc)[0]
    assert "Hello there" not in source
    assert _resolution_problem(tmp_path, case) is None
    assert _missing_quotes(tmp_path, case) == []


def test_unjoined_string_literals_fail(tmp_path: Path) -> None:
    _write(tmp_path / "src/freemyid/phrase.py", 'label = "Hello "\n"there"\n')
    doc = tmp_path / "notes.md"
    _write(doc, 'See "Hello there" (`phrase.py:1`).\n')
    case = _citations_in(doc)[0]
    assert _resolution_problem(tmp_path, case) is None
    assert _missing_quotes(tmp_path, case) == ["Hello there"]


def test_document_with_no_citations_passes(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "USER_GUIDE.md"
    _write(doc, "# Guide\n\nNo file and line pointers in this copy.\n")
    assert _citations_in(doc) == []


def test_path_outside_src_freemyid_does_not_pass(tmp_path: Path) -> None:
    _write(tmp_path / "packaging/windows/splash_win.py", "one\ntwo\nthree\n")
    _write(tmp_path / "src/freemyid/app.py", "print('ok')\n")
    doc = tmp_path / "notes.md"
    _write(
        doc,
        "See `packaging/windows/splash_win.py:2`.\n"
        "See `splash_win.py:2`.\n"
        "See `src/freemyid/../../packaging/windows/splash_win.py:2`.\n",
    )
    cases = _citations_in(doc)
    assert len(cases) == 3
    for case in cases:
        problem = _resolution_problem(tmp_path, case)
        assert problem is not None
        assert "resolves to no files" in problem
