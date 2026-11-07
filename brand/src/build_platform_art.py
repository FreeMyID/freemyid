"""Platform app icons (.icns, hicolor PNG + SVG), /developers/ art, feature art.
Run: .venv/bin/python brand/src/build_platform_art.py   (needs Playwright chromium + Pillow)
"""
from pathlib import Path
from string import Template
from io import BytesIO
from playwright.sync_api import sync_playwright
from PIL import Image

B = Path(__file__).resolve().parent.parent
LIGHT = dict(i="#14264a", p="#ffffff", t="#e6edf8", b="#1b3366", r="#a3202e", o="#1c6639", l="#6b778c",
             s="#fbe9c0", term="#14264a", tt="#e6edf8", sk="#d9a273", h="#cfd5df", g="#f2b705")
DARK = dict(i="#dde7fb", p="#172131", t="#1d2b45", b="#a9c3f3", r="#f5a3ab", o="#8fd6a6", l="#8794ab",
            s="#4a3f22", term="#0d131d", tt="#dde7fb", sk="#c98f62", h="#b8c0cf", g="#f2b705")
STAR = "M12 2l2.9 6.6 7.1.7-5.4 4.7 1.6 7L12 17.3 5.8 21l1.6-7L2 9.3l7.1-.7z"

def app_icon(margin):
    m = margin; s = 1024 - 2 * m; k = s / 24
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img"><title>Free My ID</title>'
            f'<defs><clipPath id="c"><rect x="{m}" y="{m}" width="{s}" height="{s}" rx="{s*0.225:.0f}"/></clipPath></defs>'
            f'<g clip-path="url(#c)"><rect x="{m}" y="{m}" width="{s}" height="{s}" fill="#1b2f5b"/>'
            f'<path d="{STAR}" transform="translate({m+4.8*k:.1f} {m+4.8*k:.1f}) scale({0.6*k:.2f})" fill="#fff"/>'
            f'<rect x="{m}" y="{m+20*k:.1f}" width="{s}" height="{2*k:.1f}" fill="#a3202e"/></g></svg>')

def doc(vb, title, body, p):
    w, h = vb
    return Template(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">'
                    f'<title id="t">{title}</title>{body}</svg>').substitute(p)

SW = 'stroke="$i" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"'
def chev(x, y, c="$tt"):
    return f'<path d="M{x} {y-6}l7 6-7 6" fill="none" stroke="{c}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
def bar(x, y, w, c="$tt", op=1):
    return f'<rect x="{x}" y="{y-3}" width="{w}" height="6" rx="3" fill="{c}" opacity="{op}"/>'
def tick(x, y, c="$o"):
    return f'<path d="M{x} {y}l6 6 12-13" fill="none" stroke="{c}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>'
def person(x, y, sc, hair):
    return (f'<g transform="translate({x} {y}) scale({sc})"><path d="M-34 70c0-26 14-40 34-40s34 14 34 40z" fill="$b" {SW}/>'
            f'<circle cx="0" cy="0" r="24" fill="$sk" {SW}/><path d="M-24 -4c2-22 46-24 48 0c-10-10-30-12-48 0z" fill="{hair}" {SW}/></g>')

