"""Built wheel must carry the sample registry only, never the full one.

Builds with `python -m build` when available (skipped otherwise, e.g. no `build` module).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> Path:
    if importlib.util.find_spec("build") is None:
        pytest.skip("`build` is not installed")
    out = tmp_path_factory.mktemp("dist")
    r = subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
                       capture_output=True, text=True, timeout=300, check=False)
    if r.returncode != 0:
        pytest.skip("wheel build unavailable offline: " + r.stderr[-200:])
    return next(out.glob("*.whl"))


def test_wheel_has_sample_not_full_registry(wheel):
    names = zipfile.ZipFile(wheel).namelist()
    assert "freemyid/_data/brokers/registry.sample.yaml" in names
    assert not [n for n in names if n.endswith("brokers/registry.yaml")]
    assert not any(n.startswith(("zzz_legacy", "docs/")) for n in names)


def test_wheel_has_templates_static_entrypoint(wheel):
    z = zipfile.ZipFile(wheel)
    names = z.namelist()
    assert "freemyid/templates/ccpa.txt.j2" in names
    assert "freemyid/wizard/static/app.js" in names
    ep = next(n for n in names if n.endswith("entry_points.txt"))
    assert "freemyid = freemyid.cli:app" in z.read(ep).decode()
    meta = z.read(next(n for n in names if n.endswith("METADATA"))).decode()
    assert "License-Expression: AGPL-3.0-or-later" in meta
