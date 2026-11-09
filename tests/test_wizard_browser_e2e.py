"""Real-browser (Playwright Chromium, headless) walk through the 6-screen wizard to the dashboard.

Why this exists: Starlette's TestClient never sends an Origin header, so the whole suite missed
that `Referrer-Policy: no-referrer` makes Chromium/WebView2 send `Origin: null` on form POSTs,
which the server's guard rejects ("Bad origin"). On a real Windows VM nobody could get past
step 1. This drives the real server (uvicorn on 127.0.0.1) with a real browser.

Assertions are on behaviour and status codes, never on exact error wording (the wizard's error
pages are still being reworded). Every request that is not to the local server is aborted.
Fake person only: Pat Testperson, Raleigh NC.
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from tests.conftest import BROWSER_LAUNCH_TIMEOUT_MS, no_browser

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

STEPS = ["consent", "name", "address", "about", "mailbox", "finish"]


@pytest.fixture(scope="module")
def browser():
    # The context manager stops the driver even when launch fails (see SEC-26).
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True, timeout=BROWSER_LAUNCH_TIMEOUT_MS)
        except PWError as e:
            no_browser(type(e).__name__)   # fails instead when FREEMYID_REQUIRE_BROWSER=1
        yield b
        b.close()


@pytest.fixture
def running(freemyid_env, monkeypatch):
    monkeypatch.setenv("FREEMYID_NO_BACKGROUND", "1")
    from freemyid.wizard.server import start_background
    r = start_background()
    yield r
    r.stop()


@pytest.fixture
def page(browser, running):
    origin = f"http://127.0.0.1:{running.port}"
    ctx = browser.new_context()
    blocked: list[str] = []

    def only_local(route):
        url = route.request.url
        if url.startswith(origin + "/") or url == origin:
            route.continue_()
        else:
            blocked.append(url)
            route.abort()

    ctx.route("**/*", only_local)
    pg = ctx.new_page()
    log: dict[str, list] = {"posts": [], "responses": [], "blocked": blocked}
    pg.on("requestfinished", lambda q: log["posts"].append(q) if q.method == "POST" else None)
    pg.on("response", lambda r: log["responses"].append(r))
    pg.freemyid_log = log  # type: ignore[attr-defined]
    pg.freemyid_origin = origin  # type: ignore[attr-defined]
    yield pg
    ctx.close()


def _path(url: str, origin: str) -> str:
    assert url.startswith(origin), url
    return url[len(origin):].split("?")[0]


def _submit(pg, button_name: str = "") -> None:
    """Click the form's submit button and wait for the POST/303/GET round trip."""
    btn = (pg.locator("form button[type=submit]").last if not button_name
           else pg.get_by_role("button", name=button_name))
    with pg.expect_navigation():
        btn.click()
    pg.wait_for_load_state()


def _assert_no_rejection(pg) -> None:
    for r in pg.freemyid_log["responses"]:
        assert r.status != 403, f"403 on {r.request.method} {r.url}"
        assert r.status < 500, f"{r.status} on {r.request.method} {r.url}"
    body = pg.inner_text("body").lower()
    for bad in ("bad origin", "form token", "forbidden"):
        assert bad not in body


def _check(pg, name: str) -> None:
    box = pg.locator(f"input[name={name}]")
    box.check(force=not box.is_visible())


