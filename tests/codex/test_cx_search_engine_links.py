"""Official checklist URLs preserve encoded queries; this module has no name builder.

The query values here are synthetic fixture inputs, never profile-derived. These tests
characterize the existing validator/opener, not a new search or name-sharing feature.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from freemyid.engine import search_engines as se
from freemyid.models import Checklist, ChecklistFile, Event

VALUES = (
    "O'Brien Testperson",
    "José Núñez Exampleperson",
    "Anne-Marie Testperson",
    "Smith & Sons Test Fixture",
    '"Jane Q Testperson"',
    "x" * 300,
    "x@evil.example",
    "test&next=https://evil.example/",
    "test#fragment?other=value",
    "test\n\r\t\x00\x7fvalue",
)


def checklist(step: se.EngineStep, url: str) -> Checklist:
    return Checklist(
        id=step.checklist_id, title="Synthetic engine step", why="Test fixture.",
        url=url, cost="Free.", time_needed="A few minutes.",
        steps=["Open the official page."], how_to_undo="Return to the page.",
        source_urls=["https://example.test/source"], date_checked=date(2026, 11, 10),
        verification="partial",
    )


class RecordingStore:
    def __init__(self) -> None:
        self.logged: list[Event] = []

    def log(self, event: Event) -> None:
        self.logged.append(event)


@pytest.mark.parametrize("step", se.STEPS, ids=lambda step: step.engine)
@pytest.mark.parametrize("value", VALUES, ids=lambda value: f"value-{VALUES.index(value)}")
def test_official_query_survives_validation_and_open_without_event_data(
    step: se.EngineStep, value: str,
) -> None:
    host = "goo.gle" if step.engine == "Google" else "www.bing.com"
    supplied = f"https://{host}/fixture?{urlencode({'q': value, 'mode': 'fixture'})}"
    item = checklist(step, supplied)
    cf = ChecklistFile(version="fixture", updated=date(2026, 11, 10), checklists=[item])
    store = RecordingStore()
    opened: list[str] = []

    assert se.open_step(store, "0" * 32, step.checklist_id,
                        opener=opened.append, cf=cf)
    assert opened == [supplied]
    parsed = urlsplit(opened[0])
    assert parsed.scheme == "https" and parsed.hostname in step.hosts
    assert parsed.username is None and parsed.password is None and not parsed.fragment
    assert parse_qs(parsed.query) == {"q": [value], "mode": ["fixture"]}
    assert all(ord(char) > 0x20 and ord(char) != 0x7f and char not in "\"'"
               for char in opened[0])
    assert store.logged[0].detail == {"checklist": step.checklist_id}
    assert value not in str(store.logged[0].detail)


@pytest.mark.parametrize("step", se.STEPS, ids=lambda step: step.engine)
@pytest.mark.parametrize("attack", (
    "https://{host}.evil.example/fixture",
    "https://{host}@evil.example/fixture",
    "https://evil.example/{host}",
    "http://{host}/fixture",
    "https://{host}\\@evil.example/fixture",
    "https://{host}/fixture?value=raw space",
    "https://{host}/fixture?value=raw\tcontrol",
))
def test_unsafe_raw_checklist_url_never_reaches_opener(
    step: se.EngineStep, attack: str,
) -> None:
    # Bypass validation deliberately to exercise the existing module's trust boundary.
    host = "goo.gle" if step.engine == "Google" else "www.bing.com"
    item = checklist(step, f"https://{host}/fixture")
    raw: Any = item.model_copy(update={"url": attack.format(host=host)})
    cf = ChecklistFile(version="fixture", updated=date(2026, 11, 10), checklists=[raw])
    store = RecordingStore()
    opened: list[str] = []
    assert se.official_url(step, raw) is None
    assert not se.open_step(store, "0" * 32, step.checklist_id,
                            opener=opened.append, cf=cf)
    assert opened == [] and store.logged == []
