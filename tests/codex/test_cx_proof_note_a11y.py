"""Offline browser checks for the optional note on a phone-call to-do."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, expect

from freemyid.models import Address, Consent, ConsentBasis, PersonName, Profile, Todo, TodoKind
from freemyid.storage import Store
from freemyid.wizard.server import start_background
from tests.codex.test_cx_review_card_a11y import _open, browser

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
__all__ = ["browser"]  # Re-export the existing real-Chromium fixture.

VIEWPORT = {"width": 1024, "height": 768}
CALL_URL = "https://example.invalid/SYNTHETIC-CALL-PAGE-228"
PRIVATE_MARKERS = (
    "SYNTHETIC-CALLBACK-PHONE-228",
    "SYNTHETIC-LISTING-NAME-228",
    "SYNTHETIC-RELATIVE-NAME-228",
    "SYNTHETIC-CALL-NOTE-228",
)


@pytest.fixture
def call_note_card(freemyid_env, monkeypatch):
    """Show a fake call-only site task, as created after choosing hand steps."""
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
    todo = Todo(
        profile_id=person.id,
        broker_id="examplebroker",
        kind=TodoKind.PHONE_CALL,
        title="Call the example site",
        body="Use the contact details on the example site's page.",
        links=[CALL_URL],
        copy_fields={
            "Phone number": PRIVATE_MARKERS[0],
            "Name shown": PRIVATE_MARKERS[1],
            "Relative shown": PRIVATE_MARKERS[2],
        },
        resume_token="phone:examplebroker",
    )
    store.save_todo(todo)

    from freemyid.wizard import server

    opened: list[str] = []
    monkeypatch.setattr(server.webbrowser, "open", lambda url: opened.append(url) or True)
    running = start_background(store=store, registry_loader=lambda: None)
    yield running, todo, opened
    running.stop()


def _assert_private_markers_hidden(locator) -> None:
    text = locator.inner_text()
    for marker in PRIVATE_MARKERS:
        assert marker not in text


def _text_metrics(page) -> list[dict[str, float | str]]:
    return page.locator('[data-kind="phone_call"]').evaluate("""card => {
      const rgb = text => (text.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
      const luminance = color => color.map(channel => {
        channel /= 255;
        return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
      }).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
      const contrast = (foreground, background) =>
        (Math.max(luminance(foreground), luminance(background)) + .05) /
        (Math.min(luminance(foreground), luminance(background)) + .05);
      return [...card.querySelectorAll('label, textarea, .hint, button')].map(element => {
        let ancestor = element;
        let background;
        while (ancestor) {
          const color = getComputedStyle(ancestor).backgroundColor;
          const channels = (color.match(/[\\d.]+/g) || []).map(Number);
          if (channels.length < 4 || channels[3] > 0) {
            background = channels.slice(0, 3);
            break;
          }
          ancestor = ancestor.parentElement;
        }
        const style = getComputedStyle(element);
        const foreground = rgb(style.color);
        return {
          tag: element.tagName,
          label: element.innerText || element.getAttribute('aria-label') || element.name || '',
          size: parseFloat(style.fontSize),
          contrast: background && foreground.length === 3
            ? contrast(foreground, background) : 0,
        };
      });
    }""")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_call_note_is_labeled_keyboard_ordered_large_and_private(
    browser: Browser, call_note_card, scheme: str,
) -> None:
    running, _todo, _opened = call_note_card
    context, page, origin = _open(
        browser, running, viewport=VIEWPORT, color_scheme=scheme,
    )
    try:
        response = page.goto(origin + "/more", wait_until="load")
        assert response is not None and response.status == 200
        card = page.locator('[data-kind="phone_call"]')
        expect(card).to_have_count(1)
        expect(card.get_by_label("A short note about the call (optional)")).to_be_visible()
        _assert_private_markers_hidden(card)

        opener = card.get_by_role("button", name="Open the page")
        note = card.get_by_label("A short note about the call (optional)")
        done = card.get_by_role("button", name="I finished it")
        for control in (opener, note, done):
            bounds = control.bounding_box()
            assert bounds is not None and bounds["width"] >= 44 and bounds["height"] >= 44

        opener.focus()
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.id") == note.get_attribute("id")
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.innerText") == "I finished it"

        metrics = _text_metrics(page)
        critical = [item for item in metrics if item["tag"] in {"LABEL", "TEXTAREA", "BUTTON"}]
        assert critical
        for item in critical:
            assert item["size"] >= 20, item
        for item in metrics:
            assert item["contrast"] >= 4.5, item
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.xfail(
    strict=True,
    reason=("The call-note safety hint uses .hint at 0.9rem (18px), below the 20px target; "
            "src/freemyid/wizard/static/style.css:98."),
)
def test_call_note_safety_hint_uses_at_least_20px_text(
    browser: Browser, call_note_card, scheme: str,
) -> None:
    running, _todo, _opened = call_note_card
    context, page, origin = _open(
        browser, running, viewport=VIEWPORT, color_scheme=scheme,
    )
    try:
        page.goto(origin + "/more", wait_until="load")
        card = page.locator('[data-kind="phone_call"]')
        hint = card.locator(".hint").last
        expect(hint).to_be_visible()
        size = hint.evaluate("element => parseFloat(getComputedStyle(element).fontSize)")
        assert size >= 20, {"hint": hint.inner_text(), "size": size}
    finally:
        context.close()


def test_call_note_completion_announces_flash_without_echoing_private_values(
    browser: Browser, call_note_card,
) -> None:
    running, _todo, _opened = call_note_card
    context, page, origin = _open(browser, running, viewport=VIEWPORT, color_scheme="light")
    try:
        page.goto(origin + "/more", wait_until="load")
        card = page.locator('[data-kind="phone_call"]')
        note = card.get_by_label("A short note about the call (optional)")
        note.fill(PRIVATE_MARKERS[3])
        with page.expect_navigation(wait_until="domcontentloaded"):
            card.get_by_role("button", name="I finished it").click()
        expect(page.locator('.note[role="status"]')).to_contain_text(
            "Thank you. Free My ID will carry on."
        )
        _assert_private_markers_hidden(page.locator("body"))
    finally:
        context.close()