def test_walk_all_six_screens_to_dashboard_in_real_browser(page, running, freemyid_env):
    pg, origin = page, page.freemyid_origin
    first = pg.goto(running.url)
    assert first is not None and first.ok
    # Token exchange: the ?t= URL redirects to the wizard (no profiles yet), token gone.
    assert _path(pg.url, origin) == "/wizard/consent"
    assert "t=" not in pg.url

    # Regression for 54ff105: no-referrer makes Chromium send Origin: null on POST.
    rp = (first.all_headers().get("referrer-policy") or "").lower()
    assert rp and rp != "no-referrer"

    # 1. consent
    pg.locator("input[name=basis][value=self]").check()
    pg.fill("input[name=attested_by]", "Pat Testperson")
    _check(pg, "ack")
    _submit(pg)
    assert _path(pg.url, origin) == "/wizard/name"
    # 2. name
    pg.fill("input[name=first]", "Pat")
    pg.fill("input[name=last]", "Testperson")
    _submit(pg)
    assert _path(pg.url, origin) == "/wizard/address"
    # 3. address (fake, NC)
    pg.fill("input[name=city0]", "Raleigh")
    pg.fill("input[name=state0]", "NC")
    _submit(pg)
    assert _path(pg.url, origin) == "/wizard/about"
    # 4. about
    pg.fill("input[name=birth_year]", "1950")
    _submit(pg)
    assert _path(pg.url, origin) == "/wizard/mailbox"
    # 5. mailbox: skip (do it by hand)
    pg.locator("input[name=provider][value=skip]").check()
    _submit(pg)
    assert _path(pg.url, origin) == "/wizard/finish"
    # 6. finish (no scheduler: leave the box unticked; background is disabled anyway)
    _submit(pg)
    assert _path(pg.url, origin) == "/"
    assert pg.locator("form[action$='/wizard/finish']").count() == 0
    _assert_no_rejection(pg)

    # Each wizard POST went to the step it was on, came back 303, and carried the real origin.
    posts = pg.freemyid_log["posts"]
    assert [_path(q.url, origin) for q in posts] == [f"/wizard/{s}" for s in STEPS]
    for q in posts:
        assert q.all_headers().get("origin") == origin, q.url
        resp = q.response()
        assert resp is not None and resp.status == 303, (q.url, resp and resp.status)

    # The profile really was saved (encrypted store, under the temp FREEMYID_HOME).
    from freemyid.storage import Store
    st = Store()
    try:
        profs = st.list_profiles()
        assert len(profs) == 1 and profs[0].name.last == "Testperson"
    finally:
        st.close()

    # One dashboard POST: save permissions in Settings.
    pg.goto(f"{origin}/settings")
    assert _path(pg.url, origin) == "/settings"
    n_before = len(posts)
    form = pg.locator("form[action$='/permissions']").first
    with pg.expect_navigation():
        form.locator("button[type=submit]").click()
    pg.wait_for_load_state()
    assert _path(pg.url, origin) == "/settings"
    assert "msg=saved" in pg.url
    new = pg.freemyid_log["posts"][n_before:]
    assert len(new) == 1 and new[0].all_headers().get("origin") == origin
    assert new[0].response().status == 303
    _assert_no_rejection(pg)

    # Nothing tried to leave 127.0.0.1 (no external assets, fonts or analytics).
    assert pg.freemyid_log["blocked"] == []


def test_guard_still_rejects_foreign_and_null_origins(page, running):
    """The fix must not have weakened the Origin check: same cookie, wrong origin -> 403."""
    pg, origin = page, page.freemyid_origin
    pg.goto(running.url)   # sets the session cookie in this context
    from freemyid.wizard.server import _csrf_for
    csrf = _csrf_for(running.token)
    for bad in ("http://evil.example", "null", f"http://127.0.0.1:{running.port + 1}"):
        r = pg.request.post(f"{origin}/settings/submissions/off", form={"csrf": csrf},
                            headers={"Origin": bad}, max_redirects=0)
        assert r.status == 403, bad
    ok = pg.request.post(f"{origin}/settings/submissions/off", form={"csrf": csrf},
                         headers={"Origin": origin}, max_redirects=0)
    assert ok.status == 303
    # Wrong CSRF with the right origin is still refused.
    r = pg.request.post(f"{origin}/settings/submissions/off", form={"csrf": "nope"},
                        headers={"Origin": origin}, max_redirects=0)
    assert r.status == 403


def _seed_review(label: str = "Pat"):
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
    store = Store()
    p = Profile(label=label, name=PersonName(first="Pat", last="Testperson"),
                addresses=[Address(city="Raleigh", state="NC", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                text_version="t"))
    store.save_profile(p)
    li = Listing(profile_id=p.id, broker_id="examplebroker", url="https://example.com/p/1",
                 match_score=60, match_level=MatchLevel.POSSIBLE, match_reasons=["city"])
    store.save_listing(li)
    store.save_todo(Todo(profile_id=p.id, broker_id="examplebroker", kind=TodoKind.REVIEW_MATCH,
                         title="Is this Pat? (Example)", body="b", links=[li.url],
                         resume_token=f"review:{li.id}"))
    return store, p, li


@pytest.mark.parametrize("button,level,flash", [
    ("Yes, this is me", "confirmed", "ask that site to remove"),
    ("No, this is not me", "no_match", "Nothing will be sent"),
])
def test_is_this_you_buttons_in_real_browser(page, running, freemyid_env, button, level, flash):
    store, p, li = _seed_review()
    pg, origin = page, page.freemyid_origin
    pg.goto(running.url)
    assert _path(pg.url, origin) == "/"
    btn = pg.get_by_role("button", name=button)
    assert btn.bounding_box()["height"] >= 44
    with pg.expect_navigation():
        btn.click()
    pg.wait_for_load_state()
    _assert_no_rejection(pg)
    assert flash in pg.inner_text("body")
    assert pg.freemyid_log["posts"][-1].all_headers().get("origin") == origin
    got = next(x for x in store.list_listings(p.id) if x.id == li.id)
    assert got.match_level.value == level
    assert store.list_todos(p.id) == []
    assert pg.freemyid_log["blocked"] == []
