"""Guard the draft glossary's structure, usted register and stated terminology."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY = ROOT / "docs" / "i18n" / "GLOSSARY_ES.md"
GUIDE = ROOT / "docs" / "i18n" / "TRANSLATION_GUIDE.md"
INFORMAL_WORDS = (
    "tú", "tu", "tus", "te", "ti", "contigo", "vos", "vosotros", "vosotras",
    "puedes", "quieres", "tienes", "eres", "estás", "usas", "necesitas", "prefieres",
    "sabes", "debes", "eliges", "envías", "guardas", "revisas", "confirmas", "aceptas",
    "firmas", "activas", "desactivas", "podés", "querés", "tenés", "sos",
)
INFORMAL = re.compile(
    r"\b(?:" + "|".join(map(re.escape, INFORMAL_WORDS)) + r")\b", re.IGNORECASE
)
POSITIONING = re.compile(
    r"\b(?:garant[ií]as?|garantiz\w*)\b|(?<!\d)100\s*%|\bpara\s+siempre\b", re.IGNORECASE
)
GUIDE_TERM = re.compile(
    r'\*\*([^*\n]+)\*\*|__([^_\n]+)__|“([^”\n]+)”|"([^"\n]+)"|‘([^’\n]+)’'
    r"|(?<!\w)'([^'\n]+)'(?!\w)"
)
# These are editorial instructions or labels, not English product concepts.
GUIDE_EXCEPTIONS = {
    "usted": "The Spanish formal pronoun names the required register.",
    "site(s)": "This demonstrates English plural notation that must not be translated literally.",
    "may": "A grammatical qualifier to preserve, rather than a product term.",
    "if": "A grammatical condition to preserve, rather than a product term.",
    "unless": "A grammatical condition to preserve, rather than a product term.",
    "not shipped": "This release-status label states that Spanish UI is unavailable.",
}


@dataclass(frozen=True)
class GlossaryRow:
    line: int
    concept: str
    spanish: str
    usage: str


def _normalise(text: str) -> str:
    return " ".join(text.casefold().strip(" \t\"'“”‘’,").split())


def _rows(document: str) -> list[GlossaryRow]:
    lines = document.splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip().startswith("|")), None)
    assert start is not None, "GLOSSARY_ES.md: no glossary table"
    result: list[GlossaryRow] = []
    for index, line in enumerate(lines[start:], start):
        if not line.strip():
            continue
        label = f"GLOSSARY_ES.md:{index + 1}"
        assert line.strip().startswith("|") and line.strip().endswith("|"), label
        cells = [part.strip() for part in re.split(r"(?<!\\)\|", line.strip()[1:-1])]
        assert len(cells) == 3 and all(cells), f"{label}: expected three non-empty cells"
        if index == start:
            assert cells[0] == "English concept", f"{label}: unexpected glossary header"
        elif index == start + 1:
            assert all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells), label
        else:
            result.append(GlossaryRow(index + 1, *cells))
    assert result, "GLOSSARY_ES.md: glossary has no entries"
    return result


def _conflicts(rows: list[GlossaryRow]) -> list[str]:
    seen: dict[str, GlossaryRow] = {}
    findings: list[str] = []
    for row in rows:
        key = _normalise(row.concept)
        if key in seen and _normalise(seen[key].spanish) != _normalise(row.spanish):
            findings.append(
                f"GLOSSARY_ES.md:{row.line}: {row.concept!r} conflicts with line {seen[key].line}"
            )
        else:
            seen[key] = row
    return findings


def _column_findings(rows: list[GlossaryRow], pattern: re.Pattern[str]) -> list[str]:
    return [
        f"GLOSSARY_ES.md:{row.line}: {row.concept!r}: Spanish contains {match.group()!r}"
        for row in rows
        for match in pattern.finditer(row.spanish)
    ]


def _guide_terms(document: str) -> list[tuple[int, str]]:
    return [
        (number, _normalise(next(group for group in match.groups() if group is not None)))
        for number, line in enumerate(document.splitlines(), 1)
        for match in GUIDE_TERM.finditer(re.sub(r"`[^`\n]*`", "", line))
    ]


def test_glossary_rows_are_populated_and_concepts_have_one_translation() -> None:
    findings = _conflicts(_rows(GLOSSARY.read_text(encoding="utf-8")))
    assert not findings, "\n".join(findings)


@pytest.mark.parametrize("pattern", [INFORMAL, POSITIONING], ids=["usted", "positioning"])
def test_spanish_column_preserves_register_and_positioning(pattern: re.Pattern[str]) -> None:
    findings = _column_findings(_rows(GLOSSARY.read_text(encoding="utf-8")), pattern)
    assert not findings, "\n".join(findings)


def test_highlighted_guide_terms_are_glossary_concepts_or_explained_exceptions() -> None:
    concepts = {_normalise(row.concept) for row in _rows(GLOSSARY.read_text(encoding="utf-8"))}
    terms = _guide_terms(GUIDE.read_text(encoding="utf-8"))
    assert terms, "TRANSLATION_GUIDE.md: no highlighted terms found"
    findings = [
        f"TRANSLATION_GUIDE.md:{line}: {term!r} is absent from the glossary and exceptions"
        for line, term in terms
        if term not in concepts and term not in GUIDE_EXCEPTIONS
    ]
    assert not findings, "\n".join(findings)
    assert all(reason.strip() for reason in GUIDE_EXCEPTIONS.values())
    assert set(GUIDE_EXCEPTIONS) <= {term for _, term in terms}, "Remove stale guide exceptions"


@pytest.mark.parametrize(
    "row", ["| name | nombre |", "| name | | note |", "| a | b | c | d |"]
)
def test_malformed_glossary_rows_cannot_be_silently_ignored(row: str) -> None:
    with pytest.raises(AssertionError, match="three non-empty cells"):
        _rows("| English concept | Spanish | Usage |\n|---|---|---|\n" + row)


def test_case_insensitive_concepts_allow_identical_translations_only() -> None:
    first = GlossaryRow(7, "name", "nombre", "note")
    assert not _conflicts([first, GlossaryRow(8, "NAME", "NOMBRE", "another note")])
    assert _conflicts([first, GlossaryRow(8, "NAME", "apellido", "another note")])


@pytest.mark.parametrize("word", INFORMAL_WORDS)
def test_register_guard_rejects_whole_informal_words(word: str) -> None:
    row = GlossaryRow(7, "synthetic label", word.upper(), "note")
    assert _column_findings([row], INFORMAL)


@pytest.mark.parametrize(
    "text", ["tutor legal", "tecnología", "información", "usted puede revisar"]
)
def test_register_guard_uses_word_boundaries_and_ignores_usage_notes(text: str) -> None:
    row = GlossaryRow(7, "synthetic label", text, "Avoid tú, tu, te, contigo and puedes.")
    assert not _column_findings([row], INFORMAL)


@pytest.mark.parametrize(
    "text",
    ["garantía", "GARANTIZAR", "garantizado", "garantizadas", "100%", "100 %", "para siempre"],
)
def test_positioning_guard_rejects_spanish_promises(text: str) -> None:
    row = GlossaryRow(7, "synthetic label", text, "note")
    assert _column_findings([row], POSITIONING)


def test_guide_term_extraction_handles_quotes_and_excludes_code_and_apostrophes() -> None:
    source = (
        '**possible match** __privacy__ “may,” "if" ‘unless’ \'name\' '
        '`"code"` user\'s settings'
    )
    assert _guide_terms(source) == [
        (1, "possible match"), (1, "privacy"), (1, "may"), (1, "if"), (1, "unless"), (1, "name")
    ]
