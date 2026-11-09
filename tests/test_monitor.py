"""BL-IN-06 broker monitor (freemyid.monitor): offline, fake network only."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from freemyid import monitor as mon
from freemyid.engine._dev import fixture_registry

OPT = "https://devauto.example/optout"
FORM_OK = (b'<form><input id="email" type="email" name="email">'
           b'<input type="text" name="url"><input type="hidden" name="csrf" value="r1">'
           b'<button class="submit">Send</button></form>'
           b"<p>Jane Q Testperson secret page words</p>")
RECAPTCHA = b'<iframe src="https://www.google.com/recaptcha/api2/anchor"></iframe>'
NOW = datetime(2026, 11, 9, 6, 17, tzinfo=UTC)


class FakeNet:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, url):
        self.calls.append((method, url))
        r = self.routes.get((method, url)) or self.routes.get(url) or (404, None, b"")
        if isinstance(r, Exception):
            raise r
        return r


def _run(routes, ids=("devauto",), previous=None, loader=None):
    net, sleeps = FakeNet(routes), []
    doc = mon.run_monitor(fixture_registry(), requester=net, sleep=sleeps.append, now=NOW,
                          previous=previous, broker_ids=list(ids), page_loader=loader)
    return doc, net, sleeps


def _one(doc, bid="devauto"):
    return next(b for b in doc["brokers"] if b["broker_id"] == bid)


# ------------------------------------------------------------------ health values

def test_ok_page_reads_only_and_fingerprints_structure():
    doc, net, _ = _run({OPT: (200, None, FORM_OK)})
    b = _one(doc)
    assert doc["schema"] == "monitor/1" and doc["counts"]["ok"] == 1
    assert b["health"] == "ok" and b["selectors_missing"] == []
    assert b["selectors_unchecked"] == 1            # "button.submit" needs a browser
    assert b["fingerprint"] and len(b["fingerprint"]) == 16
    assert net.calls == [("GET_BODY", OPT)]          # one GET, nothing posted


def test_hidden_tokens_and_page_text_do_not_change_the_fingerprint():
    a = _one(_run({OPT: (200, None, FORM_OK)})[0])["fingerprint"]
    other = FORM_OK.replace(b'value="r1"', b'value="r2"').replace(b"secret", b"other")
    assert _one(_run({OPT: (200, None, other)})[0])["fingerprint"] == a
    renamed = FORM_OK.replace(b'name="email"', b'name="mail"')
    assert _one(_run({OPT: (200, None, renamed)})[0])["fingerprint"] != a


def test_missing_selector_is_form_changed():
    page = FORM_OK.replace(b'id="email"', b'id="e-mail"')
    b = _one(_run({OPT: (200, None, page)})[0])
    assert b["health"] == "form_changed" and b["selectors_missing"] == ["#email"]


@pytest.mark.parametrize("route", [(200, None, RECAPTCHA), (429, None, b""),
                                   (403, None, b"<p>Access denied</p>")])
def test_challenge_or_bot_status_is_blocked_never_retried(route):
    doc, net, _ = _run({OPT: route})
    assert _one(doc)["health"] == "blocked" and len(net.calls) == 1


def test_unreachable_cases():
    assert _one(_run({OPT: (404, None, b"")})[0])["health"] == "unreachable"
    doc, net, _ = _run({OPT: (302, "https://tracker.invalid/x", b"")})
    assert _one(doc)["health"] == "unreachable"
    assert all("tracker.invalid" not in u for _, u in net.calls)
    doc, net, _ = _run({OPT: (302, "http://devauto.example/optout", b"")})
    assert _one(doc)["health"] == "unreachable" and len(net.calls) == 1
    assert "request failed: OSError" in _one(_run({OPT: OSError("x")})[0])["detail"]


def test_moved_page_report_has_no_query_string():
    new = "https://devauto.example/privacy/remove?token=abc123"
    doc, _, _ = _run({OPT: (301, new, b""), new: (200, None, FORM_OK)})
    b = _one(doc)
    assert b["health"] == "moved" and "/privacy/remove" in b["detail"]
    assert "token" not in json.dumps(doc)
    assert _one(_run({OPT: (301, OPT + "/", b""), OPT + "/": (200, None, FORM_OK)})[0])[
        "health"] == "ok"                        # a trailing slash is not a move


def test_js_only_page_is_unknown_without_a_browser():
    b = _one(_run({OPT: (200, None, b"<div id=app></div><script src=a.js></script>")})[0])
    assert b["health"] == "unknown" and b["fingerprint"] is None


def test_browser_load_is_goto_only_and_challenge_is_blocked():
    seen = []

    def loader(broker, url):
        seen.append((broker.id, url))
        return 200, url, FORM_OK.decode()

    js = {OPT: (200, None, b"<div id=app></div>")}
    b = _one(_run(js, loader=loader)[0])
    assert b["health"] == "ok" and b["used_browser"] and seen == [("devauto", OPT)]

    def challenged(broker, url):
        raise mon.ChallengeSeen()
    assert _one(_run(js, loader=challenged)[0])["health"] == "blocked"

    def off_list(broker, url):
        return 200, "https://elsewhere.invalid/", FORM_OK.decode()
    assert _one(_run(js, loader=off_list)[0])["health"] == "moved"


def test_form_steps_are_never_run():
    """Only goto pages are loaded; fill/submit steps give selectors and nothing else."""
    page, sels = mon.form_plan(next(b for b in fixture_registry().brokers
                                    if b.id == "devauto"))
    assert page == OPT and sels == ["#email", "input[name=url]", "button.submit"]
    _, net, _ = _run({OPT: (200, None, FORM_OK)})
    assert {m for m, _ in net.calls} == {"GET_BODY"}


# ------------------------------------------------------------------ week over week

def test_compare_with_last_week():
    first, _, _ = _run({OPT: (200, None, FORM_OK)})
    renamed = FORM_OK.replace(b'name="url"', b'name="link"')
    second, _, _ = _run({OPT: (200, None, renamed)}, previous=first)
    b = _one(second)
    assert b["health"] == "form_changed" and b["previous_health"] == "ok" and b["changed"]
    assert second["changed"] == ["devauto"]
    assert b["weeks_bad"] == 1 and not b["demote_suggested"]
    assert second["previous_generated_at"] == first["generated_at"]
    third, _, _ = _run({OPT: (200, None, renamed.replace(b'id="email"', b'id="x"'))},
                       previous=second)
    b = _one(third)
    assert b["health"] == "form_changed" and not b["changed"]
    assert b["weeks_bad"] == 2 and b["demote_suggested"]
    assert b["first_seen_bad"] == second["generated_at"][:10]
    assert third["demote_suggested"] == ["devauto"]


def test_bad_previous_doc_is_ignored():
    doc, _, _ = _run({OPT: (200, None, FORM_OK)}, previous={"schema": "other/1"})
    assert doc["previous_generated_at"] is None and doc["changed"] == []


# ------------------------------------------------------------------ run-level rules

def test_pacing_and_one_failure_never_stops_the_run():
    routes = {OPT: OSError("down"), "https://devweb.example/remove": (200, None, FORM_OK)}
    doc, net, sleeps = _run(routes, ids=("devauto", "devweb"))
    assert [b["health"] for b in doc["brokers"]] == ["unreachable", "ok"]
    assert len(sleeps) == len(net.calls) - 1 and all(2.0 <= s <= 5.0 for s in sleeps)


def test_report_holds_no_page_text():
    doc, _, _ = _run({OPT: (200, None, FORM_OK)})
    blob = json.dumps(doc).lower()
    for word in ("testperson", "secret", "send", "csrf", "r1"):
        assert word not in blob


def test_delay_floor_is_one_second():
    sleeps: list[float] = []
    pause = mon._pauser((0.0, 0.0), sleeps.append)
    pause(), pause()
    assert sleeps == [1.0]


# ------------------------------------------------------------------ CLI

DEV_REG = "src/freemyid/engine/_dev/registry.yaml"


def _cli(monkeypatch, routes, *args):
    from typer.testing import CliRunner

    from freemyid import cli
    from tests.conftest import ROOT
    net = FakeNet(routes)
    monkeypatch.setattr(mon, "httpx_requester", lambda *a, **k: (net, lambda: None))
    net.pauses = 0

    def pause() -> None:                  # counts the gaps; never sleeps (CR #63, #66)
        net.pauses += 1
    monkeypatch.setattr(mon, "_pauser", lambda delay, sleep: pause)
    r = CliRunner().invoke(cli.app, ["monitor", "--registry", str(ROOT / DEV_REG),
                                     "--broker", "devauto", *args])
    return r, net


def test_cli_monitor_json_and_previous(monkeypatch, tmp_path):
    r, net = _cli(monkeypatch, {OPT: (200, None, FORM_OK)}, "--json")
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)                       # exactly one JSON object
    assert doc["schema"] == "monitor/1" and _one(doc)["health"] == "ok"
    assert net.calls == [("GET_BODY", OPT)]
    prev = tmp_path / "last.json"
    prev.write_text(r.stdout, encoding="utf-8")
    renamed = FORM_OK.replace(b'name="url"', b'name="link"')
    r, _ = _cli(monkeypatch, {OPT: (200, None, renamed)}, "--json", "--previous", str(prev))
    doc = json.loads(r.stdout)
    assert doc["changed"] == ["devauto"] and _one(doc)["health"] == "form_changed"


def test_cli_monitor_text_and_bad_inputs(monkeypatch, tmp_path):
    r, _ = _cli(monkeypatch, {OPT: (429, None, b"")})
    assert r.exit_code == 0 and "devauto: blocked" in r.stdout
    junk = tmp_path / "junk.json"
    junk.write_text("[1, 2]", encoding="utf-8")
    r, _ = _cli(monkeypatch, {OPT: (200, None, FORM_OK)}, "--json", "--previous", str(junk))
    assert r.exit_code == 0 and json.loads(r.stdout)["previous_generated_at"] is None
    assert "not a monitor/1 file" in r.stderr
    from typer.testing import CliRunner

    from freemyid import cli
    r = CliRunner().invoke(cli.app, ["monitor", "--json", "--registry",
                                     str(tmp_path / "missing.yaml")])
    assert r.exit_code == 1 and json.loads(r.stdout)["schema"] == "error/1"



def test_cli_pauser_patch_really_stops_sleeping(monkeypatch):
    """Two requests through the CLI path use the patched pauser, so nothing sleeps."""
    moved = {OPT: (302, "https://devauto.example/optout2", b""),
             "https://devauto.example/optout2": (200, None, FORM_OK)}
    r, net = _cli(monkeypatch, moved, "--json")
    assert r.exit_code == 0 and len(net.calls) == 2 and net.pauses == 2


# ------------------------------------------------------------------ CR cycle 2

def test_data_attributes_are_not_ids_names_or_types():
    assert mon.selector_present("#email", '<input data-id="email">') is False
    assert mon.selector_present("[name=email]", '<input data-name="email">') is False
    assert mon.selector_present("#email", '<input data-x="1" id="email">') is True
    assert mon.selector_present("[name=email]", "<input name='email'>") is True
    html = '<input type="text" name="url" data-name="x" data-type="y">'
    assert mon.form_fields(html) == [("input", "text", "url")]


def test_browser_load_waits_its_turn():
    """The headless load is another request to the same host: it gets a pause too."""
    def loader(broker, url):
        return 200, url, FORM_OK.decode()
    doc, net, sleeps = _run({OPT: (200, None, b"<div id=app></div>")}, loader=loader)
    assert _one(doc)["used_browser"]
    assert len(net.calls) == 1 and len(sleeps) == 1 and 2.0 <= sleeps[0] <= 5.0


def test_slow_body_is_cut_off_by_the_read_budget():
    import httpx
    ticks = iter(range(0, 1000, 10))        # every clock() call is 10 s later

    def slow_body():
        for _ in range(20):
            yield b"<p>" + b"x" * 100 + b"</p>"

    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=slow_body()))
    req, close = mon.httpx_requester(transport=transport, clock=lambda: float(next(ticks)))
    with pytest.raises(TimeoutError):
        req("GET_BODY", OPT)
    close()


def test_slow_body_makes_the_broker_unreachable_not_form_changed():
    def slow(method, url):
        raise TimeoutError()
    doc = mon.run_monitor(fixture_registry(), requester=slow, sleep=lambda s: None, now=NOW,
                          broker_ids=["devauto"])
    b = _one(doc)
    assert b["health"] == "unreachable" and b["detail"] == "request failed: TimeoutError"


def test_fast_body_is_read_whole():
    import httpx
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=FORM_OK))
    req, close = mon.httpx_requester(transport=transport)
    assert req("GET_BODY", OPT) == (200, None, FORM_OK)
    close()


class _Close:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1


def test_cli_browser_flag_wires_the_loader_and_always_closes(monkeypatch):
    seen, closer = [], _Close()

    def fake_loader_factory(policy, cfg):
        def load(broker, url):
            seen.append((broker.id, url))
            return 200, url, FORM_OK.decode()
        return load, closer
    monkeypatch.setattr(mon, "browser_page_loader", fake_loader_factory)
    r, _ = _cli(monkeypatch, {OPT: (200, None, b"<div id=app></div>")}, "--json", "--browser")
    assert r.exit_code == 0, r.output
    doc = json.loads(r.stdout)
    assert _one(doc)["used_browser"] and seen == [("devauto", OPT)] and closer.n == 1

    closer2 = _Close()
    monkeypatch.setattr(mon, "browser_page_loader", lambda policy, cfg: (lambda b, u: None, closer2))

    def boom(*a, **k):
        raise RuntimeError("run failed")
    monkeypatch.setattr(mon, "run_monitor", boom)
    r, _ = _cli(monkeypatch, {}, "--json", "--browser")
    assert r.exit_code != 0 and closer2.n == 1


def test_browser_page_loader_maps_a_challenge_to_challenge_seen(monkeypatch):
    from freemyid.engine import exposure

    class FakeFetcher:
        def __init__(self, policy, cfg):
            self.closed = False

        def __call__(self, broker, url):
            raise exposure.FetchFailed("challenge" if "chal" in url else "error")

        def close(self):
            self.closed = True
    monkeypatch.setattr(exposure, "BrowserFetcher", FakeFetcher)
    load, close = mon.browser_page_loader(None, None)
    with pytest.raises(mon.ChallengeSeen):
        load(None, "https://devauto.example/chal")
    with pytest.raises(exposure.FetchFailed):
        load(None, "https://devauto.example/other")
    close()


def test_no_browser_load_after_the_broker_budget_is_spent():
    calls = []
    import itertools
    t = itertools.chain([0.0, 1.0], itertools.repeat(99.0))   # budget spent after the GET

    def loader(broker, url):
        calls.append(url)
        return 200, url, FORM_OK.decode()
    b = next(x for x in fixture_registry().brokers if x.id == "devauto")
    from freemyid.netpolicy import NetPolicy
    net = FakeNet({OPT: (200, None, b"<div id=app></div>")})
    h = mon.check_broker(b, NetPolicy(fixture_registry()), net, lambda: None,
                         page_loader=loader, clock=lambda: next(t))
    assert h.health == "unknown" and "took longer" in h.detail and calls == []


# ------------------------------------------------------------------ CR #64 / #66 cycle 3

def test_unparsable_selector_on_a_static_form_does_not_load_the_browser():
    """`button.submit` can't be checked statically or on rendered HTML: no second load."""
    calls = []

    def loader(broker, url):
        calls.append(url)
        return 200, url, FORM_OK.decode()
    doc, net, sleeps = _run({OPT: (200, None, FORM_OK)}, loader=loader)
    b = _one(doc)
    assert calls == [] and not b["used_browser"] and len(net.calls) == 1 and sleeps == []
    assert b["health"] == "ok" and b["selectors_unchecked"] == 1


