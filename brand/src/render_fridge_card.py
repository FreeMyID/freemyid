"""Render docs/assets/fridge-card.html to site_src/static/assets/free-my-id-fridge-card.pdf (Letter).
Run: .venv/bin/python brand/src/render_fridge_card.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright
R = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
    pg.goto((R / "docs/assets/fridge-card.html").as_uri())
    pg.pdf(path=str(R / "site_src/static/assets/free-my-id-fridge-card.pdf"), prefer_css_page_size=True, print_background=True)
    b.close()
