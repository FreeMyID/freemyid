"""Home-page A/B/C test arms in the built site (docs/AB_TEST.md; web/scripts/build-arms.mjs).

Each arm is a full copy of the site under web/dist/x/<arm>/. These checks keep the copies harmless for search engines
(noindex, canonical on the normal URL, not in the sitemap), keep a visitor inside their arm (every own link stays
under /x/<arm>/), make every Download button countable, and keep the test fair (same Download wording and fine print
in every arm). Marked web_dist: skipped when web/dist is missing (conftest.py)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
ARMS = ("control", "heritage", "frontier", "glory")
DIRECTIONS = ARMS[1:]
FONTS = {"heritage": ("libre-caslon", "source-sans-3"), "frontier": ("zilla-slab", "oswald", "source-sans-3"),
         "glory": ("public-sans", "archivo-condensed")}


def arm_dir(arm: str) -> Path:
    d = DIST / "x" / arm
    if not (d / "index.html").is_file():
        pytest.skip(f"web/dist/x/{arm} not built (run `pnpm build && pnpm build:ab` in web/)")
    return d


def text_of(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


@pytest.mark.parametrize("arm", ARMS)
def test_arm_pages_are_noindex_with_canonical_on_the_normal_url(arm: str) -> None:
    pages = sorted(arm_dir(arm).rglob("*.html"))
    assert len(pages) > 50
    for p in pages:
        html = p.read_text(encoding="utf-8")
        assert '<meta name="robots" content="noindex">' in html, p
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        assert canon and "/x/" not in canon.group(1), p


@pytest.mark.parametrize("arm", ARMS)
def test_own_links_stay_inside_the_arm(arm: str) -> None:
    for p in sorted(arm_dir(arm).rglob("*.html")):
        for href in re.findall(r'<a\b[^>]*\shref="(/[^"]*)"', p.read_text(encoding="utf-8")):
            assert href.startswith(f"/x/{arm}/"), (p, href)


@pytest.mark.parametrize("arm", ARMS)
def test_every_download_button_is_counted(arm: str) -> None:
    home = (arm_dir(arm) / "index.html").read_text(encoding="utf-8")
    assert f'href="/x/{arm}/get/windows/"' in home
    visible = re.sub(r'<script type="application/ld\+json".*?</script>', "", home, flags=re.DOTALL)
    assert "https://freemyid.org/get/windows" not in visible
    stub = (arm_dir(arm) / "get/windows/index.html").read_text(encoding="utf-8")
    # without the worker, the arm's download page forwards to the real download
    assert 'http-equiv="refresh" content="0; url=https://freemyid.org/get/windows"' in stub
    assert '<meta name="robots" content="noindex">' in stub


def test_per_origin_files_are_not_copied_and_the_sitemap_skips_the_arms() -> None:
    for arm in ARMS:
        d = arm_dir(arm)
        for name in ("sitemap.xml", "robots.txt", "404.html"):
            assert not (d / name).exists(), (arm, name)
    sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    assert "/x/" not in sitemap
    assert "x/" not in (DIST / "robots.txt").read_text(encoding="utf-8")


def test_normal_site_is_untouched() -> None:
    home = (DIST / "index.html").read_text(encoding="utf-8")
    arm_dir("control")
    assert "data-direction" not in home and "/x/" not in home
    assert 'href="https://freemyid.org/get/windows"' in home
    css = "".join(p.read_text(encoding="utf-8") for p in (DIST / "_assets").glob("*.css"))
    assert ".woff2" not in css  # web fonts load only in the direction arms


def test_control_arm_is_the_current_design() -> None:
    normal = text_of((DIST / "index.html").read_text(encoding="utf-8"))
    control = text_of((arm_dir("control") / "index.html").read_text(encoding="utf-8"))
    assert normal == control


@pytest.mark.parametrize("arm", DIRECTIONS)
def test_direction_arms_load_only_their_own_fonts(arm: str) -> None:
    d = arm_dir(arm)
    home = (d / "index.html").read_text(encoding="utf-8")
    assert f'<html lang="en" data-direction="{arm}">' in home
    css_files = re.findall(r'<link rel="stylesheet" href="/x/' + arm + r'/(_assets/[^"]+\.css)"', home)
    css = "".join((d / f).read_text(encoding="utf-8") for f in css_files)
    used = set(re.findall(r"/([a-z0-9-]+?)(?:-\d{3}|-var|-italic|-400-italic)*\.[A-Za-z0-9_-]+\.woff2", css))
    assert used, arm
    for font in used:
        assert font.startswith(FONTS[arm]), (arm, font)


def test_arms_differ_in_design_not_in_promises() -> None:
    """Fair test: every direction home has the same Download wording, fine print and trust panel."""
    must = ("Download Free My ID", "Free for Windows 10 and 11",
            "Practice mode comes first, so no removal requests go out until you say so.",
            'Windows may show a blue "protected your PC" box the first time.',
            ("No account. No cloud. Never asks for your Social Security number or bank or card details, and never "
             "charges you. Free and open source. Uninstall anytime."))
    for arm in DIRECTIONS:
        html = (arm_dir(arm) / "index.html").read_text(encoding="utf-8")
        text = text_of(html)
        for m in must:
            assert m in text, (arm, m)
        assert len(re.findall(r"<h1\b", html)) == 1, arm