@pytest.mark.parametrize("status", [404, 500])
def test_browser_http_error_is_unreachable_not_form_changed(status):
    def loader(broker, url):
        return status, url, "<html><p>Not here</p></html>"
    b = _one(_run({OPT: (200, None, b"<div id=app></div>")}, loader=loader)[0])
    assert b["health"] == "unreachable" and b["http_status"] == status
    assert b["selectors_missing"] == []


def test_failures_are_logged_with_a_traceback_at_debug(monkeypatch, caplog):
    import logging

    def loader(broker, url):
        raise RuntimeError("boom")
    with caplog.at_level(logging.DEBUG, logger="freemyid.monitor"):
        b = _one(_run({OPT: (200, None, b"<div id=app></div>")}, loader=loader)[0])
    assert b["detail"] == "browser load failed: RuntimeError"
    assert any(r.exc_info and r.exc_info[0] is RuntimeError for r in caplog.records)
    caplog.clear()

    def broken(*a, **k):
        raise AttributeError("bug")
    monkeypatch.setattr(mon, "check_broker", broken)
    with caplog.at_level(logging.DEBUG, logger="freemyid.monitor"):
        b = _one(_run({OPT: (200, None, FORM_OK)})[0])
    assert b["detail"] == "check failed: AttributeError"
    assert any(r.exc_info and r.exc_info[0] is AttributeError for r in caplog.records)


