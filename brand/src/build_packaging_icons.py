"""Packaging icon set for Homebrew/Flatpak/winget/AUR, copied/derived from brand/icons/platforms.
Run: .venv/bin/python brand/src/build_packaging_icons.py"""
import shutil
from pathlib import Path
from PIL import Image
B = Path(__file__).resolve().parent.parent
src, out = B / "icons/platforms", B / "icons/packaging"
out.mkdir(parents=True, exist_ok=True)
shutil.copy(src / "hicolor/scalable/apps/freemyid.svg", out / "freemyid.svg")
big = Image.open(src / "freemyid-macos-1024.png").convert("RGBA")
for n in (16, 32, 48, 64, 128, 256, 512):
    Image.open(src / f"hicolor/{n}x{n}/apps/freemyid.png").save(out / f"freemyid-{n}.png", optimize=True)
big.save(out / "freemyid-1024.png", optimize=True)
Image.open(src / "hicolor/512x512/apps/freemyid.png").convert("RGBA").save(
    out / "freemyid.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
