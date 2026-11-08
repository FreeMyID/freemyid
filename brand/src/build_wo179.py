"""WO-179: OG images for /i-do-not-consent/ and /families/ (1200x630, navy ground, white text).
Text stays inside the middle 1000x500. Run from brand/src."""
from wo17_common import *

OUT = BRAND / "social/og"
PAGES = {
    "og-i-do-not-consent": ("That post didn't stop anyone. This does.", "Free My ID asks the people-search sites to take your details down."),
    "og-families": ("Helping a parent with their privacy online.", "Free, no account, built so your grandparents can use it."),
}


def page(head, sub):
    return f"""<body style="width:1200px;height:630px;background:{NAVY}">
<div class=abs style="left:0;right:0;top:0;height:10px;background:{RED}"></div>
<div class=abs style="left:100px;top:120px;width:1000px"><h1 style="font-size:72px;line-height:1.1;font-weight:800;letter-spacing:-1px;color:#ffffff;text-wrap:balance">{head}</h1>
<p style="margin-top:32px;font-size:34px;line-height:1.35;color:#dde7fb;text-wrap:balance">{sub}</p></div>
{logo(48, "left:100px;bottom:65px")}
<p class=abs style="right:100px;bottom:65px;height:48px;line-height:48px;font-size:30px;font-weight:700;color:#ffffff">freemyid.org</p>
</body>"""


for name, (h, s) in PAGES.items():
    render(page(h, s), OUT / f"{name}.png", 1200, 630, scheme="dark", colors=64)
