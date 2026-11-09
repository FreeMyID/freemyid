"""WO-210: SmartScreen labels stay legible on narrow download pages."""

from __future__ import annotations

import pytest
from playwright.sync_api import Browser, expect

from tests.test_web_home_hero_layout import BASE, ORIGIN, serve
from tests.test_web_home_hero_layout import browser as browser  # noqa: PLC0414


@pytest.mark.parametrize("width", [320, 360, 390, 1280])
def test_smartscreen_labels_are_at_least_20px_without_clipping_or_overflow(
    browser: Browser, width: int,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        java_script_enabled=False,
        reduced_motion="reduce",
    )
    context.route("**/*", serve)
    try:
        page = context.new_page()
        response = page.goto(ORIGIN + BASE + "download/", wait_until="load")
        assert response is not None and response.status == 200
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")

        illustrations = page.locator('#smartscreen [role="img"]')
        expect(illustrations).to_have_count(2)
        labels = illustrations.locator("span")
        expect(labels).to_have_text(["More info", "Don't run", "Run anyway", "Don't run"])

        for label in labels.all():
            assert float(label.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")) >= 20
            rect = label.bounding_box()
            figure = label.locator("xpath=ancestor::figure").bounding_box()
            assert rect is not None and figure is not None
            assert rect["x"] >= figure["x"] - 1
            assert rect["x"] + rect["width"] <= figure["x"] + figure["width"] + 1
    finally:
        context.close()
