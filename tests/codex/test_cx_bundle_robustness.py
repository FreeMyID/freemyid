"""Robustness checks for the public family-bundle import boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from freemyid.wizard import flows

PASSPHRASE = "fake-bundle-passphrase"
PROFILE_ID = "f" * 32


class FakeProfile:
    """Small fake accepted by the public exporter; contains no real details."""

    id = PROFILE_ID

    def model_dump(self, *, mode: str, exclude: set[str]) -> dict[str, object]:
        assert mode == "json"
        data: dict[str, object] = {
            "id": self.id,
            "label": "Pat Testperson",
            "name": {"first": "Pat", "last": "Testperson"},
            "addresses": [{"city": "Springfield", "state": "IL", "current": True}],
            "mailbox": {"email": "fake@example.invalid", "password": "fake-only"},
            "consent": {"basis": "self", "attested_by": "Pat Testperson"},
        }
        return {key: value for key, value in data.items() if key not in exclude}


class FakeStore:
    def __init__(self) -> None:
        self.profile = FakeProfile()
        self.saved_profiles = 0

    def get_profile(self, profile_id: str) -> FakeProfile | None:
        return self.profile if profile_id == self.profile.id else None

    def save_profile(self, _profile: object) -> None:
        self.saved_profiles += 1


def _exported_bundle(tmp_path: Path) -> bytes:
    destination = flows.export_family_bundle(
        FakeStore(), PROFILE_ID, tmp_path / "fake-family", PASSPHRASE
    )
    return destination.read_bytes()


def test_public_export_import_round_trip_does_not_import_mailbox(tmp_path: Path) -> None:
    blob = _exported_bundle(tmp_path)

    draft = flows.load_bundle(blob, PASSPHRASE)

    assert draft.imported is True
    assert draft.label == "Pat Testperson"
    assert draft.mailbox == {}
    assert draft.password == ""
    assert draft.saved_password is False
    assert draft.tls_pin == ""


@pytest.mark.xfail(
    strict=True,
    reason="src/freemyid/crypto.py:198 leaks InvalidTag instead of a calm import error",
)
def test_wrong_passphrase_is_rejected(tmp_path: Path) -> None:
    blob = _exported_bundle(tmp_path)

    with pytest.raises(ValueError):
        flows.load_bundle(blob, "incorrect fake passphrase")


@pytest.mark.parametrize("damage", ["truncate", "tamper"])
@pytest.mark.xfail(
    strict=True,
    reason="src/freemyid/crypto.py:198 leaks InvalidTag instead of a calm import error",
)
def test_truncated_or_tampered_bundle_is_rejected(tmp_path: Path, damage: str) -> None:
    blob = _exported_bundle(tmp_path)
    if damage == "truncate":
        damaged = blob[:-8]
    else:
        changed = bytearray(blob)
        changed[-1] ^= 1
        damaged = bytes(changed)

    with pytest.raises(ValueError):
        flows.load_bundle(damaged, PASSPHRASE)


def test_large_malformed_bundle_is_rejected(tmp_path: Path) -> None:
    oversized = b"x" * (10 * 1024 * 1024 + 1)

    with pytest.raises(ValueError):
        flows.load_bundle(oversized, PASSPHRASE)


def test_unsupported_version_is_rejected_at_post_decryption_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = json.dumps(
        {"freemyid_bundle": flows.BUNDLE_VERSION + 100, "profile": {}}
    ).encode()
    monkeypatch.setattr(flows, "import_with_passphrase", lambda _blob, _pw: payload)

    with pytest.raises(ValueError, match="unsupported bundle version"):
        flows.load_bundle(b"opaque fake envelope", PASSPHRASE)


def test_post_decryption_mailbox_fields_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps(
        {
            "freemyid_bundle": flows.BUNDLE_VERSION,
            "profile": {
                "id": "a" * 32,
                "label": "Pat Testperson",
                "name": {"first": "Pat", "last": "Testperson"},
                "addresses": [{"city": "Springfield", "state": "IL", "current": True}],
                "mailbox": {
                    "email": "fake@example.invalid",
                    "password": "fake-only",
                    "tls_cert_sha256": "fake-fingerprint",
                },
            },
        }
    ).encode()
    monkeypatch.setattr(flows, "import_with_passphrase", lambda _blob, _pw: payload)

    draft = flows.load_bundle(b"opaque fake envelope", PASSPHRASE)

    assert draft.mailbox == {}
    assert draft.password == ""
    assert draft.saved_password is False
    assert draft.tls_pin == ""


def test_failed_cli_import_does_not_save_a_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FakeStore()
    damaged_file = tmp_path / "truncated.freemyid-profile"
    damaged_file.write_bytes(b"not a family bundle")
    monkeypatch.setattr(flows, "_secret", lambda _prompt: PASSPHRASE)

    with pytest.raises(ValueError):
        flows.setup_cli(store, prefill=damaged_file)

    assert store.saved_profiles == 0
