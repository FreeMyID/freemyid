"""Keep cited file-and-line references in selected contributor docs resolvable.

This verifies file existence and line bounds only. A valid citation does not
prove that the cited code still supports the surrounding prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = (
    "docs/dev/ARCHITECTURE.md",
    "docs/dev/TESTING.md",
    "docs/i18n/STRINGS.md",
    "docs/i18n/GLOSSARY_ES.md",
)
CODE_SPAN = re.compile(r"`([^`]+)`")
SOURCE_SUFFIX = r"(?:py|md|toml|ya?ml|ts|tsx|astro|css|json|html|js|mjs|txt)"
REFERENCE = re.compile(
    rf"^(?P<path>[^:\s`]+\.{SOURCE_SUFFIX}):(?P<lines>.*)$",
    re.IGNORECASE,
)
LINE_LIST = re.compile(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*\Z")


@dataclass(frozen=True)
class Citation:
    path: str
    ranges: tuple[tuple[int, int], ...]


def parse_citation(token: str) -> Citation | None:
    """Parse an explicit file:line citation from one inline code span.

    Ordinary code spans such as ``freemyid.cli:app`` are not citations. Once a
    code span looks like a known source filename followed by a colon, malformed
    line syntax is an error so it cannot silently evade the document check.
    """
    match = REFERENCE.fullmatch(token)
    if match is None:
        return None

    raw_path = match.group("path")
    path = Path(raw_path)
    if (path.is_absolute() or raw_path.startswith("/") or ".." in path.parts
            or "\\" in raw_path or ":" in raw_path):
        raise ValueError("path must stay repository-relative")

    raw_lines = match.group("lines")
    if not LINE_LIST.fullmatch(raw_lines):
        raise ValueError("expected line numbers like 12,14-18")

    ranges: list[tuple[int, int]] = []
    for item in raw_lines.split(","):
        start_text, separator, end_text = item.partition("-")
        start = int(start_text)
        end = int(end_text) if separator else start
        if start < 1 or end < start:
            raise ValueError(f"invalid line range {item!r}")
        ranges.append((start, end))
    return Citation(raw_path.removeprefix("./"), tuple(ranges))


def document_findings(document: str, *, root: Path = ROOT) -> list[str]:
    """Return missing or out-of-bounds citation findings for one Markdown file."""
    document_path = root / document
    findings: list[str] = []
    for token in CODE_SPAN.findall(document_path.read_text(encoding="utf-8")):
        try:
            citation = parse_citation(token)
        except ValueError as exc:
            findings.append(f"{document}: `{token}`: {exc}")
            continue
        if citation is None:
            continue

        target = root / citation.path
        label = f"{document}: `{token}`"
        if not target.is_file():
            findings.append(f"{label}: cited file does not exist")
            continue
        try:
            target.resolve().relative_to(root.resolve())
        except ValueError:
            findings.append(f"{label}: cited file resolves outside the repository")
            continue

        line_count = len(target.read_text(encoding="utf-8").splitlines())
        for start, end in citation.ranges:
            if end > line_count:
                findings.append(
                    f"{label}: lines {start}-{end} exceed target length {line_count}"
                )
    return findings


@pytest.mark.parametrize("document", DOCS)
def test_selected_docs_cite_existing_files_and_in_bounds_lines(document: str) -> None:
    findings = document_findings(document)
    assert not findings, "Invalid source citations:\n" + "\n".join(findings)


def test_parser_accepts_single_ranges_and_comma_separated_ranges() -> None:
    assert parse_citation("src/freemyid/models.py:3") == Citation(
        "src/freemyid/models.py", ((3, 3),)
    )
    assert parse_citation("src/freemyid/models.py:3-5,9,12-14") == Citation(
        "src/freemyid/models.py", ((3, 5), (9, 9), (12, 14))
    )


@pytest.mark.parametrize(
    "token",
    [
        "src/freemyid/models.py:",
        "src/freemyid/models.py:line",
        "src/freemyid/models.py:4-",
        "src/freemyid/models.py:0",
        "src/freemyid/models.py:8-3",
        "../outside/models.py:3",
        "/tmp/models.py:3",
    ],
)
def test_parser_rejects_malformed_or_non_repository_citations(token: str) -> None:
    with pytest.raises(ValueError):
        parse_citation(token)


def test_findings_name_the_document_and_bad_citation(tmp_path: Path) -> None:
    (tmp_path / "docs/dev").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/example.py").write_text("one\ntwo\n", encoding="utf-8")
    (tmp_path / "docs/dev/guide.md").write_text(
        "Missing file: `src/missing.py:1`.\n"
        "Out of range: `src/example.py:2-4`.\n"
        "Malformed: `src/example.py:1-`.\n",
        encoding="utf-8",
    )

    findings = document_findings("docs/dev/guide.md", root=tmp_path)

    assert len(findings) == 3
    assert all("docs/dev/guide.md" in item for item in findings)
    assert "src/missing.py:1" in findings[0] and "does not exist" in findings[0]
    assert "src/example.py:2-4" in findings[1] and "target length 2" in findings[1]
    assert "src/example.py:1-" in findings[2] and "expected line numbers" in findings[2]


def test_non_file_code_span_is_not_treated_as_a_citation() -> None:
    assert parse_citation("freemyid.cli:app") is None
