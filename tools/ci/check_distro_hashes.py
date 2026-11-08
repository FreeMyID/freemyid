#!/usr/bin/env python3
"""Publish gate (SEC-112): list every placeholder hash in distro/ and exit 1 if any.

Flags: SKIP in sha256sums (PKGBUILD, .SRCINFO), all-zero 64-hex values, and
REPLACE_WITH_* tokens. Release tooling MUST run this before any upstream
submission. Normal CI does not run it (placeholders are expected until release day).
Usage: check_distro_hashes.py [distro_dir]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CHECKS = [
    (re.compile(r"\b0{64}\b"), "all-zero sha256"),
    (re.compile(r"REPLACE_WITH_\w*"), "REPLACE_WITH_ token"),
    (re.compile(r"^\s*sha256sums\s*=\s*\(?.*['\"]?\bSKIP\b"), "SKIP checksum"),
]


def scan(root: Path) -> list[str]:
    found = []
    for f in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix != ".md"):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(lines, 1):
            for rx, what in CHECKS:
                if rx.search(line):
                    found.append(f"{f.relative_to(root.parent)}:{n}: {what}")
    return found


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[2] / "distro"
    if not root.is_dir():
        print(f"check_distro_hashes: {root} is not a directory", file=sys.stderr)
        return 2
    found = scan(root)
    for line in found:
        print(line)
    if found:
        print(f"{len(found)} placeholder hash(es): do NOT publish upstream.", file=sys.stderr)
        return 1
    print("distro hashes OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
