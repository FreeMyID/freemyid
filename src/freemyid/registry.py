"""Broker + state-law registry loading, validation and updates. OWNER: orchestrator.

Precedence: FREEMYID_HOME/registry.yaml (validated update) > bundled brokers/registry.yaml.
Updates: fetched ONLY from config.registry_url (the user's own GitHub repo), validated
against the pydantic model + JSON Schema, optionally pinned by sha256, then atomically
swapped in. A failed validation never replaces the working copy.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import httpx
import jsonschema
import yaml

from . import config, paths
from .models import Registry, StateLaw, StateLawRegistry
from .netpolicy import NetPolicy


class RegistryError(RuntimeError):
    pass


def bundled_registry_path() -> Path:
    return paths.bundled_data_dir() / "brokers" / "registry.yaml"


def bundled_state_laws_path() -> Path:
    return paths.bundled_data_dir() / "brokers" / "state_laws.yaml"


def schema_path() -> Path:
    return paths.bundled_data_dir() / "schema" / "registry.schema.json"


def json_schema() -> dict:
    return Registry.model_json_schema()


def validate_text(text: str) -> Registry:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise RegistryError(f"registry is not valid YAML: {e}") from e
    sp = schema_path()
    schema = json.loads(sp.read_text()) if sp.exists() else json_schema()
    try:
        jsonschema.validate(json.loads(json.dumps(raw, default=str)), schema)
        return Registry.model_validate(raw)
    except (jsonschema.ValidationError, ValueError) as e:
        raise RegistryError(f"registry failed validation: {e}") from e


def load_registry(path: Path | None = None) -> Registry:
    if path is None:
        cached = paths.registry_cache_path()
        path = cached if cached.exists() else bundled_registry_path()
    return validate_text(path.read_text())


def load_state_laws(path: Path | None = None) -> dict[str, StateLaw]:
    p = path or bundled_state_laws_path()
    if not p.exists():
        return {}
    reg = StateLawRegistry.model_validate(yaml.safe_load(p.read_text()))
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
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as e:
        raise RegistryError("registry is not valid UTF-8") from e
    reg = validate_text(text)
    dest = paths.registry_cache_path()
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(dest)
    return reg.version, len(reg.brokers)
