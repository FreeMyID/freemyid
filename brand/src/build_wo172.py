"""WO-172: per-broker guide OG template (1200x630) plus samples. Broker name is the only variable.
Usage from brand/src: build_wo172.py            -> the 3 samples (Spokeo, Whitepages, BeenVerified)
                      build_wo172.py all        -> every name in NAMES (slug -> display name)
                      build_wo172.py test DIR  -> longest-name fit check images into DIR (not shipped)
Text-only broker names: no broker logos."""
import sys, pathlib
from wo17_common import *

OUT = BRAND / "social/og"
SAMPLES = {"spokeo": "Spokeo", "whitepages": "Whitepages", "beenverified": "BeenVerified"}
NAMES = dict(SAMPLES)  # add slug: "Display Name" once broker-researcher confirms the shipped list


def glyph():
    rows = "".join(
        f'<rect x="22" y="{22 + k * 48}" width="30" height="30" rx="7" fill="#fff" stroke="{NAVY}" stroke-width="4"/>'
        f'<path d="M28 {37 + k * 48}l6 6 11-12" fill="none" stroke="{GREEN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<rect x="68" y="{30 + k * 48}" width="{w}" height="14" rx="7" fill="#cfd5df"/>' for k, w in enumerate((112, 90, 104)))
    return (f'<svg class=abs style="right:90px;bottom:60px" width=240 height=170 viewBox="0 0 240 170">'
            f'<rect x="2" y="2" width="236" height="166" rx="16" fill="#fff" stroke="{NAVY}" stroke-width="4"/>{rows}</svg>')


def page(name):
    return f"""<body style="width:1200px;height:630px;background:#ffffff">
<div class=abs style="left:0;top:0;bottom:0;width:28px;background:{NAVY}"></div>
<div class=abs style="left:28px;top:0;bottom:0;width:6px;background:{RED}"></div>
{logo(40, "left:96px;top:56px")}
<div class=abs style="left:96px;top:140px;width:1010px">
  <p style="font-size:28px;font-weight:700;letter-spacing:3px;color:{RED}">FREE GUIDE</p>
  <h1 style="margin-top:14px;font-size:66px;line-height:1.1;font-weight:800;letter-spacing:-1px;color:{HEAD}">Remove yourself from<br>{name}</h1>
  <p style="margin-top:26px;font-size:32px;color:{MUTED}">Step by step. Free. No account needed.</p>
</div>
{glyph()}
<p class=abs style="left:96px;bottom:60px;font-size:28px;font-weight:700;color:{NAVY}">freemyid.org</p>
</body>"""


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "test":
        t = pathlib.Path(sys.argv[2])  # scratch dir outside the repo
        for n in ("Instant Checkmate", "PeopleFinders", "FastPeopleSearch.com", "Intelius Public Records"):
            render(page(n), t / f"fit-{n.replace(' ', '-')}.png", 1200, 630)
    else:
        for slug, n in (NAMES if mode == "all" else SAMPLES).items():
            render(page(n), OUT / f"og-guide-{slug}.png", 1200, 630, colors=48)
