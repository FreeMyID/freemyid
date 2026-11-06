"""First-run helper: install Playwright's Chromium only when no system Chrome/Edge exists.

Always asks first. Never runs during development or tests unless explicitly called.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
               "chrome", "msedge", "microsoft-edge"]
_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def system_browser() -> str | None:
    for n in _CANDIDATES:
        if p := shutil.which(n):
            return p
    return next((p for p in _PATHS if Path(p).exists()), None)


def browser_install_command() -> list[str]:
    return [sys.executable, "-m", "playwright", "install", "chromium"]


def ensure_browser(ask=input, run=subprocess.run) -> str:
    """Returns 'system', 'declined' or 'installed'. `ask`/`run` are injectable for tests."""
    if system_browser():
        return "system"
    ans = ask("Free My ID needs a web browser to fill in forms and none was found. Download a "
              "small extra browser just for Free My ID (about 150 MB)? [y/N] ").strip().lower()
    if not ans.startswith("y"):
        return "declined"
    run(browser_install_command(), check=True)
    return "installed"
