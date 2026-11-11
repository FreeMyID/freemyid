"""Browser extension skeleton (extension/, tools/build_extension.py, docs/EXTENSION.md).

What these tests hold in place:
- one valid Manifest V3 per browser, with no permission beyond the written allow-list;
- the extension has no network code and no remote code (a grep over every shipped file);
- the broker domain list is built from the PUBLIC sample registry only;
- the build is deterministic and uses the standard library only;
- the Global Privacy Control stub ships switched off and can only add the header Sec-GPC: 1.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from freemyid import native_host
from freemyid.models import ListingState

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"
SAMPLE = ROOT / "brokers" / "registry.sample.yaml"

_spec = importlib.util.spec_from_file_location("build_extension", ROOT / "tools" / "build_extension.py")
build_extension = importlib.util.module_from_spec(_spec)
sys.modules["build_extension"] = build_extension
_spec.loader.exec_module(build_extension)

BROWSERS = build_extension.BROWSERS
BASE_PERMISSIONS = {"activeTab", "nativeMessaging", "storage"}
SHIPPED_TEXT = sorted(p for p in EXT.rglob("*") if p.suffix in {".js", ".html", ".css"})
SHIPPED_JS = [p for p in SHIPPED_TEXT if p.suffix == ".js"]


def _manifest(browser: str) -> dict:
    return json.loads(build_extension.build_tree(browser)["manifest.json"])


def _strip_js_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$", "", text)


def _messages() -> dict:
    return json.loads((EXT / "_locales" / "en" / "messages.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------- manifests

def test_three_browsers_are_built() -> None:
    assert BROWSERS == ("chrome", "edge", "firefox")


@pytest.mark.parametrize("browser", BROWSERS)
def test_manifest_is_valid_for_each_browser(browser: str) -> None:
    files = build_extension.build_tree(browser)
    manifest = json.loads(files["manifest.json"])
    assert build_extension.validate_manifest(manifest, browser) == []
    assert manifest["manifest_version"] == 3
    assert re.fullmatch(r"\d+(\.\d+){0,3}", manifest["version"])
    assert not any(key.startswith("//") for key in manifest)
    assert "//" not in manifest["content_scripts"][0]
    for path in build_extension.referenced_files(manifest):
        assert path in files, f"{browser}: manifest points at {path}, which is not packaged"
    # every __MSG_key__ in the manifest has a string
    for key in re.findall(r"__MSG_(\w+)__", files["manifest.json"].decode()):
        assert key in _messages()


@pytest.mark.parametrize("browser", ["chrome", "edge"])
def test_chromium_background_is_a_module_service_worker(browser: str) -> None:
    manifest = _manifest(browser)
    assert manifest["background"] == {"service_worker": "src/background/main.js", "type": "module"}
    assert "browser_specific_settings" not in manifest


def test_firefox_background_is_an_event_page_with_a_fixed_id() -> None:
    manifest = _manifest("firefox")
    assert manifest["background"] == {"scripts": ["src/background/main.js"], "type": "module"}
    gecko = manifest["browser_specific_settings"]["gecko"]
    assert gecko["id"] == native_host.FIREFOX_EXTENSION_ID == build_extension.FIREFOX_ID
    assert gecko["data_collection_permissions"] == {"required": ["none"]}


@pytest.mark.parametrize("browser", BROWSERS)
def test_csp_is_strict(browser: str) -> None:
    csp = _manifest(browser)["content_security_policy"]["extension_pages"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert not re.search(r"unsafe|https?:|wss?:|\*|data:|blob:", csp)


# ----------------------------------------------------------------------------- permissions

@pytest.mark.parametrize("browser", BROWSERS)
def test_no_permission_beyond_the_allowed_set(browser: str) -> None:
    manifest = _manifest(browser)
    granted = set(manifest["permissions"])
    assert BASE_PERMISSIONS <= granted
    assert granted <= build_extension.allowed_permissions(browser)
    assert "host_permissions" not in manifest          # nothing is granted on any site at install
    for bad in ("tabs", "webRequest", "webRequestBlocking", "cookies", "history", "scripting",
                "<all_urls>", "declarativeNetRequest", "management", "downloads", "clipboardRead"):
        assert bad not in granted


def test_firefox_asks_for_exactly_the_three_base_permissions() -> None:
    manifest = _manifest("firefox")
    assert set(manifest["permissions"]) == BASE_PERMISSIONS
    for key in ("optional_permissions", "optional_host_permissions", "declarative_net_request"):
        assert key not in manifest


@pytest.mark.parametrize("browser", ["chrome", "edge"])
def test_chromium_adds_only_the_gpc_stub_permissions(browser: str) -> None:
    manifest = _manifest(browser)
    assert set(manifest["permissions"]) == BASE_PERMISSIONS | {"declarativeNetRequestWithHostAccess"}
    # asked for only at the moment the person switches GPC on, never at install
    assert manifest["optional_permissions"] == ["scripting"]
    assert manifest["optional_host_permissions"] == ["*://*/*"]


@pytest.mark.parametrize("browser", BROWSERS)
@pytest.mark.parametrize("change", [
    {"permissions": ["activeTab", "nativeMessaging", "storage", "tabs"]},
    {"permissions": ["activeTab", "nativeMessaging", "storage", "webRequest"]},
    {"host_permissions": ["<all_urls>"]},
    {"host_permissions": ["https://www.spokeo.com/*"]},
    {"optional_permissions": ["scripting", "cookies"]},
    {"optional_host_permissions": ["<all_urls>"]},
    {"externally_connectable": {"matches": ["https://freemyid.org/*"]}},
    {"web_accessible_resources": [{"resources": ["data/broker_domains.json"], "matches": ["<all_urls>"]}]},
    {"update_url": "https://updates.invalid/x.xml"},
    {"content_security_policy": {"extension_pages": "script-src 'self' 'unsafe-eval'; object-src 'none'"}},
    {"content_security_policy": {"extension_pages":
                                 "default-src 'none'; script-src 'self' https://cdn.invalid; object-src 'none'"}},
    {"manifest_version": 2},
])
def test_validator_refuses_wider_manifests(browser: str, change: dict) -> None:
    manifest = {**_manifest(browser), **change}
    assert build_extension.validate_manifest(manifest, browser) != []


@pytest.mark.parametrize("pattern", ["<all_urls>", "*://*/*", "https://*/*", "https://*.spokeo.com/*",
                                     "http://www.spokeo.com/*", "https://www.spokeo.com/optout"])
def test_validator_refuses_wide_content_script_matches(pattern: str) -> None:
    manifest = _manifest("chrome")
    manifest["content_scripts"][0]["matches"].append(pattern)
    assert build_extension.validate_manifest(manifest, "chrome") != []


@pytest.mark.parametrize("change", [{"all_frames": True}, {"world": "MAIN"}, {"match_about_blank": True}])
def test_validator_keeps_the_banner_in_the_top_frame_and_isolated_world(change: dict) -> None:
    manifest = _manifest("firefox")
    manifest["content_scripts"][0].update(change)
    assert build_extension.validate_manifest(manifest, "firefox") != []


def test_a_bad_override_file_fails_the_build(tmp_path: Path) -> None:
    shutil.copytree(EXT, tmp_path / "extension")
    (tmp_path / "brokers").mkdir()
    shutil.copy(SAMPLE, tmp_path / "brokers" / SAMPLE.name)
    override = tmp_path / "extension" / "manifests" / "firefox.json"
    data = json.loads(override.read_text(encoding="utf-8"))
    data["permissions"] = ["activeTab", "nativeMessaging", "storage", "tabs"]
    override.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(build_extension.BuildError, match="permissions not allowed"):
        build_extension.build_tree("firefox", root=tmp_path)
    assert build_extension.build_tree("chrome", root=tmp_path)   # the others still build


# --------------------------------------------------------- no network code, no remote code

def test_there_are_files_to_scan() -> None:
    assert len(SHIPPED_JS) >= 10
    assert any(p.suffix == ".html" for p in SHIPPED_TEXT)


@pytest.mark.parametrize("path", SHIPPED_TEXT, ids=lambda p: p.relative_to(EXT).as_posix())
def test_no_web_address_in_extension_code(path: Path) -> None:
    """No http(s)/ws(s) address anywhere, comments included: nothing to fetch, import or load."""
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"(?i)\b(?:https?|wss?|ftp):/?/", text), f"{path.name} contains a web address"
    assert not re.search(r"""(?i)["'(=]\s*//[a-z0-9]""", text), f"{path.name}: protocol-relative address"


