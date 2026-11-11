#!/usr/bin/env python3
"""Build the Free My ID browser extension: extension/ -> dist/extension/<browser>/ plus a zip.

    python tools/build_extension.py                    # chrome, edge and firefox
    python tools/build_extension.py --browser firefox  # one browser
    python tools/build_extension.py --out /tmp/ext     # another output folder

What it does, per browser:
  1. merges extension/manifests/base.json with <browser>.json and checks the result,
  2. writes data/broker_domains.json from the PUBLIC sample registry,
  3. fills content_scripts[0].matches from that list (https, exact hosts, no wildcards),
  4. copies the extension files and writes a zip.
Chrome and Edge also get rules/gpc.json and the page script for the Global Privacy Control
stub; the Firefox package does not (Firefox has that switch built in).

Data: only brokers/registry.sample.yaml (CC BY-NC 4.0) is read. Never point this at
brokers/registry.yaml: the full registry is private and must not ship inside a public extension.

Stdlib only (no PyYAML): the registry is read by a small line reader that knows just the few
keys needed here. tests/test_extension_build.py compares it with PyYAML.
The build is deterministic: sorted inputs, no timestamps, fixed zip metadata.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
BROWSERS = ("chrome", "edge", "firefox")
SAMPLE_REGISTRY_REL = "brokers/registry.sample.yaml"   # public sample ONLY

# The complete permission list. Adding one needs a rationale in docs/EXTENSION.md and review.
ALLOWED_PERMISSIONS = frozenset({"activeTab", "nativeMessaging", "storage"})
# Chrome and Edge only, for the Global Privacy Control stub (off until the person turns it on).
# Firefox has GPC built in, so its package gets none of this.
GPC_BROWSERS = frozenset({"chrome", "edge"})
GPC_PERMISSIONS = frozenset({"declarativeNetRequestWithHostAccess"})
GPC_OPTIONAL_PERMISSIONS = ["scripting"]            # asked for at the moment GPC is switched on
GPC_OPTIONAL_HOSTS = ["*://*/*"]                    # same: never granted at install time
GPC_RULES_PATH = "rules/gpc.json"
GPC_RULE_RESOURCES = [{"id": "gpc", "enabled": False, "path": GPC_RULES_PATH}]
GPC_PAGE_SCRIPT = "src/content/gpc.js"
# Categories whose own website shows people's details to the public: the banner may appear there.
BANNER_CATEGORIES = frozenset({"people_search", "background_check", "phone_lookup", "family_tree"})
# Categories the popup may name as "a company that sells people's information" (no banner).
LISTED_CATEGORIES = BANNER_CATEGORIES | {"data_broker", "risk_data"}

# Files that live in extension/src but must not ship (future work, not wired up).
EXCLUDED_FILES = frozenset({"src/content/assisted-fill.js"})
PACKAGE_DIRS = ("_locales", "assets/icons", "src")
PACKAGE_SUFFIXES = frozenset({".css", ".html", ".js", ".json", ".png"})
DOMAINS_PATH = "data/broker_domains.json"
_RESOURCE_TYPES = frozenset({"main_frame", "sub_frame", "stylesheet", "script", "image", "font",
                             "object", "xmlhttprequest", "ping", "csp_report", "media", "websocket",
                             "other"})
FIREFOX_ID = "extension@freemyid.org"

_HOST = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_BROKER_ID = re.compile(r"^[a-z0-9_]{1,64}$")
_VERSION = re.compile(r"^\d{1,5}(\.\d{1,5}){0,3}$")
_ENTRY = re.compile(r"^  - id:\s*(\S+)\s*$")
_SCALAR = re.compile(r"^    (name|url|category):\s+(.*\S)\s*$")
_DOMAINS_FLOW = re.compile(r"^    domains:\s*\[(.*)\]\s*$")
_DOMAINS_BLOCK = re.compile(r"^    domains:\s*$")
_LIST_ITEM = re.compile(r"^\s{4,}-\s+(\S+)\s*$")
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class BuildError(Exception):
    """The inputs are wrong. The message says which file and why."""


# ----------------------------------------------------------------- registry (public sample only)

def sample_registry_path(root: Path = ROOT, override: Path | None = None) -> Path:
    """Path of the public sample registry. An override must also be a *.sample.yaml file."""
    path = Path(override) if override else root / SAMPLE_REGISTRY_REL
    if not path.name.endswith(".sample.yaml"):
        raise BuildError(f"{path.name}: only the public sample registry (*.sample.yaml) may be "
                         "used to build the extension")
    return path


def _scalar(raw: str) -> str:
    """One YAML scalar on one line: plain, 'single' or "double" quoted."""
    raw = raw.strip()
    if raw.startswith('"'):
        return str(json.loads(raw))
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return raw[1:-1].replace("''", "'")
    return raw.split(" #", 1)[0].strip()


def parse_sample_registry(text: str) -> tuple[str, list[dict]]:
    """Read (registry version, brokers) from the sample registry text.

    Reads only: id, name, url, category, domains. Everything else in the file is skipped.
    """
    version = ""
    brokers: list[dict] = []
    current: dict | None = None
    in_domains = False
    for line in text.splitlines():
        if line.startswith("version:"):
            version = _scalar(line.split(":", 1)[1])
            continue
        entry = _ENTRY.match(line)
        if entry:
            current = {"id": _scalar(entry.group(1)), "name": "", "url": "", "category": "",
                       "domains": []}
            brokers.append(current)
            in_domains = False
            continue
        if current is None:
            continue
        if in_domains:
            item = _LIST_ITEM.match(line)
            if item:
                current["domains"].append(_scalar(item.group(1)))
                continue
            in_domains = False
        flow = _DOMAINS_FLOW.match(line)
        if flow:
            current["domains"] = [_scalar(p) for p in flow.group(1).split(",") if p.strip()]
            continue
        if _DOMAINS_BLOCK.match(line):
            in_domains = True
            continue
        scalar = _SCALAR.match(line)
        if scalar:
            current[scalar.group(1)] = _scalar(scalar.group(2))
    return version, brokers


def _site_root(url: str) -> str:
    """Last two labels of the broker's own web address, e.g. 'spokeo.com'. No public-suffix
    list (stdlib only), which is enough for the hosts in the sample."""
    host = (urlsplit(url).hostname or "").lower()
    return ".".join(host.split(".")[-2:]) if host.count(".") >= 1 else ""


def build_domain_list(version: str, brokers: list[dict]) -> dict:
    """The lookup table shipped in the extension: hostname -> broker id, broker id -> name.

    A host is kept only when it belongs to the broker's own site (same last two labels as its
    `url`), so shared form hosts and a parent company's host are never claimed by the wrong
    broker. The first broker in file order that lists a host owns it.
    """
    hosts: dict[str, str] = {}
    names: dict[str, dict] = {}
    for b in brokers:
        bid, category = b["id"], b["category"]
        if category not in LISTED_CATEGORIES:
            continue
        if not _BROKER_ID.match(bid):
            raise BuildError(f"broker id {bid!r} is not a plain lower-case id")
        root = _site_root(b["url"])
        own = []
        for raw in b["domains"]:
            host = raw.lower()
            if not _HOST.match(host):
                raise BuildError(f"broker {bid}: {raw!r} is not a plain hostname")
            if root and (host == root or host.endswith("." + root)) and host not in hosts:
                hosts[host] = bid
                own.append(host)
        if own:
            names[bid] = {"name": b["name"] or bid, "banner": category in BANNER_CATEGORIES}
    return {
        "schema": 1,
        "source": SAMPLE_REGISTRY_REL,
        "registry_version": version,
        "brokers": dict(sorted(names.items())),
        "hosts": dict(sorted(hosts.items())),
    }


def banner_match_patterns(domains: dict) -> list[str]:
    """https match patterns for the content script: exact hosts of banner brokers only."""
    return sorted(f"https://{host}/*" for host, bid in domains["hosts"].items()
                  if domains["brokers"][bid]["banner"])


def load_domain_list(root: Path = ROOT, registry: Path | None = None) -> dict:
    path = sample_registry_path(root, registry)
    version, brokers = parse_sample_registry(path.read_text(encoding="utf-8"))
    if not brokers:
        raise BuildError(f"{path}: no brokers found")
    return build_domain_list(version, brokers)


# ----------------------------------------------------------------------------------- manifest

def _strip_comments(value):
    if isinstance(value, dict):
        return {k: _strip_comments(v) for k, v in value.items() if not k.startswith("//")}
    if isinstance(value, list):
        return [_strip_comments(v) for v in value]
    return value


def deep_merge(base: dict, override: dict) -> dict:
    """Dicts merge key by key; any other value in `override` replaces the one in `base`."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def build_manifest(browser: str, domains: dict, root: Path = ROOT) -> dict:
    if browser not in BROWSERS:
        raise BuildError(f"unknown browser {browser!r}; choose from {', '.join(BROWSERS)}")
    mdir = root / "extension" / "manifests"
    base = json.loads((mdir / "base.json").read_text(encoding="utf-8"))
    override = json.loads((mdir / f"{browser}.json").read_text(encoding="utf-8"))
    manifest = _strip_comments(deep_merge(base, override))
    manifest["content_scripts"][0]["matches"] = banner_match_patterns(domains)
    errors = validate_manifest(manifest, browser)
    if errors:
        raise BuildError(f"{browser} manifest: " + "; ".join(errors))
    return manifest


