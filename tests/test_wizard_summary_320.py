"""SUM-320: the printable summary must not scroll sideways at 320px (WO-116 finding)."""
from __future__ import annotations

from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

pytest.importorskip("playwright.sync_api")

from freemyid.models import ListingState
from freemyid.wizard import views
from tests.test_wizard_a11y_browser import browser  # noqa: F401
from tests.test_wizard_summary_regressions import NOW, fake_profile, status  # noqa: F401

pytestmark = pytest.mark.browser
STATIC = Path(__file__).resolve().parents[1] / "src/freemyid/wizard/static"
ORIGIN = "https://summary.freemyid.test"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("n", [1, 36])
@pytest.mark.parametrize("width", [320, 640])
def test_summary_has_no_sideways_scroll(browser, fake_profile, monkeypatch, n, theme, width):  # noqa: F811
    monkeypatch.setattr(views, "utcnow", lambda: NOW)
    fake_profile.label = "Pat Testperson — a deliberately long fake profile label for a sample summary"
    states = [ListingState.SUBMITTED, ListingState.CONFIRMED, ListingState.REMOVED]
    sts = [status(fake_profile, f"s{i:03d}", states[i % 3]) for i in range(n)]
    names = {s.broker_id: f"Fake Site {s.broker_id} — a deliberately long example name for summary layout" for s in sts}
    html = views.summary_page(fake_profile, sts, names, 2, n)

    def route(r):
        u = urlsplit(r.request.url)
        if u.path == "/summary":
            r.fulfill(body=html, content_type="text/html")
        elif u.path.startswith("/static/") and (STATIC / unquote(u.path[8:])).is_file():
            f = STATIC / unquote(u.path[8:])
            r.fulfill(body=f.read_bytes(), content_type=guess_type(f.name)[0] or "text/plain")
        else:
            r.abort()

    ctx = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=theme,
                              java_script_enabled=False)
    ctx.route("**/*", route)
    try:
        page = ctx.new_page()
        page.goto(ORIGIN + "/summary", wait_until="load")
        g = page.locator(".summary").evaluate(
            "el => [document.documentElement.scrollWidth, innerWidth, el.clientWidth, el.scrollWidth]")
        assert g[0] <= g[1] and g[3] <= g[2], g
    finally:
        ctx.close()
