"""WO-106: bounded exposure explanations and useful manual-check counts."""
from __future__ import annotations

import re
from html import escape

import pytest

from freemyid.exposure_models import ExposureResult, ScoreLine
from freemyid.wizard.views import exposure_card
from tests.test_wizard_exposure_card import PROFILE, STORE, fake_result, install_engine


@pytest.mark.parametrize("manual", [0, 1, 3])
def test_manual_check_count_is_shown_only_when_needed(
    monkeypatch: pytest.MonkeyPatch, manual: int,
) -> None:
    result = fake_result(found=1, manual=manual)
    install_engine(monkeypatch, lambda store, profile: result)
    html = exposure_card(STORE, PROFILE)
    if manual == 0:
        assert "manual check" not in html
        assert "<p>Listings found on 1 site.</p>" in html
    else:
        expected = ("1 site needs a manual check." if manual == 1 else
                    "3 sites need a manual check.")
        assert expected in html
    assert "Listings found on 1 site." in html
    assert "<b>37</b> out of 100" in html
    assert "Checked 2026-11-07." in html
    assert "only the sites checked, not every website" in html
    assert "this check, not your overall safety" in html


@pytest.mark.parametrize("count", [0, 1, 5, 6, 9])
def test_explanation_cap_preserves_order_escaping_and_input(
    monkeypatch: pytest.MonkeyPatch, count: int,
) -> None:
    result = fake_result()
    result.explanation = [
        ScoreLine(points=1, text=f'Reason {index:02d}: <script>"&</script>')
        for index in range(count)
    ]
    before = result.model_dump(mode="json")
    install_engine(monkeypatch, lambda store, profile: result)
    html = exposure_card(STORE, PROFILE)
    expected = [escape(line.text) for line in result.explanation[:5]]
    if count == 6:
        expected.append("…and 1 more reason")
    elif count == 9:
        expected.append("…and 4 more reasons")
    assert re.findall(r"<li>(.*?)</li>", html) == expected
    for index in range(5, count):
        assert f"Reason {index:02d}:" not in html
    if count <= 5:
        assert "…and" not in html
    if count == 0:
        assert '<ul class="hint">' not in html
    assert "<script>" not in html
    assert "No listings found on the sites checked." in html
    assert "<b>37</b> out of 100" in html
    assert "Checked 2026-11-07." in html
    assert "only the sites checked, not every website" in html
    assert "this check, not your overall safety" in html
    assert exposure_card(STORE, PROFILE) == html
    assert result.model_dump(mode="json") == before


def test_unavailable_result_stays_distinct_from_zero_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(store: object, profile: object) -> ExposureResult:
        raise RuntimeError("Fake unavailable result")

    install_engine(monkeypatch, fail)
    unavailable = exposure_card(STORE, PROFILE)
    install_engine(monkeypatch, lambda store, profile: fake_result())
    zero = exposure_card(STORE, PROFILE)
    assert "not available right now" in unavailable
    assert "No listings found" not in unavailable
    assert "out of 100" not in unavailable
    assert "Fake unavailable result" not in unavailable
    assert "No listings found on the sites checked." in zero
    assert "not available right now" not in zero
    assert "<b>37</b> out of 100" in zero
