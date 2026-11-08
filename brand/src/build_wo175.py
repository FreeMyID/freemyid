"""WO-175: Facebook/Instagram post set (4 templates x 1080x1080 and 1080x1350).
Run from brand/src: .venv python build_wo175.py"""
from wo17_common import *

OUT = BRAND / "social/posts"
SIZES = {"1080x1080": 1080, "1080x1350": 1350}
FOOT = "Free and open source. freemyid.org"
POSTS = {
    "a-wrong-place": ("#ffffff", "magnifier", "That post went to the wrong place.",
        "The sites that list your name, address and phone number are people-search sites. Free My ID asks them to take your details down.", FOOT),
    "b-scope": (OFFWHITE, None, "It takes your name off people-search sites.",
        "It does not change what Facebook does with your account.", FOOT),
    "c-keeps-checking": ("#ffffff", "check", "It keeps checking.",
        "Sites sometimes list people again, which is why Free My ID keeps checking.", FOOT),
    "d-download": (OFFWHITE, None, "Free for Windows 10 and 11.",
        "No account. No cloud. Runs on your own computer.", "Download at freemyid.org"),
}
ICONS = {  # 24-grid line icons, 2px stroke scaled 3x (6px at 72px), navy
    "magnifier": '<circle cx="10" cy="10" r="6.5"/><path d="M15 15l6 6"/>',
    "check": '<path d="M4.5 12.5l5 5L19.5 7"/>',
}


def tile(icon):
    if not icon:
        return ""
    return (f'<div class=abs style="right:90px;top:0;width:96px;height:96px;border-radius:22px;background:{SOFT}">'
            f'<svg viewBox="0 0 24 24" width=96 height=96 fill=none stroke="{NAVY}" stroke-width=2.2 stroke-linecap=round stroke-linejoin=round>'
            f'<g transform="translate(4.8 4.8) scale(.6)">{ICONS[icon]}</g></svg></div>')


def page(h, bg, icon, head, body, foot):
    off = (h - 1080) // 2  # keep all content inside the middle 1080x1080
    return f"""<body style="width:1080px;height:{h}px;background:{bg}"><div class=flag style="display:none"></div>
<div class=abs style="left:0;top:{off}px;width:1080px;height:1080px">
  <div class=abs style="left:90px;top:90px;width:120px;height:12px;background:{RED}"></div>
  {tile(icon).replace('top:0', 'top:90px')}
  <div class=abs style="left:90px;top:210px;width:900px"><h1 style="font-size:88px;line-height:1.08;font-weight:800;letter-spacing:-1.5px;color:{HEAD}">{head}</h1>
  <p style="margin-top:44px;font-size:42px;line-height:1.38;color:{MUTED}">{body}</p></div>
  {logo(52, "left:90px;bottom:90px")}
  <p class=abs style="right:90px;bottom:90px;height:52px;line-height:52px;font-size:32px;font-weight:700;color:{NAVY}">{foot}</p>
</div></body>"""


for key, (bg, icon, head, body, foot) in POSTS.items():
    for label, h in SIZES.items():
        html = page(h, bg, icon, head, body, foot)
        render(html, OUT / f"cb01-{key}-{label}.png", 1080, h, colors=32)
