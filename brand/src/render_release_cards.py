"""Render brand/social/release-0.2/* release cards. Run: .venv/bin/python brand/src/render_release_cards.py"""
import pathlib, io
from playwright.sync_api import sync_playwright
from PIL import Image
d = pathlib.Path(__file__).resolve().parents[1]/"social/release-0.2"
STAR = '<path d="M12 2l2.9 6.6 7.1.7-5.4 4.7 1.6 7L12 17.3 5.8 21l1.6-7L2 9.3l7.1-.7z" fill="#fff"/>'
def mark(h):
    return f'<svg viewBox="0 0 20 23.2" height="{h}"><g transform="translate(-2 -2)">{STAR}</g><rect y="21.2" width="20" height="2" rx=".3" fill="#a3202e"/></svg>'
def card(w, h, sq):
    u = min(w, h)
    big = u*(.085 if sq else .115)
    sub = u*(.046 if sq else .066)
    pad = u*.08
    return f'''<html><body style="margin:0;width:{w}px;height:{h}px;background:#1b2f5b;color:#fff;overflow:hidden;position:relative;font-family:system-ui,'DejaVu Sans',sans-serif">
<div style="position:absolute;left:0;right:0;bottom:0;height:{h*.03}px;background:#a3202e"></div>
<div style="position:absolute;left:{pad}px;right:{pad}px;top:{pad*.9}px;bottom:{pad*1.2}px;display:flex;flex-direction:column;justify-content:{'center' if sq else 'space-between'};gap:{u*.04 if sq else 0}px">
<div style="display:flex;align-items:center;gap:{u*.03}px">{mark(u*.13)}<div style="font:bold {u*.075}px Georgia,'DejaVu Serif',serif">Free My ID</div></div>
<div><div style="font:bold {big}px Georgia,'DejaVu Serif',serif;line-height:1.1">Version 0.2 is here</div>
<div style="font-size:{sub*1.15}px;line-height:1.3;margin-top:{u*.025}px;color:#fff">Now for Windows, Mac and Linux.</div></div>
<div style="font-size:{sub*.8}px;line-height:1.35;color:#d6e2fa">The Windows app is unchanged. Mac and Linux use the command line, with scheduled runs that need no one at the keyboard.</div>
<div style="font-size:{sub*.9}px;font-weight:bold;color:#fff">freemyid.org &nbsp;·&nbsp; free and open source</div>
</div></body></html>'''
sizes = {"release-0.2-x-bluesky-1200x675":(1200,675,False),"release-0.2-square-1080x1080":(1080,1080,True),"release-0.2-github-1280x640":(1280,640,False)}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for n,(w,h,sq) in sizes.items():
        pg.set_viewport_size({"width":w,"height":h}); pg.set_content(card(w,h,sq))
        Image.open(io.BytesIO(pg.screenshot())).convert("RGB").quantize(64).save(d/f"{n}.png", optimize=True)
    b.close()
