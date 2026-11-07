"""Broker + state-law registry loading, validation and updates. OWNER: orchestrator.

Precedence: FREEMYID_HOME/registry.yaml (validated update or installed family registry)
  > registry.yaml next to the installed exe (family installer; frozen builds only)
  > bundled brokers/registry.yaml (full registry; family/private builds only)
  > bundled brokers/registry.sample.yaml (small public sample; always shipped).
`registry_source()` tells the UI/CLI which one is in use: "update" | "family" | "full" | "sample".
Updates: fetched ONLY from config.registry_url (the user's own GitHub repo), validated
against the pydantic model + JSON Schema, optionally pinned by sha256, then atomically
swapped in. A failed validation never replaces the working copy.
If the preferred registry is unreadable or invalid, `load_registry()` falls back to the next
source (so a bad update never leaves the app with no broker list) and records a warning in
`load_warnings`. YAML aliases are refused (alias-expansion "billion laughs" protection).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import httpx
import jsonschema
import yaml

from . import config, paths
from .models import Registry, StateLaw, StateLawRegistry
from .netpolicy import NetPolicy

log = logging.getLogger(__name__)


class RegistryError(RuntimeError):
    pass


class _NoAliasLoader(yaml.SafeLoader):
    """SafeLoader that refuses aliases to lists/maps. Expanding those (the json round-trip
    below) turns a tiny file into gigabytes ("billion laughs"). Aliases to plain scalars
    (the registry reuses a source URL this way) cannot grow and stay allowed."""

    def compose_node(self, parent, index):  # type: ignore[no-untyped-def]
        if self.check_event(yaml.AliasEvent):
            anchor = self.peek_event().anchor
            if not isinstance(self.anchors.get(anchor), yaml.ScalarNode):
                raise yaml.YAMLError("YAML aliases to lists or maps are not allowed in a registry")
        return super().compose_node(parent, index)


SOURCE_UPDATE, SOURCE_FAMILY, SOURCE_FULL, SOURCE_SAMPLE = "update", "family", "full", "sample"


def bundled_full_registry_path() -> Path:
    """Full maintained registry. Not in the public repo; present in family/private builds."""
    return paths.bundled_data_dir() / "brokers" / "registry.yaml"


def bundled_sample_registry_path() -> Path:
    """Small public sample registry; always shipped."""
    return paths.bundled_data_dir() / "brokers" / "registry.sample.yaml"


def bundled_registry_path() -> Path:
    """The bundled registry in use: the full one if this build carries it, else the sample."""
    full = bundled_full_registry_path()
    return full if full.exists() else bundled_sample_registry_path()


def _candidates() -> list[tuple[str, Path]]:
    """Existing registries in precedence order; the sample is always last."""
    out: list[tuple[str, Path]] = []
    cached = paths.registry_cache_path()
    if cached.exists():
        out.append((SOURCE_UPDATE, cached))
    family = find_family_registry()
    if family is not None:
        out.append((SOURCE_FAMILY, family))
    full = bundled_full_registry_path()
    if full.exists():
        out.append((SOURCE_FULL, full))
    out.append((SOURCE_SAMPLE, bundled_sample_registry_path()))
    return out


def _active_registry() -> tuple[str, Path]:
    return _candidates()[0]


# (preferred candidate at load time, source actually loaded): a fallback is only reported
# while the same preferred registry is still in place.
_loaded: tuple[tuple[str, Path], str] | None = None
load_warnings: list[str] = []


def registry_source() -> str:
    """Which registry `load_registry()` used last (or would use): "update"
    (FREEMYID_HOME/registry.yaml, from the update feed or an installed family registry),
    "family" (registry.yaml next to the installed exe), "full" (bundled full registry) or
    "sample" (public sample). After a fallback this names the source actually loaded."""
    preferred = _active_registry()
    if _loaded is not None and _loaded[0] == preferred:
        return _loaded[1]
    return preferred[0]


def bundled_state_laws_path() -> Path:
    return paths.bundled_data_dir() / "brokers" / "state_laws.yaml"


def schema_path() -> Path:
    return paths.bundled_data_dir() / "schema" / "registry.schema.json"


def json_schema() -> dict:
    return Registry.model_json_schema()


def validate_text(text: str) -> Registry:
    try:
        raw = yaml.load(text, Loader=_NoAliasLoader)
    except yaml.YAMLError as e:
        raise RegistryError(f"registry is not valid YAML: {e}") from e
    sp = schema_path()
    schema = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else json_schema()
    try:
        jsonschema.validate(json.loads(json.dumps(raw, default=str)), schema)
        return Registry.model_validate(raw)
    except (jsonschema.ValidationError, ValueError) as e:
        raise RegistryError(f"registry failed validation: {e}") from e


def _load_file(path: Path) -> Registry:
    try:
        if path.stat().st_size > MAX_REGISTRY_BYTES:
            raise RegistryError(f"registry is larger than {MAX_REGISTRY_BYTES} bytes; refusing")
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise RegistryError(f"registry could not be read: {e}") from e
    return validate_text(text)


def load_registry(path: Path | None = None) -> Registry:
    """Load an explicit registry file, or the best available one with fallback."""
    global _loaded
    if path is not None:
        return _load_file(path)
    load_warnings.clear()
    err: RegistryError | None = None
    cands = _candidates()
    for source, p in cands:
        try:
            reg = _load_file(p)
        except RegistryError as e:
            msg = f"{source} registry unusable, trying the next one: {e}"
            log.warning(msg)
            load_warnings.append(msg)
            err = e
            continue
        _loaded = (cands[0], source)
        return reg
    assert err is not None
    raise err


def load_state_laws(path: Path | None = None) -> dict[str, StateLaw]:
    p = path or bundled_state_laws_path()
    if not p.exists():
        return {}
    reg = StateLawRegistry.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
    return {s.state: s for s in reg.states}


MAX_REGISTRY_BYTES = 5 * 1024 * 1024
MAX_PIN_BYTES = 4096
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _check_url(url: str, what: str, policy: NetPolicy) -> None:
    if not url.lower().startswith("https://"):
        raise RegistryError(f"{what} must be https")
    if not policy.is_allowed(url):
        raise RegistryError(f"{what} host is not on the network allowlist")


def _fetch(c: httpx.Client, url: str, cap: int, what: str) -> bytes:
    """GET url with no redirects, streaming, refusing bodies over `cap` bytes."""
    try:
        with c.stream("GET", url) as resp:
            if resp.status_code != 200:
                raise RegistryError(f"{what} fetch failed: HTTP {resp.status_code}")
            declared = resp.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > cap:
                raise RegistryError(f"{what} is larger than {cap} bytes; refusing")
            buf = bytearray()
            for chunk in resp.iter_bytes():
                buf.extend(chunk)
                if len(buf) > cap:
                    raise RegistryError(f"{what} is larger than {cap} bytes; refusing")
            return bytes(buf)
    except httpx.HTTPError as e:
        raise RegistryError(f"{what} fetch failed: {type(e).__name__}") from e


def update_registry(timeout: float = 30.0, *,
                    transport: httpx.BaseTransport | None = None) -> tuple[str, int]:
    """Pull, validate, pin, swap. Returns (version, broker_count).

    Both URLs must be https and allowed by NetPolicy; redirects are refused and bodies
    are capped at MAX_REGISTRY_BYTES. `transport` is for tests (httpx.MockTransport).
    """
    cfg = config.load()
    if not cfg.registry_url:
        raise RegistryError("registry_url is not configured (freemyid config set registry_url ...)")
    policy = NetPolicy(None)   # registry hosts + user extras only; no broker hosts needed
    _check_url(cfg.registry_url, "registry_url", policy)
    if cfg.registry_sha256_url:
        _check_url(cfg.registry_sha256_url, "registry_sha256_url", policy)
    with httpx.Client(timeout=timeout, follow_redirects=False, transport=transport) as c:
        body = _fetch(c, cfg.registry_url, MAX_REGISTRY_BYTES, "registry")
        if cfg.registry_sha256_url:
            pin = _fetch(c, cfg.registry_sha256_url, MAX_PIN_BYTES, "registry sha256 pin")
            fields = pin.decode("ascii", errors="replace").split()
            want = fields[0].strip().lower() if fields else ""
            if not _SHA256_RE.match(want):
                raise RegistryError("registry sha256 pin is empty or malformed; refusing update")
            if want != hashlib.sha256(body).hexdigest():
                raise RegistryError("registry sha256 mismatch; refusing update")
    reg = install_registry_bytes(body)
    return reg.version, len(reg.brokers)


def install_registry_bytes(body: bytes) -> Registry:
    """Validate a registry and atomically install it as FREEMYID_HOME/registry.yaml.

    Shared by `update_registry` and family-bundle import, so both get the same checks:
    size cap, UTF-8, YAML, JSON Schema + pydantic. On any failure nothing is replaced.
    """
    if len(body) > MAX_REGISTRY_BYTES:
        raise RegistryError(f"registry is larger than {MAX_REGISTRY_BYTES} bytes; refusing")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as e:
        raise RegistryError("registry is not valid UTF-8") from e
    reg = validate_text(text)
    dest = paths.registry_cache_path()
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(body)   # exact bytes: text mode would turn \r\n into \r\r\n on Windows
    tmp.replace(dest)
    return reg


FAMILY_REGISTRY_NAME = "registry.yaml"


def find_family_registry() -> Path | None:
    """A registry.yaml shipped next to the installed app (family installer), if any.

    Only checked for frozen (installed) builds, mirroring wizard.flows.find_family_bundle.
    """
    import sys
    if not getattr(sys, "frozen", False):
        return None
    p = Path(sys.executable).parent / FAMILY_REGISTRY_NAME
    return p if p.is_file() else None


def install_family_registry(src: Path | bytes) -> tuple[str, int]:
    """Install a family-bundle registry (file path or raw bytes) through the update checks."""
    if isinstance(src, Path):
        if src.stat().st_size > MAX_REGISTRY_BYTES:
            raise RegistryError(f"registry is larger than {MAX_REGISTRY_BYTES} bytes; refusing")
        src = src.read_bytes()
    reg = install_registry_bytes(src)
    return reg.version, len(reg.brokers)
