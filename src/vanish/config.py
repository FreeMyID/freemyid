"""App config (non-PII) in VANISH_HOME/config.yaml. OWNER: orchestrator."""
from __future__ import annotations

import yaml
from pydantic import BaseModel, ConfigDict

from . import paths


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    registry_url: str | None = None          # raw URL to registry.yaml in the user's GitHub repo
    registry_sha256_url: str | None = None   # optional: URL of a .sha256 file to pin content
    extra_allowed_hosts: list[str] = []      # e.g. playwright CDN if user approved download
    browser_channel: str | None = "chrome"   # use system Chrome/Edge first; None = bundled
    headless: bool = True
    min_delay_s: float = 3.0
    max_delay_s: float = 12.0
    max_retries: int = 3
    user_agent_suffix: str = "Vanish/0.1 (personal privacy opt-out tool)"
    wizard_port: int = 8765
    real_submissions_enabled: bool = False   # flipped only after explicit user approval


def load() -> Config:
    p = paths.config_path()
    if p.exists():
        return Config.model_validate(yaml.safe_load(p.read_text()) or {})
    return Config()


def save(cfg: Config) -> None:
    p = paths.config_path()
    p.write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False))
    p.chmod(0o600)