def allowed_permissions(browser: str) -> frozenset[str]:
    """Every install-time permission this browser's package may ask for."""
    return ALLOWED_PERMISSIONS | (GPC_PERMISSIONS if browser in GPC_BROWSERS else frozenset())


def validate_gpc_rules(rules: object) -> list[str]:
    """rules/gpc.json may do one thing only: add the request header 'Sec-GPC: 1'."""
    if not isinstance(rules, list) or len(rules) != 1 or not isinstance(rules[0], dict):
        return ["gpc rules: exactly one rule is expected"]
    rule = rules[0]
    errors: list[str] = []
    if set(rule) != {"id", "priority", "action", "condition"}:
        errors.append("gpc rule: unexpected keys")
    if rule.get("action") != {"type": "modifyHeaders", "requestHeaders": [
            {"header": "Sec-GPC", "operation": "set", "value": "1"}]}:
        errors.append("gpc rule: the action must only set the request header Sec-GPC: 1")
    condition = rule.get("condition")
    types = condition.get("resourceTypes") if isinstance(condition, dict) else None
    if (not isinstance(condition, dict) or set(condition) != {"resourceTypes"}
            or not isinstance(types, list) or not set(types) <= _RESOURCE_TYPES
            or "main_frame" not in types):
        errors.append("gpc rule: the condition may only list resource types (with main_frame)")
    return errors


