"""Exposure scan ("find me first", ROADMAP 3.2). Dev fixture brokers on .example hosts only;
conftest blocks every non-loopback socket, so nothing real is ever contacted."""
from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pytest
from typer.testing import CliRunner

from freemyid.engine import exposure as ex
from freemyid.engine import htmlsel
from freemyid.engine._dev import fixture_registry, fixture_server
from freemyid.exposure_models import ExposureEntry, ExposureListing
from freemyid.models import MatchLevel, utcnow
from freemyid.submitters.web_form import search_url
from tests.conftest import make_profile

HTML = """<html><body><div id="r">
<div class="result card"><a class="view" href="/p/1">View</a><span class="name">Jane Q
Testperson</span><span class="age">Age 46</span><span class="loc">Springfield, IL</span>
<span class="rel">John Testperson</span></div>
<div class="result"><a class="view" href="https://elsewhere.example/p/2">x</a>
<span class="name">Jane Testperson</span></div>
<script>document.write('<div class="result">fake</div>')</script>
</div></body></html>"""


def _reg(**access):
    reg = fixture_registry()
    brokers = [b.model_copy(update={"search_access": access[b.id]}) if b.id in access else b
               for b in reg.brokers]
    return reg.model_copy(update={"brokers": brokers})


def _saved(store, **over):
    p = make_profile(**over)
    store.save_profile(p)
    return p


class Calls:
    def __init__(self, page=None, exc=None):
        self.urls: list[str] = []
        self.page, self.exc = page, exc

    def __call__(self, broker, url):
        self.urls.append(url)
        if self.exc:
            raise self.exc
        return self.page(broker, url) if callable(self.page) else self.page


# ------------------------------------------------------------------ pure parts


def test_htmlsel_subset_and_static_only():
    root = htmlsel.parse(HTML)
    res = root.select("#r > div.result")
    assert len(res) == 2                       # script text never becomes markup
    assert res[0].select_one("a.view[href]").get("href") == "/p/1"
    assert res[0].select_one("span[class=name]").text() == "Jane Q Testperson"
    assert root.select("div .loc, h1")[0].text() == "Springfield, IL"
    for bad in ("a:hover", "a ~ b", "div >", "a[href^=x]"):
        with pytest.raises(htmlsel.UnsupportedSelector):
            root.select(bad)


def test_parse_candidates_drops_off_domain_links():
    b = fixture_registry().get("devauto")
    c = ex.parse_candidates(b, "https://devauto.example/name/x", HTML)
    assert [x.url for x in c] == ["https://devauto.example/p/1"]
    assert c[0].age == 46 and c[0].relatives == ["John Testperson"]


def test_slug_case():
    p = make_profile(addresses=[{"city": "Fort Mill", "state": "SC", "current": True}])
    b = fixture_registry().get("devauto").model_copy(update={
        "search_url_pattern": "https://devauto.example/{first}-{last}/{city}/{state}"})
    assert search_url(b, p) == "https://devauto.example/jane-testperson/fort-mill/sc"
    t = b.model_copy(update={"slug_case": "title"})
    assert search_url(t, p) == "https://devauto.example/Jane-Testperson/Fort-Mill/SC"
    a = b.model_copy(update={"slug_case": "as_is"})
    assert search_url(a, p) == "https://devauto.example/Jane-Testperson/Fort-Mill/SC"


def _entry(level, n=1, contact=False, rel=0, status="found"):
    lis = [ExposureListing(url=f"https://x.example/{i}", match_level=level,
                           contact_shown=contact, relatives_shown=rel) for i in range(n)]
    return ExposureEntry(broker_id="x", broker_name="X", status=status, match_level=level,
                         listings=lis)


def test_score_formula_and_lines():
    assert ex.score_entries([])[0] == 0
    s, lines = ex.score_entries([_entry(MatchLevel.CONFIRMED, n=4, contact=True, rel=3),
                                 _entry(MatchLevel.POSSIBLE)])
    # 15 site + 2*5 extra (capped at 2) + 5 contact + min(10, 2*3*4=24) + 5 possible
    assert s == 15 + 10 + 5 + 10 + 5
    assert sum(ln.points for ln in lines) == s
    big, lines = ex.score_entries([_entry(MatchLevel.CONFIRMED, n=3, contact=True)
                                   for _ in range(5)])
    assert big == 100 and lines[-1].text == "The score stops at 100"
    hand = ExposureEntry(broker_id="h", broker_name="H", status="check_by_hand")
    s, lines = ex.score_entries([hand])
    assert s == 0 and "not counted" in lines[0].text


