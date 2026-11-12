"""Browser smoke checks for the extension's Global Privacy Control code (SEC-EXT-6, 7, 8) and the
broker-list retry.

The extension's own, unchanged JavaScript files run in Playwright's Chromium. The browser's
extension API (`browser.*`) is a small fake defined below, so a test can make any one step fail
and then look at what is left switched on. Every request is answered from this repository;
anything else is refused and makes the test fail.

What this does NOT cover (it needs a real Chrome or Edge with the extension installed): the
browser's own permission question, the errors the real API raises, `permissions.onRemoved` fired
by the browser's settings page, and the `Sec-GPC` header on the wire.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from tests.conftest import BROWSER_LAUNCH_TIMEOUT_MS, no_browser

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"
ORIGIN = "https://extension.freemyid.test"
MESSAGES = json.loads((EXT / "_locales" / "en" / "messages.json").read_text(encoding="utf-8"))

_spec = importlib.util.spec_from_file_location("build_extension_gpc_browser",
                                               ROOT / "tools" / "build_extension.py")
build_extension = importlib.util.module_from_spec(_spec)
sys.modules["build_extension_gpc_browser"] = build_extension
_spec.loader.exec_module(build_extension)

CHROME_MANIFEST = build_extension.build_manifest("chrome", build_extension.load_domain_list())
FIREFOX_MANIFEST = build_extension.build_manifest("firefox", build_extension.load_domain_list())

# A stand-in for the browser's extension API. `__fake` is the whole browser-side state:
#   granted / rulesets / scripts   what is switched on
#   fail[name]                     make the step with that name throw
#   calls                          every step that was called, in order
# Like the real thing, `scripting` exists only while the permission is held.
FAKE_API = """
(() => {
  const state = {
    manifest: __MANIFEST__, messages: __MESSAGES__,
    granted: false, rulesets: [], scripts: [], registered: [],
    decline: false, noScripting: false, fail: {}, calls: [], removedListeners: [],
  };
  const step = (name, fn) => async (...args) => {
    state.calls.push(name);
    if (state.fail[name]) throw new Error("fake failure in " + name);
    return fn(...args);
  };
  const scripting = {
    registerContentScripts: step("scripting.register", (list) => {
      state.registered.push(...list);
      state.scripts.push(...list.map((s) => s.id));
    }),
    unregisterContentScripts: step("scripting.unregister", ({ ids }) => {
      if (!ids.every((id) => state.scripts.includes(id))) throw new Error("Nonexistent script ID");
      state.scripts = state.scripts.filter((id) => !ids.includes(id));
    }),
  };
  const enable = step("dnr.enable", (ids) => { state.rulesets = [...new Set([...state.rulesets, ...ids])]; });
  const disable = step("dnr.disable", (ids) => { state.rulesets = state.rulesets.filter((id) => !ids.includes(id)); });
  const fake = {
    runtime: {
      id: "fake-extension-id",
      getManifest: () => state.manifest,
      getURL: (path) => location.origin + "/" + path,
      onMessage: { addListener() {} },
    },
    i18n: { getMessage: (key) => state.messages[key]?.message ?? "", getUILanguage: () => "en" },
    storage: { local: { get: async () => ({}), set: async () => {}, remove: async () => {} } },
    permissions: {
      request: step("permissions.request", () => {
        if (state.decline) return false;
        state.granted = true;
        return true;
      }),
      contains: step("permissions.contains", () => state.granted),
      remove: step("permissions.remove", () => {
        const had = state.granted;
        state.granted = false;
        if (had) for (const listener of state.removedListeners) listener({});
        return had;
      }),
      onRemoved: { addListener: (listener) => state.removedListeners.push(listener) },
    },
    declarativeNetRequest: {
      updateEnabledRulesets: async ({ enableRulesetIds, disableRulesetIds }) => {
        if (enableRulesetIds) await enable(enableRulesetIds);
        if (disableRulesetIds) await disable(disableRulesetIds);
      },
      getEnabledRulesets: step("dnr.getEnabled", () => [...state.rulesets]),
    },
  };
  Object.defineProperty(fake, "scripting", {
    get: () => (state.granted && !state.noScripting ? scripting : undefined),
  });
  globalThis.browser = fake;
  globalThis.__fake = state;
})();
"""

SET_ON = "() => Object.assign(__fake, { granted: true, rulesets: ['gpc'], scripts: ['fmid-gpc'] })"
SNAPSHOT = ("() => ({ granted: __fake.granted, rulesets: __fake.rulesets, scripts: __fake.scripts,"
            " calls: __fake.calls })")
ALL_OFF = {"granted": False, "rulesets": [], "scripts": []}
ALL_ON = {"granted": True, "rulesets": ["gpc"], "scripts": ["fmid-gpc"]}


@pytest.fixture(scope="module")
def chromium():
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True, timeout=BROWSER_LAUNCH_TIMEOUT_MS)
        except PWError as e:
            no_browser(type(e).__name__)
        yield b
        b.close()


class Harness:
    """One page on a made-up origin whose every request is answered from extension/."""

    def __init__(self, browser, manifest: dict) -> None:
        self.domains_fail = False
        self.refused: list[str] = []
        self.errors: list[str] = []
        self.ctx = browser.new_context()
        self.ctx.add_init_script(FAKE_API.replace("__MANIFEST__", json.dumps(manifest))
                                 .replace("__MESSAGES__", json.dumps(MESSAGES)))
        self.ctx.route("**/*", self._route)
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(15_000)
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.open("/harness.html")

    def _route(self, route) -> None:
        url = urlsplit(route.request.url)
        rel = unquote(url.path).lstrip("/")
        target = (EXT / rel).resolve()
        if f"{url.scheme}://{url.netloc}" != ORIGIN:
            self.refused.append(route.request.url)
            route.abort()
        elif rel == "harness.html":
            route.fulfill(body="<!doctype html><meta charset='utf-8'><title>harness</title>",
                          content_type="text/html")
        elif rel == build_extension.DOMAINS_PATH:
            if self.domains_fail:
                route.abort()
            else:
                route.fulfill(body=json.dumps(build_extension.load_domain_list()),
                              content_type="application/json")
        elif target.is_file() and target.is_relative_to(EXT / "src"):
            route.fulfill(body=target.read_bytes(),
                          content_type=guess_type(target.name)[0] or "text/plain")
        else:
            self.refused.append(route.request.url)
            route.abort()

    def open(self, path: str) -> None:
        self.page.goto(ORIGIN + path, wait_until="load")

    def gpc(self, expression: str):
        """Evaluate `expression` with `gpc` bound to the extension's own lib/gpc.js module."""
        return self.page.evaluate(
            "async () => { const gpc = await import('/src/lib/gpc.js'); return " + expression + "; }")

    def state(self) -> dict:
        return self.page.evaluate(SNAPSHOT)

    def switched(self) -> dict:
        return {k: v for k, v in self.state().items() if k != "calls"}

    def close(self) -> None:
        self.ctx.close()
        assert self.refused == [], f"the extension asked for something outside itself: {self.refused}"
        assert self.errors == [], self.errors


