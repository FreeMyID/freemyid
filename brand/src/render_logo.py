"""Build brand/logo/final/ (logo A, star badge): SVGs, favicon PNGs, .ico, apple-touch-icon, preview."""
import io, pathlib
from playwright.sync_api import sync_playwright
from PIL import Image
R = pathlib.Path(__file__).resolve().parents[1]
F = R / "logo/final"; F.mkdir(exist_ok=True)
STAR = "M12 2l2.9 6.6 7.1.7-5.4 4.7 1.6 7L12 17.3 5.8 21l1.6-7L2 9.3l7.1-.7z"
def tile(dark):
    bg, st, bar = ("#c4d5f7", "#0f1520", "#f5a3ab") if dark else ("#1b2f5b", "#fff", "#a3202e")
    return (f'<rect width="24" height="24" rx="5" fill="{bg}"/>'
            f'<path d="{STAR}" transform="translate(4.8 4.8) scale(.6)" fill="{st}"/>'
            f'<rect y="20" width="24" height="2" fill="{bar}"/>')
def svg(inner, vb="0 0 24 24", extra="", title="Free My ID"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"{extra} role="img"><title>{title}</title>{inner}</svg>\n'
def lockup_adaptive():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 118 24" width="236" height="48" role="img"><title>Free My ID</title>'
            '<style>.b{fill:#1b2f5b}.s{fill:#fff}.r{fill:#a3202e}.t{fill:#1b2f5b}'
            '@media(prefers-color-scheme:dark){.b{fill:#c4d5f7}.s{fill:#0f1520}.r{fill:#f5a3ab}.t{fill:#c4d5f7}}</style>'
            f'<rect class="b" width="24" height="24" rx="5"/><path class="s" d="{STAR}" transform="translate(4.8 4.8) scale(.6)"/>'
            '<rect class="r" y="20" width="24" height="2"/>'
            '<text class="t" x="30" y="18" font-family="Georgia,\'DejaVu Serif\',serif" font-weight="700" font-size="17">Free My ID</text></svg>\n')
fav = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><style>.b{fill:#1b2f5b}.s{fill:#fff}.r{fill:#a3202e}'
       '@media(prefers-color-scheme:dark){.b{fill:#c4d5f7}.s{fill:#0f1520}.r{fill:#f5a3ab}}</style>'
       f'<rect class="b" width="24" height="24" rx="5"/><path class="s" d="{STAR}" transform="translate(4.8 4.8) scale(.6)"/>'
       '<rect class="r" y="20" width="24" height="2"/></svg>\n')
(F/"mark.svg").write_text(svg(tile(False), extra=""))
(F/"mark-dark.svg").write_text(svg(tile(True)))
(F/"favicon.svg").write_text(fav)
(F/"wordmark-lockup.svg").write_text(lockup_adaptive())
apple = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" fill="#1b2f5b"/>'
         f'<path d="{STAR}" transform="translate(3.6 3) scale(.7)" fill="#fff"/><rect y="20" width="24" height="2" fill="#a3202e"/></svg>')
def shot(pg, s, px, name, omit=True):
    pg.set_viewport_size({"width": px, "height": px})
    pg.set_content(f'<body style="margin:0;background:transparent"><div style="width:{px}px;height:{px}px">'
                   + s.replace("<svg ", f'<svg width="{px}" height="{px}" ', 1) + "</div>")
    pg.screenshot(path=str(F/name), omit_background=omit)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for n in (16, 32, 48):
        shot(pg, fav, n, f"favicon-{n}.png")
    shot(pg, apple, 180, "apple-touch-icon.png", omit=False)
    b.close()
for n in (16, 32, 48): Image.open(F/f"favicon-{n}.png").convert("RGBA").save(F/f"favicon-{n}.png", optimize=True)
Image.open(F/"apple-touch-icon.png").convert("RGB").save(F/"apple-touch-icon.png", optimize=True)
Image.open(F/"favicon-48.png").convert("RGBA").resize((48, 48)).save(
    F/"favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
    append_images=[Image.open(F/"favicon-32.png"), Image.open(F/"favicon-16.png")])
