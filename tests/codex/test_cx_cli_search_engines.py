"""Contract checks for search-engine steps belonging to the selected fake profile."""
from __future__ import annotations

import json
import webbrowser
from datetime import date
from typing import Any

import pytest
from typer.testing import CliRunner

from freemyid import checklist_state as cs
from freemyid.models import Checklist, ChecklistFile
from tests.conftest import make_profile

GOOGLE_ID = "google_results_about_you"
BING_ID = "bing_content_removal"


def _checklist(checklist_id: str, title: str, url: str) -> Checklist:
    return Checklist(
        id=checklist_id,
        title=title,
        why="A sample reason.",
        url=url,
        cost="Free.",
        time_needed="10 minutes",
        steps=["Open the page.", "Follow its steps."],
        how_to_undo="You can return to this page later.",
        source_urls=[url],
        date_checked=date(2026, 11, 7),
        verification="partial",
    )


CHECKLISTS = ChecklistFile(
    version="test",
    updated=date(2026, 11, 7),
    checklists=[
        _checklist(GOOGLE_ID, "Google sample step", "https://goo.gle/resultsaboutyou"),
        _checklist(
            BING_ID,
            "Bing sample step",
            "https://www.bing.com/webmaster/tools/contentremovalform",
        ),
        _checklist("freeze_sample", "Unrelated sample step", "https://example.test/freeze"),
    ],
)


@pytest.fixture
def opened_urls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    urls: list[str] = []
    monkeypatch.setattr(cs, "load_checklists", lambda: CHECKLISTS)
    monkeypatch.setattr(webbrowser, "open", lambda url, *args, **kwargs: urls.append(url) or True)
    return urls


def _run(*args: str):
    from freemyid.cli import app

    return CliRunner().invoke(app, ["search-engines", *args])


def _json(result: Any) -> dict[str, Any]:
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _step(doc: dict[str, Any], checklist_id: str) -> dict[str, Any]:
    return next(step for step in doc["steps"] if step["id"] == checklist_id)


def test_step_state_is_scoped_to_the_selected_fake_profile(opened_urls, store):
    jane = make_profile(label="Jane Q Testperson")
    pat = make_profile(label="Pat Exampleperson")
    store.save_profile(jane)
    store.save_profile(pat)

    # An ambiguous action must stop instead of changing either person's progress.
    ambiguous = _run("done", GOOGLE_ID)
    assert ambiguous.exit_code == 2
    assert "profile" in ambiguous.output.lower()

    assert _run("done", GOOGLE_ID, "--profile", jane.id).exit_code == 0
    jane_doc = _json(_run("--json", "--profile", jane.id))
    pat_doc = _json(_run("--json", "--profile", pat.id))
    assert jane_doc["profile_id"] == jane.id
    assert [step["id"] for step in jane_doc["steps"]] == [GOOGLE_ID, BING_ID]
    assert _step(jane_doc, GOOGLE_ID)["status"] == "done"
    assert _step(pat_doc, GOOGLE_ID)["status"] == "not_started"

    assert _run("undo", GOOGLE_ID, "--profile", jane.id).exit_code == 0
    jane_after_undo = _json(_run("--json", "--profile", jane.id))
    pat_after_undo = _json(_run("--json", "--profile", pat.id))
    assert _step(jane_after_undo, GOOGLE_ID)["status"] == "not_started"
    assert _step(pat_after_undo, GOOGLE_ID)["status"] == "not_started"
    assert opened_urls == []


def test_open_action_uses_only_the_selected_profiles_official_step(opened_urls, store):
    jane = make_profile(label="Jane Q Testperson")
    pat = make_profile(label="Pat Exampleperson")
    store.save_profile(jane)
    store.save_profile(pat)

    google = _run("open", GOOGLE_ID, "--profile", jane.id)
    bing = _run("open", "bing", "--profile", pat.id)
    assert google.exit_code == 0, google.output
    assert "Opened Google's page" in google.stdout
    assert bing.exit_code == 0, bing.output
    assert "Opened Bing's page" in bing.stdout
    assert opened_urls == [
        "https://goo.gle/resultsaboutyou",
        "https://www.bing.com/webmaster/tools/contentremovalform",
    ]

    jane_doc = _json(_run("--json", "--profile", jane.id))
    pat_doc = _json(_run("--json", "--profile", pat.id))
    assert _step(jane_doc, GOOGLE_ID)["status"] == "opened"
    assert _step(jane_doc, BING_ID)["status"] == "not_started"
    assert _step(pat_doc, GOOGLE_ID)["status"] == "not_started"
    assert _step(pat_doc, BING_ID)["status"] == "opened"
