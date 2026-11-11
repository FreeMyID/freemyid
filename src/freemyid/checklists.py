"""Identity-safety checklists (credit freezes, opt-out lists...). Public data, no PII.

Loaded from brokers/checklists.yaml (dev checkout) or the bundled copy in a built app.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from . import paths
from .models import Checklist, ChecklistFile
from .registry import _NoAliasLoader

MAX_BYTES = 512 * 1024


def _candidates() -> list[Path]:
    repo = Path(__file__).resolve().parents[2] / "brokers" / "checklists.yaml"
    return [paths.bundled_data_dir() / "brokers" / "checklists.yaml", repo]


def _item_label(item: Any, index: int) -> str:
    """Only a contract-valid ID may be repeated in a diagnostic."""
    value = item.get("id") if isinstance(item, dict) else None
    if isinstance(value, str) and re.fullmatch(r"[a-z0-9_]{2,40}", value):
        return value
    return f"item {index + 1}"


def _validation_message(raw: Any, error: ValidationError) -> str:
    """Describe one problem without Pydantic's input values or context exceptions."""
    problem = error.errors(include_input=False, include_context=False, include_url=False)[0]
    location = problem["loc"]
    label = "document"
    field = "document"
    if location and location[0] == "checklists" and len(location) > 1:
        index = location[1]
        items = raw.get("checklists") if isinstance(raw, dict) else None
        if isinstance(index, int) and isinstance(items, list) and index < len(items):
            label = _item_label(items[index], index)
            # The field comes from the model's location, never a YAML mapping key.
            field = (str(location[2]) if len(location) > 2
                     and location[2] in Checklist.model_fields else "item")
    elif location:
        field = str(location[0]) if location[0] in ChecklistFile.model_fields else "document"
    kind = problem["type"]
    if kind == "missing":
        reason = f"{field} is missing"
    elif kind in {"string_too_long", "too_long"}:
        reason = f"{field} is too long"
    elif kind == "too_short":
        reason = f"{field} needs at least one item"
    elif kind == "url_scheme":
        reason = f"{field} must use http or https"
    else:
        reason = f"{field} has an invalid value"
    return f"{label}: {reason}"


def _validate(raw: Any, filename: str) -> ChecklistFile:
    # Pydantic's model-level duplicate error has no item location. Find its safe ID
    # here, while leaving all shape and field validation to the existing model.
    items = raw.get("checklists") if isinstance(raw, dict) else None
    if isinstance(items, list):
        seen: set[str] = set()
        for index, item in enumerate(items):
            value = item.get("id") if isinstance(item, dict) else None
            if isinstance(value, str) and re.fullmatch(r"[a-z0-9_]{2,40}", value):
                if value in seen:
                    raise ValueError(f"{filename}: {_item_label(item, index)}: "
                                     "duplicate checklist id")
                seen.add(value)
    try:
        return ChecklistFile.model_validate(raw)
    except ValidationError as error:
        raise ValueError(f"{filename}: {_validation_message(raw, error)}") from None


def load(path: Path | None = None) -> ChecklistFile:
    """Load and validate the checklists. Raises FileNotFoundError or a validation error."""
    for p in [path] if path else _candidates():
        if p and p.is_file():
            if p.stat().st_size > MAX_BYTES:
                raise ValueError(f"{p.name} is too large")
            contents = p.read_text(encoding="utf-8-sig")
            raw = yaml.load(contents, Loader=_NoAliasLoader)
            return _validate(raw, p.name)
    raise FileNotFoundError("checklists.yaml not found")
