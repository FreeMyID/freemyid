#!/usr/bin/env python3
"""Publish gate (SEC-112): list every placeholder hash in distro/ and exit 1 if any.

Flags: SKIP in any checksum array (md5/sha1/sha224/sha256/sha384/sha512/b2/cksums,
arch-specific ones too, single-line or spread over several lines; PKGBUILD and
.SRCINFO), all-zero 64-hex values, REPLACE_WITH_* tokens, and any recipe that is
not valid UTF-8 (it can't be checked, so it fails). Release tooling MUST run this before any upstream
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
]
_SUMS = re.compile(r"^\s*(?:md5|sha1|sha224|sha256|sha384|sha512|b2|ck)sums(?:_\w+)?\s*=(.*)$")
_SKIP = re.compile(r"\bSKIP\b")


def _skip_lines(lines: list[str]) -> list[int]:
    """Line numbers with SKIP inside a checksum assignment, following a "(" array
    across continuation lines until its closing ")"."""
    hits, in_array = [], False
    for n, line in enumerate(lines, 1):
        if in_array:
            if _SKIP.search(line.split("#", 1)[0]):
                hits.append(n)
            if ")" in line:
                in_array = False
            continue
        m = _SUMS.match(line)
        if not m:
            continue
        rest = m.group(1)
        if _SKIP.search(rest.split("#", 1)[0]):
            hits.append(n)
        if rest.lstrip().startswith("(") and ")" not in rest:
            in_array = True
    return hits


def scan(root: Path) -> list[str]:
    found = []
    for f in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix != ".md"):
        rel = f.relative_to(root.parent)
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            found.append(f"{rel}: not valid UTF-8, cannot be checked")
            continue
        for n, line in enumerate(lines, 1):
            for rx, what in CHECKS:
                if rx.search(line):
                    found.append(f"{rel}:{n}: {what}")
        found += [f"{rel}:{n}: SKIP checksum" for n in _skip_lines(lines)]
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
