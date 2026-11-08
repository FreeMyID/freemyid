"""CR #63: the reproducible-build toolchain must install on any OS (pure-Python pins only);
twine and its binary dependencies live in a separate CI-only file that CI installs too."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "tools" / "ci"
# twine's dependencies that ship platform-specific wheels (the hashes would pin one OS)
BINARY = {"cffi", "cryptography", "nh3", "jeepney", "secretstorage", "charset-normalizer"}


def _pins(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.\-]+)==(\S+) --hash=sha256:[0-9a-f]{64}$", line)
        if m:
            out[m.group(1).lower().replace("_", "-")] = m.group(2)
        else:
            assert not line.strip() or line.startswith("#"), f"{path.name}: unpinned line {line!r}"
    return out


def test_build_toolchain_has_no_platform_wheels_or_twine() -> None:
    build = _pins(CI / "build-requirements.txt")
    assert {"build", "hatchling", "packaging"} <= set(build)
    assert not (set(build) & (BINARY | {"twine"}))


def test_twine_pins_are_separate_and_not_duplicated() -> None:
    build, twine = _pins(CI / "build-requirements.txt"), _pins(CI / "twine-requirements.txt")
    assert "twine" in twine and BINARY <= set(twine)
    assert not (set(build) & set(twine))


def test_ci_installs_both_files_wherever_twine_check_runs() -> None:
    both = ("--require-hashes -r tools/ci/build-requirements.txt "
            "-r tools/ci/twine-requirements.txt")
    for wf in ("build.yml", "pypi.yml"):
        text = (ROOT / ".github" / "workflows" / wf).read_text(encoding="utf-8")
        assert "twine check" in text and both in text, wf