def developers():
    return ('<ellipse cx="320" cy="260" rx="305" ry="205" fill="$t"/>'
        # home outline
        f'<path d="M60 250L320 70l260 180v170H60z" fill="$p" {SW}/>'
        '<path d="M290 70v-28h26v46" fill="none" stroke="$i" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" opacity="0"/>'
        # terminal
        f'<rect x="92" y="200" width="270" height="190" rx="12" fill="$term" {SW}/>'
        '<path d="M92 236h270" stroke="$l" stroke-width="2.5"/>'
        '<circle cx="114" cy="218" r="5" fill="$l"/><circle cx="132" cy="218" r="5" fill="$l"/><circle cx="150" cy="218" r="5" fill="$l"/>'
        + chev(114, 268) + bar(134, 268, 150) +
        bar(114, 302, 190, op=.55) + bar(114, 326, 130, op=.55) + tick(112, 354) + bar(142, 360, 90, "$tt") +
        # cable
        f'<path d="M362 311h48" fill="none" {SW}/>'
        # server
        f'<rect x="410" y="232" width="150" height="158" rx="12" fill="$p" {SW}/>'
        '<path d="M410 285h150M410 338h150" stroke="$i" stroke-width="3.5"/>'
        '<circle cx="436" cy="258" r="7" fill="$o"/><circle cx="436" cy="311" r="7" fill="$o"/><circle cx="436" cy="364" r="7" fill="$o"/>'
        '<rect x="462" y="254" width="70" height="8" rx="4" fill="$h"/><rect x="462" y="307" width="70" height="8" rx="4" fill="$h"/><rect x="462" y="360" width="70" height="8" rx="4" fill="$h"/>'
        # red floor line (flag bar echo) + clock for the schedule
        '<path d="M60 420h520" stroke="$r" stroke-width="6" stroke-linecap="round"/>'
        f'<circle cx="320" cy="150" r="32" fill="$s" {SW}/><path d="M320 132v19l13 8" fill="none" {SW}/>')

def f_scan():
    return ('<ellipse cx="160" cy="125" rx="150" ry="105" fill="$t"/>'
        f'<rect x="50" y="42" width="190" height="150" rx="12" fill="$p" {SW}/><path d="M50 72h190" stroke="$i" stroke-width="3.5"/>'
        '<circle cx="68" cy="57" r="4.5" fill="$l"/><circle cx="84" cy="57" r="4.5" fill="$l"/>'
        '<rect x="66" y="88" width="120" height="8" rx="4" fill="$h"/><rect x="66" y="112" width="150" height="8" rx="4" fill="$h"/>'
        '<rect x="66" y="136" width="100" height="8" rx="4" fill="$h"/><rect x="66" y="160" width="130" height="8" rx="4" fill="$h"/>'
        f'<circle cx="190" cy="132" r="40" fill="$s" fill-opacity=".9" {SW}/>'
        f'<path d="M219 161l38 38" fill="none" stroke="$i" stroke-width="9" stroke-linecap="round"/>'
        '<circle cx="178" cy="122" r="9" fill="$sk" stroke="$i" stroke-width="3"/><path d="M160 152c0-14 8-20 18-20s18 6 18 20" fill="$b" stroke="$i" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M200 118l8 8 14-16" fill="none" stroke="$o" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')

def f_report():
    return ('<ellipse cx="160" cy="125" rx="150" ry="105" fill="$t"/>'
        f'<rect x="78" y="26" width="164" height="200" rx="10" fill="$p" {SW}/>'
        f'<path d="{STAR}" transform="translate(94 40) scale(.9)" fill="$b"/><rect x="124" y="46" width="90" height="8" rx="4" fill="$i"/>'
        '<path d="M94 74h132" stroke="$l" stroke-width="2.5"/>'
        + "".join(f'<rect x="136" y="{y-4}" width="{w}" height="8" rx="4" fill="$h"/><path d="M96 {y}l6 6 12-13" fill="none" stroke="$o" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>'
                  for y, w in ((98, 90), (126, 70), (154, 84))) +
        '<rect x="136" y="178" width="60" height="8" rx="4" fill="$h"/><circle cx="105" cy="182" r="8" fill="none" stroke="$l" stroke-width="3.5"/>'
        f'<circle cx="222" cy="192" r="30" fill="$s" {SW}/><path d="{STAR}" transform="translate(206 176) scale(1.33)" fill="$r"/>')

