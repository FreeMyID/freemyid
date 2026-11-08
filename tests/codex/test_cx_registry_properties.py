"""Deterministic malformed-input checks for the public registry loader."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from freemyid import paths, registry

ROOT = Path(__file__).resolve().parents[2]
FAKE_REGISTRY = ROOT / "tests" / "fixtures" / "registry_min.yaml"


def _valid_registry() -> dict[str, object]:
    """Load only the checked-in, clearly fake public test registry."""
    payload = yaml.safe_load(FAKE_REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _broker_mutation(payload: dict[str, object], key: str, value: object) -> None:
    brokers = payload["brokers"]
    assert isinstance(brokers, list) and brokers
    first = brokers[0]
    assert isinstance(first, dict)
    first[key] = value


def test_fake_public_fixture_loads_through_yaml_schema_and_model() -> None:
    text = FAKE_REGISTRY.read_text(encoding="utf-8")

    loaded = registry.validate_text(text)

    assert len(loaded.brokers) == 2
    assert {broker.id for broker in loaded.brokers} == {"fakepeople", "fakemail"}


@pytest.mark.parametrize(
    ("target", "key", "value"),
    [
        ("root", "unexpected", True),
        ("root", "version", ["not", "a", "version"]),
        ("root", "brokers", {"id": "fakepeople"}),
        ("broker", "unexpected", "ignored fields must be rejected"),
        ("broker", "domains", "fakepeople.example"),
        ("broker", "priority", "high"),
    ],
    ids=["unknown-root-key", "wrong-version-type", "wrong-brokers-type",
         "unknown-broker-key", "wrong-domains-type", "wrong-priority-type"],
)
def test_schema_rejects_unknown_keys_and_wrong_types(
    target: str, key: str, value: object,
) -> None:
    payload = _valid_registry()
    if target == "root":
        payload[key] = value
    else:
        _broker_mutation(payload, key, value)

    with pytest.raises(registry.RegistryError, match="registry"):
        registry.validate_text(yaml.safe_dump(payload, sort_keys=False))


@pytest.mark.parametrize(
    "text",
    ["brokers: [", "- scalar-root", "null", ""],
    ids=["unclosed-sequence", "wrong-root-shape", "null-root", "empty-file"],
)
def test_malformed_yaml_and_root_shapes_fail_clearly(text: str) -> None:
    with pytest.raises(registry.RegistryError, match="registry") as caught:
        registry.validate_text(text)

    assert str(caught.value).strip()


def test_duplicate_broker_ids_are_rejected() -> None:
    payload = _valid_registry()
    brokers = payload["brokers"]
    assert isinstance(brokers, list) and len(brokers) >= 2
    first, second = brokers[0], brokers[1]
    assert isinstance(first, dict) and isinstance(second, dict)
    second["id"] = first["id"]

    with pytest.raises(registry.RegistryError, match="duplicate broker ids"):
        registry.validate_text(yaml.safe_dump(payload, sort_keys=False))


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("url", "not-a-url"),
        ("url", "https://outside.example/"),
        ("domains", ["fakepeople.example/path"]),
    ],
    ids=["malformed-url", "url-host-outside-allowlist", "domain-not-hostname"],
)
def test_invalid_urls_and_hosts_are_rejected(key: str, value: object) -> None:
    payload = _valid_registry()
    _broker_mutation(payload, key, value)

    with pytest.raises(registry.RegistryError, match="registry"):
        registry.validate_text(yaml.safe_dump(payload, sort_keys=False))


def test_size_cap_rejects_file_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = tmp_path / "oversized-registry.yaml"
    oversized.write_text("x" * 129, encoding="utf-8")
    monkeypatch.setattr(registry, "MAX_REGISTRY_BYTES", 128)

    with pytest.raises(registry.RegistryError, match="larger than 128 bytes"):
        registry.load_registry(oversized)


def test_failed_install_does_not_replace_working_registry_cache() -> None:
    cache = paths.registry_cache_path()
    cache.parent.mkdir(parents=True, exist_ok=True)
    known_good = FAKE_REGISTRY.read_bytes()
    cache.write_bytes(known_good)
    bad_payload = _valid_registry()
    bad_payload["unexpected"] = "must not replace the good cache"

    with pytest.raises(registry.RegistryError):
        registry.install_registry_bytes(
            yaml.safe_dump(bad_payload, sort_keys=False).encode("utf-8")
        )

    assert cache.read_bytes() == known_good
