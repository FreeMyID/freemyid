"""tools/registry_health.py: offline schema/content checks, polite online checks (fake transport
only; no test here touches the network), report output and exit codes."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from tests.conftest import FIXTURES, ROOT, full_registry_path

_spec = importlib.util.spec_from_file_location("registry_health",
                                               ROOT / "tools" / "registry_health.py")
assert _spec and _spec.loader
rh = importlib.util.module_from_spec(_spec)
sys.modules["registry_health"] = rh     # dataclasses look the module up
_spec.loader.exec_module(rh)

TODAY = date(2026, 11, 7)
BASE = yaml.safe_load((FIXTURES / "registry_min.yaml").read_text(encoding="utf-8"))


def _write(tmp_path: Path, mutate=None, name: str = "reg.yaml") -> Path:
    data = copy.deepcopy(BASE)
    for b in data["brokers"]:          # healthy defaults: cited + recently verified
        b.setdefault("source_urls", [f"https://{b['domains'][0]}/privacy"])
        b.setdefault("last_verified", date(2026, 10, 1))
    if mutate:
        mutate(data)
    p = tmp_path / name
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return p


def _checks(findings, level=None):
    return {(f.broker, f.check) for f in findings if level is None or f.level == level}


def _broker(data, bid):
    return next(b for b in data["brokers"] if b["id"] == bid)


# ------------------------------------------------------------------------------ offline

def test_real_sample_registry_has_no_errors():
    errs = [f for f in rh.check_offline(rh.SAMPLE) if f.level == rh.ERROR]
    assert errs == []


def test_real_full_registry_has_no_errors():
    full = full_registry_path()
    if full is None:
        pytest.skip("brokers/registry.yaml not present (public checkout)")
    errs = [f for f in rh.check_offline(full) if f.level == rh.ERROR]
    assert errs == []


def test_healthy_fixture_is_clean(tmp_path):
    assert rh.check_offline(_write(tmp_path), today=TODAY) == []


def test_non_https_url_is_an_error(tmp_path):
    def m(d):
        _broker(d, "fakemail")["source_urls"] = ["http://fakemail.example/privacy"]
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    assert ("fakemail", "https") in _checks(f, rh.ERROR)


def test_http_inside_form_step_is_an_error(tmp_path):
    def m(d):
        _broker(d, "fakepeople")["form"][0]["url"] = "HTTP://fakepeople.example/optout"
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    assert ("fakepeople", "https") in _checks(f, rh.ERROR)


@pytest.mark.parametrize("bad", ["privacy@@fakemail.example", "privacy fakemail.example",
                                 "privacy@fakemail", ".privacy@fakemail.example",
                                 "pri..vacy@fakemail.example", "privacy@-fakemail.example",
                                 "privacy@fakemail.example "])
def test_bad_email_syntax_is_an_error(tmp_path, bad):
    def m(d):
        _broker(d, "fakemail")["opt_out_email"] = bad
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    assert ("fakemail", "email") in _checks(f, rh.ERROR)


@pytest.mark.parametrize("good", ["privacy@fakemail.example", "opt.out+x@mail.fakemail.example"])
def test_good_email_syntax_passes(good):
    assert rh.EMAIL_RE.match(good)


def test_missing_citation_is_a_warning(tmp_path):
    def m(d):
        _broker(d, "fakepeople")["source_urls"] = []
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    assert ("fakepeople", "citation") in _checks(f, rh.WARN)
    assert not _checks(f, rh.ERROR)


def test_stale_and_missing_verified_dates_warn(tmp_path):
    def m(d):
        _broker(d, "fakepeople")["last_verified"] = date(2026, 5, 9)    # 182 days
        del _broker(d, "fakemail")["last_verified"]
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    assert {("fakepeople", "stale"), ("fakemail", "stale")} <= _checks(f, rh.WARN)
    # exactly 180 days is still fresh
    f2 = rh.check_offline(_write(tmp_path, lambda d: _broker(d, "fakepeople").update(
        last_verified=date(2026, 5, 11))), today=TODAY)
    assert ("fakepeople", "stale") not in _checks(f2)


def test_stale_registry_updated_date_warns(tmp_path):
    f = rh.check_offline(_write(tmp_path, lambda d: d.update(updated=date(2025, 1, 1))),
                         today=TODAY)
    assert ("-", "stale") in _checks(f, rh.WARN)


def test_duplicate_domains(tmp_path):
    def m(d):
        _broker(d, "fakepeople")["domains"] = ["fakepeople.example", "FakePeople.example."]
        _broker(d, "fakemail")["domains"] = ["fakemail.example", "fakepeople.example"]
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    assert ("fakepeople", "duplicate_domain") in _checks(f, rh.ERROR)      # twice in one broker
    assert ("fakepeople,fakemail", "duplicate_domain") in _checks(f, rh.WARN)  # shared


def test_schema_failure_names_the_broker(tmp_path):
    def m(d):
        _broker(d, "fakemail")["category"] = "not_a_category"
    f = rh.check_offline(_write(tmp_path, m), today=TODAY)
    errs = _checks(f, rh.ERROR)
    assert ("-", "schema") in errs and ("fakemail", "schema") in errs


def test_yaml_alias_bomb_and_garbage_are_errors(tmp_path):
    bomb = tmp_path / "bomb.yaml"
    bomb.write_text("a: &x [1, 2]\nbrokers: *x\n", encoding="utf-8")
    assert ("-", "load") in _checks(rh.check_offline(bomb, today=TODAY), rh.ERROR)
    junk = tmp_path / "junk.yaml"
    junk.write_text("- just\n- a list\n", encoding="utf-8")
    assert ("-", "schema") in _checks(rh.check_offline(junk, today=TODAY), rh.ERROR)


# ------------------------------------------------------------------------------ CLI

def test_offline_never_opens_a_connection(tmp_path, monkeypatch):
    import httpx

    def boom(*a, **k):
        raise AssertionError("network used without --online")
    monkeypatch.setattr(httpx, "Client", boom)
    assert rh.main([str(_write(tmp_path)), "-q", "--today", "2026-11-07"]) == 0


def test_exit_codes_and_strict(tmp_path):
    ok = _write(tmp_path)
    warn = _write(tmp_path, lambda d: _broker(d, "fakepeople").update(source_urls=[]), "w.yaml")
    err = _write(tmp_path, lambda d: _broker(d, "fakemail").update(opt_out_email="x"), "e.yaml")
    t = ["-q", "--today", "2026-11-07"]
    assert rh.main([str(ok), *t]) == 0
    assert rh.main([str(warn), *t]) == 0
    assert rh.main([str(warn), "--strict", *t]) == 1
    assert rh.main([str(err), *t]) == 1
    assert rh.main([str(tmp_path / "missing.yaml"), *t]) == 2


def test_selectors_requires_online(tmp_path):
    with pytest.raises(SystemExit):
        rh.main([str(_write(tmp_path)), "--selectors"])


def test_reports_markdown_and_json(tmp_path):
    p = _write(tmp_path, lambda d: _broker(d, "fakepeople").update(source_urls=[]))
    md, js = tmp_path / "r.md", tmp_path / "r.json"
    rh.main([str(p), "-q", "--today", "2026-11-07", "--report", str(md)])
    rh.main([str(p), "-q", "--today", "2026-11-07", "--report", str(js)])
    assert "| WARN | reg.yaml | fakepeople | citation |" in md.read_text(encoding="utf-8")
    rows = json.loads(js.read_text(encoding="utf-8"))
    assert rows == [{"level": "WARN", "registry": "reg.yaml", "broker": "fakepeople",
                     "check": "citation", "detail": "no source_urls"}]


def test_default_files_are_sample_plus_full_when_present(monkeypatch, capsys):
    monkeypatch.setattr(rh, "FULL", Path("/nonexistent/registry.yaml"))
    assert rh.main(["-q"]) == 0
    assert "1 file(s)" in capsys.readouterr().out


# ------------------------------------------------------------------------------ online (fake)

class FakeNet:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, url):
        self.calls.append((method, url))
        r = self.routes.get((method, url)) or self.routes.get(url) or (404, None, b"")
        if isinstance(r, Exception):
            raise r
        return r


def _online(tmp_path, routes, mutate=None, **kw):
    net, sleeps = FakeNet(routes), []
    f = rh.check_online(_write(tmp_path, mutate), requester=net, sleep=sleeps.append, **kw)
    return f, net, sleeps


OPT = "https://fakepeople.example/optout"
MAILURL = "https://fakemail.example/"


def test_online_ok_is_polite(tmp_path):
    f, net, sleeps = _online(tmp_path, {OPT: (200, None, b""), MAILURL: (200, None, b"")},
                             delay=0.01)
    assert f == []
    assert [m for m, _ in net.calls] == ["HEAD", "HEAD"]
    assert sleeps == [1.0]                       # delay is clamped to at least 1 s


def test_online_404_error_403_warn(tmp_path):
    f, _, _ = _online(tmp_path, {OPT: (404, None, b""), MAILURL: (403, None, b"")})
    assert ("fakepeople", "online") in _checks(f, rh.ERROR)
    assert ("fakemail", "online") in _checks(f, rh.WARN)


def test_online_head_refused_falls_back_to_get(tmp_path):
    routes = {("HEAD", OPT): (405, None, b""), ("GET", OPT): (200, None, b""),
              MAILURL: (200, None, b"")}
    f, net, _ = _online(tmp_path, routes)
    assert f == [] and ("GET", OPT) in net.calls


def test_online_redirect_off_allowlist_is_never_fetched(tmp_path):
    routes = {OPT: (302, "https://tracker.invalid/x", b""), MAILURL: (301, "/home", b""),
              "https://fakemail.example/home": (200, None, b"")}
    f, net, _ = _online(tmp_path, routes)
    assert ("fakepeople", "online") in _checks(f, rh.ERROR)
    assert all("tracker.invalid" not in u for _, u in net.calls)
    assert ("HEAD", "https://fakemail.example/home") in net.calls   # same-site relative ok


def test_online_redirect_to_http_is_refused(tmp_path):
    routes = {OPT: (302, "http://fakepeople.example/optout", b""), MAILURL: (200, None, b"")}
    f, net, _ = _online(tmp_path, routes)
    assert ("fakepeople", "online") in _checks(f, rh.ERROR)
    assert all(u.startswith("https://") for _, u in net.calls)


def test_online_redirect_loop_and_network_error(tmp_path):
    routes = {OPT: (302, OPT, b""), MAILURL: OSError("boom")}
    f, net, _ = _online(tmp_path, routes)
    details = {f.broker: f.detail for f in f}
    assert "redirects" in details["fakepeople"]
    assert details["fakemail"] == "request failed: OSError"
    assert len([u for _, u in net.calls if u == OPT]) == rh.MAX_REDIRECTS + 1


def test_online_selector_presence(tmp_path):
    page = b'<form><input id="email"><input name="other"></form>'
    routes = {OPT: (200, None, b""), ("GET_BODY", OPT): (200, None, page),
              MAILURL: (200, None, b"")}
    f, _, _ = _online(tmp_path, routes, selectors=True)
    sel = [x for x in f if x.check == "selector"]
    # "#email" found; "input[name=url]" missing; "button.submit" is not a simple selector (skipped)
    assert [(x.level, x.detail) for x in sel] == [(rh.ERROR, "not found: input[name=url]")]


def test_online_skips_invalid_registry(tmp_path):
    p = _write(tmp_path, lambda d: _broker(d, "fakemail").update(category="nope"))
    f = rh.check_online(p, requester=FakeNet({}), sleep=lambda s: None)
    assert [x.check for x in f] == ["online"] and f[0].level == rh.ERROR
