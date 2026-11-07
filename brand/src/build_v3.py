"""Generate brand/v3 SVGs (hero, sections, icons) from shared palette + parts. Run: .venv/bin/python brand/src/build_v3.py"""
import pathlib, re
R = pathlib.Path(__file__).resolve().parents[1] / "v3"
(R / "sections").mkdir(parents=True, exist_ok=True); (R / "icons").mkdir(parents=True, exist_ok=True)

L = dict(i="#14264a", p="#ffffff", t="#e6edf8", b="#1b3366", r="#a3202e", o="#1c6639", l="#6b778c", s="#fbe9c0", sk="#d9a273", h="#cfd5df", k="#4a3a30")
D = dict(i="#dde7fb", p="#172131", t="#1d2b45", b="#a9c3f3", r="#f5a3ab", o="#8fd6a6", l="#8794ab", s="#4a3f22", sk="#c98f62", h="#b8c0cf", k="#2b221d")
V = dict(i="ink", p="paper", t="tint", b="brand", r="red", o="ok", l="line", s="sun")

def style():
    def decl(m, dark):
        return "".join(f"--{k}:" + (f"var(--fmi-{V[k]},{v})" if k in V else v) + ";" for k, v in m.items())
    cls = "".join(f".f{k}{{fill:var(--{k})}}.k{k}{{stroke:var(--{k})}}" for k in L)
    return (f"<style>svg{{{decl(L,0)}}}@media(prefers-color-scheme:dark){{svg{{{decl(D,1)}}}}}{cls}"
            ".n{fill:none}.rc{stroke-linecap:round;stroke-linejoin:round}.g{fill:#f2b705}</style>")

def svg(vb, body, title, extra=""):
    w, h = vb.split()[2:]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-labelledby="t"{extra}><title id="t">{title}</title>'
            + style() + body + "</svg>")

def star(): return "M12 2l2.9 6.6 7.1.7-5.4 4.7 1.6 7L12 17.3 5.8 21l1.6-7L2 9.3l7.1-.7z"
def mark(x, y, s):
    return (f'<g transform="translate({x} {y}) scale({s/24:.3f})"><rect width="24" height="24" rx="5" class="fb"/>'
            f'<path d="{star()}" transform="translate(4.8 4.8) scale(.6)" fill="var(--p)"/><rect y="20" width="24" height="2" class="fr"/></g>')
def person(x, y, sc=1, hair="h", skin="sk", glasses=True, base=140, shirt="b"):
    g = (f'<g transform="translate({x} {y}) scale({sc})">'
         f'<path d="M-62 {base}C-62 62-34 42 0 42C34 42 62 62 62 {base}Z" class="f{shirt}"/>'
         '<rect x="-9" y="24" width="18" height="22" rx="6" class="fsk"/>'
         '<circle r="30" class="fsk"/>'
         f'<path d="M-32 2C-37-34-14-40 0-40C16-40 37-32 32 2C28-16 14-22 0-22C-14-22-27-16-32 2Z" class="f{hair}"/>')
    if glasses:
        g += '<g class="n kl i rc" stroke="var(--i)" stroke-width="2.5"><circle cx="-12" cy="3" r="8"/><circle cx="12" cy="3" r="8"/><path d="M-4 3h8"/></g>'
    g += '<path d="M-9 16Q0 23 9 16" class="n rc" stroke="var(--i)" stroke-width="2.5"/></g>'
    return g.replace("fsk", "f" + skin) if skin != "sk" else g
def blob(cx=160, cy=125, rx=150, ry=100): return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" class="ft"/>'
def laptop(x, y, w, h, inner=""):
    return (f'<g stroke-width="3" class="kk"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="fp" stroke="var(--i)"/><g stroke="none">{inner}</g>'
            f'<path d="M{x-18} {y+h+4}H{x+w+18}l-12 14H{x-6}z" class="ft" stroke="var(--i)" stroke-linejoin="round"/></g>')
def browser(x, y, w, h, ghost=True, extra=""):
    s = (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="fp" stroke="var(--i)" stroke-width="3"/>'
         f'<path d="M{x} {y+26}H{x+w}" stroke="var(--i)" stroke-width="3" class="n"/>'
         f'<path d="M{x+3} {y+26}V{y+10}a7 7 0 0 1 7-7H{x+w-10}a7 7 0 0 1 7 7V{y+26}z" class="ft"/>'
         f'<circle cx="{x+16}" cy="{y+14}" r="3.5" class="fr"/><circle cx="{x+28}" cy="{y+14}" r="3.5" class="fl"/><circle cx="{x+40}" cy="{y+14}" r="3.5" class="fl"/>')
    if ghost:
        s += f'<rect x="{x+14}" y="{y+38}" width="{w-28}" height="28" rx="6" class="n" stroke="var(--l)" stroke-width="2.5" stroke-dasharray="6 5"/>'
    s += f'<rect x="{x+14}" y="{y+h-34}" width="{(w-28)*.7:.0f}" height="7" rx="3.5" class="fl" opacity=".5"/><rect x="{x+14}" y="{y+h-20}" width="{(w-28)*.45:.0f}" height="7" rx="3.5" class="fl" opacity=".5"/>'
    return s + extra + "</g>"
