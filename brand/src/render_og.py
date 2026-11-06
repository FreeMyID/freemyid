"""Render brand/src/og-default.html to brand/social/og-default.png (1200x630)."""
import pathlib
from playwright.sync_api import sync_playwright
from PIL import Image
r = pathlib.Path(__file__).resolve().parents[1]
out = r / "social/og-default.png"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1200,"height":630})
    pg.goto((r/"src/og-default.html").as_uri()); pg.screenshot(path=str(out)); b.close()
Image.open(out).convert("RGB").quantize(64).save(out, optimize=True)
