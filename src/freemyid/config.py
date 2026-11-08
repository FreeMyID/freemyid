"""App config (non-PII) in FREEMYID_HOME/config.yaml. OWNER: orchestrator."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from . import paths


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    registry_url: str | None = None          # raw URL to registry.yaml in the user's GitHub repo
    registry_sha256_url: str | None = None   # optional: URL of a .sha256 file to pin content
    extra_allowed_hosts: list[str] = []      # e.g. playwright CDN if user approved download
    browser_channel: str | None = "msedge" if sys.platform == "win32" else "chrome"
    browser_automation: bool = True          # Automatic tier on/off (engine.tiers)
    headless: bool = True
    min_delay_s: float = 3.0
    max_delay_s: float = 12.0
    max_retries: int = 3
    user_agent_suffix: str = "FreeMyID/0.1 (personal privacy opt-out tool)"
    wizard_port: int = 8765
    real_submissions_enabled: bool = False   # flipped only after explicit user approval
    # Exposure scan: also search ONE previous address per broker (docs/EXPOSURE.md). Off.
    exposure_old_addresses: bool = False
    # Exposure scan: also search ONE previous name (e.g. maiden name) per broker. Off: searching
    # sends that name to people-search sites, so it is the person's explicit choice (opt-in).
    exposure_previous_names: bool = False
    # Where the data key and mailbox passwords live (secret_backends). None = auto: OS
    # keychain if usable, else passphrase. Change with `freemyid secrets migrate`.
    secrets_backend: Literal["keyring", "passphrase", "systemd-creds"] | None = None


class ConfigError(ValueError):
    """config.yaml can't be read. The message names the file and the bad fields, never
    the values."""


def load() -> Config:
    p = paths.config_path()
    if not p.exists():
        return Config()
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as e:
        raise ConfigError(
            f"{p} is damaged and can't be read. Fix it, or delete it to go back to the "
            "default settings"
        ) from e
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(f"{p} is damaged: expected 'name: value' settings")
    try:
        return Config.model_validate(data)
    except ValidationError as e:
        fields = sorted({".".join(str(x) for x in err["loc"]) or "?" for err in e.errors()})
        raise ConfigError(
            f"{p} has invalid settings: {', '.join(fields)}. Fix them, or delete the file "
            "to go back to the default settings"
        ) from e


def save(cfg: Config) -> None:
    """Atomic: a temp file in the same folder (0600 before it gets the real name), fsync,
    os.replace. A crash leaves the old or the new config, never a truncated one."""
    p = paths.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_dump(cfg.model_dump(), sort_keys=False).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=p.parent, prefix=".config.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, p)
    finally:
        tmp.unlink(missing_ok=True)
    if sys.platform != "win32":
        try:
            dfd = os.open(p.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(dfd)
        except OSError:
            pass
        finally:
            os.close(dfd)
