"""Screenshot the real wizard with a fake person, for the walkthrough video.
Temp FREEMYID_HOME, test key (no OS keychain), no background, no scheduler, local-only network."""
import os
import pathlib
import sys
import tempfile

OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
home = tempfile.mkdtemp(prefix="fmid-video-")
os.environ.update(FREEMYID_HOME=home, FREEMYID_TEST_KEY="video-demo-key-not-secret",
                  FREEMYID_ALLOW_TEST_KEY="1", FREEMYID_NO_BACKGROUND="1")

from playwright.sync_api import sync_playwright  # noqa: E402

from freemyid.wizard.server import start_background  # noqa: E402

r = start_background()
origin = f"http://127.0.0.1:{r.port}"
blocked = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)

        def only_local(route):
            u = route.request.url
            if u.startswith(origin):
                route.continue_()
            else:
                blocked.append(u)
                route.abort()
        ctx.route("**/*", only_local)
        pg = ctx.new_page()

        def shot(name):
            pg.wait_for_load_state()
            pg.screenshot(path=str(OUT / f"{name}.png"))

        def submit():
            with pg.expect_navigation():
                pg.locator("form button[type=submit]").last.click()
            pg.wait_for_load_state()

        pg.goto(r.url)
        shot("01_welcome_top")
        pg.locator("input[name=basis][value=self]").check()
        pg.fill("input[name=attested_by]", "Pat Example")
        box = pg.locator("input[name=ack]")
        box.check(force=not box.is_visible())
        pg.locator("input[name=attested_by]").scroll_into_view_if_needed()
        shot("02_welcome_sign")
        submit()
        pg.fill("input[name=first]", "Pat")
        pg.fill("input[name=last]", "Example")
        shot("03_name")
        submit()
        pg.fill("input[name=city0]", "Raleigh")
        pg.fill("input[name=state0]", "NC")
        shot("04_address")
        submit()
        pg.fill("input[name=birth_year]", "1952")
        shot("05_about")
        submit()
        pg.locator("input[name=provider][value=skip]").check()
        shot("06_mailbox")
        submit()
        wk = pg.locator("input[name=weekly_recheck]")
        if wk.count():
            wk.check(force=True)
            shot("07_finish")
            wk.uncheck(force=True)          # never install a real scheduler task
        else:
            shot("07_finish")
        submit()
        shot("08_dashboard")
        pg.goto(f"{origin}/settings")
        shot("09_settings")
        b.close()
finally:
    r.stop()
print("blocked:", blocked)
print("home:", home)