def f_family():
    return ('<ellipse cx="160" cy="125" rx="150" ry="105" fill="$t"/>'
        + person(92, 66, .9, "$h") + person(228, 78, .8, "$k") +
        f'<rect x="96" y="150" width="128" height="66" rx="8" fill="$p" {SW}/><path d="M78 224h164" stroke="$i" stroke-width="6" stroke-linecap="round"/>'
        '<rect x="110" y="164" width="46" height="38" rx="6" fill="$t" stroke="$i" stroke-width="3"/><rect x="164" y="164" width="46" height="38" rx="6" fill="$t" stroke="$i" stroke-width="3"/>'
        '<circle cx="133" cy="176" r="6" fill="$b"/><rect x="120" y="188" width="26" height="5" rx="2.5" fill="$h"/>'
        '<circle cx="187" cy="176" r="6" fill="$b"/><rect x="174" y="188" width="26" height="5" rx="2.5" fill="$h"/>'
        f'<path d="M160 112c-14-12-28 4-14 16l14 12 14-12c14-12 0-28-14-16z" fill="$r" {SW} transform="translate(0 -12) scale(1)"/>')

ART = [
 ("developers/developers", (640, 480), "A terminal on your own computer connected to a small home server, inside a house outline, with a clock for the schedule", developers),
 ("features/find-me-first", (320, 250), "A magnifying glass over a web page, finding a person's listing", f_scan),
 ("features/proof-report", (320, 250), "A progress report with checked rows and a star seal", f_report),
 ("features/family-helper", (320, 250), "A grown child and a parent sharing one laptop with two name cards", f_family),
]
ALT = {}

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page()
        def png(svg, px, out, w=None, h=None, omit=True, opt=False):
            pg.set_viewport_size({"width": w or px, "height": h or px})
            pg.set_content(f'<body style="margin:0;background:transparent"><div style="width:{w or px}px;height:{h or px}px">{svg}</div><style>svg{{width:100%;height:100%;display:block}}</style></body>')
            data = pg.screenshot(omit_background=omit)
            im = Image.open(BytesIO(data)).convert("RGBA")
            if opt:
                im = im.quantize(64, method=Image.Quantize.FASTOCTREE) if not omit else im
            return im
        # --- platform icons
        P = B / "icons/platforms"
        mac = app_icon(100); lin = app_icon(24)
        (P / "freemyid-macos.svg").write_text(mac); 
        sizes = {}
        for s in (16, 32, 64, 128, 256, 512, 1024):
            sizes[s] = png(mac, s, None)
        sizes[1024].save(P / "freemyid-macos-1024.png", optimize=True)
        iset = P / "freemyid.iconset"; iset.mkdir(exist_ok=True)
        for name, s in (("icon_16x16", 16), ("icon_16x16@2x", 32), ("icon_32x32", 32), ("icon_32x32@2x", 64),
                        ("icon_128x128", 128), ("icon_128x128@2x", 256), ("icon_256x256", 256),
                        ("icon_256x256@2x", 512), ("icon_512x512", 512), ("icon_512x512@2x", 1024)):
            sizes[s].save(iset / f"{name}.png", optimize=True)
        sizes[1024].save(P / "freemyid.icns", format="ICNS", append_images=[sizes[s] for s in (512, 256, 128, 64, 32, 16)])
        for s in (16, 22, 24, 32, 48, 64, 128, 256, 512):
            d = P / f"hicolor/{s}x{s}/apps"; d.mkdir(parents=True, exist_ok=True)
            png(lin, s, None).save(d / "freemyid.png", optimize=True)
        d = P / "hicolor/scalable/apps"; d.mkdir(parents=True, exist_ok=True); (d / "freemyid.svg").write_text(lin)
        # --- illustrations
        for name, vb, title, fn in ART:
            for mode, pal in (("light", LIGHT), ("dark", DARK)):
                pal2 = dict(pal, k=pal["i"] if mode == "light" else "#2b221d")
                pal2["k"] = "#4a3a30" if mode == "light" else "#2b221d"
                svg = doc(vb, title, fn(), pal2)
                out = B / f"v3/{name}-{mode}"
                out.with_suffix(".svg").write_text(svg)
                w, h = vb
                bg = f'<rect width="{w}" height="{h}" fill="{pal["p"] if mode=="dark" else "#ffffff"}"/>'
                im = png(svg, 0, None, w * 2 // (1 if w > 400 else 1), h * 2 // 1) if False else png(svg, 0, None, w, h)
                im.save(out.with_suffix(".png"), optimize=True)
        br.close()

main()
