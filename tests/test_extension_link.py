"""The link between the app and its browser extension (freemyid.extension_link, docs/EXTENSION.md):
pairing, the PII-free status file, the removal inbox, form-fill plans and the 127.0.0.1 bridge."""
from __future__ import annotations

import http.client
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from freemyid import extension_link as el
from freemyid import native_host
from freemyid.engine import filler
from freemyid.models import BrokerStatus, ListingState, MatchLevel, ProfileField
from tests.conftest import make_profile

ROOT = Path(__file__).resolve().parents[1]
FF = "firefox:extension@freemyid.org"
CHROME = "chrome-extension://" + "abcdefghijklmnop" * 2 + "/"
T0 = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def _req(msg_type: str, **fields: object) -> dict:
    return {"v": 1, "type": msg_type, "id": "3f2c9d1e-0000-4000-8000-000000000002", **fields}


def _pair(origin: str = FF) -> None:
    code = el.start_pairing(origin)
    assert el.confirm_pairing(code) == origin


# ------------------------------------------------------------------------------------ pairing

def test_pairing_needs_the_code_the_browser_shows() -> None:
    code = el.start_pairing(FF, now=T0)
    assert re.fullmatch(r"\d{6}", code)
    assert el.pending_pairing(now=T0)["origin"] == FF
    assert not el.is_paired(FF)
    assert el.confirm_pairing(code, now=T0 + timedelta(minutes=9)) == FF
    assert el.is_paired(FF) and el.pending_pairing(now=T0) is None


def test_a_code_expires_and_wrong_guesses_void_it() -> None:
    code = el.start_pairing(FF, now=T0)
    assert el.confirm_pairing(code, now=T0 + el.PAIR_CODE_TTL + timedelta(seconds=1)) is None
    code = el.start_pairing(FF)
    wrong = f"{(int(code) + 1) % 10 ** 6:06d}"
    for _ in range(el.MAX_PAIR_ATTEMPTS):
        assert el.confirm_pairing(wrong) is None
    assert el.pending_pairing() is None
    assert el.confirm_pairing(code) is None          # the right code no longer works either
    assert el.paired_origins() == []


@pytest.mark.parametrize("origin", ["", "https://evil.example/", "chrome-extension://short/",
                                    "chrome-extension://" + "z" * 32 + "/", "firefox:", 7])
def test_only_extension_origins_can_pair(origin: object) -> None:
    with pytest.raises(ValueError):
        el.start_pairing(origin)            # type: ignore[arg-type]
    assert not el.is_paired(origin)


def test_unpair_and_files_are_private() -> None:
    _pair(FF)
    _pair(CHROME)
    assert set(el.paired_origins()) == {FF, CHROME}
    assert el.unpair(CHROME) == 1 and el.paired_origins() == [FF]
    f = el._dir() / el.PAIRING_FILE
    assert f.stat().st_mode & 0o077 == 0
    assert el.unpair() == 1 and el.paired_origins() == []


# ------------------------------------------------------------------------- the native host

def test_host_answers_only_ping_status_and_pair_start_before_pairing() -> None:
    assert native_host.handle_message(_req("ping"), origin=FF)["ok"] is True
    status = native_host.handle_message(_req("status"), origin=FF)
    assert status["ok"] is True and status["paired"] is False and status["app_open"] is False
    for req in (_req("site_check", hostname="fakepeople.example"),
                _req("start_removal", broker_id="fakepeople"),
                _req("fill_plan", broker_id="fakepeople", controls=[])):
        reply = native_host.handle_message(req, origin=FF)
        assert reply["ok"] is False and reply["error"] == "not_paired", req["type"]
    code = native_host.handle_message(_req("pair_start"), origin=FF)
    assert code["ok"] is True and el.pending_pairing()["code"] == code["code"]


def test_pair_start_needs_a_named_caller() -> None:
    reply = native_host.handle_message(_req("pair_start"), origin="")
    assert reply["ok"] is False and reply["error"] == "not_allowed"


def test_caller_origin_names_the_extension() -> None:
    dev = "abcdefghijklmnop" * 2
    assert native_host.caller_origin([f"chrome-extension://{dev}/"], [dev]) == CHROME
    assert native_host.caller_origin(["/path/manifest.json", "extension@freemyid.org"], []) == FF
    assert native_host.caller_origin([f"chrome-extension://{dev}/"], []) == ""
    assert native_host.caller_origin([], [dev]) == ""


def test_site_check_reads_the_status_file(store, fake_registry) -> None:
    _pair()
    p = make_profile()
    store.save_profile(p)
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="fakepeople",
                                   state=ListingState.SUBMITTED))
    el.write_status(store, fake_registry)
    reply = native_host.handle_message(_req("site_check", hostname="www.fakepeople.example"),
                                       origin=FF)
    assert (reply["ok"], reply["broker_id"], reply["listing_state"]) == (True, "fakepeople",
                                                                         "submitted")
    other = native_host.handle_message(_req("site_check", hostname="news.example.org"), origin=FF)
    assert other["broker_id"] is None and other["listing_state"] == "unknown"


