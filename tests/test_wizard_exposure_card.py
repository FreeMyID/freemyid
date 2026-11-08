"""Exposure-card presentation using fake results; no storage or network calls."""
from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, cast

import pytest

from freemyid.exposure_models import EntryStatus, ExposureEntry, ExposureResult, ScoreLine
from freemyid.models import Profile
from freemyid.wizard.views import exposure_card

if TYPE_CHECKING:
    from freemyid.storage import Store

PROFILE = Profile.model_construct(id="a" * 32, label="Pat Testperson")
STORE = cast("Store", object())


def install_engine(
    monkeypatch: pytest.MonkeyPatch,
    lookup: Callable[[Store, Profile], ExposureResult | None],
) -> None:
    module = ModuleType("freemyid.engine.exposure")
    module.latest_exposure = lookup  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module.__name__, module)


def fake_result(found: int = 0, manual: int = 0) -> ExposureResult:
    counts: tuple[tuple[EntryStatus, int], ...] = (("found", found), ("check_by_hand", manual))
    return ExposureResult(
        profile_id=PROFILE.id, score=37,
        created_at=datetime(2026, 11, 7, tzinfo=UTC),
        entries=[
            ExposureEntry(broker_id=f"fake-{status}-{i}", broker_name="Example site",
                          status=status)
            for status, count in counts
            for i in range(count)
        ],
    )


def test_missing_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "freemyid.engine.exposure", None)
    html = exposure_card(STORE, PROFILE)
    assert "Coming soon" in html
    assert "does not include the listing check" in html
    assert "out of 100" not in html


def test_no_saved_result_and_no_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def lookup(store: Store, profile: Profile) -> None:
        calls.append((store, profile))

    install_engine(monkeypatch, lookup)
    for profile in (PROFILE, None):
        html = exposure_card(STORE, profile)
        assert "no saved result" in html
        assert "out of 100" not in html
    assert calls == [(STORE, PROFILE)]


def test_failure_is_generic(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(store: Store, profile: Profile) -> ExposureResult:
        raise RuntimeError('<script>private fake error</script>')

    install_engine(monkeypatch, fail)
    html = exposure_card(STORE, PROFILE)
    assert "not available right now" in html
    assert "private fake error" not in html
    assert "<script>" not in html
    assert "out of 100" not in html


@pytest.mark.parametrize("found", [0, 1, 3])
@pytest.mark.parametrize("manual", [0, 1, 3])
def test_counts_score_date_and_limits(
    monkeypatch: pytest.MonkeyPatch, found: int, manual: int,
) -> None:
    result = fake_result(found, manual)
    install_engine(monkeypatch, lambda store, profile: result)
    html = exposure_card(STORE, PROFILE)
    expected = ("No listings found on the sites checked." if found == 0 else
                f"Listings found on {found} site{'' if found == 1 else 's'}.")
    assert expected in html
    assert (f"{manual} site needs a manual check." if manual == 1 else
            f"{manual} sites need a manual check.") in html
    assert "only the sites checked, not every website" in html
    assert "<b>37</b> out of 100" in html
    assert "this check, not your overall safety" in html
    assert "Checked 2026-11-07." in html


def test_all_explanations_are_escaped(monkeypatch: pytest.MonkeyPatch) -> None:
    result = fake_result()
    result.explanation = [ScoreLine(points=1, text=f'Line {i}: <script>"&</script>')
                          for i in range(6)]
    install_engine(monkeypatch, lambda store, profile: result)
    html = exposure_card(STORE, PROFILE)
    assert html.count("<li>") == 6
    for i in range(6):
        assert f"Line {i}: &lt;script&gt;&quot;&amp;&lt;/script&gt;" in html
    assert "<script>" not in html
    assert result.score == 37 and len(result.explanation) == 6


@pytest.mark.browser
def test_card_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Effective widths for 150% scaling and 200% zoom, with scrolling allowed."""
    from playwright.sync_api import sync_playwright

    static = Path(__file__).resolve().parents[1] / "src/freemyid/wizard/static"
    css = (static / "tokens.css").read_text() + (static / "style.css").read_text()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort())
        try:
            for state in ("missing", "empty", "failure", "zero", "found"):
                if state == "missing":
                    monkeypatch.setitem(sys.modules, "freemyid.engine.exposure", None)
                elif state == "failure":
                    def fail(store: Store, profile: Profile) -> ExposureResult:
                        raise RuntimeError("Fake failure")
                    install_engine(monkeypatch, fail)
                else:
                    result = None if state == "empty" else fake_result(state == "found", 1)
                    if result is not None:
                        result.explanation = [ScoreLine(points=1, text="Example score explanation.")]
                    install_engine(monkeypatch, lambda store, profile, saved=result: saved)
                for theme in ("light", "dark"):
                    for width, height in ((683, 512), (512, 384)):
                        page.set_viewport_size({"width": width, "height": height})
                        page.set_content(
                            f'<html data-theme="{theme}"><head><style>{css}</style></head>'
                            f'<body><main>{exposure_card(STORE, PROFILE)}</main></body></html>'
                        )
                        assert page.locator("section").is_visible()
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= window.innerWidth"
                        ), (state, theme, width)
                        assert page.locator("button, input, a, script").count() == 0
                        for box in page.locator("section p, section li, section h2").all():
                            bounds = box.bounding_box()
                            assert bounds is not None and bounds["width"] > 0
                            assert bounds["x"] >= 0
                            assert bounds["x"] + bounds["width"] <= width
        finally:
            browser.close()
