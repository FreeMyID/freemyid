"""WO-177: 'What we never ask for' trust card, 1080x1080 and 1080x1350.
Copy override (Morgan): the /safety/ master list, never the bare phrase 'email password'.
Run from brand/src."""
from wo17_common import *

OUT = BRAND / "social/posts"
ITEMS = ["Your Social Security number", "Your bank or card details", "A payment of any kind",
         "Your full birthday", "The password to your everyday email"]
HEAD_TXT = "Free My ID will never ask for:"
CLOSER = "If something says it is us and asks, it isn't. Stop and ask someone you trust."


def page(h):
    big = h == 1350
    row, gap, fs = (100, 48, 42) if big else (76, 26, 42)
    dot = 56 if big else 48
    items = "".join(
        f'<li style="display:flex;align-items:center;gap:26px;height:{row}px;font-size:{fs}px;font-weight:600;color:{TEXT};'
        f'border-top:2px solid #dbe1ea"><span style="flex:none;width:{dot}px;height:{dot}px;border-radius:50%;background:{NAVY};display:flex;align-items:center;justify-content:center">'
        f'<span style="width:{dot*.46:.0f}px;height:{dot*.09:.0f}px;border-radius:3px;background:#fff"></span></span>{t}</li>' for t in ITEMS)
    return f"""<body style="width:1080px;height:{h}px;background:#ffffff">
<div class=abs style="left:90px;top:90px;width:120px;height:12px;background:{NAVY}"></div>
<div class=abs style="left:90px;top:{ 126 if not big else 140 }px;width:900px;display:flex;flex-direction:column;gap:{gap}px">
  <h1 style="font-size:{84 if big else 80}px;line-height:1.08;font-weight:800;letter-spacing:-1.2px;color:{HEAD}">{HEAD_TXT}</h1>
  <ul style="list-style:none;padding:0;border-bottom:2px solid #dbe1ea">{items}</ul>
  <p style="font-size:{44 if big else 40}px;line-height:1.35;color:{MUTED}">{CLOSER}</p>
</div>
{logo(52, "left:90px;bottom:90px")}
<p class=abs style="right:90px;bottom:90px;height:52px;line-height:52px;font-size:34px;font-weight:700;color:{NAVY}">freemyid.org</p>
</body>"""


for label, h in {"1080x1080": 1080, "1080x1350": 1350}.items():
    render(page(h), OUT / f"cb04-never-ask-{label}.png", 1080, h, colors=64)
