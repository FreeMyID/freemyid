"""At-rest encryption. Key lives in the OS keychain or a passphrase wrap. OWNER: orchestrator.

Where the key lives is decided by `secret_backends` (keyring | passphrase | systemd-creds).

Field/blob-level AES-256-GCM. Ciphertext format: b"V1" + 12-byte nonce + ct||tag.
SQLCipher was considered; blob encryption avoids cross-platform native packaging issues.
Only ids, enums and timestamps are stored in clear; all PII is inside encrypted blobs.

Evidence files are bound (AAD) to their path relative to FREEMYID_HOME/evidence, so a file
cannot be swapped between profiles/brokers. Store a `key_check()` value in the DB `meta`
table on first use and `verify_key_check()` it on open to detect a wrong/lost key early.

Keychain entry names (WO-605): the default data folder keeps the legacy entry
``freemyid``/``db-key-v1`` (Windows installs depend on it; it is never moved). Any other
FREEMYID_HOME gets its own entry ``db-key-v1:<sha256(resolved folder)[:16]>``, so a new
folder never adopts another folder's key and wiping it can't delete another folder's key.
A non-default folder made before per-folder names keeps reading the shared legacy entry,
but only after the DB key_check proves that key is its own (``doctor`` warns; ``secrets
migrate --to keyring`` gives it its own entry). A folder whose DB holds data but whose key
is missing or wrong fails closed with `KeyMismatch`; a new key is never made over it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import sys
import unicodedata
from pathlib import Path
from typing import NamedTuple

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


KEY_RECOVERY_HELP = (
    "The encryption key for this data folder is missing or does not match the saved data, "
    "so Free My ID stopped without changing anything. Nothing was deleted, and no new key "
    "was made. To get your data back: if you saved a passphrase copy of the key ('freemyid "
    "secrets migrate --to passphrase' keeps it in datakey.wrapped.json in this folder), put "
    "that file back; if this folder was moved, move it back to where it was; or restore the "
    "whole folder from a backup. Ask for help before deleting anything."
)


class KeyMismatch(KeyUnavailable):
    """The folder's DB holds data, but no key we can reach opens it (WO-605). Fail closed:
    never create a new key over existing data."""

    def __init__(self, msg: str = KEY_RECOVERY_HELP) -> None:
        super().__init__(msg)


# --- which keychain entry belongs to this data folder (WO-605) --------------------------

def default_home() -> Path:
    """The platform default data folder: `paths.home()` without FREEMYID_HOME. Mirrors
    paths.home(); creates nothing."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "FreeMyID"
    return Path.home() / ".freemyid"


def _norm(p: Path) -> str:
    """The resolved folder path in one canonical form. Windows: `normcase` (case and `/`).
    macOS: APFS and HFS+ are case-insensitive by default, so the path is also NFC-normalised
    and case-folded, giving one folder one name however it is typed. Linux paths are taken
    as they are (case-sensitive)."""
    s = os.path.normcase(str(Path(os.path.abspath(p)).resolve()))
    if sys.platform == "darwin":
        s = unicodedata.normalize("NFC", s).casefold()
    return s


def is_default_home(home: Path | None = None) -> bool:
    return _norm(home if home is not None else paths.home()) == _norm(default_home())


def folder_key_name(home: Path | None = None) -> str:
    """The keychain entry name this data folder owns: the legacy `db-key-v1` for the
    default folder, `db-key-v1:<16 hex>` (hash of the resolved path) for any other."""
    h = home if home is not None else paths.home()
    if is_default_home(h):
        return KEY_NAME
    return f"{KEY_NAME}:{hashlib.sha256(_norm(h).encode()).hexdigest()[:16]}"


DB_UNREADABLE_HELP = (
    "Free My ID couldn't read its saved data just now (another Free My ID window may be "
    "busy with it, or the file may be damaged), so it stopped without changing anything. "
    "Close other Free My ID windows and try again later."
)


class DbState(NamedTuple):
    """What the data folder's DB shows without a key (WO-605 review F2)."""
    readable: bool          # False: the file exists but sqlite couldn't read it
    has_data: bool          # a key_check value or a saved person: never make a new key
    key_check: str | None


def db_state(db: Path | None = None) -> DbState:
    """Read a data folder's DB with sqlite in ro mode (no key). An unreadable DB is reported
    as such, never as "has data, no key_check": that case alone may use an unproven key."""
    db = db if db is not None else paths.db_path()
    if not db.exists():
        return DbState(True, False, None)
    import sqlite3
    try:
        con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "meta" in tables:
                row = con.execute("SELECT v FROM meta WHERE k='key_check'").fetchone()
                if row is not None:
                    return DbState(True, True, str(row[0]))
            if "profiles" in tables and con.execute(
                    "SELECT 1 FROM profiles LIMIT 1").fetchone() is not None:
                return DbState(True, True, None)
        finally:
            con.close()
    except sqlite3.Error:
        return DbState(False, True, None)
    return DbState(True, False, None)


