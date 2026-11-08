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
    monkeypatch.setattr(mon.time, "sleep", lambda s: None)
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