@pytest.fixture
def chrome(chromium):
    h = Harness(chromium, CHROME_MANIFEST)
    yield h
    h.close()


@pytest.fixture
def firefox(chromium):
    h = Harness(chromium, FIREFOX_MANIFEST)
    yield h
    h.close()


# ------------------------------------------------------------------ SEC-EXT-6: switching it on

def test_switching_on_turns_on_all_three_parts(chrome) -> None:
    assert chrome.gpc("gpc.isGpcOn()") is False
    assert chrome.gpc("gpc.turnGpcOn()") is True
    assert chrome.switched() == ALL_ON
    assert chrome.gpc("gpc.isGpcOn()") is True
    registered = chrome.page.evaluate("() => __fake.registered")
    assert registered == [{"id": "fmid-gpc", "js": ["src/content/gpc.js"], "matches": ["*://*/*"],
                           "runAt": "document_start", "world": "MAIN", "allFrames": True,
                           "persistAcrossSessions": True}]


@pytest.mark.parametrize("broken", ["dnr.enable", "scripting.register", "dnr.getEnabled",
                                    "noScripting"])
def test_a_failed_step_after_the_grant_leaves_nothing_on(chrome, broken: str) -> None:
    """SEC-EXT-6: no error escapes, the answer is false, the permission is handed back."""
    if broken == "noScripting":
        chrome.page.evaluate("() => { __fake.noScripting = true; }")
    else:
        chrome.page.evaluate("(name) => { __fake.fail[name] = true; }", broken)
    assert chrome.gpc("gpc.turnGpcOn()") is False
    state = chrome.state()
    assert {k: state[k] for k in ALL_OFF} == ALL_OFF
    assert state["calls"][0] == "permissions.request"
    assert "permissions.remove" in state["calls"]
    chrome.page.evaluate("() => { __fake.fail = {}; __fake.noScripting = false; }")
    assert chrome.gpc("gpc.isGpcOn()") is False
    assert chrome.gpc("gpc.turnGpcOn()") is True          # and it can be tried again
    assert chrome.switched() == ALL_ON


