"""WO-116: fake summaries in screen and emulated print media, fully offline.

Paper cases model the printable content box with the product's 1.5cm margins.
They do not invoke a print dialog or establish physical pagination/PDF support.
"""
from __future__ import annotations

from collections.abc import Iterator
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Page, Route, expect

from freemyid.models import ListingState, Profile
from freemyid.wizard import views
from tests.test_wizard_a11y_browser import browser
from tests.test_wizard_summary_regressions import NOW, fake_profile, status

__all__ = ["browser", "fake_profile"]
pytestmark = pytest.mark.browser
STATIC = Path(__file__).resolve().parents[1] / "src/freemyid/wizard/static"
ORIGIN = "https://summary.freemyid.test"
LABEL = "Pat Testperson — a deliberately long fake profile label for a sample summary"
PRINT_CASES = [("print", "A4", 680, 1009), ("print", "US-Letter", 703, 943)]
MEDIA_CASES = [("screen", "narrow", 320, 900), ("screen", "wide", 640, 900), *PRINT_CASES]


@pytest.fixture(params=["empty", "single", "many"])
def summary_case(
    request: pytest.FixtureRequest, fake_profile: Profile, monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, str]:
    monkeypatch.setattr(views, "utcnow", lambda: NOW)
    fake_profile.label = LABEL
    kind = request.param
    states = ([] if kind == "empty" else [ListingState.SUBMITTED] if kind == "single" else
              [ListingState.SUBMITTED, ListingState.CONFIRMED,
               ListingState.REMOVED, ListingState.NOT_FOUND] * 12)
    statuses = [status(fake_profile, f"fake_site_{index:03d}", state)
                for index, state in enumerate(states)]
    names = {row.broker_id: f"Fake Site {index:03d} — a deliberately long example name for summary layout"
             for index, row in enumerate(statuses)}
    sent, todos = {"empty": (0, 0), "single": (1, 0), "many": (12, 3)}[kind]
    return kind, views.summary_page(fake_profile, statuses, names, todos, sent)


@pytest.fixture(params=[(*case, theme) for case in MEDIA_CASES for theme in ("light", "dark")],
                ids=[f"{media}-{paper}-{theme}" for media, paper, _, _ in MEDIA_CASES
                     for theme in ("light", "dark")])
def summary_page(
    browser: Browser, summary_case: tuple[str, str], request: pytest.FixtureRequest,
) -> Iterator[tuple[Page, str, str]]:
    media, _, width, height, theme = request.param
    kind, html = summary_case

    def offline(route: Route) -> None:
        url = urlsplit(route.request.url)
        if f"{url.scheme}://{url.netloc}" != ORIGIN:
            route.abort()
        elif url.path == "/summary":
            route.fulfill(body=html, content_type="text/html")
        elif url.path.startswith("/static/"):
            path = (STATIC / unquote(url.path[len("/static/"):])).resolve()
            if path.is_relative_to(STATIC.resolve()) and path.is_file():
                route.fulfill(body=path.read_bytes(), content_type=guess_type(path.name)[0] or "text/plain")
            else:
                route.fulfill(status=404, body="Not found")
        else:
            route.abort()

    context = browser.new_context(viewport={"width": width, "height": height},
                                  color_scheme=theme, java_script_enabled=False)
    context.route("**/*", offline)
    try:
        page = context.new_page()
        page.emulate_media(media=media)
        response = page.goto(ORIGIN + "/summary", wait_until="load")
        assert response is not None and response.status == 200
        yield page, kind, media
    finally:
        context.close()


def test_summary_counts_states_and_print_rules(summary_page: tuple[Page, str, str]) -> None:
    page, kind, media = summary_page
    summary = page.locator(".summary")
    expect(summary.locator("h1")).to_have_text("What Free My ID did for " + LABEL)
    expect(summary).to_contain_text("Written on 2026-11-07.")
    counts = summary.locator("p.lead")
    expect(counts).to_be_visible()
    sent, good, waiting, clean, visible_rows = {
        "empty": (0, 0, 0, 0, 0), "single": (1, 0, 1, 0, 1), "many": (12, 24, 12, 12, 36),
    }[kind]
    expect(counts).to_contain_text(f"sent {sent} request{'' if sent == 1 else 's'} asking")
    expect(counts).to_contain_text(f"{good} sites have confirmed or no longer list them.")
    expect(counts).to_contain_text(f"{waiting} {'is' if waiting == 1 else 'are'} still waiting to reply.")
    expect(counts).to_contain_text(f"{clean} sites were checked and did not list them.")
    if not visible_rows:
        expect(summary.locator("table")).to_have_count(0)
        expect(summary).to_contain_text("No site has needed a request so far.")
    else:
        expect(summary.locator("tr")).to_have_count(visible_rows + 1)
        expect(summary.locator("th")).to_have_text(["Site", "What happened", "Date"])
        outcomes = summary.locator("tr td:nth-child(2)").all_inner_texts()
        assert outcomes.count("We asked them to delete it") == waiting
        assert outcomes.count("They confirmed") == (12 if kind == "many" else 0)
        assert outcomes.count("No longer listed") == (12 if kind == "many" else 0)
        assert "Not listed there" not in outcomes  # Not-found contributes to its separate count.
    if media == "print":
        expect(page.locator("header.top")).to_be_hidden()
        expect(summary.locator(".noprint")).to_be_hidden()
        assert page.locator("body").evaluate("el => getComputedStyle(el).color") == "rgb(0, 0, 0)"
        for row in summary.locator("tr").all():
            assert row.evaluate("el => getComputedStyle(el).breakInside") == "avoid"
        if kind == "many":
            bounds = summary.bounding_box()
            assert bounds is not None and page.viewport_size is not None
            assert bounds["height"] > page.viewport_size["height"], "Exercise content longer than a sheet"
    else:
        expect(summary.locator('button[data-print="1"]')).to_be_visible()
        expect(summary.locator(".noprint a")).to_be_visible()


def test_summary_content_fits_without_horizontal_clipping(summary_page: tuple[Page, str, str]) -> None:
    page, kind, media = summary_page
    geometry = page.locator(".summary").evaluate("""el => ({
        viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
        summaryWidth: el.clientWidth, summaryScroll: el.scrollWidth,
        tableWidth: el.querySelector('table')?.getBoundingClientRect().width ?? 0,
        headingWidth: el.querySelector('h1').clientWidth,
        headingScroll: el.querySelector('h1').scrollWidth
    })""")
    assert geometry["documentWidth"] <= geometry["viewport"], (kind, media, geometry)
    assert geometry["summaryScroll"] <= geometry["summaryWidth"], (kind, media, geometry)
    assert geometry["headingScroll"] <= geometry["headingWidth"], (kind, media, geometry)