@pytest.mark.parametrize("path", SHIPPED_JS, ids=lambda p: p.relative_to(EXT).as_posix())
def test_no_network_or_dynamic_code_api_in_extension_js(path: Path) -> None:
    code = _strip_js_comments(path.read_text(encoding="utf-8"))
    for pattern in (r"\bXMLHttpRequest\b", r"\bWebSocket\b", r"\bEventSource\b", r"\bsendBeacon\b",
                    r"\bWebTransport\b", r"\bRTCPeerConnection\b", r"\bimportScripts\b",
                    r"\beval\s*\(", r"\bnew\s+Function\b", r"\bimport\s*\(", r"\binnerHTML\b",
                    r"\bouterHTML\b", r"\binsertAdjacentHTML\b", r"document\.write",
                    r"\bstorage\.sync\b", r"\bexecuteScript\b", r"\bconnectNative\b",
                    r"\bwebRequest\b", r"\bcookies\b", r"\bsetTimeout\s*\(\s*[\"'`]"):
        assert not re.search(pattern, code), f"{path.name} uses {pattern}"
    # static imports are relative files inside the package
    for target in re.findall(r"""(?m)^\s*(?:import|export)\b[^;]*?\bfrom\s+["']([^"']+)["']""", code):
        assert target.startswith(("./", "../")) and target.endswith(".js"), f"{path.name}: {target}"


