"""Browser check for the extension's form help (extension/src/content/assisted-fill.js).

The unchanged content script runs in Playwright's Chromium on a local fake removal form. The
browser's extension API is a tiny fake that lets the test act as the extension's background:
it sends the same three messages the real background sends (probe, scan, apply). The plan comes
from the app's own rules (`freemyid.engine.filler.fill_plan`), so this is the whole round trip
minus native messaging, which tests/test_extension_link.py covers.

Nothing here leaves the machine: the page is served from memory and every other request fails.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from freemyid import extension_link as el
from freemyid.engine import filler
from tests.conftest import BROWSER_LAUNCH_TIMEOUT_MS, no_browser

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "extension" / "src" / "content" / "assisted-fill.js").read_text(encoding="utf-8")
ORIGIN = "https://fakepeople.example"

PAGE = """<!doctype html><meta charset="utf-8"><title>Opt out</title>
<form id="optout" action="/done" method="post">
  <label>First name <input name="first"></label>
  <label>Last name <input name="last"></label>
  <label>Email address <input type="email" name="email"></label>
  <label>Phone <input name="phone"></label>
  <label>Password <input type="password" name="pw"></label>
  <label>Already typed <input name="city" value="Typed by the person"></label>
  <label>State <select name="state"><option value="">Choose</option>
    <option value="IL">Illinois</option><option value="IN">Indiana</option></select></label>
  <div class="g-recaptcha" data-sitekey="x"><input name="captcha_answer"></div>
  <div style="position:absolute;left:-9999px"><label>Your website <input name="website"></label></div>
  <label><input type="checkbox" name="robot"> I am not a robot</label>
  <button type="submit">Send</button>
</form>
<script>
  window.__events = [];
  window.__submitted = false;
  document.getElementById('optout').addEventListener('submit', (e) => { e.preventDefault(); window.__submitted = true; });
  for (const el of document.querySelectorAll('input,select'))
    el.addEventListener('input', () => window.__events.push(el.name));
</script>"""

# The fake API: the content script registers its message listener here, and the test calls it
# as the extension's background would (sender.id is the extension's own id, no tab).
FAKE_API = """
(() => {
  const listeners = [];
  window.chrome = { runtime: { id: "fake-ext", onMessage: { addListener: (fn) => listeners.push(fn) } } };
  window.__ask = (message, sender) => new Promise((resolve) => {
    let answered = false;
    for (const fn of listeners) fn(message, sender ?? { id: "fake-ext" }, (r) => { answered = true; resolve(r); });
    if (!answered) resolve(undefined);
  });
})();
"""


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, timeout=BROWSER_LAUNCH_TIMEOUT_MS)
        except PWError as e:
            no_browser(type(e).__name__)
        ctx = browser.new_context()
        ctx.add_init_script(FAKE_API)
        refused: list[str] = []

        def route(r):
            if r.request.url.rstrip("/") == ORIGIN + "/optout":
                r.fulfill(body=PAGE, content_type="text/html")
            else:
                refused.append(r.request.url)
                r.abort()
        ctx.route("**/*", route)
        pg = ctx.new_page()
        pg.goto(ORIGIN + "/optout", wait_until="load")
        pg.add_script_tag(content=SCRIPT)
        yield pg
        assert refused == []
        browser.close()


def test_nothing_happens_until_the_background_asks(page) -> None:
    assert page.evaluate("() => document.querySelectorAll('[data-freemyid-field]').length") == 0
    assert page.evaluate("() => window.__events") == []


def test_a_message_from_anyone_else_is_ignored(page) -> None:
    assert page.evaluate("() => window.__ask({type: 'fmid.scan'}, {id: 'other-ext'})") is None
    assert page.evaluate(
        "() => window.__ask({type: 'fmid.scan'}, {id: 'fake-ext', tab: {id: 3}})") is None


def test_probe_scan_plan_apply_round_trip(page) -> None:
    probe = page.evaluate("() => window.__ask({type: 'fmid.form_probe'})")
    assert probe["ok"] is True and probe["boxes"] >= 5
    scan = page.evaluate("() => window.__ask({type: 'fmid.scan'})")
    assert scan["ok"] is True
    assert not [c for c in scan["controls"] if set(c) - {
        *el.CONTROL_TEXT_FIELDS, *el.CONTROL_BOOL_FIELDS, "maxlength", "option_values",
        "option_texts"}]
    assert "Typed by the person" not in json.dumps(scan)      # the scan never carries values
    controls = [filler.Control.from_js(c) for c in el.parse_controls(scan["controls"])]
    plan, _rep = filler.fill_plan(controls, {
        "first_name": "Jane", "last_name": "Testperson", "email": "box@example.test",
        "city": "Springfield", "state": "IL", "listing_url": "https://fakepeople.example/p/1"})
    by_name = {c.name: c.key for c in controls}
    for protected in ("pw", "captcha_answer", "website", "phone", "city"):
        assert by_name.get(protected) not in plan, protected
    # A plan that also names protected boxes (as a hostile reply might) still cannot fill them.
    hostile = [{"key": k, "value": v} for k, v in plan.items()]
    hostile += [{"key": by_name["pw"], "value": "x"}, {"key": by_name["captcha_answer"], "value": "x"},
                {"key": by_name["website"], "value": "x"}, {"key": by_name["city"], "value": "x"}]
    done = page.evaluate("(a) => window.__ask({type: 'fmid.apply', assignments: a})", hostile)
    assert done["ok"] is True and done["filled"] == len(plan) and done["skipped"] == 4
    values = page.evaluate("""() => Object.fromEntries(Array.from(
        document.querySelectorAll('input,select')).map(e => [e.name, e.type === 'checkbox' ? e.checked : e.value]))""")
    assert values["first"] == "Jane" and values["last"] == "Testperson"
    assert values["email"] == "box@example.test" and values["state"] == "IL"
    assert values["pw"] == "" and values["captcha_answer"] == "" and values["website"] == ""
    assert values["phone"] == "" and values["city"] == "Typed by the person"
    assert values["robot"] is False                             # never ticks a robot check
    assert page.evaluate("() => window.__submitted") is False   # never submits
    assert set(page.evaluate("() => window.__events")) >= {"first", "last", "email"}


def test_values_are_forgotten_after_one_apply(page) -> None:
    again = page.evaluate(
        "() => window.__ask({type: 'fmid.apply', assignments: [{key: 'f0', value: 'Again'}]})")
    assert again == {"ok": True, "filled": 0, "skipped": 1}
