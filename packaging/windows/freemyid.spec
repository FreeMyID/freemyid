# PyInstaller spec for Windows (onedir). Build from the repository root:
#   pyinstaller packaging/windows/freemyid.spec --noconfirm --distpath dist --workpath build
# Output: dist/FreeMyID/ containing FreeMyID.exe (windowed) and freemyid-cli.exe (console).
#
# Playwright: the Python package and its small driver are bundled, but NOT the browsers.
# Free My ID drives the Microsoft Edge that every Windows 10/11 PC already has (channel="msedge"),
# so there is no browser download.
# ruff: noqa
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
ICON = str(Path(SPECPATH).resolve() / "freemyid.ico")
SRC = ROOT / "src" / "freemyid"

datas = [
    (str(SRC / "templates"), "freemyid/templates"),                  # letter templates
    (str(SRC / "wizard" / "static"), "freemyid/wizard/static"),      # css / js, no CDNs
    (str(ROOT / "schema"), "freemyid/_data/schema"),                 # json schemas
]
# Broker data. The public sample registry and state laws are always bundled. The full maintained
# registry (brokers/registry.yaml) is private: it is bundled ONLY when FMID_BUNDLE_FULL_REGISTRY=1
# (family/private builds), never just because the file happens to be on disk, and never in a
# GitHub Actions tag build (those become public Releases).
import os
BROKERS = ROOT / "brokers"
for _name in ("registry.sample.yaml", "state_laws.yaml", "LICENSE-DATA.md"):
    _f = BROKERS / _name
    if not _f.exists():
        raise SystemExit(f"missing required data file: {_f}")
    datas.append((str(_f), "freemyid/_data/brokers"))
_full = BROKERS / "registry.yaml"
if os.environ.get("FMID_BUNDLE_FULL_REGISTRY") == "1":
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_REF", "").startswith("refs/tags/"):
        raise SystemExit("refusing to bundle the private full registry into a public release build")
    if not _full.exists():
        raise SystemExit(f"FMID_BUNDLE_FULL_REGISTRY=1 but {_full} is missing")
    datas.append((str(_full), "freemyid/_data/brokers"))
    print("bundling FULL broker registry (private build)")
else:
    print("bundling SAMPLE broker registry only")
datas += collect_data_files("desktop_notifier")
datas += collect_data_files("jsonschema_specifications")

hiddenimports = (
    collect_submodules("freemyid")            # engine/submitters are imported lazily
    + collect_submodules("uvicorn")
    + collect_submodules("keyring.backends")
    + collect_submodules("webview")
    + collect_submodules("desktop_notifier")
    + ["multipart", "python_multipart", "win32timezone"]
)
excludes = ["tkinter", "matplotlib", "numpy", "pytest", "mypy", "weasyprint", "IPython"]


def analysis(script):
    return Analysis(
        [str(ROOT / "packaging" / "windows" / script)],
        pathex=[str(ROOT / "src")],
        datas=datas, hiddenimports=hiddenimports, excludes=excludes,
        noarchive=False,
    )


a_gui = analysis("launcher_gui.py")
a_cli = analysis("launcher_cli.py")

exe_gui = EXE(PYZ(a_gui.pure), a_gui.scripts, [], exclude_binaries=True, name="FreeMyID",
              console=False, icon=ICON, upx=False)
exe_cli = EXE(PYZ(a_cli.pure), a_cli.scripts, [], exclude_binaries=True, name="freemyid-cli",
              console=True, icon=ICON, upx=False)

coll = COLLECT(
    exe_gui, a_gui.binaries, a_gui.datas,
    exe_cli, a_cli.binaries, a_cli.datas,
    strip=False, upx=False, name="FreeMyID",
)
