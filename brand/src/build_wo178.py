"""WO-178: 'How it works' step spot art (3 subjects x light/dark), SVG 320x250 + PNG 640x500, no text.
Run from brand/src."""
import pathlib
from playwright.sync_api import sync_playwright
from PIL import Image

BRAND = pathlib.Path(__file__).resolve().parents[1]
OUT = BRAND / "web/steps"
P = {
    "light": dict(i="#14264a", p="#ffffff", t="#e6edf8", b="#1b3366", r="#a3202e", o="#1c6639", l="#cfd5df", d="#6b778c", lens="#fbe9c0"),
    "dark": dict(i="#dde7fb", p="#172131", t="#1d2b45", b="#a9c3f3", r="#f5a3ab", o="#8fd6a6", l="#3a475c", d="#8794ab", lens="#a98a3a"),
}
SW = 3.5  # same stroke weight as brand/v3/features


def wrap(title, body, c):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 250" role="img" aria-labelledby="t"><title id="t">{title}</title>'
            f'<ellipse cx="160" cy="125" rx="150" ry="105" fill="{c["t"]}"/>{body}</svg>')


def st(c, extra=""):
    return f'stroke="{c["i"]}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round" {extra}'


def who(c):  # a name card in front of a small house
    b = (f'<path d="M160 118l60-52 60 52" fill="none" {st(c)}/>'
         f'<rect x="170" y="116" width="100" height="84" fill="{c["p"]}" {st(c)}/>'
         f'<rect x="218" y="156" width="24" height="44" fill="{c["r"]}" {st(c)}/>'
         f'<rect x="52" y="92" width="150" height="104" rx="10" fill="{c["p"]}" {st(c)}/>'
         f'<circle cx="90" cy="128" r="12" fill="{c["b"]}" {st(c)}/>'
         f'<path d="M68 172c0-14 10-22 22-22s22 8 22 22" fill="{c["b"]}" {st(c)}/>'
         f'<rect x="124" y="118" width="60" height="9" rx="4.5" fill="{c["l"]}"/><rect x="124" y="140" width="46" height="9" rx="4.5" fill="{c["l"]}"/>'
         f'<rect x="124" y="162" width="56" height="9" rx="4.5" fill="{c["l"]}"/>')
    return wrap("A name card in front of a small house", b, c)


def sent(c):  # a page with an arrow going out to a web page
    b = (f'<path d="M40 62h56l20 20v100a6 6 0 0 1-6 6H40a6 6 0 0 1-6-6V68a6 6 0 0 1 6-6z" fill="{c["p"]}" {st(c)}/>'
         f'<path d="M96 62v20h20" fill="none" {st(c)}/>'
         f'<rect x="50" y="102" width="52" height="8" rx="4" fill="{c["l"]}"/><rect x="50" y="124" width="40" height="8" rx="4" fill="{c["l"]}"/><rect x="50" y="146" width="52" height="8" rx="4" fill="{c["l"]}"/>'
         f'<path d="M122 124h60M166 106l20 18-20 18" fill="none" stroke="{c["r"]}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<rect x="196" y="58" width="92" height="132" rx="10" fill="{c["p"]}" {st(c)}/><path d="M196 86h92" fill="none" {st(c)}/>'
         f'<circle cx="212" cy="72" r="4.5" fill="{c["d"]}"/><circle cx="226" cy="72" r="4.5" fill="{c["d"]}"/>'
         f'<rect x="210" y="104" width="64" height="8" rx="4" fill="{c["l"]}"/><rect x="210" y="126" width="50" height="8" rx="4" fill="{c["l"]}"/><rect x="210" y="148" width="64" height="8" rx="4" fill="{c["l"]}"/>')
    return wrap("A page with an arrow going out to a web page", b, c)


def checked(c):  # a magnifier over a list with check marks
    rows = "".join(
        f'<path d="M66 {y}l7 7 13-14" fill="none" stroke="{c["o"]}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<rect x="98" y="{y - 5}" width="{w}" height="9" rx="4.5" fill="{c["l"]}"/>' for y, w in ((78, 110), (118, 90), (158, 120)))
    b = (f'<rect x="48" y="40" width="190" height="170" rx="12" fill="{c["p"]}" {st(c)}/>{rows}'
         f'<circle cx="190" cy="150" r="38" fill="{c["lens"]}" fill-opacity=".45" {st(c)}/>'
         f'<path d="M218 178l30 30" fill="none" stroke="{c["i"]}" stroke-width="9" stroke-linecap="round"/>')
    return wrap("A magnifying glass over a list with check marks", b, c)


ART = {"1-who": who, "2-sent": sent, "3-checked": checked}
if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_context(viewport={"width": 320, "height": 250}, device_scale_factor=2).new_page()
        for name, fn in ART.items():
            for mode, c in P.items():
                svg = fn(c)
                (OUT / f"step-{name}-{mode}.svg").write_text(svg)
                pg.set_content(f'<body style="margin:0;background:transparent">{svg}</body>')
                png = OUT / f"step-{name}-{mode}.png"
                pg.screenshot(path=str(png), omit_background=True)
                Image.open(png).convert("RGBA").quantize(48, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(png, optimize=True)
                print(png.name, png.stat().st_size // 1024, "KB")
        br.close()
    # contact sheet for review (not shipped; set SHEET=path): light on white, dark on #0d131d
    sheet = Image.new("RGB", (1920, 1000), "#ffffff")
    sheet.paste(Image.new("RGB", (1920, 500), "#0d131d"), (0, 500))
    for r, mode in enumerate(P):
        for k, name in enumerate(ART):
            im = Image.open(OUT / f"step-{name}-{mode}.png").convert("RGBA")
            sheet.paste(im, (k * 640, r * 500), im)
    import os
    if os.environ.get("SHEET"):
        sheet.save(os.environ["SHEET"])
