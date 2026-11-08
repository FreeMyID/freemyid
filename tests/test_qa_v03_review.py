"""qa-security review of the v0.3 additions (SEC-89..94, docs/SECURITY_REVIEW.md).

Exposure scan, htmlsel, state-law letters, checklist state, the v0.3 dashboard pages.
Fake people and *.example brokers only; conftest blocks every non-loopback socket.
Strict xfails mark open bugs: each one starts passing (and so fails the suite) when fixed.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.engine import exposure as ex
from freemyid.engine import htmlsel, outbox
from freemyid.engine._dev import fixture_registry
from freemyid.models import (
    Address,
    Broker,
    BrokerStatus,
    Listing,
    ListingState,
    MatchLevel,
    Request,
    RequestKind,
)
from freemyid.netpolicy import NetPolicy, _host_ok, host_of
from freemyid.registry import load_state_laws
from freemyid.wizard import views
from freemyid.wizard.server import _csrf_for, create_app
from tests.conftest import make_profile

DEV = fixture_registry().get("devauto")
PAGE_URL = "https://devauto.example/name/jane-testperson/IL"


def _result(href: str) -> str:
    return (f'<html><body><div class="result"><a class="view" href="{href}">View</a>'
            '<span class="name">Jane Q Testperson</span><span class="age">Age 46</span>'
            '<span class="loc">Springfield, IL</span><span class="rel">John Testperson</span>'
            "</div></body></html>")


def _safe_on_broker(url: str) -> bool:
    """What the browser will open is what NetPolicy checked: no backslash/control chars."""
    h = host_of(url)
    return url.startswith("https://") and bool(h) and _host_ok(str(h), set(DEV.domains))


# --------------------------------------------------------------------------- SEC-89

HOSTILE_HREFS = [
    "https://evil.example\\@devauto.example/p/1",     # WHATWG: host is evil.example
    "//evil.example\\@devauto.example/p/1",
    "/p/1\x1b]52;c;cHduZWQ=\x07",                     # OSC 52 clipboard write in a terminal
]


@pytest.mark.xfail(strict=True, reason="SEC-89: listing URLs are checked with urlsplit, not "
                   "host_of; backslash host confusion and control chars pass")
@pytest.mark.parametrize("href", HOSTILE_HREFS)
def test_sec89_parse_candidates_refuses_confusable_urls(href):
    cands = ex.parse_candidates(DEV, PAGE_URL, _result(href))
    assert all(_safe_on_broker(c.url) for c in cands), [c.url for c in cands]


@pytest.mark.xfail(strict=True, reason="SEC-89: a hostile result page plants an off-domain "
                   "link in the stored listing / 'Is this you?' to-do")
def test_sec89_scan_never_stores_an_off_domain_listing(store):
    p = make_profile()
    store.save_profile(p)
    page = ex.Fetched(PAGE_URL, 200, _result(HOSTILE_HREFS[0]))
    ex.scan_exposure(store, p.id, registry=fixture_registry(), broker_ids=["devauto"],
                     fetch=lambda b, u: page, use_browser=False)
    urls = [li.url for li in store.list_listings(p.id)] + \
        [u for t in store.list_todos(p.id) for u in t.links]
    assert urls and all(_safe_on_broker(u) for u in urls), urls


def test_sec89_plain_relative_link_still_works():
    cands = ex.parse_candidates(DEV, PAGE_URL, _result("/p/1"))
    assert [c.url for c in cands] == ["https://devauto.example/p/1"]


# --------------------------------------------------------------------------- SEC-90

B = Broker(id="fakeb", name="Fake B", url="https://fakeb.example/", category="data_broker",
           domains=["fakeb.example"], method="email", opt_out_email="privacy@fakeb.example")
LAWS = load_state_laws()


def _letter(state: str, kind: RequestKind) -> str:
    p = make_profile(addresses=[Address(city="Testville", state=state, current=True)])
    orig = Request(profile_id=p.id, broker_id=B.id, kind=RequestKind.OPT_OUT, method="email",
                   created_at=datetime(2026, 9, 1, tzinfo=UTC))
    return outbox.compose(p, B, [], LAWS.get(state), kind, original=orig)[1]


@pytest.mark.xfail(strict=True, reason="SEC-90: follow-up / formal demand state a due date "
                   "from broker.typical_processing_days when the law's window is unverified")
@pytest.mark.parametrize("state", ["OR", "NC"])
@pytest.mark.parametrize("kind", [RequestKind.FOLLOW_UP, RequestKind.LEGAL_DEMAND])
def test_sec90_no_deadline_claim_without_a_verified_window(state, kind):
    body = _letter(state, kind)
    assert "was due by" not in body and "response period ended" not in body


def test_sec90_verified_window_may_state_the_deadline():
    # VA: matrix response_days evidence is statute_text (45 days)
    assert "2026-10-16" in _letter("VA", RequestKind.LEGAL_DEMAND)


def test_letters_cite_only_the_matrix_citation_for_every_state():
    from freemyid.engine import law_matrix
    m = law_matrix.default()
    checked = 0
    for st, law in LAWS.items():
        body = _letter(st, RequestKind.LEGAL_DEMAND)
        checked += 1
        ent = m.get(st)
        if ent is None or not ent.citable():
            assert "Legal basis" not in body and (law.citation or "\0") not in body, st
        else:
            assert ent.citation in body, st
    assert checked > 20


# --------------------------------------------------------------------------- SEC-91


def test_http_fetcher_sends_no_cookie_on_first_hop():
    seen: list[str | None] = []

    def h(req: httpx.Request) -> httpx.Response:
        seen.append(req.headers.get("cookie"))
        return httpx.Response(200, text="<html></html>")
    cl = httpx.Client(transport=httpx.MockTransport(h), follow_redirects=False)
    ex.http_fetcher(NetPolicy(fixture_registry()), client=cl)(DEV, "https://devauto.example/")
    assert seen == [None]


@pytest.mark.xfail(strict=True, reason="SEC-91: the client's cookie jar replays a redirect "
                   "hop's Set-Cookie on the next hop ('no cookies' is the contract)")
def test_sec91_no_cookie_replayed_across_redirect_hops():
    seen: list[str | None] = []

    def h(req: httpx.Request) -> httpx.Response:
        seen.append(req.headers.get("cookie"))
        if req.url.path == "/a":
            return httpx.Response(302, headers={"location": "/b",
                                                "set-cookie": "sid=track; Path=/; Secure"})
        return httpx.Response(200, text="<html></html>")
    # the default (non-injected) client is built the same way, so test that shape
    cl = httpx.Client(transport=httpx.MockTransport(h), follow_redirects=False)
    ex.http_fetcher(NetPolicy(fixture_registry()), client=cl)(DEV, "https://devauto.example/a")
    assert seen == [None, None]


# --------------------------------------------------------------------------- SEC-92


@pytest.mark.xfail(strict=True, reason="SEC-92: Node.text() recurses per nesting level; a "
                   "deep page raises RecursionError (scan reports it as 'network')")
def test_sec92_text_survives_deep_nesting():
    html = ('<div class="result"><span class="name">' + "<b>" * 3000 + "Jane"
            + "</b>" * 3000 + "</span></div>")
    assert htmlsel.parse(html).select_one(".name").text() == "Jane"


def test_htmlsel_ignores_scripts_and_never_runs_markup():
    root = htmlsel.parse('<div class="result"><script>x="<div class=result>"</script>'
                         '<span class="name">A &lt;b&gt;</span></div>')
    assert len(root.select(".result")) == 1
    assert root.select_one(".name").text() == "A <b>"


# --------------------------------------------------------------------------- events / consent


def test_exposure_check_events_are_pii_free(store):
    p = make_profile()
    store.save_profile(p)
    page = ex.Fetched(PAGE_URL, 200, _result("/p/1"))
    ex.scan_exposure(store, p.id, registry=fixture_registry(), fetch=lambda b, u: page,
                     use_browser=False)
    evs = [e for e in store.events(p.id) if e.action in (ex.EVENT_ACTION, ex.CHECK_ACTION)]
    assert any(e.action == ex.CHECK_ACTION for e in evs)
    blob = json.dumps([e.detail for e in evs]).lower()
    for pii in ("jane", "testperson", "springfield", "62704", "555", "evergreen", "http"):
        assert pii not in blob, pii


def test_exposure_without_consent_fetches_nothing(store):
    from freemyid.models import Consent, ConsentBasis
    p = make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by="x",
                                     text_version="old-version"))
    store.save_profile(p)
    calls: list[str] = []
    with pytest.raises(ex.ExposureRefused):
        ex.scan_exposure(store, p.id, registry=fixture_registry(),
                         fetch=lambda b, u: calls.append(u), use_browser=False)
    assert calls == [] and store.list_listings(p.id) == []


# --------------------------------------------------------------------------- dashboard

EVIL = '<script>alert(1)</script>"\'><img src=x onerror=alert(2)>'


@pytest.fixture
def app(store, monkeypatch):
    monkeypatch.setattr(keyring, "set_password", lambda *a: None)
    opened: list[str] = []
    a = create_app(store, "tok-qa", {"testserver"}, registry_loader=lambda: None,
                   open_url=lambda u: opened.append(u) or True)
    c = TestClient(a, follow_redirects=False)
    c.cookies.set("freemyid_session", "tok-qa")
    p = make_profile(label=EVIL)
    store.save_profile(p)
    return c, store, p, opened


def test_broker_and_summary_pages_escape_hostile_text(app):
    c, store, p, _ = app
    store.save_listing(Listing(profile_id=p.id, broker_id="examplebroker",
                               url="https://example.com/p/1", name_shown=EVIL,
                               locations_shown=[EVIL], match_score=90,
                               match_level=MatchLevel.CONFIRMED))
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.FOUND, needs_human_reason=EVIL))
    for path in (f"/profile/{p.id}/site/examplebroker", f"/profile/{p.id}/summary", "/protect",
                 "/"):
        r = c.get(path)
        assert r.status_code == 200, path
        assert "<script>alert" not in r.text and "<img src=x" not in r.text, path


def test_summary_page_shows_only_label_and_site_names(app):
    c, store, p, _ = app
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.SUBMITTED))
    t = c.get(f"/profile/{p.id}/summary").text.lower()
    for pii in ("testperson", "springfield", "62704", "217-555", "evergreen", "1980",
                "jane.testperson", "john"):
        assert pii not in t, pii


def test_protect_posts_need_csrf_and_open_only_checklist_urls(app):
    c, store, p, opened = app
    from freemyid import checklist_state as cs
    cf = cs.load_checklists()
    assert cf is not None and cf.checklists
    cid = cf.checklists[0].id
    assert c.post(f"/protect/{p.id}/{cid}/done").status_code == 403
    assert c.post(f"/protect/{p.id}/{cid}/done", data={"csrf": "nope"}).status_code == 403
    assert not cs.progress(store, p.id)
    ok = {"csrf": _csrf_for("tok-qa")}
    r = c.post(f"/protect/{p.id}/{cid}/open", data=ok)
    assert r.status_code == 303 and opened == [str(cf.checklists[0].url)]
    # no open redirect / injection through the path
    r = c.post(f"/protect/{p.id}/Evil-ID%3Cx%3E/open", data=ok)
    assert r.headers["location"] == "/protect" and len(opened) == 1
    r = c.post("/protect/nobody/ca_drop/done", data=ok)
    assert r.headers["location"] == "/protect"


def test_theme_cookie_is_never_reflected(app):
    c, *_ = app
    c.cookies.set("fmi_theme", 'dark"><script>alert(1)</script>')
    r = c.get("/protect")
    assert "<script>alert" not in r.text and "set-cookie" not in {k.lower() for k in r.headers}
    from pathlib import Path

    import freemyid.wizard.server as srv
    js = (Path(srv.__file__).parent / "static" / "theme.js").read_text()
    assert "(light|dark)" in js          # read side is a whitelist


def test_exposure_card_escapes_and_has_no_urls(store):
    p = make_profile()
    store.save_profile(p)
    page = ex.Fetched(PAGE_URL, 200, _result("/p/1"))
    ex.scan_exposure(store, p.id, registry=fixture_registry(), fetch=lambda b, u: page,
                     use_browser=False)
    html = views.exposure_card(store, p)
    assert "out of 100" in html and "https://" not in html
    assert urlsplit(PAGE_URL).path not in html
