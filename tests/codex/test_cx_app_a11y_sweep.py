"""Browser accessibility sweep for app pages missing from the existing checks.

Uses only the local app, existing Playwright fixtures, and obviously fake profile data.
The 640px viewport models 200% reflow from a 1280px layout; it is not browser zoom.
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page

from tests.test_wizard_a11y_browser import _open, browser, seeded
from tests.test_wizard_browser_e2e import _submit
from tests.test_wizard_flow_a11y_browser import give_fake_draft_permission

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
__all__ = ["browser", "seeded"]  # Re-export the existing pytest fixtures.


def _finish_fake_draft_setup(page: Page, origin: str) -> None:
    """Open a new draft through the mailbox step, without saving or sending anything."""
    page.goto(origin + "/wizard/consent?new=1")
    give_fake_draft_permission(page)
    page.locator('input[name="first"]').fill("Pat")
    page.locator('input[name="last"]').fill("Testperson")
    _submit(page)
    page.locator('input[name="city0"]').fill("Springfield")
    page.locator('input[name="state0"]').fill("IL")
    _submit(page)
    page.locator('input[name="birth_year"]').fill("1950")
    _submit(page)
    assert page.url.endswith("/wizard/mailbox")


def _audit_screen(page: Page, width: int, path: str) -> None:
    assert page.locator("h1").count() == 1, f"{path}: expected one page heading"
    assert page.evaluate("document.documentElement.scrollWidth") <= width, (
        f"{path}: horizontal overflow at {width}px"
    )

    positive_tabstops = page.locator("[tabindex]").evaluate_all(
        "els => els.filter(el => Number(el.getAttribute('tabindex')) > 0)"
                 ".map(el => el.outerHTML.slice(0, 120))"
    )
    assert positive_tabstops == [], f"{path}: positive tabindex: {positive_tabstops}"

    labelled_controls = page.locator(
        'main input:not([type="hidden"]), main select, main textarea'
    ).evaluate_all("els => els.filter(el => el.getClientRects().length && !el.labels?.length)"
                   ".map(el => el.outerHTML.slice(0, 120))")
    assert labelled_controls == [], f"{path}: unlabeled controls: {labelled_controls}"

    expected = page.evaluate("""() => {
      const all = [...document.querySelectorAll(
        'a[href], button, input, select, textarea, summary, [tabindex]')];
      const visible = all.filter(el => {
        const style = getComputedStyle(el);
        return el.tabIndex >= 0 && !el.disabled && el.getClientRects().length > 0
          && style.visibility !== 'hidden' && style.display !== 'none'
          && !(el instanceof HTMLInputElement && el.type === 'hidden');
      });
      const radios = visible.filter(el => el instanceof HTMLInputElement && el.type === 'radio');
      const selectedRadios = new Set();
      for (const radio of radios) {
        const group = radios.filter(other => other.name === radio.name && other.form === radio.form);
        const stop = group.find(other => other.checked) || group[0];
        if (stop) selectedRadios.add(stop);
      }
      const stops = visible.filter(el => !(el instanceof HTMLInputElement && el.type === 'radio')
        || selectedRadios.has(el));
      stops.forEach((el, i) => el.setAttribute('data-cx-tab-index', String(i)));
      return stops.map((_, i) => String(i));
    }""")
    visited: set[str] = set()
    for _ in range(len(expected) + 2):
        page.keyboard.press("Tab")
        active = page.evaluate(
            "document.activeElement?.getAttribute('data-cx-tab-index')"
        )
        if active is None:
            if visited == set(expected):
                break
            continue
        visited.add(active)
        style = page.evaluate("""() => {
          const s = getComputedStyle(document.activeElement);
          return [s.outlineStyle, parseFloat(s.outlineWidth)];
        }""")
        assert style[0] != "none" and style[1] >= 3, (
            f"{path}: focused control has no visible 3px outline: {style}"
        )
        if visited == set(expected):
            break
    assert visited == set(expected), (
        f"{path}: keyboard missed tab stops {sorted(set(expected) - visited)}"
    )


@pytest.mark.parametrize("screen", ["summary", "mailbox-settings"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("width", [640, 320], ids=["modeled-200-percent", "narrow"])
def test_profile_summary_and_mailbox_settings_are_keyboard_accessible(
    browser, seeded, screen: str, scheme: str, width: int,
) -> None:
    running, profile = seeded
    context, page, origin = _open(
        browser, running, viewport={"width": width, "height": 900}, color_scheme=scheme,
    )
    try:
        path = (f"/profile/{profile.id}/summary" if screen == "summary"
                else f"/settings/{profile.id}/mailbox")
        page.goto(origin + path)
        _audit_screen(page, width, path)
    finally:
        context.close()


@pytest.mark.parametrize("target", ["mailbox", "finish"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("width", [640, 320], ids=["modeled-200-percent", "narrow"])
def test_new_draft_mailbox_and_finish_screens_are_keyboard_accessible(
    browser, seeded, target: str, scheme: str, width: int,
) -> None:
    running, _profile = seeded
    context, page, origin = _open(
        browser, running, viewport={"width": width, "height": 900}, color_scheme=scheme,
    )
    try:
        _finish_fake_draft_setup(page, origin)
        if target == "finish":
            page.locator('input[name="provider"][value="skip"]').check()
            _submit(page)
            assert page.url.endswith("/wizard/finish")
            path = "/wizard/finish"
        else:
            path = "/wizard/mailbox"
        _audit_screen(page, width, path)
    finally:
        context.close()
