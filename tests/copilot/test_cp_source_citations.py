"""Keep docs/user source citations tied to the current local source tree (WO-165).

This is deliberately offline: it reads only documentation and ``src/freemyid``.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "freemyid"
DOCS = sorted((ROOT / "docs" / "user").glob("*.md"))

CITATION = re.compile(
    r"(?P<reference>(?:src/freemyid/)?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py):"
    r"(?P<line>[1-9][0-9]*)(?:-[1-9][0-9]*)?"
)
QUOTED_TEXT = re.compile(r'"([^"\n]+)"|\'([^\'\n]+)\'|`([^`\n]+)`')


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _citations() -> list[tuple[Path, int, str, int, str]]:
    found: list[tuple[Path, int, str, int, str]] = []
    for doc in DOCS:
        for doc_line, text in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for match in CITATION.finditer(text):
                found.append(
                    (doc, doc_line, match["reference"], int(match["line"]), text)
                )
    return found


def _source_matches(reference: str) -> list[Path]:
    if reference.startswith("src/freemyid/"):
        candidate = ROOT / reference
        return [candidate] if candidate.is_file() else []
    return sorted(path for path in SOURCE.rglob("*.py") if path.name == reference)


def _quoted_ui_text(text: str) -> list[str]:
    """Quoted UI text on a citation line, excluding the citation itself."""
    without_citations = CITATION.sub("", text)
    without_citations = without_citations.replace("``", "")
    return [next(part for part in match.groups() if part is not None) for match in QUOTED_TEXT.finditer(without_citations)]


def _citation_id(case: tuple[Path, int, str, int, str]) -> str:
    doc, doc_line, reference, source_line, _ = case
    return f"{_relative(doc)}:{doc_line}->{reference}:{source_line}"


CASES = _citations()
KNOWN_BROKEN_UI_CITATIONS = {
}


def _quoted_ui_cases() -> list[object]:
    cases: list[object] = []
    for case in CASES:
        doc, doc_line, reference, source_line, _ = case
        reason = KNOWN_BROKEN_UI_CITATIONS.get(
            (_relative(doc), doc_line, reference, source_line)
        )
        if reason:
            cases.append(
                pytest.param(
                    case,
                    marks=pytest.mark.xfail(strict=True, reason=reason),
                    id=_citation_id(case),
                )
            )
        else:
            cases.append(pytest.param(case, id=_citation_id(case)))
    return cases


def test_docs_contain_source_citations() -> None:
    assert CASES, "docs/user contains no file.py:NNN citations"


@pytest.mark.parametrize("case", CASES, ids=_citation_id)
def test_source_citation_resolves_to_one_current_line(
    case: tuple[Path, int, str, int, str],
) -> None:
    doc, doc_line, reference, source_line, _ = case
    matches = _source_matches(reference)
    where = f"{_relative(doc)}:{doc_line}"
    assert matches, f"{where}: {reference}:{source_line} resolves to no files"
    if len(matches) != 1:
        pytest.fail(
            f"{where}: {reference}:{source_line} is ambiguous; matches: "
            f"{[_relative(path) for path in matches]}"
        )
    assert source_line <= len(matches[0].read_text(encoding="utf-8").splitlines()), (
        f"{where}: {reference}:{source_line} does not exist"
    )


@pytest.mark.parametrize("case", _quoted_ui_cases())
def test_quoted_ui_text_exists_in_cited_source(
    case: tuple[Path, int, str, int, str],
) -> None:
    doc, doc_line, reference, source_line, text = case
    matches = _source_matches(reference)
    assert len(matches) == 1, f"{_relative(doc)}:{doc_line}: cannot check {reference}"
    source = matches[0].read_text(encoding="utf-8")
    # UI text in Python is often split across adjacent string literals on several lines
    # ("...approved "\n    "it. ..."): also search a copy with those joins removed.
    joined = re.sub(r"""(["'])\s*\n\s*[rbfu]{0,2}\1""", "", source)
    missing = [phrase for phrase in _quoted_ui_text(text)
               if phrase not in source and phrase not in joined]
    assert not missing, (
        f"{_relative(doc)}:{doc_line}: {reference}:{source_line} does not contain "
        f"quoted UI text {missing}"
    )
