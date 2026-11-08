"""WO-125 (CA-1): the onBrand button label stays readable on hover in both themes. Offline."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "web/src/components/ui/button-variants.ts"
TOKENS = ROOT / "web/src/styles/tokens.css"
MIN_RATIO = 4.5
# onBrand buttons sit on the brand band, so a translucent hover fill blends with it.
BAND_TOKEN = "band-brand"

Rgb = tuple[float, float, float]


def on_brand_classes() -> list[str]:
    match = re.search(r'onBrand:\s*"([^"]+)"', VARIANTS.read_text(encoding="utf-8"))
    assert match, "onBrand variant not found"
    return match.group(1).split()


def tokens() -> dict[str, tuple[str, str]]:
    """Map token name to (light, dark) from the first :root block's light-dark() values."""
    root = TOKENS.read_text(encoding="utf-8").split(":root[data-theme", 1)[0]
    found = re.findall(
        r"--fmi-color-([\w-]+):\s*light-dark\((#[0-9a-fA-F]{6}),\s*(#[0-9a-fA-F]{6})\)", root
    )
    return {name: (light, dark) for name, light, dark in found}


def rgb(hex_color: str) -> Rgb:
    return tuple(int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def luminance(color: Rgb) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: Rgb, b: Rgb) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(top: Rgb, bottom: Rgb, alpha: float) -> Rgb:
    return tuple(t * alpha + b * (1 - alpha) for t, b in zip(top, bottom))  # type: ignore[return-value]


def utility(prefix: str) -> tuple[str, float]:
    """Return (token, opacity) for a class such as `hover:bg-name/90`."""
    for cls in on_brand_classes():
        match = re.fullmatch(re.escape(prefix) + r"([\w-]+?)(?:/(\d+))?", cls)
        if match:
            return match.group(1), int(match.group(2) or 100) / 100
    raise AssertionError(f"no {prefix}* class in onBrand")


@pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])
def test_on_brand_hover_text_is_readable(theme: int) -> None:
    palette = tokens()
    text_token, _ = utility("text-")
    hover_token, alpha = utility("hover:bg-")
    band = rgb(palette[BAND_TOKEN][theme])
    hover_bg = blend(rgb(palette[hover_token][theme]), band, alpha)
    value = ratio(rgb(palette[text_token][theme]), hover_bg)
    print(f"onBrand hover {'dark' if theme else 'light'}: {value:.2f}:1")
    assert value >= MIN_RATIO
