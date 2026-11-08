"""WO-149: contrast of the token pairs used by web/src/components/ui/, both themes. Offline.

Each case reads the class string from the component source, so renaming a token fails loudly,
then recomputes the WCAG 2.x ratio from the light-dark() values in tokens.css.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "web/src/components/ui"
TOKENS = ROOT / "web/src/styles/tokens.css"
TEXT, UI_MIN = 4.5, 3.0

Rgb = tuple[float, float, float]


def tokens() -> dict[str, tuple[str, str]]:
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


def ratio(fg: str, bg: str, theme: int) -> float:
    toks = tokens()
    hi, lo = sorted((luminance(rgb(toks[fg][theme])), luminance(rgb(toks[bg][theme]))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def source(name: str) -> str:
    return (UI / name).read_text(encoding="utf-8")


def variant(text: str, name: str) -> list[str]:
    match = re.search(rf'\b{name}:\s*"([^"]+)"', text)
    assert match, f"variant {name!r} not found"
    return match.group(1).split()


# (label, variant key, classes that must be present, text token, background token, minimum)
BUTTON_PAIRS = [
    ("primary rest", "primary", ["bg-brand", "text-brand-ink"], "brand-ink", "brand", TEXT),
    ("primary hover", "primary", ["hover:bg-heading", "text-brand-ink"], "brand-ink", "heading", TEXT),
    ("secondary rest", "secondary", ["bg-card", "text-brand"], "brand", "card", TEXT),
    ("secondary hover", "secondary", ["hover:bg-brand-soft", "text-brand"], "brand", "brand-soft", TEXT),
    ("secondary border", "secondary", ["border-line-strong", "bg-card"], "line-strong", "card", UI_MIN),
    ("ghost rest", "ghost", ["text-link"], "link", "bg", TEXT),
    ("ghost hover", "ghost", ["hover:bg-brand-soft", "text-link"], "link", "brand-soft", TEXT),
    ("onBrand rest", "onBrand", ["bg-band-brand-ink", "text-band-brand"], "band-brand", "band-brand-ink", TEXT),
]
# (label, variant key, text token, background token, minimum)
BADGE_PAIRS = [
    ("default", "default", "text", "surface", TEXT),
    ("ok", "ok", "ok", "card", TEXT),
    ("warn", "warn", "warn", "card", TEXT),
    ("brand", "brand", "heading", "brand-soft", TEXT),
    ("ok border", "ok", "ok", "card", UI_MIN),
    ("warn border", "warn", "warn", "card", UI_MIN),
]

THEMES = pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])


@THEMES
@pytest.mark.parametrize("label,key,classes,fg,bg,minimum", BUTTON_PAIRS, ids=[p[0] for p in BUTTON_PAIRS])
def test_button_variant_pairs(
    label: str, key: str, classes: list[str], fg: str, bg: str, minimum: float, theme: int
) -> None:
    found = variant(source("button-variants.ts"), key)
    missing = [c for c in classes if c not in found]
    assert not missing, f"{label}: {missing} not in {found}"
    assert ratio(fg, bg, theme) >= minimum


@THEMES
@pytest.mark.parametrize("label,key,fg,bg,minimum", BADGE_PAIRS, ids=[p[0] for p in BADGE_PAIRS])
def test_badge_pairs(label: str, key: str, fg: str, bg: str, minimum: float, theme: int) -> None:
    found = variant(source("Badge.astro"), key)
    assert f"text-{fg}" in found and f"bg-{bg}" in found
    assert ratio(fg, bg, theme) >= minimum


@THEMES
def test_alert_pairs(theme: int) -> None:
    text = source("Alert.astro")
    assert "bg-brand-soft text-text" in text and "bg-surface text-text" in text
    assert "text-brand" in text
    assert ratio("text", "brand-soft", theme) >= TEXT
    assert ratio("text", "surface", theme) >= TEXT
    assert ratio("brand", "brand-soft", theme) >= UI_MIN  # icon


@THEMES
def test_card_text(theme: int) -> None:
    card = source("Card.astro")
    assert "bg-card" in card and "text-text" in card
    assert ratio("text", "card", theme) >= TEXT
