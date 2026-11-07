"""At-rest encryption. Key lives in the OS keychain or a passphrase wrap. OWNER: orchestrator.

Where the key lives is decided by `secret_backends` (keyring | passphrase | systemd-creds).

Field/blob-level AES-256-GCM. Ciphertext format: b"V1" + 12-byte nonce + ct||tag.
SQLCipher was considered; blob encryption avoids cross-platform native packaging issues.
Only ids, enums and timestamps are stored in clear; all PII is inside encrypted blobs.

Evidence files are bound (AAD) to their path relative to FREEMYID_HOME/evidence, so a file
cannot be swapped between profiles/brokers. Store a `key_check()` value in the DB `meta`
table on first use and `verify_key_check()` it on open to detect a wrong/lost key early.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import sys
from pathlib import Path

import keyring
import keyring.errors
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import paths

SERVICE = "freemyid"
KEY_NAME = "db-key-v1"
_MAGIC = b"V1"
_KEY_CHECK_PLAINTEXT = b"freemyid-key-check-v1"
_KEY_CHECK_AAD = b"meta:key_check"
_FILE_AAD_PREFIX = b"evidence:"

log = logging.getLogger(__name__)

# Backends that would silently lose the key or store it in clear text.
_REJECTED_BACKENDS = {
    "keyring.backends.fail.Keyring",
    "keyring.backends.null.Keyring",
    "keyrings.alt.file.PlaintextKeyring",
}


class KeyUnavailable(RuntimeError):
    """OS keychain locked/unavailable (e.g. headless session). Surface as NEEDS_HUMAN."""


def _test_key() -> bytes | None:
    """FREEMYID_TEST_KEY is honored only under pytest or with FREEMYID_ALLOW_TEST_KEY=1.

    The test key is a SHA-256 of an env string (no KDF): never acceptable for real data.
    A leftover variable outside tests is refused loudly rather than silently ignored, so
    data is never split between two keys.
    """
    test_key = os.environ.get("FREEMYID_TEST_KEY")
    if not test_key:
        return None
    if "pytest" in sys.modules or os.environ.get("FREEMYID_ALLOW_TEST_KEY") == "1":
        log.warning("Using FREEMYID_TEST_KEY: weak test-only key, never use with real data")
        return hashlib.sha256(test_key.encode()).digest()
    raise KeyUnavailable(
        "FREEMYID_TEST_KEY is set outside the test suite; unset it to use the OS keychain"
    )


def _backend_names(kr: object) -> list[str]:
    backends = getattr(kr, "backends", None)  # ChainerBackend
    objs = list(backends) if backends else [kr]
    return [f"{type(b).__module__}.{type(b).__qualname__}" for b in objs]


def _check_backend() -> None:
    names = _backend_names(keyring.get_keyring())
    bad = [n for n in names if n in _REJECTED_BACKENDS]
    if bad and len(bad) == len(names):
        raise KeyUnavailable(f"no secure OS keychain available (backend: {', '.join(bad)})")


def _decode_key(stored: str) -> bytes:
    try:
        key = base64.b64decode(stored, validate=True)
    except ValueError as e:
        raise KeyUnavailable("stored key is corrupt") from e
    if len(key) != 32:
        raise KeyUnavailable("stored key has the wrong length")
    return key


def _get_or_create_key() -> bytes:
    """Test key (pytest only), else the selected secrets backend (secret_backends.select)."""
    if (tk := _test_key()) is not None:
        return tk
    from . import secret_backends
    return secret_backends.select().load_data_key()


def _keyring_get_or_create_key() -> bytes:
    """The OS keychain path (default backend; unchanged since 0.1)."""
    try:
        _check_backend()
        stored = keyring.get_password(SERVICE, KEY_NAME)
        if stored is None:
            key = AESGCM.generate_key(bit_length=256)
            keyring.set_password(SERVICE, KEY_NAME, base64.b64encode(key).decode())
            # Re-read: if another process won a first-run race, use its key, not ours.
            stored = keyring.get_password(SERVICE, KEY_NAME)
            if stored is None:
                raise KeyUnavailable("keychain did not persist the key")
        return _decode_key(stored)
    except keyring.errors.KeyringError as e:
        raise KeyUnavailable(str(e)) from e


def delete_key() -> None:
    """Remove this folder's data key from every backend (used by `freemyid wipe`): the
    passphrase-wrapped key file, and the OS keychain entry when it is this folder's key.
    The keychain entry is global, so another folder's key is left alone (SEC-72).
    Missing key or no keychain at all is fine."""
    from . import secret_backends
    secret_backends.wipe_data_keys()


class Cipher:
    def __init__(self, key: bytes | None = None) -> None:
        if key is None:
            key = _get_or_create_key()
        elif len(key) != 32:
            raise ValueError("Cipher key must be 32 bytes (AES-256)")
        self._aes = AESGCM(key)

    def encrypt(self, data: bytes, aad: bytes = b"") -> bytes:
        nonce = os.urandom(12)
        return _MAGIC + nonce + self._aes.encrypt(nonce, data, aad or None)

    def decrypt(self, blob: bytes, aad: bytes = b"") -> bytes:
        if blob[:2] != _MAGIC:
            raise ValueError("unknown ciphertext format")
        return self._aes.decrypt(blob[2:14], blob[14:], aad or None)

    # --- key check (store in DB meta to detect a wrong key before touching data) ---------

    def key_check(self) -> str:
        """Encrypted constant, base64 text, for storing in `meta`."""
        return base64.b64encode(self.encrypt(_KEY_CHECK_PLAINTEXT, _KEY_CHECK_AAD)).decode()

    def verify_key_check(self, value: str) -> bool:
        try:
            pt = self.decrypt(base64.b64decode(value), _KEY_CHECK_AAD)
        except (InvalidTag, ValueError):
            return False
        return pt == _KEY_CHECK_PLAINTEXT

    # --- files ----------------------------------------------------------------------------

    @staticmethod
    def _file_aad(path: Path) -> bytes:
        """AAD = path relative to FREEMYID_HOME/evidence (POSIX form), so it survives moving
        FREEMYID_HOME. Files outside the evidence dir are bound to their absolute path."""
        p = Path(os.path.abspath(path))
        base = Path(os.path.abspath(paths.home() / "evidence"))
        try:
            rel = p.relative_to(base).as_posix()
        except ValueError:
            rel = p.as_posix()
        return _FILE_AAD_PREFIX + rel.encode()

    def encrypt_file(self, src_bytes: bytes, dest: Path) -> str:
        """Write encrypted file; return sha256 of the plaintext."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.encrypt(src_bytes, aad=self._file_aad(dest)))
        dest.chmod(0o600)
        return hashlib.sha256(src_bytes).hexdigest()

    def decrypt_file(self, path: Path) -> bytes:
        return self.decrypt(path.read_bytes(), aad=self._file_aad(path))


# --- passphrase-based export (family installer pre-filled profiles) --------------------------

def export_with_passphrase(data: bytes, passphrase: str) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    salt = os.urandom(16)
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    nonce = os.urandom(12)
    return b"VP1" + salt + nonce + AESGCM(key).encrypt(nonce, data, b"freemyid-profile")


def import_with_passphrase(blob: bytes, passphrase: str) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    if blob[:3] != b"VP1":
        raise ValueError("not a Free My ID profile file")
    salt, nonce, ct = blob[3:19], blob[19:31], blob[31:]
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    return AESGCM(key).decrypt(nonce, ct, b"freemyid-profile")
