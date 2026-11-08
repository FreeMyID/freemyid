"""WO-112: wizard-step keyboard, labels, errors and reflow in real Chromium.

Only local draft-step forms are exercised. No finish, mail setup, connection
test, background job or broker submission is performed; all values are fake.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Page, expect

from tests.test_wizard_a11y_browser import _open, browser
from tests.test_wizard_browser_e2e import _submit, running

if TYPE_CHECKING:
    from freemyid.wizard.server import Running

pytestmark = [pytest.mark.browser, pytest.mark.filterwarnings("ignore::DeprecationWarning")]
__all__ = ["browser", "running"]  # Re-export the existing pytest fixtures.


@pytest.fixture(
    params=[("light", 320), ("dark", 320), ("light", 640), ("dark", 640)],
    ids=["light-320", "dark-320", "light-640", "dark-640"],
)
def wizard_page(
    browser: Browser, running: Running, request: pytest.FixtureRequest,
) -> Iterator[tuple[Page, str]]:
    scheme, width = request.param
    context, page, origin = _open(
        browser, running, viewport={"width": width, "height": 900}, color_scheme=scheme,
    )
    posts: list[str] = []
    page.on("request", lambda req: posts.append(req.url) if req.method == "POST" else None)
    try:
        yield page, origin
        assert all(url in {origin + "/wizard/consent", origin + "/wizard/name"} for url in posts)
    finally:
        context.close()


def give_fake_draft_permission(page: Page) -> None:
    """Advance a temporary draft; never finish or save a profile."""
    page.locator('input[name="basis"][value="self"]').check()
    page.locator('input[name="attested_by"]').fill("Pat Testperson")
    page.locator('input[name="ack"]').check()
    _submit(page)
    expect(page.locator('input[name="first"]')).to_be_visible()


def test_wizard_steps_reflow_labels_and_target_sizes(wizard_page: tuple[Page, str]) -> None:
    page, origin = wizard_page
    for step in ("consent", "name", "address", "about"):
        if step == "name":
            give_fake_draft_permission(page)
        else:
            page.goto(origin + "/wizard/" + step)
        expect(page.locator(f'form[action="/wizard/{step}"]')).to_be_visible()
        # Open optional details too: their controls must be labelled and fit.
        for summary in page.locator("main details > summary").all():
            summary.click()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        ), f"{step}: horizontal scrolling"
        missing_labels = page.evaluate("""() => [...document.querySelectorAll(
            'main input:not([type=hidden]), main textarea, main select')]
            .filter(el => el.getClientRects().length)
            .filter(el => !el.labels?.length || ![...el.labels].some(label => label.textContent.trim()))
            .map(el => el.name || el.id)""")
        assert missing_labels == [], (step, missing_labels)
        small_targets = page.evaluate("""() => [...document.querySelectorAll(
            'main button, main summary, main input:not([type=hidden]), main textarea, main select, main a.btn')]
            .filter(el => el.getClientRects().length)
            .map(el => (el.type === 'checkbox' || el.type === 'radio') ? el.closest('label') : el)
            .map(el => {const box = el.getBoundingClientRect();
                return {name: el.getAttribute('name') || el.textContent.trim().slice(0, 40),
                        width: box.width, height: box.height};})
            .filter(box => box.width < 44 || box.height < 44)""")
        assert small_targets == [], (step, small_targets)
        # Collapse again before continuing; the closed optional section has a
        # different, legitimate tab order from its expanded state.
        for summary in page.locator("main details > summary").all():
            summary.click()


def test_wizard_tab_order_skip_link_and_focus_ring(wizard_page: tuple[Page, str]) -> None:
    page, origin = wizard_page
    give_fake_draft_permission(page)
    steps = {
        "name": ["#first", "#middle", "#last", "summary", 'a[href="/wizard/consent"]', "button[type=submit]"],
        "address": ["#city0", "#state0", "summary", 'a[href="/wizard/name"]', "button[type=submit]"],
        "about": ["#birth_year", "#phones", "#emails", "summary", 'a[href="/wizard/address"]', "button[type=submit]"],
    }
    for step, selectors in steps.items():
        page.goto(origin + "/wizard/" + step)
        page.keyboard.press("Tab")
        assert page.locator("a.skip").evaluate("el => el === document.activeElement")
        page.keyboard.press("Enter")
        assert page.evaluate("document.activeElement.id") == "main"
        for selector in selectors:
            page.keyboard.press("Tab")
            expected = page.locator("main form").locator(selector)
            assert expected.evaluate("el => el === document.activeElement"), (step, selector)
            style = expected.evaluate("""el => {
                const css = getComputedStyle(el);
                return {style: css.outlineStyle, width: parseFloat(css.outlineWidth), color: css.outlineColor};
            }""")
            assert style["style"] != "none" and style["width"] >= 3, (step, selector, style)
            assert style["color"] not in {"transparent", "rgba(0, 0, 0, 0)"}
            bounds = expected.bounding_box()
            assert bounds is not None
            assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= page.viewport_size["width"]


@pytest.mark.xfail(strict=True, reason="SEC-98: wizard field errors lack aria-invalid/aria-describedby")
def test_wizard_validation_error_is_associated_with_its_field(
    wizard_page: tuple[Page, str],
) -> None:
    page, _ = wizard_page
    give_fake_draft_permission(page)
    # A space satisfies native required validation, but the server strips it
    # and returns the real missing-name validation error.
    page.locator("#first").fill(" ")
    page.locator("#last").fill("Testperson")
    with page.expect_response(
        lambda response: response.request.method == "POST" and response.url.endswith("/wizard/name"),
    ) as response:
        _submit(page)
    assert response.value.status == 400
    expect(page.get_by_role("alert")).to_be_visible()
    field = page.locator("#first")
    assert field.get_attribute("aria-invalid") == "true"
    references = (field.get_attribute("aria-errormessage") or field.get_attribute("aria-describedby") or "").split()
    assert references, "Invalid field must reference its visible validation error"
    error_text = page.get_by_role("alert").inner_text().strip()
    assert any(
        page.locator(f'[id="{target}"]').is_visible()
        and error_text in page.locator(f'[id="{target}"]').inner_text()
        for target in references
    ), "The field's referenced text must include its visible validation error"