def test_status_file_holds_ids_and_state_words_only(store, fake_registry) -> None:
    a, b = make_profile(), make_profile(label="Second")
    store.save_profile(a)
    store.save_profile(b)
    store.save_status(BrokerStatus(profile_id=a.id, broker_id="fakepeople",
                                   state=ListingState.REMOVED))
    store.save_status(BrokerStatus(profile_id=b.id, broker_id="fakepeople",
                                   state=ListingState.REAPPEARED))
    el.write_status(store, fake_registry)
    text = (el._dir() / el.STATUS_FILE).read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["brokers"]["fakepeople"] == "reappeared"      # the most urgent wins
    assert data["hosts"]["fakepeople.example"] == "fakepeople"
    for secret in ("Jane", "Testperson", "Springfield", "742", "217-555", a.id, b.id):
        assert secret not in text


def test_start_removal_goes_to_the_inbox_and_the_app_takes_it() -> None:
    _pair()
    reply = native_host.handle_message(_req("start_removal", broker_id="fakepeople"), origin=FF)
    assert reply["ok"] is True and reply["accepted"] is True and reply["now"] is False
    native_host.handle_message(_req("start_removal", broker_id="fakepeople"), origin=FF)
    assert el.take_inbox() == ["fakepeople"]                   # repeats collapse
    assert el.take_inbox() == []


def test_the_inbox_is_capped() -> None:
    for _ in range(el.MAX_INBOX):
        assert el.queue_removal("fakepeople", FF)
    assert not el.queue_removal("fakepeople", FF)
    assert not el.queue_removal("Not An Id", FF)


def test_process_inbox_runs_only_known_brokers_for_people_with_permission(store,
                                                                         fake_registry) -> None:
    ok = make_profile()
    store.save_profile(ok)
    calls = []
    el.queue_removal("fakepeople", FF)
    el.queue_removal("not_in_registry", FF)
    ran = el.process_inbox(store, fake_registry, dry_run=True,
                           run=lambda *a, **k: calls.append((a, k)))
    assert ran == ["fakepeople"]
    (args, kwargs), = calls
    assert [p.id for p in args[2]] == [ok.id]
    assert kwargs["broker_ids"] == ["fakepeople"] and kwargs["dry_run"] is True
    assert kwargs["interactive"] is False
    assert any(e.action == "extension_removal_request" for e in store.events(ok.id))


def test_process_inbox_drops_requests_when_nobody_gave_permission(store, fake_registry) -> None:
    from freemyid.models import Consent, ConsentBasis
    store.save_profile(make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by=" ",
                                                    text_version="old")))
    el.queue_removal("fakepeople", FF)
    calls = []
    assert el.process_inbox(store, fake_registry, dry_run=True,
                            run=lambda *a, **k: calls.append(1)) == []
    assert calls == [] and el.take_inbox() == []


# --------------------------------------------------------------------------------- fill plans

def _ctl(key: str, **kw: object) -> dict:
    base = {"key": key, "tag": "input", "type": "text", "name": "", "id": "", "label": "",
            "labelledby": "", "aria": "", "placeholder": "", "autocomplete": "", "title": "",
            "visible": True, "in_captcha": False, "disabled": False, "has_value": False,
            "maxlength": -1, "option_values": [], "option_texts": []}
    base.update(kw)
    return base


FORM = [
    _ctl("f0", label="First name"), _ctl("f1", label="Last name"),
    _ctl("f2", label="Email address", type="email"), _ctl("f3", label="Phone"),
    _ctl("f4", label="Profile URL"), _ctl("f5", label="City", in_captcha=True),
    _ctl("f6", label="Password", type="password"), _ctl("f7", label="Email", visible=False),
    _ctl("f8", tag="select", type="select", label="State",
         option_values=["", "IL", "IN"], option_texts=["Choose", "Illinois", "Indiana"]),
    _ctl("f9", label="Card number"),
]


def test_fill_plan_uses_the_filler_rules() -> None:
    controls = [filler.Control.from_js(c) for c in el.parse_controls(FORM)]
    values = {"first_name": "Jane", "last_name": "Testperson", "email": "box@example.test",
              "listing_url": "https://fakepeople.example/p/1", "state": "IL", "city": "Springfield"}
    plan, rep = filler.fill_plan(controls, values)
    assert plan == {"f0": "Jane", "f1": "Testperson", "f2": "box@example.test",
                    "f4": "https://fakepeople.example/p/1", "f8": "IL"}
    assert rep.protected >= 4                 # captcha, password, hidden, card number


