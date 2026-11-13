"""Filesystem locations. OWNER: orchestrator."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def home() -> Path:
    """~/.freemyid (or %APPDATA%\\Free My ID on Windows). Override with FREEMYID_HOME."""
    if env := os.environ.get("FREEMYID_HOME"):
        p = Path(env)
    elif sys.platform == "win32":
        p = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "FreeMyID"
    else:
        p = Path.home() / ".freemyid"
    created = not p.exists()
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = p / MARKER
    # Mark only folders Free My ID created itself (or that already hold its database), so
    # `freemyid wipe` can never mistake an arbitrary folder for Free My ID's own (SEC-20).
    if not marker.exists() and (created or (p / "freemyid.db").exists()):
        try:
            marker.write_text("This folder belongs to Free My ID. `freemyid wipe` deletes it.\n")
        except OSError:
            pass
    return p


MARKER = ".freemyid-home"
# Every top-level entry Free My ID may create in home(); `freemyid wipe` deletes only these.
OWNED_ENTRIES = ("freemyid.db", "freemyid.db-wal", "freemyid.db-shm", "evidence", "artifacts", "logs",
                 "config.yaml", "registry.yaml", "app-instance.json", "freemyid-task.xml", ".fill-confirmed",
                 "datakey.wrapped.json", "secrets.enc", "secrets.enc.lock", "migrate.pending",
                 # WO-612 search window: temp browser folders + the one-session lock. The
                 # person's encrypted cookies live in evidence/<id>/ (SEC-WO612-1).
                 "browser_profile", "browser_profile.lock",
                 # Browser extension link (docs/EXTENSION.md): pairing, PII-free status, inbox.
                 "extension", MARKER)


def is_safe_wipe_target(p: Path) -> bool:
    """True only for a folder that is clearly Free My ID's own and not a home/system root."""
    p = p.resolve()
    user_home = Path.home().resolve()
    if p == user_home or p in user_home.parents or p.parent == p or len(p.parts) <= 2:
        return False
    return (p / MARKER).exists() or (p / "freemyid.db").exists()


def db_path() -> Path:
    return home() / "freemyid.db"


def evidence_dir() -> Path:
    d = home() / "evidence"
    d.mkdir(exist_ok=True, mode=0o700)
    return d


def artifacts_dir() -> Path:
    """Generated letters / call scripts / reports (encrypted unless user exports)."""
    d = home() / "artifacts"
    d.mkdir(exist_ok=True, mode=0o700)
    return d


def logs_dir() -> Path:
    d = home() / "logs"
    d.mkdir(exist_ok=True, mode=0o700)
    return d


def extension_dir() -> Path:
    """Files shared with the browser extension's native host. PII-free by design: pairing
    records, a broker-id -> listing-state summary, removal requests and the bridge address."""
    d = home() / "extension"
    d.mkdir(exist_ok=True, mode=0o700)
    return d


def config_path() -> Path:
    return home() / "config.yaml"


def registry_cache_path() -> Path:
    return home() / "registry.yaml"


def bundled_data_dir() -> Path:
    """Registry/schema shipped with the package (wheel or PyInstaller) or repo checkout."""
    here = Path(__file__).resolve().parent
    if (here / "_data").exists():
        return here / "_data"
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "freemyid" / "_data"  # type: ignore[attr-defined]
    return here.parent.parent  # repo root: brokers/, schema/
