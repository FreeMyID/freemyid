"""Generate packaging/windows/freemyid.ico (original art: a blue shield with a white eraser).

Needs Pillow (dev only):  python tools/make_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "packaging" / "windows" / "freemyid.ico"
S = 512   # draw big, let Pillow downsample for each icon size


def draw() -> Image.Image:
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    shield = [(256, 24), (456, 90), (456, 250), (420, 355), (256, 488), (92, 355), (56, 250),
              (56, 90)]
    d.polygon(shield, fill=(23, 82, 160, 255))
    inner = [(256, 64), (420, 118), (420, 246), (390, 332), (256, 442), (122, 332), (92, 246),
             (92, 118)]
    d.polygon(inner, fill=(41, 121, 214, 255))
    # eraser: a rotated rounded block, white end and soft pink end
    blk = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    b = ImageDraw.Draw(blk)
    b.rounded_rectangle((136, 186, 376, 326), radius=28, fill=(255, 255, 255, 255))
    b.rounded_rectangle((136, 186, 232, 326), radius=28, fill=(244, 143, 160, 255))
    b.rectangle((200, 186, 232, 326), fill=(244, 143, 160, 255))
    blk = blk.rotate(35, resample=Image.BICUBIC, center=(256, 256))
    im.alpha_composite(blk)
    return im


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw().save(OUT, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                          (128, 128), (256, 256)])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