# ------------------------------------------------------------------ scans


def test_fixture_scan_end_to_end(store):
    p = _saved(store)
    with fixture_server():
        res = ex.scan_exposure(store, p.id, registry=fixture_registry(), use_browser=False)
    by = {e.broker_id: e for e in res.entries}
    assert set(by) == {"devauto", "devblocked"}      # only brokers with a search pattern
    auto = by["devauto"]
    assert auto.status == "found" and auto.match_level == MatchLevel.CONFIRMED
    assert auto.signals == ["age", "city", "relative"]
    assert [li.url for li in auto.listings] == [
        "https://devauto.example/person/jane-q-testperson-abc123"]
    blocked = by["devblocked"]
    assert blocked.status == "check_by_hand" and blocked.reason == "challenge"
    assert blocked.check_url == "https://devblocked.example/name/jane-testperson/il"
    assert res.score == 17 and res.practice_mode
    # same listing record a scan keeps, so the runner/fill_for_me can use it
    assert [li.url for li in store.list_listings(p.id, "devauto")] == [auto.listings[0].url]
    # stored scan: PII-free, no HTML, round-trips through latest_exposure
    ev = next(e for e in store.events(p.id) if e.action == ex.EVENT_ACTION)
    blob = json.dumps(ev.detail).lower()
    for pii in ("testperson", "springfield", "jane", "<", "http"):
        assert pii not in blob
    assert ex.latest_exposure(store, p, fixture_registry()) == res
    assert ex.latest_exposure(store, p.id, fixture_registry()).score == 17
    assert [s for _, s in ex.exposure_history(store, p.id)] == [17]


def test_bot_blocked_and_unknown_are_never_fetched(store):
    p = _saved(store)
    calls = Calls(exc=AssertionError("fetched"))
    res = ex.scan_exposure(store, p.id, registry=_reg(devauto="bot_blocked",
                                                      devblocked="unknown"),
                           fetch=calls, browser_fetch=calls)
    assert calls.urls == []
    assert {e.broker_id: e.reason for e in res.entries} == {
        "devauto": "bot_blocked", "devblocked": "unknown_access"}
    assert all(e.check_url and e.check_url.startswith("https://dev") for e in res.entries)


def test_one_failure_does_not_stop_the_scan(store):
    p = _saved(store)
    first = {"n": 0}

    def page(broker, url):
        first["n"] += 1
        if first["n"] == 1:
            raise RuntimeError("boom")
        return ex.Fetched(url, 200, "<p>No records found</p>")

    calls = Calls(page=page)
    res = ex.scan_exposure(store, p.id, registry=_reg(devblocked="open"), fetch=calls,
                           use_browser=False)
    assert len(calls.urls) == 2                       # exactly one request per broker
    assert [(e.broker_id, e.status, e.reason) for e in res.entries] == [
        ("devauto", "check_by_hand", "network"), ("devblocked", "not_found", None)]


def test_js_required_uses_browser_only(store):
    p = _saved(store)
    http = Calls(exc=AssertionError("plain fetch for js_required"))
    res = ex.scan_exposure(store, p.id, registry=_reg(devauto="js_required",
                                                      devblocked="bot_blocked"),
                           fetch=http, use_browser=False)
    assert res.entries[0].reason == "needs_browser"
    br = Calls(page=ex.Fetched("https://devauto.example/name/x", 200,
                               "<p>No records found</p>"))
    res = ex.scan_exposure(store, p.id, registry=_reg(devauto="js_required",
                                                      devblocked="bot_blocked"),
                           fetch=http, browser_fetch=br, refresh=True)
    assert len(br.urls) == 1 and res.entries[0].status == "not_found"


