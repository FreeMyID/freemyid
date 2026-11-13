"""WO-632: the Windows build carries honest metadata and a from-source bootloader (text checks)."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIN = ROOT / "packaging" / "windows"


def _version_info():
    spec = importlib.util.spec_from_file_location("version_info", WIN / "version_info.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_numeric_version_handles_release_candidates():
    vi = _version_info()
    assert vi.numeric_version("0.3.1") == (0, 3, 1, 0)
    assert vi.numeric_version("0.3.0rc1") == (0, 3, 0, 0)
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert vi.read_version(ROOT) == re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)


def test_version_resource_has_company_product_description_version():
    vi = _version_info()
    text = vi.render_version_file("0.3.1", filename="FreeMyID.exe", description="Free My ID")
    for key in ("CompanyName", "FileDescription", "FileVersion", "ProductName", "ProductVersion",
                "LegalCopyright", "OriginalFilename"):
        assert f"StringStruct('{key}'," in text
    assert "filevers=(0, 3, 1, 0)" in text
    assert text.count("(") == text.count(")")


def test_spec_uses_version_resource_and_no_packer():
    spec = (WIN / "freemyid.spec").read_text()
    assert spec.count("version=str(") == 2
    assert "upx=True" not in spec
    assert "a_gui.binaries, a_gui.datas" in spec  # onedir COLLECT, not onefile


def test_installer_script_has_version_info():
    iss = (WIN / "freemyid.iss").read_text()
    for key in ("VersionInfoVersion", "VersionInfoCompany", "VersionInfoDescription",
                "VersionInfoProductName", "AppPublisherURL"):
        assert key in iss


def test_workflow_builds_bootloader_from_source():
    wf = (ROOT / ".github" / "workflows" / "build.yml").read_text()
    assert "--no-binary pyinstaller" in wf
    assert re.search(r'PYINSTALLER_VERSION: "\d+\.\d+\.\d+"', wf)
    assert "AppVersionNumeric" in wf
