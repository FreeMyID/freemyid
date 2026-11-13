"""Deprecated: use tools/import_registries.py (multi-source). Kept so old notes still work.

    .venv/bin/python tools/import_ca_registry.py path/to/registry.csv  ==  import_registries.py
    --ca path/to/registry.csv --write
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "import_registries", Path(__file__).with_name("import_registries.py"))
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["import_registries"] = _mod
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    raise SystemExit(_mod.main(["--dir", "/nonexistent", "--ca", sys.argv[1], "--write"]))