def test_fill_plan_respects_maxlength_and_existing_values() -> None:
    controls = [filler.Control.from_js(c) for c in el.parse_controls(
        [_ctl("f0", label="Full name", maxlength=4), _ctl("f1", label="Email", has_value=True)])]
    plan, rep = filler.fill_plan(controls, {"full_name": "Jane Testperson", "email": "a@b.test"})
    assert plan == {"f0": "Jane"} and rep.already_filled == ["email"]


@pytest.mark.parametrize("bad", [
    "not a list", [7], [{**_ctl("f0"), "value": "typed text"}], [_ctl("f0", label=7)],
    [_ctl("f0", visible="yes")], [_ctl("f0", maxlength=True)], [_ctl("f0", label="x" * 201)],
    [_ctl("f0", option_values=["a"], option_texts=[])], [_ctl("f0")] * (el.MAX_CONTROLS + 1),
])
def test_parse_controls_refuses_anything_unexpected(bad: object) -> None:
    with pytest.raises(el.FillRefused):
        el.parse_controls(bad)


def test_plan_fill_sends_only_what_the_listing_shows(store, fake_registry) -> None:
    from freemyid.models import Listing
    p = make_profile()
    store.save_profile(p)
    store.save_listing(Listing(profile_id=p.id, broker_id="fakepeople",
                               url="https://fakepeople.example/p/1", match_score=90,
                               match_level=MatchLevel.CONFIRMED,
                               shown_fields=[ProfileField.FULL_NAME]))
    plan = el.plan_fill(store, fake_registry, "fakepeople", FORM)
    assert "f3" not in plan                              # never a phone
    assert "217-555-0142" not in json.dumps(plan) and "742" not in json.dumps(plan)
    ev = [e for e in store.events(p.id) if e.action == "extension_fill"]
    assert ev and "Jane" not in json.dumps(ev[0].detail)


def test_plan_fill_asks_the_app_when_two_people_could_be_meant(store, fake_registry) -> None:
    store.save_profile(make_profile())
    store.save_profile(make_profile(label="Second"))
    with pytest.raises(el.FillRefused) as e:
        el.plan_fill(store, fake_registry, "fakepeople", FORM)
    assert e.value.code == "choose_person"


def test_plan_fill_refuses_an_unknown_broker(store, fake_registry) -> None:
    store.save_profile(make_profile())
    with pytest.raises(el.FillRefused) as e:
        el.plan_fill(store, fake_registry, "nobody", FORM)
    assert e.value.code == "unknown_broker"


@pytest.mark.parametrize("assignments", [
    [{"key": "f0", "value": "Jane\n"}], [{"key": "x", "value": "Jane"}],
    [{"key": "f0", "value": ""}], [{"key": "f0", "value": "a" * 301}],
    [{"key": "f0", "value": "Jane", "extra": 1}], "f0=Jane",
])
def test_host_refuses_a_fill_plan_reply_that_is_not_clean(assignments: object) -> None:
    reply = native_host.handle_message(
        _req("fill_plan", broker_id="fakepeople", controls=[]), origin=FF,
        is_paired=lambda o: True,
        fill_plan=lambda b, c, o: {"ok": True, "assignments": assignments})
    assert reply == {"v": 1, "id": _req("x")["id"], "type": "fill_plan", "ok": False,
                     "error": "internal_error"}


def test_fill_plan_without_an_open_app_says_so() -> None:
    _pair()
    reply = native_host.handle_message(_req("fill_plan", broker_id="fakepeople",
                                            controls=[_ctl("f0", label="Name")]), origin=FF)
    assert reply["ok"] is False and reply["error"] == "app_closed"


# ------------------------------------------------------------------------------------ bridge

@pytest.fixture
def bridge(store, fake_registry):
    from freemyid.storage import Store
    b = el.Bridge(Store, lambda: fake_registry, lambda: True).start()   # a fresh store per call
    yield b
    b.stop()


def _post(b: el.Bridge, path: str, body: dict, **headers: str) -> tuple[int, dict]:
    conn = http.client.HTTPConnection("127.0.0.1", b.port, timeout=5)
    data = json.dumps(body).encode()
    h = {"Host": f"127.0.0.1:{b.port}", "Content-Type": "application/json",
         "Authorization": f"Bearer {b.token}", **headers}
    conn.request("POST", path, body=data, headers={k: v for k, v in h.items() if v})
    r = conn.getresponse()
    out = (r.status, json.loads(r.read()))
    conn.close()
    return out


