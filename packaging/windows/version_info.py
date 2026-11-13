"""Windows version resource (the "Details" tab) for the PyInstaller executables.

Honest, ordinary metadata only: who makes the program, what it is, which version, and the
licence. A program with no version resource looks anonymous to antivirus engines and to
people reading the file properties; this fills in the facts. It changes nothing at run time.

Used by freemyid.spec (render_version_file) and covered by tests/test_packaging_wo632.py.
"""
from __future__ import annotations

import re
from pathlib import Path

COMPANY = "Free My ID"
PRODUCT = "Free My ID"
COPYRIGHT = "Copyright (C) Free My ID contributors. Licensed AGPL-3.0-or-later."
HOMEPAGE = "https://freemyid.org"


def read_version(root: Path) -> str:
    """The package version, read from source so the spec needs no import of the app."""
    text = (root / "src" / "freemyid" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise SystemExit("cannot read __version__ from src/freemyid/__init__.py")
    return m.group(1)


def numeric_version(version: str) -> tuple[int, int, int, int]:
    """0.3.1 -> (0, 3, 1, 0). Pre-release suffixes such as rc1 are dropped from the number."""
    nums = [int(n) for n in re.findall(r"\d+", version.split("rc")[0].split("a")[0])[:4]]
    nums += [0] * (4 - len(nums))
    return (nums[0], nums[1], nums[2], nums[3])


def render_version_file(version: str, *, filename: str, description: str) -> str:
    """Text in the format PyInstaller's `version=` option reads (same as pyi-grab_version)."""
    nums = numeric_version(version)
    dotted = ".".join(str(n) for n in nums)
    strings = [
        ("CompanyName", COMPANY),
        ("FileDescription", description),
        ("FileVersion", dotted),
        ("InternalName", filename.rsplit(".", 1)[0]),
        ("LegalCopyright", COPYRIGHT),
        ("OriginalFilename", filename),
        ("ProductName", PRODUCT),
        ("ProductVersion", version),
        ("Comments", f"Runs on your own computer. {HOMEPAGE}"),
    ]
    body = ",\n        ".join(f"StringStruct({k!r}, {v!r})" for k, v in strings)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={nums!r},
    prodvers={nums!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        {body}
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
