"""WO-284 tolerant state identification, without changing citation eligibility."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from freemyid.engine import law_matrix
from freemyid.engine.matcher import STATE_NAMES


@pytest.mark.parametrize("value", ["CA", "ca", "CA ", " California ", "CALIFORNIA", "calif."])
def test_california_names_codes_and_documented_alias(value: str) -> None:
    assert law_matrix.resolve_state(value) == "CA"


@pytest.mark.parametrize("value", [None, "", "  ", "XX", "Cal", "Calif", "Cali", "Californiax"])
def test_unknown_names_are_not_guessed(value: str | None) -> None:
    assert law_matrix.resolve_state(value) is None


def test_repeated_state_name_whitespace() -> None:
    assert law_matrix.resolve_state("  new   york  ") == "NY"
    assert law_matrix.resolve_state("District Of Columbia") == "DC"


@pytest.mark.parametrize("value", ["899", "962", "000", "100", "90000", "900-961", "９００"])
def test_unknown_ambiguous_or_nonprefix_values_are_not_guessed(value: str) -> None:
    assert law_matrix.resolve_state(value) is None


def test_only_specified_three_digit_prefix_range_is_supported() -> None:
    for prefix in range(900, 962):
        assert law_matrix.resolve_state(str(prefix)) == "CA"


def test_every_shipped_matrix_entry_has_name_and_abbreviation_lookup() -> None:
    path = Path(__file__).resolve().parents[2] / "brokers" / law_matrix.FILE_NAME
    matrix = law_matrix.load(path)
    assert matrix.states, "test must inspect shipped data rather than an empty fallback"
    before = matrix.model_dump()
    for code, entry in matrix.states.items():
        assert matrix.lookup(code.lower()) is entry
        assert matrix.lookup(f" {STATE_NAMES[code].upper()} ") is entry
    assert matrix.model_dump() == before


def test_lookup_returns_only_entries_present_and_leaves_get_unchanged() -> None:
    entry = law_matrix.MatrixEntry(state="CA")
    matrix = law_matrix.Matrix(version="test", states={"CA": entry})
    for value in ("California", "calif.", "900", "961"):
        assert matrix.lookup(value) is entry
        assert matrix.get(value) is None  # existing strict API remains unchanged
    for value in ("Virginia", "VA", "XX", None, "100"):
        assert matrix.lookup(value) is None
    assert law_matrix.EMPTY.lookup("California") is None


@pytest.mark.parametrize("evidence", ["background", "limited", "not_yet", "statute_text"])
def test_identification_never_changes_legal_eligibility(evidence: str) -> None:
    entry = law_matrix.MatrixEntry(
        state="CA", evidence=evidence, in_force=False, deletion_right="yes",
        citation="Example Code 1", effective_date=date(2099, 1, 1),
    )
    matrix = law_matrix.Matrix(version="test", states={"CA": entry})
    before = entry.model_dump()
    for value in ("CA", "California", "calif.", "900"):
        resolved = matrix.lookup(value)
        assert resolved is entry
        assert not resolved.citable(date(2026, 1, 1))
        assert resolved.model_dump() == before


def test_carried_forward_loader_retains_bom_and_collection_alias_protection(tmp_path: Path) -> None:
    path = tmp_path / "matrix.yaml"
    path.write_bytes(b'\xef\xbb\xbfversion: test\r\nstates: [{state: CA}]\r\n')
    assert law_matrix.load(path).lookup("California") is not None
    path.write_text("shared: &x [CA]\nversion: test\nstates: *x\n", encoding="utf-8")
    assert law_matrix.load(path) == law_matrix.EMPTY