def test_the_only_fetch_reads_the_bundled_domain_list() -> None:
    calls = {}
    for path in SHIPPED_JS:
        found = re.findall(r"\bfetch\s*\(([^\n]*)", _strip_js_comments(path.read_text(encoding="utf-8")))
        if found:
            calls[path.relative_to(EXT).as_posix()] = found
    assert list(calls) == ["src/lib/brokers.js"]
    assert len(calls["src/lib/brokers.js"]) == 1
    assert calls["src/lib/brokers.js"][0].startswith('api.runtime.getURL("data/broker_domains.json"))')


def test_native_messaging_is_used_in_one_place_only() -> None:
    users = [p.relative_to(EXT).as_posix() for p in SHIPPED_JS
             if "sendNativeMessage" in _strip_js_comments(p.read_text(encoding="utf-8"))]
    assert users == ["src/lib/native.js"]


@pytest.mark.parametrize("path", [p for p in SHIPPED_TEXT if p.suffix == ".html"],
                         ids=lambda p: p.name)
def test_pages_have_no_inline_script_style_or_outside_asset(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    for script in re.findall(r"<script\b([^>]*)>(.*?)</script>", html, flags=re.DOTALL):
        assert 'type="module"' in script[0] and "src=" in script[0] and not script[1].strip()
    assert not re.search(r"<style\b|\sstyle=|\son[a-z]+\s*=", html)
    for target in re.findall(r"""(?:src|href|action)=["']([^"']+)["']""", html):
        assert not re.match(r"(?i)[a-z][a-z0-9+.-]*:|//", target), f"{path.name}: {target}"
    assert not re.search(r"<(?:iframe|object|embed|form|base)\b", html)


@pytest.mark.parametrize("path", [p for p in SHIPPED_TEXT if p.suffix == ".css"], ids=lambda p: p.name)
def test_css_loads_nothing(path: Path) -> None:
    css = path.read_text(encoding="utf-8")
    assert not re.search(r"(?i)@import|url\s*\(|@font-face", css)


def test_no_npm_or_bundler_files_and_no_vendored_code() -> None:
    names = {p.name for p in EXT.rglob("*")}
    assert not names & {"package.json", "package-lock.json", "node_modules", "yarn.lock",
                        "pnpm-lock.yaml", "webpack.config.js", "rollup.config.js", "vite.config.js",
                        "browser-polyfill.js", "browser-polyfill.min.js"}
    assert not [p for p in EXT.rglob("*.min.js")]
    assert not [p for p in EXT.rglob("*") if p.is_symlink()]


def test_banner_reads_nothing_from_the_page_and_touches_no_form() -> None:
    code = _strip_js_comments((EXT / "src" / "content" / "banner.js").read_text(encoding="utf-8"))
    for pattern in (r"querySelector", r"getElementById", r"getElementsBy", r"document\.cookie",
                    r"document\.forms", r"document\.body", r"document\.title", r"\binnerText\b",
                    r"\blocalStorage\b", r"\bsessionStorage\b", r"\blocation\b", r"\.value\b",
                    r"\.click\s*\(", r"\.submit\s*\(", r"dispatchEvent", r"MutationObserver",
                    r"(?i)captcha", r"\bstorage\b"):
        assert not re.search(pattern, code), f"banner.js uses {pattern}"
    assert code.count("event.isTrusted") == 2          # both buttons need a real click
    assert 'attachShadow({ mode: "closed" })' in code


def test_assisted_fill_is_a_todo_that_ships_nowhere() -> None:
    rel = "src/content/assisted-fill.js"
    text = (EXT / rel).read_text(encoding="utf-8")
    assert text.startswith("// TODO (FUTURE, NOT BUILT, NOT SHIPPED)")
    assert "only after the person clicks" in text and "never touches a CAPTCHA" in text
    for browser in BROWSERS:
        files = build_extension.build_tree(browser)
        assert rel not in files
        assert "assisted-fill" not in files["manifest.json"].decode()
    others = [p for p in SHIPPED_TEXT if p.name != "assisted-fill.js"
              and "assisted-fill.js" in _strip_js_comments(p.read_text(encoding="utf-8"))]
    assert others == []


# ------------------------------------------------------- domain list: public sample only

def _sample_brokers() -> list[dict]:
    return yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))["brokers"]


