"""WO-170 / WO-171: OG images for /developers/cli/ and /developers/config/ (1200x630).
Run: .venv/bin/python brand/src/build_wo170_171.py"""
from wo17_common import *

OUT = BRAND / "social/og"


def page(bg, headline, sub, panel_html, tab_html):
    return f"""<body style="width:1200px;height:630px;background:{bg}">
<div class=flag></div>
{logo(40, "left:60px;top:58px")}
<div class=abs style="left:60px;top:140px;width:550px"><h1 style="font-size:66px;line-height:1.1;font-weight:800;color:{HEAD};letter-spacing:-.8px">{headline}</h1>
<p style="margin-top:28px;font-size:32px;line-height:1.3;color:{MUTED}">{sub}</p></div>
<p class=abs style="left:60px;bottom:60px;font-size:28px;font-weight:700;color:{NAVY}">freemyid.org</p>
<div class=abs style="left:650px;top:110px;width:490px;height:410px;background:{NAVY};border-radius:20px;overflow:hidden">
  {tab_html}
  <div style="padding:30px 34px;font-family:{MONO};font-size:28px;line-height:1.65;color:#eef1f6">{panel_html}</div>
</div></body>"""


DOTS = '<span style="width:14px;height:14px;border-radius:7px;background:#c4d5f7;opacity:.55;display:inline-block;margin-right:10px"></span>' * 3
BAR = f'<div style="height:52px;background:#14264a;padding:19px 24px">{DOTS}</div>'
TAB = (f'<div style="height:52px;background:#14264a;padding:0 24px;display:flex;align-items:flex-end">'
       f'<span style="display:block;width:150px;height:40px;background:{NAVY};border-radius:10px 10px 0 0;padding:14px 0 0 20px">'
       f'<span style="display:block;width:70px;height:8px;border-radius:4px;background:#c4d5f7;opacity:.6"></span></span></div>')

cli = ('<div><span style="color:#9db8ea">$</span> freemyid status</div>'
       '<div style="margin-top:18px;color:#ffffff;font-weight:700">3 requests sent,<br>1 confirmed</div>'
       '<div style="margin-top:18px"><span style="color:#9db8ea">$</span> <span style="display:inline-block;width:14px;height:28px;background:#c4d5f7;vertical-align:-5px"></span></div>')
K = '<span style="color:#9db8ea">'
cfg = (f'<div>{K}version:</span> 1</div><div>{K}email_mode:</span> approve_each</div>'
       f'<div>{K}permissions:</span></div><div>&nbsp;&nbsp;{K}allow_id_upload:</span> false</div>')

render(page("#ffffff", "The Free My ID command line", "Scriptable. Local. No account.", cli, BAR),
       OUT / "og-developers-cli.png", 1200, 630, colors=48)
render(page(SURFACE, "Free My ID settings, in one file", "Plain text. Yours to read and change.", cfg, TAB),
       OUT / "og-developers-config.png", 1200, 630, colors=48)
