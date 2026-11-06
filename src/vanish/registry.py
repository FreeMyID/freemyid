"""Broker + state-law registry loading, validation and updates. OWNER: orchestrator.

Precedence: VANISH_HOME/registry.yaml (validated update) > bundled brokers/registry.yaml.
Updates: fetched ONLY from config.registry_url (the user's own GitHub repo), validated
against the pydantic model + JSON Schema, optionally pinned by sha256, then atomically
swapped in. A failed validation never replaces the working copy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import jsonschema
import yaml

from . import config, paths
from .models import Registry, StateLaw, StateLawRegistry


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


def update_registry(timeout: float = 30.0) -> tuple[str, int]:
    """Pull, validate, pin, swap. Returns (version, broker_count)."""
    cfg = config.load()
    if not cfg.registry_url:
        raise RegistryError("registry_url is not configured (vanish config set registry_url ...)")
    if not cfg.registry_url.startswith("https://"):
        raise RegistryError("registry_url must be https")
    with httpx.Client(timeout=timeout, follow_redirects=False) as c:
        resp = c.get(cfg.registry_url)
        resp.raise_for_status()
        text = resp.text
        if cfg.registry_sha256_url:
            pin = c.get(cfg.registry_sha256_url)
            pin.raise_for_status()
            want = pin.text.split()[0].strip().lower()
            got = hashlib.sha256(resp.content).hexdigest()
            if want != got:
                raise RegistryError("registry sha256 mismatch; refusing update")
    reg = validate_text(text)
    dest = paths.registry_cache_path()
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(dest)
    return reg.version, len(reg.brokers)
