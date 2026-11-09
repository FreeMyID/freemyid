"""Offline browser checks for the dashboard's possible-match review card."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, expect

from freemyid.models import (
    Address,
    Consent,
    ConsentBasis,
    Listing,
    MatchLevel,
    PersonName,
    Profile,
    Todo,
    TodoKind,
)
from freemyid.storage import Store
from freemyid.wizard.server import start_background
from tests.test_wizard_a11y_browser import _open, browser

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
__all__ = ["browser"]  # Re-export the existing real-Chromium fixture.

VIEWPORTS = [(1024, 768), (1280, 800)]
SCHEMES = ["light", "dark"]
FAKE_LISTING_URL = "https://example.invalid/SYNTHETIC-URL-213"
FAKE_LISTING_VALUES = (
    "SYNTHETIC-NAME-213",
    "SYNTHETIC-LOCATION-213",
    "SYNTHETIC-RELATIVE-213",
    "83",
    FAKE_LISTING_URL,
)


@pytest.fixture
def review_card(freemyid_env, monkeypatch):
    """Start the local app with one fake Jane and a deliberately private fake listing."""
    monkeypatch.setenv("FREEMYID_NO_BACKGROUND", "1")
    store = Store()
    person = Profile(
        label="Jane Q Testperson",
        name=PersonName(first="Jane", middle="Q", last="Testperson"),
        addresses=[Address(city="Springfield", state="IL", current=True)],
        consent=Consent(
            basis=ConsentBasis.SELF,
            attested_by="Jane Q Testperson",
            text_version="test",
        ),
    )
    store.save_profile(person)
    listing = Listing(
        profile_id=person.id,
        broker_id="examplebroker",
        url=FAKE_LISTING_URL,
        name_shown=FAKE_LISTING_VALUES[0],
        age_shown=83,
        locations_shown=[FAKE_LISTING_VALUES[1]],
        relatives_shown=[FAKE_LISTING_VALUES[2]],
        match_score=60,
        match_level=MatchLevel.POSSIBLE,
        match_reasons=["city"],
    )
    store.save_listing(listing)
    todo = Todo(
        profile_id=person.id,
        broker_id="examplebroker",
        kind=TodoKind.REVIEW_MATCH,
        title="Possible match for Jane Q Testperson",
        links=[FAKE_LISTING_URL],
        resume_token=f"review:{listing.id}",
    )
    store.save_todo(todo)

    opened: list[str] = []
    from freemyid.wizard import server

    monkeypatch.setattr(server.webbrowser, "open", lambda url: opened.append(url) or True)
    running = start_background(store=store, registry_loader=lambda: None)
    yield running, listing, todo, opened
    running.stop()


def _assert_listing_values_hidden(page) -> None:
    text = page.locator("body").inner_text()
    for value in FAKE_LISTING_VALUES:
        assert value not in text


def _audit_card(page, width: int) -> None:
    card = page.locator('[data-kind="review_match"]')
    expect(card).to_have_count(1)
    _assert_listing_values_hidden(page)
    assert page.evaluate("document.documentElement.scrollWidth") <= width

    labels = ["Open the page", "Yes, this is me", "No, this is not me"]
    reached: list[str] = []
    focus_styles = {}
    for _ in range(60):
        page.keyboard.press("Tab")
        state = page.evaluate("""() => {
          const e = document.activeElement;
          if (!e.matches('[data-kind="review_match"] button[type="submit"]')) return null;
          const s = getComputedStyle(e);
          return {label: e.innerText.trim(), outline: s.outlineStyle,
                  outlineWidth: parseFloat(s.outlineWidth)};
        }""")
        if state:
            reached.append(state["label"])
            focus_styles[state["label"]] = state
        if len(reached) == len(labels):
            break
    assert reached == labels
    assert all(s["outline"] != "none" and s["outlineWidth"] >= 3
               for s in focus_styles.values())

    for label in labels:
        button = card.get_by_role("button", name=label)
        box = button.bounding_box()
        assert box is not None and box["width"] >= 44 and box["height"] >= 44, (label, box)

    measures = card.evaluate("""root => {
      const rgb = s => (s.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
      const lum = c => c.map(v => {v /= 255; return v <= .04045 ? v / 12.92
        : ((v + .055) / 1.055) ** 2.4;}).reduce((a, v, i) => a + v * [.2126,.7152,.0722][i], 0);
      const ratio = (fg, bg) => (Math.max(lum(fg), lum(bg)) + .05)
        / (Math.min(lum(fg), lum(bg)) + .05);
      return [...root.querySelectorAll('h1, p, button')].map(e => {
        let node = e, bg;
        while (node) {
          const c = getComputedStyle(node).backgroundColor;
          const values = (c.match(/[\\d.]+/g) || []).map(Number);
          if (values.length < 4 || values[3] > 0) { bg = values.slice(0, 3); break; }
          node = node.parentElement;
        }
        const s = getComputedStyle(e), fg = rgb(s.color);
        return {tag: e.tagName, text: e.innerText.trim(), size: parseFloat(s.fontSize),
                contrast: bg && fg.length === 3 ? ratio(fg, bg) : 0};
      });
    }""")
    assert measures
    for item in measures:
        assert item["size"] >= 20, item
        threshold = 7 if item["tag"] == "P" else 4.5
        assert item["contrast"] >= threshold, item


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["1024x768", "1280x800"])
@pytest.mark.parametrize("scheme", SCHEMES)
def test_review_card_controls_meet_keyboard_visual_and_privacy_checks(
    browser: Browser, review_card, viewport: tuple[int, int], scheme: str,
) -> None:
    running, _listing, _todo, _opened = review_card
    width, height = viewport
    context, page, origin = _open(
        browser, running, viewport={"width": width, "height": height}, color_scheme=scheme,
    )
    try:
        response = page.goto(origin + "/", wait_until="load")
        assert response is not None and response.status == 200
        _audit_card(page, width)
    finally:
        context.close()


@pytest.mark.parametrize("answer,key,message", [
    ("yes", "Enter", "Thank you. Free My ID will ask that site to remove the listing"),
    ("yes", "Space", "Thank you. Free My ID will ask that site to remove the listing"),
    ("no", "Enter", "Thank you. Nothing will be sent for that listing."),
    ("no", "Space", "Thank you. Nothing will be sent for that listing."),
])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["1024x768", "1280x800"])
@pytest.mark.parametrize("scheme", SCHEMES)
def test_each_answer_works_with_keyboard_and_announces_flash(
    browser: Browser, review_card, answer: str, key: str, message: str,
    viewport: tuple[int, int], scheme: str,
) -> None:
    running, _listing, _todo, _opened = review_card
    width, height = viewport
    context, page, origin = _open(
        browser, running, viewport={"width": width, "height": height}, color_scheme=scheme,
    )
    try:
        page.goto(origin + "/", wait_until="load")
        _assert_listing_values_hidden(page)
        button = page.get_by_role(
            "button", name="Yes, this is me" if answer == "yes" else "No, this is not me"
        )
        button.focus()
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.keyboard.press(key)
        status = page.locator('.note[role="status"]')
        expect(status).to_contain_text(message)
        _assert_listing_values_hidden(page)
        assert page.locator('[data-kind="review_match"]').count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("key", ["Enter", "Space"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["1024x768", "1280x800"])
@pytest.mark.parametrize("scheme", SCHEMES)
def test_open_page_action_is_keyboard_operable_and_offline(
    browser: Browser, review_card, key: str, viewport: tuple[int, int], scheme: str,
) -> None:
    running, _listing, _todo, opened = review_card
    width, height = viewport
    context, page, origin = _open(
        browser, running, viewport={"width": width, "height": height}, color_scheme=scheme,
    )
    try:
        page.goto(origin + "/", wait_until="load")
        button = page.get_by_role("button", name="Open the page")
        button.focus()
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.keyboard.press(key)
        assert opened == [FAKE_LISTING_URL]
        expect(page.locator('.note[role="status"]')).to_contain_text(
            "Opened in your web browser. Come back here when you are finished."
        )
        assert page.locator('[data-kind="review_match"]').count() == 1
        _assert_listing_values_hidden(page)
    finally:
        context.close()
