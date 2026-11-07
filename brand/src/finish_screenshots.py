"""Crop raw captures and write PNG + WebP (<150 KB) to brand/screenshots/. Usage: finish_screenshots.py <raw_dir> <out_dir>"""
import sys, io
from pathlib import Path
from PIL import Image
raw, out = Path(sys.argv[1]), Path(sys.argv[2])
crops = {"wizard-address": 1580, "wizard-name": None, "dashboard": 2090, "report": 2250}
for n, h in crops.items():
    im = Image.open(raw / f"{n}.png").convert("RGB")
    if n == "wizard-name":
        h = min(im.height, 1850)
    im = im.crop((0, 0, im.width, h))
    im.save(out / f"{n}.png", optimize=True)
    for q in (88, 82, 76, 70, 62, 55):
        b = io.BytesIO(); im.save(b, "WEBP", quality=q, method=6)
        if b.tell() < 150_000: break
    (out / f"{n}.webp").write_bytes(b.getvalue())
    print(n, im.size, q, b.tell() // 1024, "KB webp", (out / f"{n}.png").stat().st_size // 1024, "KB png")