def test_run_monitor_looks_up_time_sleep_at_call_time(monkeypatch):
    """No `sleep=` given: the gap uses time.sleep as it is now, not as bound at import."""
    slept: list[float] = []
    monkeypatch.setattr(mon.time, "sleep", slept.append)
    moved = {OPT: (302, "https://devauto.example/optout2", b""),
             "https://devauto.example/optout2": (200, None, FORM_OK)}
    net = FakeNet(moved)
    mon.run_monitor(fixture_registry(), requester=net, now=NOW, broker_ids=["devauto"])
    assert len(net.calls) == 2 and len(slept) == 1 and 2.0 <= slept[0] <= 5.0


# ------------------------------------------------------------------ WO-211 findings

def test_previous_reports_new_and_removed_brokers():
    """A broker in last week's file but not checked now is `removed_brokers`; one checked
    now but absent last week is `new_brokers` (WO-211 finding 2)."""
    prev = {"schema": "monitor/1", "generated_at": "2026-11-02T06:17:00+00:00",
            "brokers": [{"broker_id": "devauto", "health": "ok"},
                        {"broker_id": "retired", "health": "ok"},
                        {"broker_id": "devauto", "health": "ok"}, "junk"]}
    doc, _, _ = _run({OPT: (200, None, FORM_OK)}, ids=(), previous=prev)
    checked = [b["broker_id"] for b in doc["brokers"]]
    assert "devauto" in checked and len(checked) > 1
    assert doc["removed_brokers"] == ["retired"]
    assert doc["new_brokers"] == sorted(set(checked) - {"devauto"})