def idcard(x, y, w=160, h=100, rot=0, extra=""):
    return (f'<g transform="translate({x} {y}) rotate({rot} {w/2} {h/2})"{extra}><rect width="{w}" height="{h}" rx="12" class="fp" stroke="var(--b)" stroke-width="3.5"/>'
            '<circle cx="30" cy="34" r="15" class="ft" stroke="var(--b)" stroke-width="2.5"/><circle cx="30" cy="30" r="5.5" class="fb"/><path d="M19 42c2-6 6-8 11-8s9 2 11 8" class="fb"/>'
            '<text x="52" y="31" font-family="system-ui,Segoe UI,Arial,sans-serif" font-size="11.5" font-weight="700" class="fi">Jane Q Testperson</text>'
            '<text x="52" y="47" font-family="system-ui,Segoe UI,Arial,sans-serif" font-size="10.5" class="fi" opacity=".85">Springfield, IL</text>'
            f'<rect x="16" y="68" width="{w-50}" height="7" rx="3.5" class="fl" opacity=".5"/><rect x="16" y="82" width="{(w-32)*.5:.0f}" height="7" rx="3.5" class="fl" opacity=".5"/></g>')
def env(x, y, rot=0):
    return (f'<g transform="translate({x} {y}) rotate({rot} 18 13)" stroke="var(--i)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"><rect width="36" height="26" rx="4" class="fp"/><path d="M2 4l16 11L34 4" class="n"/></g>')
def tick(cx, cy, r=9): return f'<circle cx="{cx}" cy="{cy}" r="{r}" class="fo"/><path d="M{cx-r*.45:.1f} {cy+.5}l{r*.32:.1f} {r*.35:.1f} {r*.6:.1f}-{r*.7:.1f}" stroke="var(--p)" stroke-width="{r*.3:.1f}" class="n rc"/>'
def dash(d, w=3): return f'<path d="{d}" class="n rc" stroke="var(--b)" stroke-width="{w}" stroke-dasharray="2 8"/>'
def arrowhead(x, y, rot): return f'<path d="M-7-6 1 0-7 6" transform="translate({x} {y}) rotate({rot})" class="n rc" stroke="var(--b)" stroke-width="3"/>'

def write(p, s):
    s = re.sub(r">\s+<", "><", s)
    (R / p).write_text(s); print(p, len(s.encode()))

# ---------------- hero ----------------
hero = (
 '<g id="bg">' + blob(320, 255, 305, 215) +
 '<rect x="46" y="64" width="176" height="196" rx="14" class="fs" stroke="var(--i)" stroke-width="3.5"/><path d="M134 64v196M46 162h176" class="n" stroke="var(--i)" stroke-width="3"/>'
 '<circle cx="90" cy="108" r="17" class="g" opacity=".85"/>'
 '<path d="M24 440H616" class="n rc" stroke="var(--l)" stroke-width="3"/>'
'</g>'
 '<g id="person">' + person(122, 296, 1, base=144) + '</g>'
 '<g id="pages">'
 '<g id="page-1">' + browser(352, 38, 244, 128) + '</g><g id="page-2">' + browser(384, 176, 236, 124) + '</g><g id="page-3">' + browser(338, 308, 240, 124) + '</g></g>'
 '<g id="trail">' + dash("M350 118C318 128 312 168 300 198") + arrowhead(300, 200, 100) +
 dash("M384 246C372 248 364 252 352 256") + arrowhead(350, 257, 165) +
 dash("M344 350C334 326 322 312 306 308") + arrowhead(305, 307, 200) + '</g>'
 '<g id="card">' + idcard(176, 208, 184, 100, -5) + '</g>'
 '<g id="check">' + tick(356, 208, 21) + '</g>'
)
write("hero.svg", svg("0 0 640 480", hero, "A person at home with their name card, coming back from three web pages"))

# ---------------- sections ----------------
S = "0 0 320 240"
W = 'font-family="system-ui,Segoe UI,Arial,sans-serif"'
write("sections/step-install.svg", svg(S, blob() + laptop(70, 38, 180, 118,
  mark(132, 56, 56) + '<rect x="100" y="126" width="120" height="10" rx="5" class="fl n" stroke-width="0" style="fill:var(--l);opacity:.4"/><rect x="100" y="126" width="78" height="10" rx="5" class="fo" stroke-width="0"/>') +
  '<circle cx="266" cy="62" r="26" class="fb"/><path d="M266 48v22m-10-9 10 10 10-10" class="n rc" stroke="var(--p)" stroke-width="5"/>',
  "A laptop installing the Free My ID app"))
