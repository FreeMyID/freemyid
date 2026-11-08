"""WO-176: 'How it works in 3 steps' carousel, 5 slides 1080x1350 + PDF.
Screenshot crops come unaltered from brand/screenshots/app-v3 (fake persona). Run from brand/src."""
from wo17_common import *

OUT = BRAND / "social/carousel"
SHOTS = BRAND / "screenshots/app-v3"
SLIDES = [
    dict(n=1, head="How Free My ID works, in 3 steps.", body="Free, open source, and it runs on your own computer."),
    dict(n=2, step=1, head="Step 1. Tell it who to look for.", body="A name, and the city and state you live in.",
         shot=("01-wizard-name-light.png", 150, 560)),
    dict(n=3, step=2, head="Step 2. It asks the sites to take you down.",
         body="It uses each site's own removal process. If a site needs you to tick \"I'm not a robot\", it shows you a card and you do it.",
         shot=("03-today-light.png", 470, 300)),
    dict(n=4, step=3, head="Step 3. It keeps checking.", body="You see what is confirmed, what is waiting and what needs you.",
         shot=("04-broker-detail-light.png", 150, 380)),
    dict(n=5, head="No account. No cloud.",
         body="It never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime.",
         foot="freemyid.org"),
]


def shot_html(f, y0, h, top):
    s = 900 / 960  # crop x 160..1120 of the 1280 wide screenshot, scaled to 900 wide
    return (f'<div class=abs style="left:90px;top:{top}px;width:900px;height:{h}px;overflow:hidden;border-radius:18px;border:2px solid #b9c4d6;background:#fff">'
            f'<img src="{(SHOTS / f).as_uri()}" style="position:absolute;width:{1280*s:.1f}px;left:{-160*s - 2:.1f}px;top:{-y0*s - 2:.1f}px" alt=""></div>')


def slide(d):
    big = "step" not in d
    circle = ""
    if "step" in d:
        circle = (f'<div class=abs style="left:90px;top:140px;width:92px;height:92px;border-radius:50%;background:{NAVY};color:#fff;'
                  f'font-size:56px;font-weight:800;text-align:center;line-height:92px">{d["step"]}</div>')
    top = 270 if "step" in d else 300
    hs = 96 if big else 80
    foot = f'<p class=abs style="right:90px;bottom:90px;height:52px;line-height:52px;font-size:34px;font-weight:700;color:{NAVY}">{d["foot"]}</p>' if d.get("foot") else ""
    sh = shot_html(d["shot"][0], d["shot"][1], d["shot"][2], 1350 - 90 - 52 - 36 - d["shot"][2]) if "shot" in d else ""
    return f"""<body style="width:1080px;height:1350px;background:{'#ffffff' if d['n'] % 2 else OFFWHITE}">
<div class=abs style="left:90px;top:90px;width:120px;height:12px;background:{RED}"></div>
<p class=abs style="right:90px;top:70px;font-size:32px;font-weight:600;color:{MUTED}">{d['n']} of 5</p>
{circle}
<div class=abs style="left:90px;top:{top}px;width:900px"><h1 style="font-size:{hs}px;line-height:1.08;font-weight:800;letter-spacing:-1.3px;text-wrap:balance;color:{HEAD}">{d['head']}</h1>
<p style="margin-top:32px;font-size:40px;line-height:1.38;color:{MUTED}">{d['body']}</p></div>
{sh}{logo(52, "left:90px;bottom:90px")}{foot}</body>"""


if __name__ == "__main__":
    from PIL import Image
    files = []
    for d in SLIDES:
        f = OUT / f"cb03-carousel-{d['n']}-of-5-1080x1350.png"
        render(slide(d), f, 1080, 1350, colors=64)
        files.append(f)
    ims = [Image.open(f).convert("RGB") for f in files]
    pdf = OUT / "cb03-carousel-1080x1350.pdf"
    ims[0].save(pdf, save_all=True, append_images=ims[1:], resolution=100)
    print(pdf.name, pdf.stat().st_size // 1024, "KB")