def test_line_reader_agrees_with_pyyaml_on_the_sample() -> None:
    version, mine = build_extension.parse_sample_registry(SAMPLE.read_text(encoding="utf-8"))
    reference = _sample_brokers()
    assert version == yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))["version"]
    assert [b["id"] for b in mine] == [b["id"] for b in reference]
    for got, want in zip(mine, reference, strict=True):
        for key in ("name", "url", "category"):
            assert got[key] == want[key], (want["id"], key)
        assert got["domains"] == want["domains"], want["id"]


def test_domain_list_holds_only_hosts_from_the_sample() -> None:
    domains = build_extension.load_domain_list()
    by_id = {b["id"]: b for b in _sample_brokers()}
    assert domains["source"] == "brokers/registry.sample.yaml"
    assert domains["hosts"], "no hosts built"
    for host, broker_id in domains["hosts"].items():
        assert host in by_id[broker_id]["domains"]
        assert domains["brokers"][broker_id]["name"] == by_id[broker_id]["name"]
    assert set(domains["hosts"].values()) == set(domains["brokers"])
    assert domains["hosts"]["www.spokeo.com"] == "spokeo"
    # a host belongs to the broker whose own site it is, not to a sister site that lists it
    assert domains["hosts"]["www.whitepages.com"] == "whitepages"
    assert domains["hosts"]["www.beenverified.com"] == "beenverified"
    # nothing but ids, names, a flag and hostnames: no emails, phone numbers or notes
    dumped = json.dumps(domains)
    assert "@" not in dumped and "opt_out" not in dumped and "verification" not in dumped


