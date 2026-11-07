"""Identity-safety checklists (credit freezes, opt-out lists...). Public data, no PII.

Loaded from brokers/checklists.yaml (dev checkout) or the bundled copy in a built app.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from . import paths
from .models import ChecklistFile

MAX_BYTES = 512 * 1024


def _candidates() -> list[Path]:
    repo = Path(__file__).resolve().parents[2] / "brokers" / "checklists.yaml"
    return [paths.bundled_data_dir() / "brokers" / "checklists.yaml", repo]


def load(path: Path | None = None) -> ChecklistFile:
    """Load and validate the checklists. Raises FileNotFoundError or a validation error."""
    for p in [path] if path else _candidates():
        if p and p.is_file():
            if p.stat().st_size > MAX_BYTES:
                raise ValueError(f"{p.name} is too large")
            return ChecklistFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
    raise FileNotFoundError("checklists.yaml not found")
