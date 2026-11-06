# PyInstaller spec for Windows (onedir). Build from the repository root:
#   pyinstaller packaging/windows/vanish.spec --noconfirm --distpath dist --workpath build
# Output: dist/Vanish/ containing Vanish.exe (windowed) and vanish-cli.exe (console).
#
# Playwright: the Python package and its small driver are bundled, but NOT the browsers.
# Vanish drives the Microsoft Edge that every Windows 10/11 PC already has (channel="msedge"),
# so there is no browser download.
# ruff: noqa
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
SRC = ROOT / "src" / "vanish"

datas = [
    (str(SRC / "templates"), "vanish/templates"),                  # letter templates
    (str(SRC / "wizard" / "static"), "vanish/wizard/static"),      # css / js, no CDNs
    (str(ROOT / "brokers"), "vanish/_data/brokers"),               # registry + state laws
    (str(ROOT / "schema"), "vanish/_data/schema"),                 # json schemas
]
datas += collect_data_files("desktop_notifier")
datas += collect_data_files("jsonschema_specifications")

hiddenimports = (
    collect_submodules("vanish")            # engine/submitters are imported lazily
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

exe_gui = EXE(PYZ(a_gui.pure), a_gui.scripts, [], exclude_binaries=True, name="Vanish",
              console=False, icon=None, upx=False)
exe_cli = EXE(PYZ(a_cli.pure), a_cli.scripts, [], exclude_binaries=True, name="vanish-cli",
              console=True, icon=None, upx=False)

coll = COLLECT(
    exe_gui, a_gui.binaries, a_gui.datas,
    exe_cli, a_cli.binaries, a_cli.datas,
    strip=False, upx=False, name="Vanish",
)
