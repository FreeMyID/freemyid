"""WO-170 / WO-171: OG images for /developers/cli/ and /developers/config/ (1200x630).
Run: .venv/bin/python brand/src/build_wo170_171.py"""
from __future__ import annotations

from wo17_common import *

OUT = BRAND / "social/og"


def page(bg: str, headline: str, sub: str, panel_html: str, tab_html: str,
         px: int = 650, hw: int = 550, fs: int = 28) -> str:
    return f"""<body style="width:1200px;height:630px;background:{bg}">
<div class=flag></div>
{logo(40, "left:60px;top:58px")}
<div class=abs style="left:60px;top:140px;width:{hw}px"><h1 style="font-size:66px;line-height:1.1;font-weight:800;color:{HEAD};letter-spacing:-.8px">{headline}</h1>
<p style="margin-top:28px;font-size:32px;line-height:1.3;color:{MUTED}">{sub}</p></div>
<p class=abs style="left:60px;bottom:60px;font-size:28px;font-weight:700;color:{NAVY}">freemyid.org</p>
<div class=abs style="left:{px}px;top:110px;width:{1200-60-px}px;height:410px;background:{NAVY};border-radius:20px;overflow:hidden">
  {tab_html}
  <div style="padding:30px 34px;font-family:{MONO};font-size:{fs}px;line-height:1.65;white-space:nowrap;color:#eef1f6">{panel_html}</div>
</div></body>"""


DOTS = '<span style="width:14px;height:14px;border-radius:7px;background:#c4d5f7;opacity:.55;display:inline-block;margin-right:10px"></span>' * 3
BAR = f'<div style="height:52px;background:#14264a;padding:19px 24px">{DOTS}</div>'
TAB = (f'<div style="height:52px;background:#14264a;padding:0 24px;display:flex;align-items:flex-end">'
       f'<span style="display:block;width:150px;height:40px;background:{NAVY};border-radius:10px 10px 0 0;padding:14px 0 0 20px">'
       f'<span style="display:block;width:70px;height:8px;border-radius:4px;background:#c4d5f7;opacity:.6"></span></span></div>')


M = "#9db0cf"  # dim text on navy
K = '<span style="color:#9db8ea">'
cfg = (f'<div>{K}version:</span> 1</div><div>{K}consent:</span></div><div>&nbsp;&nbsp;{K}agreed:</span> true</div>'
       f'<div>&nbsp;&nbsp;{K}signed_name:</span> Jane Q Testperson</div><div>&nbsp;&nbsp;{K}basis:</span> self</div>')
SUB_CFG = 'Prepare one file for <span style="font-family:' + MONO + ';font-weight:700;color:' + HEAD + '">freemyid setup</span>'

COLS = "190px 190px 160px 190px 1fr"
def row(c: tuple[str, ...], bold: bool = False, color: str = "#eef1f6") -> str:
    return (f'<div style="display:grid;grid-template-columns:{COLS};height:34px;line-height:34px;color:{color};{"font-weight:700;" if bold else ""}">'
            + "".join(f"<span>{x}</span>" for x in c) + "</div>")
rule = '<div style="height:2px;background:#4a5f8c;margin:2px 0"></div>'
cli_panel = (
    '<div><span style="color:#9db8ea">$</span> freemyid status</div>'
    '<div style="margin:10px 0 4px;text-align:center;font-weight:700;color:#fff">Jane Q Testperson</div>'
    + row(("Broker", "State", "Updated", "Next check", "Escalation"), True, "#ffffff") + rule
    + row(("Spokeo", "found", "2026-11-05", "2026-11-12", "0"))
    + row(("Whitepages", "submitted", "2026-11-03", "2026-11-10", "0"))
    + row(("BeenVerified", "removed", "2026-10-29", "2026-11-26", "0")) + rule
    + '<div style="margin-top:8px;color:#f2c94c">1 item(s) need you: `freemyid todo list`</div>'
    + f'<div style="color:{M};line-height:1.3;margin-top:6px;font-size:21px">\'removed\' means removed from that broker, not from the whole internet.</div>')

def cli_page() -> str:
    return f"""<body style="width:1200px;height:630px;background:#ffffff"><div class=flag></div>
{logo(40, "left:60px;top:44px")}
<p class=abs style="right:60px;top:50px;font-size:28px;font-weight:700;color:{NAVY}">freemyid.org</p>
<h1 class=abs style="left:60px;top:106px;font-size:66px;line-height:1.1;font-weight:800;letter-spacing:-.8px;color:{HEAD};white-space:nowrap">The Free My ID command line</h1>
<p class=abs style="left:60px;top:190px;font-size:32px;color:{MUTED}">Scriptable. Local. No account.</p>
<div class=abs style="left:60px;top:246px;width:1080px;height:368px;background:{NAVY};border-radius:20px;overflow:hidden">
  {BAR.replace("height:52px","height:36px").replace("padding:19px 24px","padding:11px 24px")}
  <div style="padding:14px 34px;font-family:{MONO};font-size:23px;line-height:1.5;color:#eef1f6">{cli_panel}</div></div></body>"""

import sys
sys.path.insert(0, ".")
render(cli_page(), OUT / "og-developers-cli.png", 1200, 630, colors=48)
render(page(SURFACE, "Setup file reference", SUB_CFG, cfg, TAB, px=610, hw=520, fs=23),
       OUT / "og-developers-config.png", 1200, 630, colors=48)