def test_bridge_is_reachable_only_with_its_secret_and_without_an_origin(bridge) -> None:
    _pair()
    body = {"origin": FF, "broker_id": "fakepeople", "controls": []}
    assert _post(bridge, "/v1/fill-plan", body, Authorization="Bearer wrong")[0] == 403
    assert _post(bridge, "/v1/fill-plan", body, Origin="https://evil.example")[0] == 403
    assert _post(bridge, "/v1/fill-plan", body, Host="evil.example")[0] == 403
    assert _post(bridge, "/v1/fill-plan", body, **{"Content-Type": "text/plain"})[0] == 403
    assert _post(bridge, "/v1/fill-plan", {**body, "origin": CHROME})[0] == 403   # not paired
    assert el.app_is_open()


def test_fill_plan_end_to_end_through_the_host_and_the_bridge(bridge, store) -> None:
    from freemyid.models import Listing
    _pair()
    p = make_profile()
    store.save_profile(p)
    store.save_listing(Listing(profile_id=p.id, broker_id="fakepeople",
                               url="https://fakepeople.example/p/1", match_score=90,
                               match_level=MatchLevel.CONFIRMED,
                               shown_fields=[ProfileField.FIRST_NAME, ProfileField.LAST_NAME]))
    reply = native_host.handle_message(
        _req("fill_plan", broker_id="fakepeople", controls=FORM), origin=FF)
    assert reply["ok"] is True
    got = {a["key"]: a["value"] for a in reply["assignments"]}
    assert got["f0"] == "Jane" and got["f1"] == "Testperson"
    assert "f3" not in got and "f6" not in got and "f9" not in got


def test_bridge_stop_removes_its_file(store, fake_registry) -> None:
    from freemyid.storage import Store
    b = el.Bridge(Store, lambda: fake_registry, lambda: True).start()
    assert el.app_is_open()
    b.stop()
    assert not el.app_is_open()
    assert el.bridge_call("/v1/inbox", {"origin": FF}) is None


# ---------------------------------------------------------------- one source of truth checks

def test_the_extension_scans_a_page_exactly_like_the_app() -> None:
    js = (ROOT / "extension" / "src" / "content" / "assisted-fill.js").read_text(encoding="utf-8")
    block = js.split("// BEGIN generated from freemyid.engine.filler.SCAN_JS (do not edit by hand)")[1]
    block = block.split("// END generated from freemyid.engine.filler.SCAN_JS")[0]
    assert filler.SCAN_JS.strip() in block


def test_manifest_paths_match_install_locations() -> None:
    spec = json.loads((ROOT / "extension" / "native-host" / "install-locations.json")
                      .read_text(encoding="utf-8"))
    for plat, key in (("darwin", "macos"), ("linux", "linux")):
        for browser in el.BROWSERS:
            assert spec[key][browser]["path"] == f"{el.MANIFEST_PATHS[plat][browser]}/{el.HOST_FILE}"
    for browser in el.BROWSERS:
        assert spec["windows"][browser]["registry_key"] == "HKEY_CURRENT_USER\\" + el.WINDOWS_KEYS[browser]


def test_register_host_writes_firefox_and_skips_chromium_without_an_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(el, "_platform", lambda: "linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    done = el.register_host()
    assert set(done) == {"firefox"}
    manifest = json.loads(Path(done["firefox"]).read_text(encoding="utf-8"))
    assert manifest["name"] == native_host.HOST_NAME
    assert manifest["allowed_extensions"] == [native_host.FIREFOX_EXTENSION_ID]
    assert Path(manifest["path"]).exists()
    assert el.registered_browsers() == ["firefox"]
    dev = "abcdefghijklmnop" * 2
    assert set(el.register_host((dev,))) == {"chrome", "edge", "firefox"}
    assert dev in Path(el.register_host((dev,))["chrome"]).read_text(encoding="utf-8")
    assert set(el.unregister_host()) == {"chrome", "edge", "firefox"}


# -------------------------------------------------------------------------- wizard settings

def test_settings_page_offers_the_pairing_code_and_connects(store) -> None:
    from fastapi.testclient import TestClient

    from freemyid.wizard.server import COOKIE, _csrf_for, create_app
    token = "tok-ext-link"
    client = TestClient(create_app(store, token, {"testserver"}, registry_loader=lambda: None),
                        follow_redirects=False)
    client.cookies.set(COOKIE, token)
    code = el.start_pairing(FF)
    page = client.get("/settings").text
    assert "Browser helper" in page and f"{code[:3]} {code[3:]}" in page
    r = client.post("/settings/browser/pair", data={"code": code, "csrf": _csrf_for(token)})
    assert r.status_code == 303 and "browser_paired" in r.headers["location"]
    assert el.is_paired(FF)
    assert "Firefox" in client.get("/settings").text
    r = client.post("/settings/browser/disconnect", data={"csrf": _csrf_for(token)})
    assert r.status_code == 303 and el.paired_origins() == []