def test_broker_filter_does_not_report_unchecked_brokers_as_removed():
    prev = {"schema": "monitor/1", "brokers": [{"broker_id": "devauto", "health": "ok"},
                                               {"broker_id": "devweb", "health": "ok"}]}
    doc, _, _ = _run({OPT: (200, None, FORM_OK)}, previous=prev)
    assert doc["new_brokers"] == [] and doc["removed_brokers"] == []


def test_without_previous_new_and_removed_are_empty():
    doc, _, _ = _run({OPT: (200, None, FORM_OK)})
    assert doc["new_brokers"] == [] and doc["removed_brokers"] == []


def test_cli_oversized_previous_is_not_compared(monkeypatch, tmp_path):
    """A valid monitor/1 file over 2 MB is refused like a non-monitor/1 file (finding 3)."""
    prev = tmp_path / "big.json"
    doc = {"schema": "monitor/1", "generated_at": "2026-11-02T06:17:00+00:00",
           "brokers": [{"broker_id": "devauto", "health": "ok", "pad": "x" * mon.MAX_PREVIOUS}]}
    prev.write_text(json.dumps(doc), encoding="utf-8")
    r, _ = _cli(monkeypatch, {OPT: (200, None, FORM_OK)}, "--json", "--previous", str(prev))
    assert r.exit_code == 0, r.output
    out = json.loads(r.stdout)
    assert out["previous_generated_at"] is None and out["removed_brokers"] == []
    assert "not a monitor/1 file; not compared" in r.stderr and "2 MB" in r.stderr


def test_load_previous_reads_at_most_the_cap(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"schema": "monitor/1", "brokers": []}), encoding="utf-8")
    assert mon.load_previous(p) == ({"schema": "monitor/1", "brokers": []}, "")
    p.write_bytes(b" " * (mon.MAX_PREVIOUS + 1))
    assert mon.load_previous(p) == (None, "larger than 2 MB")
    p.write_bytes(b"\xff{")
    assert mon.load_previous(p)[0] is None
    assert mon.load_previous(tmp_path / "missing.json")[0] is None
