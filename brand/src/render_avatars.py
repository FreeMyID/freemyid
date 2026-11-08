"""Render brand/social/avatar/*: avatar PNGs, headers/covers, circle sheet, 32px check. Run: .venv/bin/python brand/src/render_avatars.py"""
import pathlib, io
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
r = pathlib.Path(__file__).resolve().parents[1]; d = r/"social/avatar"
svg = (d/"avatar.svg").read_text()
STAR = '<path d="M12 2l2.9 6.6 7.1.7-5.4 4.7 1.6 7L12 17.3 5.8 21l1.6-7L2 9.3l7.1-.7z" fill="#fff"/>'
def mark(h):  # star + red bar, height h px
    return f'<svg viewBox="0 0 20 23.2" height="{h}"><g transform="translate(-2 -2)">{STAR}</g><rect y="21.2" width="20" height="2" rx=".3" fill="#a3202e"/></svg>'
def banner(w, h, scale, name):
    u = h*scale
    return f'''<html><body style="margin:0;width:{w}px;height:{h}px;background:#1b2f5b;display:flex;align-items:center;justify-content:center;gap:{u*.12}px;font-family:Georgia,'DejaVu Serif',serif;color:#fff;overflow:hidden">
<div style="position:absolute;left:0;right:0;bottom:0;height:{h*.025}px;background:#a3202e"></div>
{mark(u*.62)}<div><div style="font-size:{u*.36}px;font-weight:bold;line-height:1">Free My ID</div>
<div style="font-size:{u*.115}px;margin-top:{u*.06}px;color:#c4d5f7;font-family:system-ui,'DejaVu Sans',sans-serif">Take your name off the websites that sell it.</div></div></body></html>'''
heads = {"mastodon-header":(1500,500,.8),"bluesky-banner":(3000,1000,.8),"x-header":(1500,500,.8),
 "facebook-cover":(1640,624,.5),"youtube-banner":(2560,1440,.38),"linkedin-banner":(1584,396,.8)}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1024,"height":1024})
    pg.set_content(f'<body style="margin:0">{svg}</body>'); pg.set_viewport_size({"width":1024,"height":1024})
    pg.evaluate("document.querySelector('svg').setAttribute('width',1024)")
    big = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    for n,(w,h,s) in heads.items():
        pg.set_viewport_size({"width":w,"height":h}); pg.set_content(banner(w,h,s,n))
        Image.open(io.BytesIO(pg.screenshot())).convert("RGB").quantize(64).save(d/f"{n}-{w}x{h}.png", optimize=True)
    b.close()
for s in (1024,512,400,256,200,128):
    big.resize((s,s), Image.LANCZOS).save(d/f"avatar-{s}.png", optimize=True)
big.resize((512,512), Image.LANCZOS).save(d/"gravatar-512.png", optimize=True)
big.resize((512,512), Image.LANCZOS).save(d/"discord-icon-512.png", optimize=True)
def circ(s, bg):
    im = big.resize((s,s), Image.LANCZOS); m = Image.new("L",(s*4,s*4),0)
    ImageDraw.Draw(m).ellipse((0,0,s*4-1,s*4-1),fill=255); m = m.resize((s,s), Image.LANCZOS)
    c = Image.new("RGB",(s,s),bg); c.paste(im,(0,0),m); return c
sheet = Image.new("RGB",(1400,520),"#ffffff"); dk = Image.new("RGB",(700,520),"#0f1520"); sheet.paste(dk,(700,0))
for bgx,bg in ((0,"#ffffff"),(700,"#0f1520")):
    x = bgx+30
    for s in (256,128,64,48,32):
        sheet.paste(circ(s,bg),(x,40)); x += s+24
    sheet.paste(big.resize((160,160)).convert("RGB"),(bgx+30,320))   # square (e.g. GitHub)
    sheet.paste(circ(160,bg),(bgx+230,320))
sheet.save(d/"circle-crop-preview.png", optimize=True)
chk = Image.new("RGB",(360,100),"#ffffff"); dd = ImageDraw.Draw(chk)
dd.rectangle((180,0,360,100),fill="#0f1520")
for i,s in enumerate((32,24,16)):
    for off in (0,180):
        chk.paste(circ(s,"#ffffff" if off==0 else "#0f1520"),(off+20+i*55,34))
chk = chk.resize((1080,300), Image.NEAREST); chk.save(d/"legibility-32px.png", optimize=True)
