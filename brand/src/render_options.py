"""Render brand/logo/options.html to brand/logo/options-preview.png."""
import pathlib
from playwright.sync_api import sync_playwright
r = pathlib.Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1164,"height":800})
    pg.goto((r/"logo/options.html").as_uri()); pg.screenshot(path=str(r/"logo/options-preview.png"), full_page=True); b.close()
