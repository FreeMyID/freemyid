from pathlib import Path

import pytest
from pydantic import ValidationError

from freemyid import checklists
from freemyid.models import Broker, ChecklistFile

REPO_FILE = Path(__file__).resolve().parents[1] / "brokers" / "checklists.yaml"


def test_repo_checklists_validate():
    cf = checklists.load(REPO_FILE)
    ids = {c.id for c in cf.checklists}
    assert {"freeze_equifax", "freeze_experian", "freeze_transunion"} <= ids
    assert all(c.steps and c.source_urls for c in cf.checklists)


def test_duplicate_ids_rejected():
    raw = {"version": "x", "updated": "2026-11-07", "checklists": [
        {"id": "a1", "title": "t", "why": "w", "url": "https://example.org/", "cost": "free",
         "time_needed": "1m", "steps": ["s"], "how_to_undo": "u",
         "source_urls": ["https://example.org/"], "date_checked": "2026-11-07",
         "verification": "partial"}] * 2}
    with pytest.raises(ValidationError):
        ChecklistFile.model_validate(raw)


def test_broker_scan_fields_default_and_validate():
    fields = Broker.model_fields
    assert fields["search_access"].default == "unknown"
    assert fields["slug_case"].default == "lower"
