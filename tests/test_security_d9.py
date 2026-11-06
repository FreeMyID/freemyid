"""Security review tests for D9 "Fill it in for me" (docs/SECURITY_REVIEW.md, SEC-30+).

Strict xfail = a confirmed open finding; when the fix lands the test XPASSes and fails the
suite, so remove the marker then. Pages are inline (page.set_content) or served by a
loopback-only server defined here. Fake people only.
"""
from __future__ import annotations

import contextlib
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from freemyid.engine import filler
from freemyid.engine.fill_for_me import (
    BANNER_ID,
    MSG_DONE,
    MSG_FILLED,
    MSG_HINT,
    MSG_PRACTICE,
    _banner_js,
    _matched,
    fill_for_me,
)
from freemyid.models import (
    Broker,
    Listing,
    MailboxConfig,
    MatchLevel,
    ProfileField,
    Registry,
)
from tests.conftest import make_profile

pytest.importorskip("playwright.async_api")

F = ProfileField
VALUES = {"first_name": "Jane", "last_name": "Testperson", "full_name": "Jane Testperson",
          "city": "Springfield", "state": "IL", "email": "removals.testperson@example.com",
          "listing_url": "https://devd9.example/p/jane-testperson"}


@pytest.fixture
async def page():
    from playwright.async_api import Error as PWError
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        try:
            b = await p.chromium.launch(headless=True)
        except PWError as e:
            pytest.skip(f"Playwright Chromium not available: {type(e).__name__}")
        ctx = await b.new_context()
        # Nothing may leave the machine: inline pages only.
        await ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith(
            ("about:", "data:")) else r.continue_())
        pg = await ctx.new_page()
        yield pg
        await b.close()


# --------------------------------------------------------------------------- passes (guards)


async def test_banner_is_text_only_even_with_markup(page):
    await page.set_content("<html><body><form><input name=a></form></body></html>")
    evil = ['<img src=x onerror="window.__pwned=1">', "</div><script>window.__pwned=1</script>",
            " '\"`${1}`"]
    await page.evaluate(_banner_js(evil, done=False))
    sel = f"#{BANNER_ID} img, #{BANNER_ID} script"
    assert await page.evaluate(f"document.querySelectorAll({sel!r}).length") == 0
    assert await page.evaluate("window.__pwned") is None
    texts = await page.evaluate(
        f"Array.from(document.getElementById('{BANNER_ID}').children).map(e => e.textContent)")
    assert texts == evil


async def test_banner_own_words_never_count_as_success(page):
    await page.set_content("<html><body><form><input name=a></form></body></html>")
    await page.evaluate(_banner_js([MSG_FILLED, MSG_PRACTICE, MSG_HINT], done=False))
    # words that appear in the banner itself
    assert await _matched(page, ["you're done", "press submit", "not a robot"], []) is None
    await page.evaluate(_banner_js([MSG_DONE], done=True))
    assert await _matched(page, ["saved proof"], []) is None


async def test_captcha_robot_password_file_never_touched(page):
    await page.set_content("""<html><body><form>
      <label>First name <input id=fn name=fn></label>
      <div class="g-recaptcha" data-sitekey="x"><label>Name <input id=cap name=n2></label></div>
      <label>Password <input id=pw type=password name=pw></label>
      <label>Upload ID <input id=up type=file name=up></label>
      <label><input id=robot type=checkbox> I'm not a robot</label>
      <label>Email <input id=hid type=hidden name=email></label>
      <textarea id=gr name=g-recaptcha-response></textarea>
    </form></body></html>""")
    rep = await filler.fill_page(page, VALUES)
    assert await page.input_value("#fn") == "Jane"
    for sel in ("#cap", "#pw", "#hid", "#gr"):
        assert await page.input_value(sel) == "", sel
    assert not await page.is_checked("#robot")
    assert await page.evaluate("document.querySelector('#up').files.length") == 0
    assert rep.filled == ["first_name"]
    assert "Jane" not in repr(rep.summary())


