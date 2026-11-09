"""Offline Windows forced-colors emulation for the possible-match review card."""
from __future__ import annotations

import pytest
from playwright.sync_api import Browser, expect

from tests.codex.test_cx_review_card_a11y import (
    FAKE_LISTING_URL,
    _assert_listing_values_hidden,
    browser,
    review_card,
)
from tests.test_wizard_a11y_browser import _open

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
__all__ = ["browser", "review_card"]

VIEWPORTS = [(1024, 768), (1280, 800)]
ACTION_LABELS = ["Open the page", "Yes, this is me", "No, this is not me"]


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["1024x768", "1280x800"])
def test_review_actions_stay_visible_and_focused_in_forced_colors(
    browser: Browser, review_card, viewport: tuple[int, int],
) -> None:
    running, _listing, _todo, _opened = review_card
    width, height = viewport
    context, page, origin = _open(
        browser,
        running,
        viewport={"width": width, "height": height},
        forced_colors="active",
    )
    try:
        response = page.goto(origin + "/", wait_until="load")
        assert response is not None and response.status == 200
        assert page.evaluate("matchMedia('(forced-colors: active)').matches")

        card = page.locator('[data-kind="review_match"]')
        expect(card).to_have_count(1)
        _assert_listing_values_hidden(page)

        actions = [card.get_by_role("button", name=label) for label in ACTION_LABELS]
        for action in actions:
            expect(action).to_be_visible()
        assert len({action.get_attribute("aria-label") or action.inner_text()
                    for action in actions}) == 3

        # Tab through the actual document order so :focus-visible is exercised.
        reached: list[str] = []
        for _ in range(80):
            page.keyboard.press("Tab")
            active = page.evaluate("""() => {
              const e = document.activeElement;
              const card = e.closest('[data-kind="review_match"]');
              if (!card || e.tagName !== 'BUTTON') return null;
              const s = getComputedStyle(e);
              return {label:e.innerText.trim(), outline:s.outlineStyle,
                      width:parseFloat(s.outlineWidth), color:s.outlineColor,
                      background:s.backgroundColor};
            }""")
            if active is None:
                continue
            reached.append(active["label"])
            outline_ratio = page.evaluate("""x => {
              const lum = s => {
                const c = (s.match(/[\\d.]+/g) || []).slice(0,3).map(Number).map(v => {
                  v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
                });
                return c[0] * .2126 + c[1] * .7152 + c[2] * .0722;
              };
              const a=lum(x.color), b=lum(x.background);
              return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
            }""", active)
            assert active["outline"] != "none" and active["width"] >= 3, active
            assert active["color"] not in ("transparent", "rgba(0, 0, 0, 0)"), active
            assert outline_ratio >= 3, (active, outline_ratio)
            if len(reached) == len(ACTION_LABELS):
                break

        assert reached == ACTION_LABELS

        text_audit = card.evaluate("""root => {
          const rgb = s => (s.match(/[\\d.]+/g) || []).slice(0,3).map(Number);
          const lum = c => c.map(v => {v/=255; return v<=.04045 ? v/12.92
            : ((v+.055)/1.055)**2.4;}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
          return [...root.querySelectorAll('h1,h2,h3,p,button')].map(e => {
            let n=e, bg;
            while (n) {
              const c=rgb(getComputedStyle(n).backgroundColor);
              if (c.length===3) { bg=c; break; }
              n=n.parentElement;
            }
            const fg=rgb(getComputedStyle(e).color);
            const ratio=bg&&fg.length===3 ? (Math.max(lum(fg),lum(bg))+.05)
              /(Math.min(lum(fg),lum(bg))+.05) : 0;
            return {tag:e.tagName,text:e.innerText.trim(),ratio};
          });
        }""")
        assert text_audit
        for item in text_audit:
            assert item["ratio"] >= 4.5, item
    finally:
        context.close()


@pytest.mark.parametrize("answer,key,message", [
    ("yes", "Enter", "Thank you. Free My ID will ask that site to remove the listing"),
    ("yes", "Space", "Thank you. Free My ID will ask that site to remove the listing"),
    ("no", "Enter", "Thank you. Nothing will be sent for that listing."),
    ("no", "Space", "Thank you. Nothing will be sent for that listing."),
])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["1024x768", "1280x800"])
def test_yes_no_feedback_remains_available_in_forced_colors(
    browser: Browser, review_card, answer: str, key: str, message: str,
    viewport: tuple[int, int],
) -> None:
    running, _listing, _todo, _opened = review_card
    width, height = viewport
    context, page, origin = _open(
        browser,
        running,
        viewport={"width": width, "height": height},
        forced_colors="active",
    )
    try:
        page.goto(origin + "/", wait_until="load")
        assert page.evaluate("matchMedia('(forced-colors: active)').matches")
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
def test_open_page_remains_keyboard_operable_and_offline_in_forced_colors(
    browser: Browser, review_card, key: str, viewport: tuple[int, int],
) -> None:
    running, _listing, _todo, opened = review_card
    width, height = viewport
    context, page, origin = _open(
        browser,
        running,
        viewport={"width": width, "height": height},
        forced_colors="active",
    )
    try:
        page.goto(origin + "/", wait_until="load")
        assert page.evaluate("matchMedia('(forced-colors: active)').matches")
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