def test_cache_offline_and_refresh(store):
    p = _saved(store)
    reg = _reg(devblocked="bot_blocked")
    with fixture_server():
        ex.scan_exposure(store, p.id, registry=reg, use_browser=False)
    boom = Calls(exc=AssertionError("fetched again"))
    again = ex.scan_exposure(store, p.id, registry=reg, fetch=boom, use_browser=False)
    assert boom.urls == [] and again.entries[0].status == "found"
    off = ex.scan_exposure(store, p.id, registry=reg, offline=True)
    auto = off.entries[0]
    assert off.offline and auto.reason == "offline" and auto.from_store
    assert auto.match_level == MatchLevel.CONFIRMED and off.score == again.score
    later = utcnow() + timedelta(hours=ex.CACHE_HOURS + 1)
    calls = Calls(page=ex.Fetched("https://devauto.example/", 200, "<p>No records found</p>"))
    gone = ex.scan_exposure(store, p.id, registry=reg, fetch=calls, now=later,
                            use_browser=False)
    assert len(calls.urls) == 1 and gone.entries[0].status == "not_found"
    assert all(li.gone_since for li in store.list_listings(p.id, "devauto"))


def test_unrecognized_page_and_bad_selector_go_to_hand(store):
    p = _saved(store)
    calls = Calls(page=ex.Fetched("https://devauto.example/", 200, "<p>new design</p>"))
    res = ex.scan_exposure(store, p.id, registry=_reg(devblocked="bot_blocked"),
                           fetch=calls, use_browser=False)
    assert res.entries[0].reason == "page_unrecognized"
    reg = _reg(devblocked="bot_blocked")
    b = reg.get("devauto")
    odd = b.model_copy(update={"search": b.search.model_copy(
        update={"result_selector": "div:has(a)"})})
    reg = reg.model_copy(update={"brokers": [odd if x.id == "devauto" else x
                                             for x in reg.brokers]})
    calls = Calls(page=ex.Fetched("https://devauto.example/", 200, HTML))
    res = ex.scan_exposure(store, p.id, registry=reg, fetch=calls, refresh=True,
                           use_browser=False)
    assert res.entries[0].reason == "no_parser"


def test_consent_is_required(store):
    from freemyid.models import Consent, ConsentBasis
    p = _saved(store, consent=Consent(basis=ConsentBasis.SELF, attested_by="x",
                                      text_version="0"))
    with pytest.raises(ex.ExposureRefused):
        ex.scan_exposure(store, p.id, registry=fixture_registry(),
                         fetch=Calls(exc=AssertionError("fetched")))


# ------------------------------------------------------------------ http fetcher


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_http_fetcher_honest_ua_and_redirect_policy():
    from freemyid.netpolicy import NetPolicy
    reg = fixture_registry()
    b = reg.get("devauto")
    seen = []

    def ok(req):
        seen.append(req)
        if req.url.path == "/start":
            return httpx.Response(302, headers={"location": "/name/jane-testperson/il"})
        return httpx.Response(200, html="<p>No records found</p>")

    f = ex.http_fetcher(NetPolicy(reg), client=_client(ok))
    got = f(b, "https://devauto.example/start")
    assert got.url == "https://devauto.example/name/jane-testperson/il"
    assert seen[0].headers["user-agent"].startswith("FreeMyID/")
    assert "freemyid.org/safety" in seen[0].headers["user-agent"]

    def away(req):
        return httpx.Response(302, headers={"location": "https://tracker.example/x"})

    with pytest.raises(ex.FetchFailed) as e:
        ex.http_fetcher(NetPolicy(reg), client=_client(away))(b, "https://devauto.example/")
    assert e.value.reason == "blocked_by_policy"
    with pytest.raises(ex.FetchFailed) as e:
        ex.http_fetcher(NetPolicy(reg), client=_client(ok))(b, "http://devauto.example/")
    assert e.value.reason == "blocked_by_policy"

    def huge(req):
        return httpx.Response(200, content=b"x" * (ex.MAX_BYTES + 10))

    with pytest.raises(ex.FetchFailed) as e:
        ex.http_fetcher(NetPolicy(reg), client=_client(huge))(b, "https://devauto.example/")
    assert e.value.reason == "too_large"


def _bomb(coding: str, size: int) -> bytes:
    import gzip
    import zlib
    raw = b"<p>" + b"A" * size
    if coding == "gzip":
        return gzip.compress(raw, 9)
    if coding == "deflate":
        return zlib.compress(raw, 9)
    c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)      # raw deflate
    return c.compress(raw) + c.flush()


@pytest.mark.parametrize("coding,header", [("gzip", "gzip"), ("deflate", "deflate"),
                                           ("rawdeflate", "deflate")])