@pytest.mark.parametrize("setup", ["() => { __fake.decline = true; }",
                                   "() => { __fake.fail['permissions.request'] = true; }"])
def test_a_no_to_the_permission_question_changes_nothing(chrome, setup: str) -> None:
    chrome.page.evaluate(setup)
    assert chrome.gpc("gpc.turnGpcOn()") is False
    state = chrome.state()
    assert {k: state[k] for k in ALL_OFF} == ALL_OFF
    assert "dnr.enable" not in state["calls"] and "scripting.register" not in state["calls"]


# ----------------------------------------------------------------- SEC-EXT-7: switching it off

@pytest.mark.parametrize("broken", [[], ["dnr.disable"], ["scripting.unregister"],
                                    ["dnr.disable", "scripting.unregister"]])
def test_switching_off_always_hands_the_permission_back(chrome, broken: list[str]) -> None:
    """SEC-EXT-7: whatever else fails, permissions.remove runs, and only then is it "off"."""
    chrome.page.evaluate(SET_ON)
    chrome.page.evaluate("(names) => { for (const n of names) __fake.fail[n] = true; }", broken)
    assert chrome.gpc("gpc.turnGpcOff()") is True
    state = chrome.state()
    assert state["granted"] is False
    assert state["calls"].count("permissions.remove") >= 1
    # "off" is read from the browser after the permission was handed back, not assumed
    assert state["calls"].index("permissions.remove") < len(state["calls"]) - 1
    assert state["calls"][-2:] == ["permissions.contains", "dnr.getEnabled"] or \
        state["calls"][-2:] == ["dnr.getEnabled", "permissions.contains"]
    assert chrome.gpc("gpc.isGpcOn()") is False


@pytest.mark.parametrize("broken", [["permissions.remove", "dnr.disable"], ["permissions.contains"],
                                    ["dnr.getEnabled", "permissions.remove"]])
def test_off_is_not_reported_when_the_browser_does_not_confirm_it(chrome, broken: list[str]) -> None:
    """SEC-EXT-7: still on, or the browser cannot say: the answer is false, and nothing throws."""
    chrome.page.evaluate(SET_ON)
    chrome.page.evaluate("(names) => { for (const n of names) __fake.fail[n] = true; }", broken)
    assert chrome.gpc("gpc.turnGpcOff()") is False
    assert "permissions.remove" in chrome.state()["calls"]


def test_the_firefox_package_never_touches_the_gpc_parts(firefox) -> None:
    assert firefox.gpc("gpc.gpcSupport()") == "browser"
    assert firefox.gpc("gpc.turnGpcOn()") is False
    assert firefox.gpc("gpc.turnGpcOff()") is True
    firefox.gpc("gpc.turnGpcOffIfGrantGone()")
    assert firefox.state()["calls"] == []


# ------------------------------------------------------------ the Settings page tells the truth

def _wait_idle(page) -> None:
    page.wait_for_function("() => !document.getElementById('gpc-enabled').disabled "
                           "&& document.getElementById('gpc-result').textContent !== ''")


def _settings(h: Harness) -> tuple[bool, str]:
    _wait_idle(h.page)
    return (h.page.locator("#gpc-enabled").is_checked(),
            h.page.locator("#gpc-result").text_content())


def _say(key: str) -> str:
    return MESSAGES[key]["message"]


