"""Large-text layout guard for app pages across narrow and desktop viewports."""
from __future__ import annotations

import pytest

from tests.test_wizard_a11y_browser import _open, browser, seeded  # noqa: F401

pytestmark = pytest.mark.browser


@pytest.mark.parametrize(
    ("width", "scheme"),
    [(320, "dark"), (1024, "light"), (1024, "dark")],
    ids=["narrow-dark", "desktop-light", "desktop-dark"],
)
def test_large_text_has_no_horizontal_overflow_and_survives_reload(
    browser, seeded, width: int, scheme: str,  # noqa: F811
) -> None:
    running, profile = seeded
    context, page, origin = _open(
        browser,
        running,
        viewport={"width": width, "height": 900},
        color_scheme=scheme,
    )
    try:
        page.click("#text-toggle")
        assert page.get_attribute("html", "data-text") == "large"
        page.reload()
        assert page.get_attribute("html", "data-text") == "large"

        paths = [
            "/",
            "/more",
            f"/profile/{profile.id}",
            f"/profile/{profile.id}/site/examplebroker",
        ]
        for path in paths:
            page.goto(origin + path)
            assert page.get_attribute("html", "data-text") == "large", path
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            assert scroll_width <= width, (
                f"{path} at {width}px in {scheme} mode scrolls sideways "
                f"({scroll_width}px)"
            )
    finally:
        context.close()