write("sections/step-who.svg", svg(S, blob() + '<rect x="64" y="30" width="192" height="180" rx="14" class="fp" stroke="var(--i)" stroke-width="3.5"/>'
  '<circle cx="104" cy="72" r="19" class="ft" stroke="var(--i)" stroke-width="3"/><circle cx="104" cy="66" r="7" class="fb"/><path d="M90 84c3-8 8-10 14-10s11 2 14 10" class="fb"/>'
  '<rect x="136" y="60" width="96" height="10" rx="5" class="fi" opacity=".85"/><rect x="136" y="78" width="60" height="8" rx="4" class="fl" opacity=".5"/>'
  '<g class="n" stroke="var(--l)" stroke-width="3"><rect x="84" y="108" width="152" height="26" rx="7"/><rect x="84" y="142" width="152" height="26" rx="7"/><rect x="84" y="176" width="100" height="22" rx="7" stroke-dasharray="6 5"/></g>'
  '<rect x="94" y="118" width="80" height="7" rx="3.5" class="fi" opacity=".8"/><rect x="94" y="152" width="58" height="7" rx="3.5" class="fi" opacity=".8"/>'
  '<g transform="translate(236 168) rotate(40)" stroke="var(--i)" stroke-width="3" stroke-linejoin="round"><rect x="-8" y="-6" width="16" height="58" rx="3" class="g"/><path d="M-8 52 0 70l8-18z" class="fs"/><rect x="-8" y="-18" width="16" height="12" rx="3" class="fr"/></g>',
  "A simple form asking for a name and town"))
write("sections/step-send.svg", svg(S, blob() + laptop(18, 112, 84, 54, '<path d="M38 140h44" class="n rc" stroke="var(--b)" stroke-width="5"/>') +
  browser(214, 14, 92, 64, False) + browser(214, 88, 92, 64, False) + browser(214, 162, 92, 64, False) +
  dash("M104 118C140 90 168 60 206 48") + dash("M108 134C150 130 170 124 206 122") + dash("M108 150C140 170 170 190 206 198") +
  env(128, 56, -14) + env(150, 112, 0) + env(128, 168, 14), "Letters flying from a laptop to three web pages"))
rows = "".join(tick(114, y) + f'<rect x="134" y="{y-5}" width="{w}" height="9" rx="4.5" class="fi" opacity=".8"/>' for y, w in [(92, 70), (124, 54), (156, 76)])
write("sections/step-report.svg", svg(S, blob() + '<rect x="86" y="24" width="148" height="192" rx="12" class="fp" stroke="var(--i)" stroke-width="3.5"/>'
  '<path d="M89 56V38a11 11 0 0 1 11-11H220a11 11 0 0 1 11 11V56z" class="fb"/>' + f'<path d="{star()}" transform="translate(98 31) scale(.9)" fill="var(--p)"/><rect x="126" y="38" width="76" height="9" rx="4.5" fill="var(--p)"/>' + rows +
  '<circle cx="114" cy="188" r="9" class="g"/><path d="M114 183v6h4" class="n rc" stroke="#14264a" stroke-width="2.4"/><rect x="134" y="183" width="60" height="9" rx="4.5" class="fi" opacity=".8"/>', "A printable progress report with checked-off rows"))
cloud = "M236 96h-34a20 20 0 0 1-2-40 28 28 0 0 1 54-6 24 24 0 0 1 4 46z"
write("sections/safety-local.svg", svg(S, blob() + laptop(24, 76, 150, 92, idcard(58, 92, 82, 56, 0).replace('font-size="11.5"', 'font-size="7"').replace('font-size="10.5"', 'font-size="6.5"').replace('stroke-width="3.5"', 'stroke-width="2.5"')) +
  f'<path d="{cloud}" transform="translate(30 6)" class="n rc" stroke="var(--l)" stroke-width="3.5" stroke-dasharray="7 6"/><path d="M252 36l50 66" class="n rc" stroke="var(--r)" stroke-width="5"/>'
  '<path d="M200 130h-26" class="n" />' , "Your details stay on your computer, not in the cloud"))
write("sections/families-help.svg", svg(S, blob() + person(92, 84, .85, base=150, shirt="b") + person(230, 92, .82, hair="k", glasses=False, base=150, shirt="o") +
  laptop(100, 140, 120, 66, tick(160, 168, 14)), "A grown child helping a parent at a laptop"))

# ---------------- icons (lucide style) ----------------
ICONS = {
 "people-search-site": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><circle cx="8.5" cy="13" r="1.8"/><path d="M5.5 18c0-1.7 1.3-3 3-3s3 1.3 3 3"/><path d="M14.5 13h3.5"/><path d="M14.5 16h2.5"/>',
 "opt-out-letter": '<path d="M7 8V4a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v4"/><rect x="3" y="8" width="18" height="13" rx="2"/><path d="m3 10 9 6 9-6"/>',
 "removal-report": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="m8 9 1.5 1.5L12 8"/><path d="M14.5 9.5H17"/><path d="m8 15 1.5 1.5L12 14"/><path d="M14.5 15.5H17"/>',
 "practice-mode": '<circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/><path d="M10 8.5v7l5.5-3.5z"/>',
 "windows-install": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/><path d="M12 6.5v6"/><path d="m9.5 10 2.5 2.5 2.5-2.5"/>',
}
for n, b in ICONS.items():
    write(f"icons/{n}.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{b}</svg>')
