"""The state-law deletion matrix (brokers/state_law_deletion_matrix.yaml) and the one rule
that decides whether a letter may cite a statute.

A letter cites a state law ONLY when the matrix entry for the person's current state says
`evidence: statute_text` (the researcher read the statute or the official AG page), the law
is in force today, and it gives a real deletion right (`deletion_right: yes`). Everything
else (evidence `background`, `limited`, `not_yet`, a missing entry, a missing or broken
matrix file) falls back to the generic voluntary letter with no citation. We never invent
a citation: the one cited is the matrix's own, verified one.

The response window is quoted as a legal deadline only when its own evidence is
statute_text: an entry may carry `response_days_evidence` (default = the entry's evidence).
Otherwise the letter only asks for a reply within that many days.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .. import paths

log = logging.getLogger(__name__)

FILE_NAME = "state_law_deletion_matrix.yaml"
MAX_BYTES = 256 * 1024
VERIFIED = "statute_text"


class MatrixEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state: str = Field(min_length=2, max_length=2)
    in_force: bool = False
    deletion_right: str = "no"
    citation: str | None = None
    response_days: int | None = Field(default=None, ge=1, le=365)
    extension_days: int | None = Field(default=None, ge=0, le=365)
    effective_date: date | None = None
    evidence: str = "background"
    response_days_evidence: str | None = None

    @field_validator("state")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("deletion_right", mode="before")
    @classmethod
    def _yaml_bool(cls, v: Any) -> Any:
        # YAML 1.1 reads a bare `yes` as True.
        if v is True:
            return "yes"
        if v is False or v is None:
            return "no"
        return v

    def citable(self, today: date | None = None) -> bool:
        if self.evidence != VERIFIED or not self.in_force or self.deletion_right != "yes":
            return False
        if not self.citation:
            return False
        return self.effective_date is None or self.effective_date <= (today or date.today())

    def deadline_verified(self) -> bool:
        return bool(self.response_days) and \
            (self.response_days_evidence or self.evidence) == VERIFIED


class Matrix(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: str
    states: dict[str, MatrixEntry] = {}
    verification_verified: bool = False   # common_rules.verification.evidence == statute_text

    def get(self, state: str | None) -> MatrixEntry | None:
        return self.states.get((state or "").upper())


EMPTY = Matrix(version="none")


def _candidates() -> list[Path]:
    repo = Path(__file__).resolve().parents[3] / "brokers" / FILE_NAME
    return [paths.bundled_data_dir() / "brokers" / FILE_NAME, repo]


def parse(raw: Any) -> Matrix:
    """Validate a parsed YAML document. Raises ValueError on a bad shape."""
    if not isinstance(raw, dict) or not isinstance(raw.get("states"), list):
        raise ValueError("matrix has no states list")  # noqa: TRY004 (load() catches it)
    try:
        entries = [MatrixEntry.model_validate(s) for s in raw["states"]]
    except ValidationError as e:
        raise ValueError(f"matrix entry failed validation: {e.error_count()} error(s)") from e
    by_state: dict[str, MatrixEntry] = {}
    for ent in entries:
        if ent.state in by_state:
            raise ValueError(f"duplicate matrix state {ent.state}")
        by_state[ent.state] = ent
    ver = ((raw.get("common_rules") or {}).get("verification") or {}).get("evidence")
    return Matrix(version=str(raw.get("version", "")), states=by_state,
                  verification_verified=ver == VERIFIED)


def load(path: Path | None = None) -> Matrix:
    """Load the matrix. A missing or broken file yields an EMPTY matrix (so every letter
    is the generic one): failing closed never cites a law by mistake."""
    for p in [path] if path else _candidates():
        if p is None or not p.is_file():
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                raise ValueError("matrix file is too large")
            return parse(yaml.safe_load(p.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as e:
            log.warning("state-law matrix unusable, letters will not cite a law: %s",
                        type(e).__name__)
            return EMPTY
    return EMPTY


_cached: Matrix | None = None


def default() -> Matrix:
    """The bundled matrix, loaded once per process."""
    global _cached
    if _cached is None:
        _cached = load()
    return _cached
