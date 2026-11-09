"""SEC-112 residual: distro/nix/flake.nix has a floating nixpkgs input and no flake.lock, and the
publish gate (tools/ci/check_distro_hashes.py) doesn't notice. Strict xfail: when the gate learns to
fail on a flake.nix without a flake.lock next to it, this XPASSes and the marker must come off.

Offline: builds a fake distro/ tree under tmp_path."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "ci" / "check_distro_hashes.py"
FLAKE = '{\n  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";\n  outputs = { self, nixpkgs }: { };\n}\n'


def _run(d: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(GATE), str(d)], capture_output=True, text=True, check=False)


@pytest.mark.xfail(strict=True, reason="SEC-112 residual (Dana): gate does not require distro/nix/flake.lock")
def test_gate_fails_on_flake_without_lock(tmp_path: Path) -> None:
    d = tmp_path / "distro" / "nix"
    d.mkdir(parents=True)
    (d / "flake.nix").write_text(FLAKE, encoding="utf-8")
    r = _run(tmp_path / "distro")
    assert r.returncode == 1
    assert "flake.lock" in r.stdout + r.stderr


def test_gate_passes_flake_with_lock(tmp_path: Path) -> None:
    """Guard for the future fix: a locked flake with no placeholders must still pass."""
    d = tmp_path / "distro" / "nix"
    d.mkdir(parents=True)
    (d / "flake.nix").write_text(FLAKE, encoding="utf-8")
    (d / "flake.lock").write_text('{"nodes": {}, "root": "root", "version": 7}\n', encoding="utf-8")
    assert _run(tmp_path / "distro").returncode == 0