# --------------------------------------------------------------------------- open findings


async def test_sec30_clipped_or_offscreen_honeypots_not_filled(page):
    await page.set_content("""<html><body><form>
      <label>Your name <input id=real name=fullname></label>
      <div style="overflow:hidden;height:0">
        <label>Website <input id=hp1 type=url name=website></label></div>
      <div style="position:absolute;left:20000px;top:0">
        <label>Name <input id=hp2 name=contact_name></label></div>
    </form></body></html>""")
    await filler.fill_page(page, VALUES)
    assert await page.input_value("#real") == "Jane Testperson"
    assert await page.input_value("#hp1") == ""
    assert await page.input_value("#hp2") == ""


async def test_sec31_homemade_robot_checkbox_never_ticked(page):
    await page.set_content("""<html><body><form>
      <label><input type=checkbox id=agree name=agree> I agree to the terms</label>
      <label><input type=checkbox id=human name=human_check> I am not a robot</label>
    </form></body></html>""")
    await filler.tick_safe_checkboxes(page, ["input[type=checkbox]"])
    assert await page.is_checked("#agree")
    assert not await page.is_checked("#human")


# ---- SEC-32: success false positive with a pre-existing success phrase + a POST reload


FORM_PAGE = b"""<html><body><h1>Opt out</h1>
<p>FAQ: once your request has been received we remove it within 72 hours.</p>
<form method="post" action="/optout">
  <label>First name <input id=fn name=fn></label>
  <label>Last name <input id=ln name=ln></label>
  <label>Email <input type=email name=em></label>
  <button id=send type=submit>Submit</button>
</form></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def _serve(self) -> None:
        if self.command == "POST":   # validation error: same form page comes back
            self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 100_000))
        body = FORM_PAGE if self.path.split("?")[0] == "/devd9.example/optout" else b"nf"
        self.send_response(200 if body != b"nf" else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = _serve

    def log_message(self, format, *args):
        return


@contextlib.contextmanager
def _site(monkeypatch):
    from freemyid.engine.outbox import DEV_FIXTURES_ENV
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv(DEV_FIXTURES_ENV, f"http://127.0.0.1:{srv.server_address[1]}")
    try:
        yield
    finally:
        srv.shutdown()
        srv.server_close()


async def test_sec32_preexisting_success_text_plus_reload_is_not_success(store, monkeypatch):
    b = Broker(id="d9_fp", name="D9 FP", url="https://devd9.example/", category="people_search",
               domains=["devd9.example"], opt_out_url="https://devd9.example/optout",
               method="web_form", required_fields=[F.FULL_NAME, F.EMAIL],
               success_text=["request has been received"])
    reg = Registry(version="t", updated=date(2026, 11, 6), brokers=[b])
    mb = MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                       smtp_host="smtp.example.com", username="removals.testperson@example.com")
    p = make_profile(mailbox=mb)
    store.save_profile(p)
    store.save_listing(Listing(profile_id=p.id, broker_id=b.id, url="https://devd9.example/p/j",
                               match_score=95, match_level=MatchLevel.CONFIRMED,
                               shown_fields=[F.FULL_NAME]))

    async def person(pg):
        await pg.click("#send")    # the server answers with the same form (not accepted)

    with _site(monkeypatch):
        res = await fill_for_me(store, p.id, b.id, registry=reg, headed=False, timeout_s=4,
                                on_ready=person, close_delay_s=0)
    assert res.reason != "browser_unavailable", "needs the Playwright browser"
    assert res.status != "submitted", res


async def test_sec33_checkbox_in_captcha_shadow_host_never_ticked(page):
    await page.set_content("""<html><body><form>
      <div class="h-captcha" data-sitekey="x"><span id=host></span></div>
      <script>
        const r = document.getElementById('host').attachShadow({mode: 'open'});
        r.innerHTML = '<label><input type=checkbox id=inner name=ok> Continue</label>';
      </script></form></body></html>""")
    n = await filler.tick_safe_checkboxes(page, ["input#inner"])
    assert n == 0
