"""SEC-112: the distro publish gate flags placeholders and passes real-looking hashes."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "ci" / "check_distro_hashes.py"
REAL = "ab12" * 16


def _run(d: Path):
    return subprocess.run([sys.executable, str(GATE), str(d)], capture_output=True, text=True, check=False)


def test_flags_todays_placeholders():
    r = _run(ROOT / "distro")
    assert r.returncode == 1
    for needle in ("aur/PKGBUILD", "aur/.SRCINFO", "flatpak/", "scoop/freemyid.json",
                   "winget/FreeMyID.FreeMyID.installer.yaml", "homebrew/freemyid.rb"):
        assert needle in r.stdout, needle


def test_passes_on_real_looking_hashes(tmp_path):
    d = tmp_path / "distro"
    (d / "aur").mkdir(parents=True)
    (d / "aur" / "PKGBUILD").write_text(f"sha256sums=('{REAL}')\n")
    (d / "aur" / ".SRCINFO").write_text(f"\tsha256sums = {REAL}\n")
    (d / "scoop.json").write_text(f'{{"hash": "{REAL}"}}\n')
    (d / "w.yaml").write_text(f"InstallerSha256: {REAL}\n")
    (d / "h.rb").write_text(f'sha256 "{REAL}"\n')
    r = _run(d)
    assert r.returncode == 0 and "OK" in r.stdout


def test_each_placeholder_kind_fails(tmp_path):
    for body in ("sha256sums=('SKIP')", "x: " + "0" * 64, 'sha256 "REPLACE_WITH_X"'):
        d = tmp_path / str(abs(hash(body)))
        d.mkdir()
        (d / "f").write_text(body + "\n")
        assert _run(d).returncode == 1, body