def db_key_check(db: Path | None = None, *, strict: bool = True) -> tuple[bool, str | None]:
    """(has_data, key_check) of a data folder's DB, read with sqlite in ro mode (no key).

    has_data is True when the DB holds a key_check value or a saved person, i.e. a new key
    must never be made for it. A DB that exists but can't be read raises `KeyUnavailable`
    (try again later); with strict=False (wipe) it counts as holding data (fail closed)."""
    st = db_state(db)
    if not st.readable:
        if strict:
            raise KeyUnavailable(DB_UNREADABLE_HELP)
        return True, None
    return st.has_data, st.key_check


def _opens(key: bytes, key_check: str) -> bool:
    return Cipher(key).verify_key_check(key_check)


def _decode_or_none(stored: str | None) -> bytes | None:
    if stored is None:
        return None
    try:
        return _decode_key(stored)
    except KeyUnavailable:
        return None


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
    """Test key (pytest only), else the selected secrets backend (secret_backends.select).
    A key that doesn't open this folder's DB is refused here, before any data is touched."""
    if (tk := _test_key()) is not None:
        return tk
    from . import secret_backends
    key = secret_backends.select().load_data_key()
    _, kc = db_key_check()
    if kc is not None and not _opens(key, kc):
        raise KeyMismatch()
    return key


def _keyring_shared_legacy_key(key_check: str | None) -> bytes | None:
    """For a non-default folder made before per-folder names: the shared legacy entry's
    key, but only when this folder's DB key_check proves it is this folder's key, or the DB
    was read and holds saved people but is too old to have a key_check (Store then proves
    the key by decrypting before it writes one). Callers get `key_check` from a strict
    `db_key_check`, so an unreadable DB never gets here (WO-605 review F2)."""
    legacy = _decode_or_none(keyring.get_password(SERVICE, KEY_NAME))
    if legacy is None:
        return None
    if key_check is None or _opens(legacy, key_check):
        return legacy
    return None


def _copy_shared_to_own_entry(name: str, key: bytes) -> bool:
    """WO-605 review F1: copy the proven shared legacy key into this folder's own (absent)
    entry and read it back, so wiping the default folder can't lock this folder. The shared
    entry is never changed or deleted. A failed copy is logged; the caller still uses the
    proven shared key and `doctor` keeps warning. True if the copy was confirmed."""
    try:
        keyring.set_password(SERVICE, name, base64.b64encode(key).decode())
        back = _decode_or_none(keyring.get_password(SERVICE, name))
    except keyring.errors.KeyringError:
        log.warning("keychain: could not give this data folder its own key entry; "
                    "still using the shared entry")
        return False
    if back is None or not hmac.compare_digest(back, key):
        log.warning("keychain: this data folder's own key entry did not read back; "
                    "still using the shared entry")
        return False
    log.info("keychain: this data folder now has its own key entry (the shared one is kept)")
    return True


def _keyring_get_or_create_key(create: bool = True) -> bytes:
    """The OS keychain path (default backend). Reads this folder's own entry (see
    `folder_key_name`). Creates a key only for a folder with no saved data, and never
    adopts another folder's entry (WO-605). A DB that can't be read raises
    `KeyUnavailable` (try again later) before any key is chosen."""
    try:
        _check_backend()
        name = folder_key_name()
        has_data, kc = db_key_check()
        stored = keyring.get_password(SERVICE, name)
        if stored is not None:
            key = _decode_key(stored)
            if kc is None or _opens(key, kc):
                return key
        if has_data:
            # No own key that opens the data. A non-default folder made before per-folder
            # names may still be on the shared legacy entry (proven by key_check).
            if name != KEY_NAME and (legacy := _keyring_shared_legacy_key(kc)) is not None:
                if stored is None and kc is not None:   # proven, and nothing to overwrite
                    _copy_shared_to_own_entry(name, legacy)
                return legacy
            raise KeyMismatch()   # never a new key over saved data
        if not create:
            raise KeyUnavailable("no data key in the OS keychain")
        key = AESGCM.generate_key(bit_length=256)
        keyring.set_password(SERVICE, name, base64.b64encode(key).decode())
        # Re-read: if another process won a first-run race, use its key, not ours.
        stored = keyring.get_password(SERVICE, name)
        if stored is None:
            raise KeyUnavailable("keychain did not persist the key")
        return _decode_key(stored)
    except keyring.errors.KeyringError as e:
        raise KeyUnavailable(str(e)) from e


def delete_key() -> None:
    """Remove this folder's data key from every backend (used by `freemyid wipe`): the
    passphrase-wrapped key file, and this folder's own keychain entry (WO-605). The shared
    legacy entry goes only when wiping the default folder and it is provably that folder's
    key (SEC-72). Missing key or no keychain at all is fine."""
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
    from cryptography.exceptions import InvalidTag

    salt, nonce, ct = blob[3:19], blob[19:31], blob[31:]
    if len(ct) < 16:  # shorter than the GCM tag: truncated before we spend time on scrypt
        raise ValueError("wrong passphrase, or the file is damaged")
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    try:
        return AESGCM(key).decrypt(nonce, ct, b"freemyid-profile")
    except InvalidTag:  # wrong passphrase, truncated or tampered: one calm error for all three
        raise ValueError("wrong passphrase, or the file is damaged") from None
