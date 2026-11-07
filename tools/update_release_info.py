"""Write site_src/data/release.yaml from a published installer (used by CI after each v* release).

    python tools/update_release_info.py 0.1.2 path/to/FreeMyIDSetup.exe [--date 2026-11-07]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site_src/data/release.yaml"


def render(version: str, date: str, size: int, sha256: str) -> str:
    mb = size / 1_048_576
    return (
        "# Filled in automatically by .github/workflows/build.yml (site-release-info job) after each v* release,\n"
        "# from the published FreeMyIDSetup.exe. Leave values null until a release exists; the download page then\n"
        "# says so plainly.\n"
        f"# v{version}: https://github.com/FreeMyID/freemyid/releases/tag/v{version} (published {date}).\n"
        f'version: "{version}"\n'
        f"date: {date}\n"
        f"size_mb: {mb:.1f}        # {size:,} bytes = {mb:.1f} MB the way Windows File Explorer counts (1 MB = 1,048,576 bytes)\n"
        f"sha256: {sha256}\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("installer", type=Path)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", a.version):
        raise SystemExit(f"bad version {a.version!r}")
    data = a.installer.read_bytes()
    OUT.write_text(render(a.version, a.date, len(data), hashlib.sha256(data).hexdigest()), encoding="utf-8")
    print(f"release.yaml -> {a.version}, {len(data)} bytes")


if __name__ == "__main__":
    main()
