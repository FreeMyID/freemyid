"""Render brand/src/repo-preview.html to brand/social/repo-preview.png (1280x640)."""
import pathlib
from playwright.sync_api import sync_playwright
from PIL import Image
r = pathlib.Path(__file__).resolve().parents[1]
out = r / "social/repo-preview.png"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1280,"height":640})
    pg.goto((r/"src/repo-preview.html").as_uri()); pg.screenshot(path=str(out)); b.close()
Image.open(out).convert("RGB").quantize(64).save(out, optimize=True)
