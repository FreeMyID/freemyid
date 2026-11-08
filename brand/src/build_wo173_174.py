"""WO-173 (help-a-parent OG) and WO-174 (credit freeze OG), 1200x630. Run from brand/src.
Flat shapes only: no people, no faces, no bureau logos (bureau names are plain text)."""
from wo17_common import *

OUT = BRAND / "social/og"


def frame(bg, head, sub, art, hsize=66, hw=700):
    return f"""<body style="width:1200px;height:630px;background:{bg}">
<div class=flag></div>
{logo(40, "left:60px;top:58px")}
<div class=abs style="left:60px;top:140px;width:{hw}px"><h1 style="font-size:{hsize}px;line-height:1.1;font-weight:800;letter-spacing:-.8px;color:{HEAD}">{head}</h1>
<p style="margin-top:26px;font-size:32px;line-height:1.3;color:{MUTED}">{sub}</p></div>
<p class=abs style="left:60px;bottom:60px;font-size:28px;font-weight:700;color:{NAVY}">freemyid.org</p>
{art}</body>"""


def bars(x, y, ws, fill="#cfd5df"):
    return "".join(f'<rect x="{x}" y="{y + k * 26}" width="{w}" height="12" rx="6" fill="{fill}"/>' for k, w in enumerate(ws))


# WO-173: two simple overlapping rounded cards (no faces), calm
parent_art = f"""<svg class=abs style="right:50px;top:150px" width=330 height=330 viewBox="0 0 330 330">
<g transform="rotate(-7 130 160)"><rect x="20" y="40" width="210" height="240" rx="22" fill="{SOFT}" stroke="{NAVY}" stroke-width="4"/>{bars(46, 70, (120, 90, 110))}</g>
<rect x="100" y="70" width="210" height="240" rx="22" fill="#ffffff" stroke="{NAVY}" stroke-width="4"/>
<circle cx="150" cy="130" r="26" fill="{NAVY}"/><path d="M137 130l9 9 17-19" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
{bars(130, 190, (140, 110, 130))}</svg>"""

# WO-174: flat checklist card, three bureau names as plain text, navy boxes + green ticks
rows = "".join(
    f'<rect x="30" y="{34 + k * 82}" width="46" height="46" rx="10" fill="#fff" stroke="{NAVY}" stroke-width="5"/>'
    f'<path d="M41 {58 + k * 82}l9 9 16-18" fill="none" stroke="{GREEN}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
    f'<text x="100" y="{67 + k * 82}" font-family="{SANS.replace(chr(39), chr(34))}" font-weight="700" font-size="34" fill="{HEAD}">{n}</text>'
    for k, n in enumerate(("Equifax", "Experian", "TransUnion")))
freeze_art = (f'<svg class=abs style="right:60px;top:150px" width=380 height=290 viewBox="0 0 380 290">'
              f'<rect x="3" y="3" width="374" height="284" rx="22" fill="#fff" stroke="{NAVY}" stroke-width="5"/>{rows}</svg>')

if __name__ == "__main__":
    render(frame(SURFACE, "Helping a parent get their details off <span style=\"white-space:nowrap\">people-search</span> sites", "A calm, step-by-step guide. Free.", parent_art, 64, 760),
           OUT / "og-guide-help-a-parent.png", 1200, 630, colors=48)
    render(frame("#ffffff", "Freeze your credit for free", "A checklist for you and your parents", freeze_art, 66, 660),
           OUT / "og-credit-freeze.png", 1200, 630, colors=48)
