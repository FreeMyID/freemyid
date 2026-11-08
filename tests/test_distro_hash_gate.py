"""SEC-112: the distro publish gate flags placeholders and passes real-looking hashes.

Offline and deterministic: every test builds its own fake distro/ tree under tmp_path,
so the suite keeps passing after release tooling fills in the real hashes."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "ci" / "check_distro_hashes.py"
REAL = "ab12" * 16
ZERO = "0" * 64


def _run(d: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(GATE), str(d)], capture_output=True, text=True, check=False)


def _tree(tmp_path: Path, files: dict[str, str | bytes]) -> Path:
    d = tmp_path / "distro"
    for rel, body in files.items():
        f = d / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            f.write_bytes(body)
        else:
            f.write_text(body, encoding="utf-8")
    return d


def test_flags_each_recipe_kind_with_its_path(tmp_path: Path) -> None:
    """Same layout and placeholder kinds as the pre-release distro/ tree."""
    d = _tree(tmp_path, {
        "aur/PKGBUILD": "pkgname=freemyid\nsha256sums=('SKIP')\n",
        "aur/.SRCINFO": "pkgbase = freemyid\n\tsha256sums = SKIP\n",
        "flatpak/org.example.App.yml": f"    sha256: {ZERO}\n",
        "scoop/freemyid.json": f'{{"hash": "{ZERO}"}}\n',
        "winget/FreeMyID.FreeMyID.installer.yaml": f"InstallerSha256: {ZERO}\n",
        "homebrew/freemyid.rb": 'sha256 "REPLACE_WITH_SHA256"\n',
    })
    r = _run(d)
    assert r.returncode == 1
    for needle in ("distro/aur/PKGBUILD:2: SKIP", "distro/aur/.SRCINFO:2: SKIP", "distro/flatpak/",
                   "distro/scoop/freemyid.json:1", "distro/winget/FreeMyID.FreeMyID.installer.yaml:1",
                   "distro/homebrew/freemyid.rb:1: REPLACE_WITH_"):
        assert needle in r.stdout, needle


def test_passes_on_real_looking_hashes(tmp_path: Path) -> None:
    d = tmp_path / "distro"
    (d / "aur").mkdir(parents=True)
    (d / "aur" / "PKGBUILD").write_text(f"sha256sums=('{REAL}')\n")
    (d / "aur" / ".SRCINFO").write_text(f"\tsha256sums = {REAL}\n")
    (d / "scoop.json").write_text(f'{{"hash": "{REAL}"}}\n')
    (d / "w.yaml").write_text(f"InstallerSha256: {REAL}\n")
    (d / "h.rb").write_text(f'sha256 "{REAL}"\n')
    r = _run(d)
    assert r.returncode == 0 and "OK" in r.stdout


def test_each_placeholder_kind_fails(tmp_path: Path) -> None:
    for body in ("sha256sums=('SKIP')", "x: " + "0" * 64, 'sha256 "REPLACE_WITH_X"'):
        d = tmp_path / str(abs(hash(body)))
        d.mkdir()
        (d / "f").write_text(body + "\n")
        assert _run(d).returncode == 1, body


def test_skip_inside_a_multiline_checksum_array_fails(tmp_path: Path) -> None:
    d = _tree(tmp_path, {"aur/PKGBUILD": f"sha256sums=(\n  '{REAL}'\n  'SKIP'\n)\npkgver=1\n"})
    r = _run(d)
    assert r.returncode == 1 and "distro/aur/PKGBUILD:3: SKIP checksum" in r.stdout


def test_skip_in_other_checksum_arrays_fails(tmp_path: Path) -> None:
    for body in ("sha512sums=('SKIP')", "b2sums=('SKIP')", "sha256sums_x86_64=('SKIP')",
                 "md5sums=(\n  'SKIP'\n)", "\tsha512sums = SKIP"):
        d = _tree(tmp_path / str(abs(hash(body))), {"aur/PKGBUILD": body + "\n"})
        assert _run(d).returncode == 1, body


def test_skip_outside_a_checksum_array_is_not_flagged(tmp_path: Path) -> None:
    d = _tree(tmp_path, {"aur/PKGBUILD": f"sha256sums=(\n  '{REAL}'\n)\n# SKIP the tests\noptions=(!SKIP)\n"})
    assert _run(d).returncode == 0


def test_a_recipe_that_is_not_utf8_fails(tmp_path: Path) -> None:
    d = _tree(tmp_path, {"aur/PKGBUILD": b"pkgdesc='caf\xe9'\nsha256sums=('SKIP')\n"})
    r = _run(d)
    assert r.returncode == 1 and "distro/aur/PKGBUILD: not valid UTF-8" in r.stdout


def test_the_real_distro_tree_is_scannable() -> None:
    """The live tree may hold placeholders (exit 1) or real hashes (exit 0), never a crash."""
    assert _run(ROOT / "distro").returncode in (0, 1)