def test_sec93d_compression_bomb_stops_at_the_cap(coding, header):
    from freemyid.netpolicy import NetPolicy
    reg = fixture_registry()
    b = reg.get("devauto")
    bomb = _bomb(coding, 50 * ex.MAX_BYTES)      # ~100 MB inflated, ~100 KB on the wire
    assert len(bomb) < ex.MAX_BYTES // 10
    import tracemalloc
    pieces = [bomb[i:i + 65536] for i in range(0, len(bomb), 65536)]
    served: list[int] = []

    def stream():
        for p in pieces:
            served.append(len(p))
            yield p

    def h(req):
        # a streamed body, as from a real socket (bytes content is pre-read by httpx)
        return httpx.Response(200, headers={"content-encoding": header}, content=stream())

    tracemalloc.start()
    try:
        with pytest.raises(ex.FetchFailed) as e:
            ex.http_fetcher(NetPolicy(reg), client=_client(h))(b, "https://devauto.example/")
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert e.value.reason == "too_large"
    # it stopped early: not all of the bomb was read, and memory stayed near the cap
    assert sum(served) < len(bomb)
    assert peak < 6 * ex.MAX_BYTES


@pytest.mark.parametrize("coding,header", [("gzip", "gzip"), ("deflate", "deflate"),
                                           ("rawdeflate", "deflate")])
def test_sec93d_compressed_page_under_the_cap_reads(coding, header):
    from freemyid.netpolicy import NetPolicy
    reg = fixture_registry()
    b = reg.get("devauto")

    def h(req):
        assert req.headers["accept-encoding"] == "gzip, deflate"
        return httpx.Response(200, headers={"content-encoding": header,
                                            "content-type": "text/html; charset=utf-8"},
                              content=iter([_bomb(coding, 1000)]))

    got = ex.http_fetcher(NetPolicy(reg), client=_client(h))(b, "https://devauto.example/")
    assert got.html == "<p>" + "A" * 1000


def test_sec93d_unrequested_encoding_and_bad_stream_are_refused():
    from freemyid.netpolicy import NetPolicy
    reg = fixture_registry()
    b = reg.get("devauto")
    for ce, body in (("br", b"\x0b\x02\x80hi\x03"), ("gzip", b"not gzip at all")):
        def h(req, ce=ce, body=body):
            return httpx.Response(200, headers={"content-encoding": ce},
                                  content=iter([body]))
        with pytest.raises(ex.FetchFailed) as e:
            ex.http_fetcher(NetPolicy(reg), client=_client(h))(b, "https://devauto.example/")
        assert e.value.reason == "http_error"


def test_read_timeout_is_too_slow_with_plain_wording():
    from freemyid.exposure_models import HAND_REASONS
    from freemyid.netpolicy import NetPolicy
    reg = fixture_registry()

    def h(req):
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(ex.FetchFailed) as e:
        ex.http_fetcher(NetPolicy(reg), client=_client(h))(reg.get("devauto"),
                                                           "https://devauto.example/")
    assert e.value.reason == "too_slow"
    assert HAND_REASONS["too_slow"] == "The site took too long to answer."


# ------------------------------------------------------------------ CLI


def test_cli_exposure_json_and_text(store, monkeypatch):
    from freemyid import cli
    p = _saved(store)
    monkeypatch.setattr(cli, "_registry", fixture_registry)
    runner = CliRunner()
    with fixture_server():
        r = runner.invoke(cli.app, ["exposure", "--json", "--profile", p.id])
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)
    assert doc["schema"] == "exposure/1" and doc["exit_code"] == 0
    prof = doc["profiles"][0]
    assert prof["score"] == 17 and prof["counts"]["confirmed_sites"] == 1
    assert {e["status"] for e in prof["entries"]} == {"found", "check_by_hand"}
    r = runner.invoke(cli.app, ["exposure", "--offline"])
    assert r.exit_code == 0 and "exposure score 17" in r.stdout
    assert "Please check these yourself" in r.stdout


def test_cli_exposure_headless_not_configured(monkeypatch):
    from freemyid import cli
    r = CliRunner().invoke(cli.app, ["exposure", "--headless", "--json"])
    assert r.exit_code == 4
    assert json.loads(r.stdout)["schema"] == "error/1"