def test_banner_runs_only_on_people_search_style_sites() -> None:
    domains = build_extension.load_domain_list()
    by_id = {b["id"]: b for b in _sample_brokers()}
    patterns = build_extension.banner_match_patterns(domains)
    assert patterns == sorted(patterns) and len(patterns) == len(set(patterns))
    for pattern in patterns:
        host = re.fullmatch(r"https://([a-z0-9.-]+)/\*", pattern).group(1)
        assert by_id[domains["hosts"][host]]["category"] in build_extension.BANNER_CATEGORIES
    for broker_id, entry in domains["brokers"].items():
        assert entry["banner"] == (by_id[broker_id]["category"] in build_extension.BANNER_CATEGORIES)
    # government portals, search engines and the like are never called brokers
    for broker_id, broker in by_id.items():
        if broker["category"] == "other":
            assert broker_id not in domains["brokers"]
    assert "privacy.ca.gov" not in domains["hosts"] and "www.google.com" not in domains["hosts"]
    for browser in BROWSERS:
        assert _manifest(browser)["content_scripts"][0]["matches"] == patterns


def test_private_registry_is_refused_by_name() -> None:
    for name in ("registry.yaml", "registry.yml", "brokers.yaml", "registry.sample.yaml.bak"):
        with pytest.raises(build_extension.BuildError, match="public sample"):
            build_extension.sample_registry_path(ROOT, ROOT / "brokers" / name)
    assert build_extension.sample_registry_path(ROOT) == SAMPLE
    assert build_extension.main(["--registry", str(ROOT / "brokers" / "registry.yaml"),
                                 "--out", str(ROOT / "dist" / "never-written")]) == 1
    assert not (ROOT / "dist" / "never-written").exists()


def test_a_private_registry_next_to_the_sample_is_never_read(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(EXT, tmp_path / "extension")
    (tmp_path / "brokers").mkdir()
    shutil.copy(SAMPLE, tmp_path / "brokers" / SAMPLE.name)
    (tmp_path / "brokers" / "registry.yaml").write_text(
        'version: "private"\nbrokers:\n  - id: private_only_broker\n    name: Private Only\n'
        "    url: https://www.private-only.example/\n    category: people_search\n"
        "    domains: [www.private-only.example]\n", encoding="utf-8")
    opened: list[str] = []
    real_text, real_bytes = Path.read_text, Path.read_bytes
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (opened.append(self.name),
                                                                  real_text(self, *a, **k))[1])
    monkeypatch.setattr(Path, "read_bytes", lambda self, *a, **k: (opened.append(self.name),
                                                                   real_bytes(self, *a, **k))[1])
    for browser in BROWSERS:
        archive = build_extension.write_build(browser, tmp_path / "out", root=tmp_path)
        with zipfile.ZipFile(archive) as zf:
            blob = b"".join(zf.read(name) for name in zf.namelist())
        assert b"private-only" not in blob and b"private_only_broker" not in blob
    assert "registry.sample.yaml" in opened
    assert "registry.yaml" not in opened


def test_bad_hostnames_in_a_registry_stop_the_build() -> None:
    for bad in ("*.spokeo.com", "spokeo.com/optout", "https://spokeo.com", "<all_urls>", "localhost"):
        with pytest.raises(build_extension.BuildError):
            build_extension.build_domain_list("x", [{"id": "spokeo", "name": "Spokeo",
                                                     "url": "https://www.spokeo.com/",
                                                     "category": "people_search", "domains": [bad]}])


# ----------------------------------------------------------- build output and determinism