def validate_manifest(manifest: dict, browser: str) -> list[str]:
    """Rules every build must pass. Returns a list of problems (empty = fine)."""
    errors: list[str] = []
    if manifest.get("manifest_version") != 3:
        errors.append("manifest_version must be 3")
    if not _VERSION.match(str(manifest.get("version", ""))):
        errors.append("version must be 1 to 4 dot-separated numbers")
    for key in ("name", "description", "default_locale", "icons", "action", "background"):
        if not manifest.get(key):
            errors.append(f"missing {key}")
    extra = set(manifest.get("permissions", [])) - allowed_permissions(browser)
    if extra:
        errors.append(f"permissions not allowed: {sorted(extra)}")
    for key in ("host_permissions", "externally_connectable", "web_accessible_resources",
                "update_url", "content_security_policy_report_only", "sandbox", "devtools_page",
                "chrome_url_overrides"):
        if key in manifest:
            errors.append(f"{key} is not allowed")
    # Global Privacy Control stub: exactly this shape on Chrome and Edge, nothing on Firefox.
    gpc = browser in GPC_BROWSERS
    expected = {
        "optional_permissions": GPC_OPTIONAL_PERMISSIONS if gpc else None,
        "optional_host_permissions": GPC_OPTIONAL_HOSTS if gpc else None,
        "declarative_net_request": {"rule_resources": GPC_RULE_RESOURCES} if gpc else None,
    }
    for key, want in expected.items():
        if manifest.get(key) != want:
            errors.append(f"{key} must be {want!r}" if gpc else f"{key} is not allowed on {browser}")
    scripts = manifest.get("content_scripts", [])
    if len(scripts) != 1:
        errors.append("exactly one content_scripts entry is expected")
    for cs in scripts:
        if cs.get("all_frames") or cs.get("match_about_blank") or cs.get("world") == "MAIN":
            errors.append("content script must stay in the top frame and the isolated world")
        for pattern in cs.get("matches", []):
            m = re.fullmatch(r"https://([^/*]+)/\*", pattern)
            if not m or not _HOST.match(m.group(1)):
                errors.append(f"content script match {pattern!r} is not an exact https host")
        if not cs.get("matches"):
            errors.append("content script has no matches")
    csp = manifest.get("content_security_policy")
    policy = csp.get("extension_pages", "") if isinstance(csp, dict) else ""
    directives = {d.split()[0]: d.split()[1:] for d in policy.split(";") if d.strip()}
    if directives.get("default-src") != ["'none'"] or directives.get("script-src") != ["'self'"]:
        errors.append("CSP must set default-src 'none' and script-src 'self'")
    if directives.get("object-src") != ["'none'"]:
        errors.append("CSP must set object-src 'none'")
    if re.search(r"unsafe|https?:|wss?:|\*|data:|blob:", policy):
        errors.append("CSP must not allow unsafe-*, remote or wildcard sources")
    background = manifest.get("background") or {}
    if background.get("type") != "module":
        errors.append("background must be an ES module")
    gecko = (manifest.get("browser_specific_settings") or {}).get("gecko") or {}
    if browser == "firefox":
        if "service_worker" in background or not background.get("scripts"):
            errors.append("firefox needs background.scripts and no service_worker")
        if gecko.get("id") != FIREFOX_ID:
            errors.append(f"firefox needs browser_specific_settings.gecko.id = {FIREFOX_ID}")
    else:
        if "scripts" in background or not background.get("service_worker"):
            errors.append(f"{browser} needs background.service_worker and no scripts")
        if "browser_specific_settings" in manifest:
            errors.append(f"{browser} must not carry browser_specific_settings")
    return errors


