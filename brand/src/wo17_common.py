"""Shared helpers for the WO-170..179 art (hand-authored HTML/SVG rendered with Playwright).
Run the build_wo17x_*.py scripts with .venv/bin/python from the repo root."""
import pathlib
from playwright.sync_api import sync_playwright
from PIL import Image

BRAND = pathlib.Path(__file__).resolve().parents[1]
LOCKUP = (BRAND / "logo/final/wordmark-lockup.svg").as_uri()
NAVY, HEAD, TEXT, MUTED = "#1b2f5b", "#14264a", "#151b26", "#414b5c"
RED, SURFACE, OFFWHITE, SOFT = "#a3202e", "#eef2f7", "#f4f6f9", "#e6edf8"
GREEN = "#1c6639"
SANS = "'Segoe UI','Open Sans',Inter,system-ui,Arial,sans-serif"
SERIF = "Georgia,'DejaVu Serif',serif"
MONO = "'Cascadia Mono',Consolas,'DejaVu Sans Mono','Adwaita Mono',monospace"

BASE = f"""*{{box-sizing:border-box;margin:0}}html,body{{margin:0}}
body{{font-family:{SANS};color:{TEXT};position:relative;overflow:hidden;-webkit-font-smoothing:antialiased}}
.flag{{position:absolute;left:0;right:0;top:0;height:14px;background:linear-gradient({NAVY} 0 8px,{RED} 8px)}}
.abs{{position:absolute}}"""


def logo(h=48, extra=""):
    """The unaltered wordmark lockup. In a dark-scheme render it uses its own dark colours."""
    return f'<img class="abs" src="{LOCKUP}" style="height:{h}px;{extra}" alt="">'


def render(html, out, w, h, scheme="light", colors=None, transparent=False):
    """Render html to PNG at `out`, optionally palette-quantized to `colors` for size."""
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = BRAND / "src" / "_tmp_render.html"
    tmp.write_text(f"<!doctype html><meta charset=utf-8><style>{BASE}</style>" + html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
        pg = ctx.new_page()
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(150)
        pg.screenshot(path=str(out), omit_background=transparent)
        b.close()
    tmp.unlink()
    im = Image.open(out)
    im = im.convert("RGBA" if transparent else "RGB")
    if colors:
        im = im.quantize(colors, method=Image.Quantize.FASTOCTREE if transparent else Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    im.save(out, optimize=True)
    print(out.relative_to(BRAND.parent), im.size, out.stat().st_size // 1024, "KB")