def test_build_script_uses_the_standard_library_only() -> None:
    tree = ast.parse((ROOT / "tools" / "build_extension.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)
    assert not imported & {"urllib3", "http", "socket", "subprocess", "ssl"}


def test_build_is_deterministic_and_complete(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    for browser in BROWSERS:
        one = build_extension.write_build(browser, first)
        two = build_extension.write_build(browser, second)
        assert one.read_bytes() == two.read_bytes()
        again = build_extension.write_build(browser, first)      # rebuilding over an old build
        assert again.read_bytes() == two.read_bytes()
        with zipfile.ZipFile(one) as zf:
            names = zf.namelist()
            assert names == sorted(names)
            assert {info.date_time for info in zf.infolist()} == {(1980, 1, 1, 0, 0, 0)}
            assert zf.testzip() is None
            on_disk = sorted(p.relative_to(first / browser).as_posix()
                             for p in (first / browser).rglob("*") if p.is_file())
            assert names == on_disk
            for name in names:
                assert zf.read(name) == (first / browser / name).read_bytes()
        assert {"manifest.json", "data/broker_domains.json", "_locales/en/messages.json",
                "src/background/main.js", "src/content/banner.js", "src/popup/popup.html",
                "src/options/options.html", "assets/icons/icon-128.png"} <= set(names)
        assert not [n for n in names if n.startswith(("manifests/", "native-host/"))]
        assert not [n for n in names if n.endswith((".md", ".template", ".map", ".py"))]


def test_build_refuses_to_delete_a_folder_it_did_not_make(tmp_path: Path) -> None:
    (tmp_path / "chrome").mkdir()
    (tmp_path / "chrome" / "family-photos.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(build_extension.BuildError, match="not deleting"):
        build_extension.write_build("chrome", tmp_path)
    assert (tmp_path / "chrome" / "family-photos.txt").read_text(encoding="utf-8") == "keep me"


def test_build_output_folder_is_gitignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "dist/" in ignored


def test_icons_are_png_at_the_named_size() -> None:
    for size in (16, 32, 48, 128):
        data = (EXT / "assets" / "icons" / f"icon-{size}.png").read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert int.from_bytes(data[16:20], "big") == int.from_bytes(data[20:24], "big") == size


# ------------------------------------------------------- Global Privacy Control (stub, off)

def test_gpc_rule_only_adds_the_sec_gpc_header() -> None:
    rules = json.loads((EXT / "rules" / "gpc.json").read_text(encoding="utf-8"))
    assert build_extension.validate_gpc_rules(rules) == []
    assert rules[0]["action"] == {"type": "modifyHeaders", "requestHeaders": [
        {"header": "Sec-GPC", "operation": "set", "value": "1"}]}
    assert "main_frame" in rules[0]["condition"]["resourceTypes"]


@pytest.mark.parametrize("change", [
    {"action": {"type": "block"}},
    {"action": {"type": "redirect", "redirect": {"url": "https://elsewhere.invalid/"}}},
    {"action": {"type": "modifyHeaders", "requestHeaders": [
        {"header": "Sec-GPC", "operation": "set", "value": "1"},
        {"header": "User-Agent", "operation": "set", "value": "something else"}]}},
    {"action": {"type": "modifyHeaders", "requestHeaders": [
        {"header": "Cookie", "operation": "remove"}]}},
    {"action": {"type": "modifyHeaders",
                "requestHeaders": [{"header": "Sec-GPC", "operation": "set", "value": "1"}],
                "responseHeaders": [{"header": "content-security-policy", "operation": "remove"}]}},
    {"condition": {"resourceTypes": ["main_frame"], "urlFilter": "spokeo"}},
    {"condition": {"resourceTypes": ["script"]}},
    {"extra": True},
])
def test_gpc_rule_validator_refuses_anything_else(change: dict) -> None:
    rule = json.loads((EXT / "rules" / "gpc.json").read_text(encoding="utf-8"))[0]
    assert build_extension.validate_gpc_rules([{**rule, **change}]) != []
    assert build_extension.validate_gpc_rules([rule, rule]) != []
    assert build_extension.validate_gpc_rules({}) != []


@pytest.mark.parametrize("browser", ["chrome", "edge"])
def test_gpc_ships_switched_off_on_chromium(browser: str) -> None:
    files = build_extension.build_tree(browser)
    manifest = json.loads(files["manifest.json"])
    assert manifest["declarative_net_request"] == {
        "rule_resources": [{"id": "gpc", "enabled": False, "path": "rules/gpc.json"}]}
    assert "rules/gpc.json" in files and "src/content/gpc.js" in files
    # the page-side script is registered on demand, never listed in the manifest
    assert "gpc.js" not in json.dumps(manifest["content_scripts"])
    enabled = dict(manifest["declarative_net_request"]["rule_resources"][0], enabled=True)
    manifest["declarative_net_request"] = {"rule_resources": [enabled]}
    assert build_extension.validate_manifest(manifest, browser) != []


def test_gpc_is_left_to_firefox_itself() -> None:
    files = build_extension.build_tree("firefox")
    assert "rules/gpc.json" not in files and "src/content/gpc.js" not in files
    assert "src/lib/gpc.js" in files                       # options.js imports it on every browser
    manifest = json.loads(files["manifest.json"])
    manifest["declarative_net_request"] = {"rule_resources": [
        {"id": "gpc", "enabled": False, "path": "rules/gpc.json"}]}
    assert build_extension.validate_manifest(manifest, "firefox") != []


def test_gpc_code_matches_the_manifest_and_starts_from_the_options_page_only() -> None:
    lib = (EXT / "src" / "lib" / "gpc.js").read_text(encoding="utf-8")
    assert 'GPC_RULESET_ID = "gpc"' in lib
    assert 'GPC_SCRIPT_FILE = "src/content/gpc.js"' in lib
    assert 'permissions: ["scripting"], origins: ["*://*/*"]' in lib
    assert "permissions.request(GPC_GRANT)" in lib and "permissions.remove(GPC_GRANT)" in lib
    importers = sorted(p.relative_to(EXT).as_posix() for p in SHIPPED_JS
                       if re.search(r"""from\s+["'][./]+(?:lib/)?gpc\.js["']""",
                                    p.read_text(encoding="utf-8")))
    assert importers == ["src/background/main.js", "src/options/options.js"]
    # Switching it ON starts from the options page only (the person's own click). The
    # background imports one thing: the function that switches it off (SEC-EXT-8).
    users_of_on = sorted(p.relative_to(EXT).as_posix() for p in SHIPPED_JS
                         if "turnGpcOn" in _strip_js_comments(p.read_text(encoding="utf-8")))
    assert users_of_on == ["src/lib/gpc.js", "src/options/options.js"]
    background = _strip_js_comments((EXT / "src" / "background" / "main.js").read_text(encoding="utf-8"))
    assert 'import { turnGpcOffIfGrantGone } from "../lib/gpc.js";' in background
    assert not re.search(r"permissions\??\.(request|contains|remove)\b", background)
    assert "permissions.request" not in _strip_js_comments(
        (EXT / "src" / "options" / "options.js").read_text(encoding="utf-8"))
    page = _strip_js_comments((EXT / "src" / "content" / "gpc.js").read_text(encoding="utf-8"))
    assert "globalPrivacyControl" in page
    for pattern in (r"\bchrome\b", r"\bbrowser\b", r"sendMessage", r"\bdocument\b", r"\bfetch\b",
                    r"userAgent", r"\bwebdriver\b"):
        assert not re.search(pattern, page), f"gpc.js uses {pattern}"
    options = (EXT / "src" / "options" / "options.html").read_text(encoding="utf-8")
    assert re.search(r'<input type="checkbox" id="gpc-enabled">', options)   # not pre-ticked


# ------------------------------------------------------------------ copy strings and protocol

def test_every_string_used_exists_in_the_english_messages() -> None:
    messages = _messages()
    used = set()
    for path in SHIPPED_TEXT:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            used |= set(re.findall(r'data-i18n="(\w+)"', text))
        if path.suffix == ".js":
            # every quoted word that looks like a string key, however it reaches t()
            used |= set(re.findall(r'"((?:banner|popup|options|ext|action)[A-Z]\w*)"',
                                   _strip_js_comments(text)))
    used |= {f"state_{state.value}" for state in ListingState}
    missing = sorted(used - set(messages))
    assert not missing, f"strings missing from _locales/en/messages.json: {missing}"
    assert len(used) > 30
    for key, entry in messages.items():
        assert entry["message"].strip() and entry["description"].strip(), key
    assert len(messages["extDescription"]["message"]) <= 132          # store limit


def test_banner_copy_is_the_agreed_sentence_and_stays_honest() -> None:
    messages = _messages()
    assert messages["bannerText"]["message"] == (
        "This site sells people's information. Free My ID can ask them to remove you.")
    assert messages["bannerRemove"]["message"] == "Remove me"
    assert messages["bannerNotNow"]["message"] == "Not now"
    assert "this site only" in messages["bannerStarted"]["message"]
    assert "come back" in messages["bannerStarted"]["message"]
    assert "does not remove a listing" in messages["optionsGpcHint"]["message"]
    everything = " ".join(entry["message"] for entry in messages.values()).lower()
    for claim in ("guarantee", "never leaves your computer", "100%", "everywhere", "all sites"):
        assert claim not in everything


def test_protocol_constants_match_the_python_host_and_the_models() -> None:
    protocol = (EXT / "src" / "lib" / "protocol.js").read_text(encoding="utf-8")
    assert f'HOST_NAME = "{native_host.HOST_NAME}"' in protocol
    assert f"PROTOCOL_VERSION = {native_host.PROTOCOL_VERSION};" in protocol
    app_block = re.search(r"AppMessage = Object\.freeze\(\{(.*?)\}\)", protocol, flags=re.DOTALL).group(1)
    assert tuple(re.findall(r':\s*"(\w+)"', app_block)) == native_host.MESSAGE_TYPES
    states_block = re.search(r"LISTING_STATES = Object\.freeze\(\[(.*?)\]\)", protocol, flags=re.DOTALL).group(1)
    assert re.findall(r'"(\w+)"', states_block) == [state.value for state in ListingState]
    quiet = re.search(r"QUIET_STATES = Object\.freeze\(\[(.*?)\]\)", protocol, flags=re.DOTALL).group(1)
    assert set(re.findall(r'"(\w+)"', quiet)) <= {state.value for state in ListingState}
    # the content script cannot import, so it repeats the internal message names
    internal = dict(re.findall(r'(\w+):\s*"(fmid\.\w+)"', protocol))
    banner = (EXT / "src" / "content" / "banner.js").read_text(encoding="utf-8")
    for name in ("SITE_CHECK", "START_REMOVAL", "DISMISS"):
        assert f'MSG_{name} = "{internal[name]}"' in banner


def test_docs_cover_what_the_brief_asked_for() -> None:
    doc = (ROOT / "docs" / "EXTENSION.md").read_text(encoding="utf-8")
    for needle in ("org.freemyid.host", "activeTab", "nativeMessaging", "storage",
                   "declarativeNetRequestWithHostAccess", "scripting", "Sec-GPC",
                   "globalPrivacyControl", "chrome://extensions", "edge://extensions",
                   "about:debugging", "start_removal", "site_check", "CAPTCHA",
                   "registry.sample.yaml", "California", "Colorado", "Connecticut"):
        assert needle in doc, f"docs/EXTENSION.md does not mention {needle}"