# -------------------------------------------------------------------------------------- output

def _dump(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def package_files(browser: str, root: Path = ROOT) -> dict[str, bytes]:
    """The static files that ship for one browser, as {relative posix path: bytes}, sorted."""
    ext = root / "extension"
    files: dict[str, bytes] = {}
    excluded = EXCLUDED_FILES if browser in GPC_BROWSERS else EXCLUDED_FILES | {GPC_PAGE_SCRIPT}
    if browser in GPC_BROWSERS:
        raw = (ext / GPC_RULES_PATH).read_bytes()
        errors = validate_gpc_rules(json.loads(raw))
        if errors:
            raise BuildError("; ".join(errors))
        files[GPC_RULES_PATH] = raw
    for top in PACKAGE_DIRS:
        for path in sorted((ext / top).rglob("*")):
            rel = path.relative_to(ext).as_posix()
            if path.is_symlink():
                raise BuildError(f"{rel}: symlinks are not packaged")
            if path.is_file() and path.suffix in PACKAGE_SUFFIXES and rel not in excluded:
                files[rel] = path.read_bytes()
    return dict(sorted(files.items()))


def referenced_files(manifest: dict) -> list[str]:
    """Every packaged file the manifest points at."""
    background = manifest.get("background", {})
    out = [*manifest.get("icons", {}).values(),
           *manifest.get("action", {}).get("default_icon", {}).values(),
           manifest.get("action", {}).get("default_popup", ""),
           manifest.get("options_ui", {}).get("page", ""),
           background.get("service_worker", ""), *background.get("scripts", [])]
    for cs in manifest.get("content_scripts", []):
        out += cs.get("js", []) + cs.get("css", [])
    out += [r.get("path", "") for r in
            manifest.get("declarative_net_request", {}).get("rule_resources", [])]
    return sorted({p for p in out if p})


def build_tree(browser: str, root: Path = ROOT, registry: Path | None = None) -> dict[str, bytes]:
    """All files of one browser's package, in memory."""
    domains = load_domain_list(root, registry)
    manifest = build_manifest(browser, domains, root)
    files = package_files(browser, root)
    files[DOMAINS_PATH] = _dump(domains)
    files["manifest.json"] = _dump(manifest)
    missing = [p for p in referenced_files(manifest) if p not in files]
    if missing:
        raise BuildError(f"{browser} manifest points at missing files: {missing}")
    if manifest.get("default_locale") and "_locales/en/messages.json" not in files:
        raise BuildError("default_locale is set but _locales/en/messages.json is missing")
    return dict(sorted(files.items()))


def zip_bytes_to(path: Path, files: dict[str, bytes]) -> None:
    """Write a zip whose bytes depend only on the file names and contents."""
    with zipfile.ZipFile(path, "w") as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            zf.writestr(info, files[name], compresslevel=9)


def write_build(browser: str, out: Path, root: Path = ROOT, registry: Path | None = None) -> Path:
    """Write <out>/<browser>/ and <out>/freemyid-extension-<browser>-<version>.zip."""
    files = build_tree(browser, root, registry)
    target = out / browser
    if target.exists():
        # only ever delete a folder this script made
        if any(target.iterdir()) and not (target / "manifest.json").is_file():
            raise BuildError(f"{target} exists and is not an extension build; not deleting it")
        shutil.rmtree(target)
    for rel, data in files.items():
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    version = json.loads(files["manifest.json"])["version"]
    archive = out / f"freemyid-extension-{browser}-{version}.zip"
    zip_bytes_to(archive, files)
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--browser", choices=(*BROWSERS, "all"), default="all")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "extension")
    parser.add_argument("--registry", type=Path, default=None,
                        help="another public *.sample.yaml (never the private registry)")
    args = parser.parse_args(argv)
    try:
        for browser in BROWSERS if args.browser == "all" else (args.browser,):
            archive = write_build(browser, args.out, ROOT, args.registry)
            print(f"{browser}: {args.out / browser}  ->  {archive.name}")
    except (BuildError, OSError, json.JSONDecodeError) as exc:
        print(f"build_extension: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
