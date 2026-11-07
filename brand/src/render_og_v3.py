"""Render v3 OG images (1200x630) to brand/v3/og/. Run: .venv/bin/python brand/src/render_og_v3.py"""
import pathlib
from playwright.sync_api import sync_playwright
from PIL import Image
r = pathlib.Path(__file__).resolve().parents[1]; v3 = r / "v3"
mark = (r / "logo/final/mark.svg").read_text()
PAGES = {
 "og-home": ("hero.svg", "Take your name off the websites that sell it.", "A free Windows app that asks people-search sites to remove your listing. Runs on your computer. Nothing is sent to us."),
 "og-download": ("sections/step-install.svg", "Download Free&nbsp;My&nbsp;ID for Windows", "Free. No account. Nothing leaves your computer. Uninstall anytime."),
}
def page(img, h, sub):
    svg = (v3 / img).read_text()
    return f'''<!doctype html><meta charset=utf-8><style>*{{box-sizing:border-box}}body{{margin:0;width:1200px;height:630px;background:#f4f6f9;font-family:system-ui,"Segoe UI",Arial,sans-serif;color:#151b26;position:relative;overflow:hidden}}
.bar{{position:absolute;left:0;right:0;top:0;height:14px;background:linear-gradient(#1b2f5b 0 8px,#a3202e 8px)}}
.t{{position:absolute;left:72px;top:78px;width:540px}}.lg{{display:flex;align-items:center;gap:14px;font-weight:700;font-size:30px;color:#14264a;margin-bottom:44px}}.lg svg{{width:52px;height:52px}}
h1{{font-size:54px;line-height:1.08;margin:0 0 26px;color:#14264a;letter-spacing:-.5px}}p{{font-size:28px;line-height:1.4;margin:0;color:#414b5c}}
.i{{position:absolute;right:24px;top:110px;width:{ 530 if "hero" in img else 500}px}}.i svg{{width:100%;height:auto;display:block}}
.u{{position:absolute;left:72px;bottom:42px;font-size:24px;color:#17488f;font-weight:600}}</style>
<div class=bar></div><div class=t><div class=lg>{mark}Free My ID</div><h1>{h}</h1><p>{sub}</p></div><div class=i>{svg}</div>'''
(v3 / "og").mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    for name, (img, h, sub) in PAGES.items():
        f = r / f"src/_{name}.html"; f.write_text(page(img, h, sub)); pg.goto(f.as_uri())
        out = v3 / f"og/{name}.png"; pg.screenshot(path=str(out)); f.unlink()
        Image.open(out).convert("RGB").quantize(96, dither=Image.Dither.NONE).save(out, optimize=True); print(name, out.stat().st_size)
    b.close()
