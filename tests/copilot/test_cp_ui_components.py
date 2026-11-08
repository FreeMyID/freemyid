"""WO-156 (GP-11): SOURCE-LEVEL guard for web/src/components/ui/. Not a browser run. Offline.

Reads component source and global.css as text. It cannot prove a focus ring is painted on screen;
it checks that the shared :focus-visible rule exists and that no UI component switches it off, and
that no component disables an element from a click handler. Add a browser test for rendering.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "web/src/components/ui"
GLOBAL_CSS = ROOT / "web/src/styles/global.css"

SOURCES = sorted(p for p in UI.iterdir() if p.suffix in {".astro", ".ts", ".tsx"})

INTERACTIVE = re.compile(
    r"<(?:a|button|input|select|textarea|summary|details)\b|tabindex=|buttonVariants|role=[\"'](?:button|link|tab|switch)",
    re.IGNORECASE,
)
FOCUS_OFF = re.compile(
    r"(?:^|[\s\"'`:])(?:(?:focus|focus-visible)(?:-within)?:)?(?:outline-none|outline-hidden|outline-0|ring-0)(?=[\s\"'`]|$)"
    r"|outline\s*:\s*(?:none|0)\b",
    re.IGNORECASE,
)
DISABLED_IN_HANDLER = re.compile(
    r"(?:on(?:click|press)\s*=\s*[^>]*\.disabled\s*=(?!=)"
    r"|addEventListener\(\s*[\"']click[\"'][\s\S]{0,400}?\.disabled\s*=(?!=)"
    r"|setAttribute\(\s*[\"']disabled[\"'])",
    re.IGNORECASE,
)


def hits(pattern: re.Pattern[str], path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [
        f"{path.relative_to(ROOT)}:{text.count(chr(10), 0, m.start()) + 1}"
        for m in pattern.finditer(text)
    ]


def test_components_found() -> None:
    assert {p.name for p in SOURCES} >= {"button-variants.ts", "Card.astro"}


def test_global_focus_visible_rule_is_visible() -> None:
    css = GLOBAL_CSS.read_text(encoding="utf-8")
    rule = re.search(r"(?<![\w-]):focus-visible\s*\{([^}]*)\}", css)
    assert rule, "global.css has no :focus-visible rule"
    body = rule.group(1)
    width = re.search(r"outline\s*:\s*(\d+)px\s+solid\s+var\(--fmi-color-focus\)", body)
    assert width and int(width.group(1)) >= 2, "focus outline must be >=2px and use the focus token"


def test_interactive_components_are_identified() -> None:
    interactive = {p.name for p in SOURCES if INTERACTIVE.search(p.read_text(encoding="utf-8"))}
    assert "button-variants.ts" in interactive
    assert "Badge.astro" not in interactive


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_component_does_not_remove_focus_style(path: Path) -> None:
    assert hits(FOCUS_OFF, path) == []


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_component_does_not_set_disabled_in_click_handler(path: Path) -> None:
    assert hits(DISABLED_IN_HANDLER, path) == []


@pytest.mark.parametrize(
    ("snippet", "pattern"),
    [
        ('class="btn focus:outline-none"', FOCUS_OFF),
        ('class="x outline-none"', FOCUS_OFF),
        ("a { outline: none; }", FOCUS_OFF),
        ('<button onclick="this.disabled = true">', DISABLED_IN_HANDLER),
        ("b.addEventListener('click', () => { b.disabled = true; })", DISABLED_IN_HANDLER),
    ],
)
def test_detectors_catch_known_bad_patterns(
    snippet: str, pattern: re.Pattern[str], tmp_path: Path
) -> None:
    f = tmp_path / "Bad.astro"
    f.write_text(snippet, encoding="utf-8")
    text = f.read_text(encoding="utf-8")
    assert pattern.search(text)
