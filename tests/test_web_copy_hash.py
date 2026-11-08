"""WO-104/108: exercise built checksum feedback with a fake clipboard, offline."""

from collections.abc import Iterator
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Page, Route, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
ORIGIN = "https://freemyid.test"
FAILURE = "Couldn't copy the code. You can select and copy the code above."


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    assert (DIST / "download/index.html").is_file(), "Build web/dist before running tests"
    with sync_playwright() as driver:
        instance = driver.chromium.launch(headless=True)
        yield instance
        instance.close()


def serve(route: Route) -> None:
    """Fulfill built assets from disk; never issue any network request."""
    url = urlsplit(route.request.url)
    if f"{url.scheme}://{url.netloc}" != ORIGIN:
        route.abort()
        return
    path = (DIST / unquote(url.path).lstrip("/")).resolve()
    if not path.is_relative_to(DIST.resolve()):
        route.abort()
        return
    if path.is_dir():
        path /= "index.html"
    if not path.is_file():
        route.fulfill(status=404, body="Not found")
        return
    route.fulfill(body=path.read_bytes(), content_type=guess_type(path.name)[0] or "text/plain")


def open_checksum(
    browser: Browser, script: str, *, javascript: bool = True, open_disclosure: bool = True,
) -> Page:
    context = browser.new_context(java_script_enabled=javascript)
    context.route("**/*", serve)
    context.add_init_script(script)
    page = context.new_page()
    page.goto(ORIGIN + "/download/", wait_until="load")
    if open_disclosure:
        page.locator("#checksum summary").click()
    return page


def test_rejection_retry_keyboard_and_pending_success(browser: Browser) -> None:
    page = open_checksum(browser, """
        window.calls = [];
        window.outcome = 'reject';
        Object.defineProperty(navigator, 'clipboard', {value: {
            writeText(value) {
                window.calls.push(value);
                return new Promise((resolve, reject) => {
                    window.finishCopy = () => window.outcome === 'reject'
                        ? reject(new Error('Fake denial')) : resolve();
                });
            }
        }});
    """)
    try:
        button = page.get_by_role("button", name="Copy the code", exact=True)
        status = page.locator("#checksum [role=status]")
        expect(button).to_be_visible()
        expect(status).to_have_attribute("aria-live", "polite")
        expect(status).to_have_attribute("aria-atomic", "true")
        expect(status).to_have_text("")
        status.evaluate("el => { window.originalStatus = el; }")
        pending = page.locator("#checksum [data-copy-pending]")
        code = page.locator("#checksum code.block").inner_text()
        for key, outcome, message in [
            ("Enter", "reject", FAILURE),
            ("Space", "resolve", "Copied"),
            ("Enter", "reject", FAILURE),
        ]:
            page.evaluate("value => { window.outcome = value; }", outcome)
            button.focus()
            button.press(key)
            expect(button).to_be_disabled()
            expect(status).to_have_text("")
            expect(pending).to_be_visible()
            expect(pending).to_have_text("Copying…")
            expect(pending).to_have_attribute("aria-hidden", "true")
            assert pending.evaluate("el => !el.closest('[aria-live], [role=status]')")
            page.evaluate("window.finishCopy()")
            expect(status).to_have_text(message)
            expect(button).to_be_enabled()
            expect(pending).to_be_hidden()
            assert status.evaluate("el => el === window.originalStatus")
        assert page.evaluate("window.calls") == [code, code, code]
        expect(page.locator("#checksum code.block")).to_have_text(code)
    finally:
        page.context.close()


def test_unavailable_clipboard_explains_manual_copy(browser: Browser) -> None:
    page = open_checksum(browser, """
        Object.defineProperty(navigator, 'clipboard', {value: undefined});
    """, open_disclosure=False)
    try:
        status = page.locator("#checksum [role=status]")
        expect(status).to_have_count(1)
        expect(status).to_have_text("")
        status.evaluate("el => { window.originalStatus = el; }")
        summary = page.locator("#checksum summary")
        summary.focus()
        summary.press("Enter")
        expect(status).to_have_text(FAILURE)
        expect(status).to_have_attribute("aria-live", "polite")
        expect(status).to_have_attribute("aria-atomic", "true")
        assert status.evaluate("el => el === window.originalStatus")
        expect(page.locator("#checksum [data-copy-pending]")).to_be_hidden()
        expect(page.get_by_role("button", name="Copy the code", exact=True)).to_have_count(0)
        expect(page.locator("#checksum code.block")).to_be_visible()
    finally:
        page.context.close()


def test_without_javascript_checksum_remains_selectable(browser: Browser) -> None:
    page = open_checksum(browser, "", javascript=False)
    try:
        code = page.locator("#checksum code.block")
        expect(code).to_be_visible()
        assert len(code.inner_text().strip()) == 64
        assert code.evaluate("el => getComputedStyle(el).userSelect") != "none"
        expect(page.locator("#checksum [role=status]")).to_have_count(1)
        expect(page.locator("#checksum [role=status]")).to_have_text("")
        expect(page.locator("#checksum [data-copy-pending]")).to_be_hidden()
        expect(page.get_by_role("button", name="Copy the code", exact=True)).to_have_count(0)
    finally:
        page.context.close()
