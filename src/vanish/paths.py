"""Filesystem locations. OWNER: orchestrator."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def home() -> Path:
    """~/.vanish (or %APPDATA%\\Vanish on Windows). Override with VANISH_HOME."""
    if env := os.environ.get("VANISH_HOME"):
        p = Path(env)
    elif sys.platform == "win32":
        p = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Vanish"
    else:
        p = Path.home() / ".vanish"
    created = not p.exists()
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = p / MARKER
    # Mark only folders Vanish created itself (or that already hold its database), so
    # `vanish wipe` can never mistake an arbitrary folder for Vanish's own (SEC-20).
    if not marker.exists() and (created or (p / "vanish.db").exists()):
        try:
            marker.write_text("This folder belongs to Vanish. `vanish wipe` deletes it.\n")
        except OSError:
            pass
    return p


MARKER = ".vanish-home"
# Every top-level entry Vanish may create in home(); `vanish wipe` deletes only these.
OWNED_ENTRIES = ("vanish.db", "vanish.db-wal", "vanish.db-shm", "evidence", "artifacts", "logs",
                 "config.yaml", "registry.yaml", "app-instance.json", "vanish-task.xml", MARKER)


def is_safe_wipe_target(p: Path) -> bool:
    """True only for a folder that is clearly Vanish's own and not a home/system root."""
    p = p.resolve()
    user_home = Path.home().resolve()
    if p == user_home or p in user_home.parents or p.parent == p or len(p.parts) <= 2:
        return False
    return (p / MARKER).exists() or (p / "vanish.db").exists()


def db_path() -> Path:
    return home() / "vanish.db"


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
        return Path(sys._MEIPASS) / "vanish" / "_data"  # type: ignore[attr-defined]
    return here.parent.parent  # repo root: brokers/, schema/