def test_settings_page_shows_the_real_state_after_a_failure(chrome) -> None:
    chrome.open("/src/options/options.html")
    box = chrome.page.locator("#gpc-enabled")
    assert box.is_checked() is False

    # a step fails after the person said yes: the box goes back to unticked
    chrome.page.evaluate("() => { __fake.fail['scripting.register'] = true; }")
    box.click()
    assert _settings(chrome) == (False, _say("optionsGpcDeclined"))
    assert chrome.switched() == ALL_OFF

    chrome.page.evaluate("() => { __fake.fail = {}; document.getElementById('gpc-result').textContent = ''; }")
    box.click()
    assert _settings(chrome) == (True, _say("optionsGpcOn"))
    assert chrome.switched() == ALL_ON

    # switching off fails and it really is still on: the box stays ticked and says so
    chrome.page.evaluate("() => { __fake.fail = { 'permissions.remove': true, 'dnr.disable': true };"
                         " document.getElementById('gpc-result').textContent = ''; }")
    box.click()
    assert _settings(chrome) == (True, _say("optionsGpcStillOn"))
    assert chrome.gpc("gpc.isGpcOn()") is True

    chrome.page.evaluate("() => { __fake.fail = {}; document.getElementById('gpc-result').textContent = ''; }")
    box.click()
    assert _settings(chrome) == (False, _say("optionsGpcOff"))
    assert chrome.switched() == ALL_OFF


def test_settings_page_says_not_turned_on_when_the_person_says_no(chrome) -> None:
    chrome.open("/src/options/options.html")
    chrome.page.evaluate("() => { __fake.decline = true; }")
    chrome.page.locator("#gpc-enabled").click()
    assert _settings(chrome) == (False, _say("optionsGpcDeclined"))
    assert chrome.switched() == ALL_OFF


# --------------------------------------------------------------- SEC-EXT-8: the background script

def _start_background(h: Harness) -> None:
    h.page.evaluate("async () => { await import('/src/background/main.js'); }")


def test_background_switches_gpc_off_at_startup_when_the_grant_is_missing(chrome) -> None:
    """The permission was taken back while the background was not running."""
    chrome.page.evaluate("() => Object.assign(__fake, { granted: false, rulesets: ['gpc'] })")
    _start_background(chrome)
    chrome.page.wait_for_function("() => __fake.calls.includes('permissions.remove')")
    chrome.page.wait_for_function("() => __fake.rulesets.length === 0")
    assert chrome.state()["granted"] is False


def test_background_leaves_gpc_alone_at_startup_when_the_grant_is_there(chrome) -> None:
    chrome.page.evaluate(SET_ON)
    _start_background(chrome)
    chrome.page.wait_for_function("() => __fake.calls.includes('permissions.contains')")
    chrome.page.wait_for_timeout(200)
    state = chrome.state()
    assert {k: state[k] for k in ALL_ON} == ALL_ON
    assert "permissions.remove" not in state["calls"] and "dnr.disable" not in state["calls"]


def test_background_switches_gpc_off_when_the_permission_is_taken_back(chrome) -> None:
    """permissions.onRemoved: the person removed the permission in the browser's own settings."""
    chrome.page.evaluate(SET_ON)
    _start_background(chrome)
    chrome.page.wait_for_function("() => __fake.removedListeners.length === 1")
    chrome.page.wait_for_function("() => __fake.calls.includes('permissions.contains')")
    assert chrome.switched() == ALL_ON
    chrome.page.evaluate("() => { __fake.granted = false;"
                         " for (const listener of __fake.removedListeners) listener({ origins: ['*://*/*'] }); }")
    chrome.page.wait_for_function("() => __fake.rulesets.length === 0"
                                  " && __fake.calls.includes('permissions.remove')")
    assert chrome.gpc("gpc.isGpcOn()") is False


def test_background_never_asks_for_the_permission(chrome, firefox) -> None:
    for h in (chrome, firefox):
        _start_background(h)
        h.page.wait_for_timeout(200)
        assert "permissions.request" not in h.state()["calls"]
        assert "dnr.enable" not in h.state()["calls"]
    assert firefox.state()["calls"] == []


# ------------------------------------------------------------------- the bundled broker list

def test_a_failed_read_of_the_broker_list_is_tried_again(chrome) -> None:
    host = next(iter(build_extension.load_domain_list()["hosts"]))
    lookup = ("async (host) => { const brokers = await import('/src/lib/brokers.js');"
              " try { return await brokers.lookupHost(host); } catch { return 'failed'; } }")
    chrome.domains_fail = True
    assert chrome.page.evaluate(lookup, host) == "failed"
    assert chrome.page.evaluate(lookup, host) == "failed"
    chrome.domains_fail = False
    found = chrome.page.evaluate(lookup, host)
    assert found != "failed" and found["id"] == build_extension.load_domain_list()["hosts"][host]
    chrome.refused.clear()   # the two refused reads above were this test's own doing
