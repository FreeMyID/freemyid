"""Per-page Open Graph images: pages.yaml og_image/og_alt drive Base.astro, a missing file falls back to og-home.

Unit cases run web/src/lib/og.ts directly with Node's built-in type stripping (Node >= 22.6); the build cases read
web/dist (run the web build first, as for the other tests/test_web_*.py files).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OG_TS = ROOT / "web/src/lib/og.ts"
OG_DIR = ROOT / "web/src/art/og"
DIST = ROOT / "web/dist"
BASE = yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8"))["base_url"]


def run_og(expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    code = f"import * as og from {json.dumps(OG_TS.as_uri())};\nconsole.log(JSON.stringify((() => {{ {expr} }})()));"
    r = subprocess.run([node, "--no-warnings", "--input-type=module", "-e", code],
                       capture_output=True, text=True, timeout=30, check=False)
    if r.returncode and "Unknown file extension" in r.stderr:
        pytest.skip("this node cannot strip TypeScript types")
    return r


def ok(expr: str):
    r = run_og(expr)
    assert r.returncode == 0, r.stderr[-500:]
    return json.loads(r.stdout)


def test_named_image_that_exists_is_used() -> None:
    got = ok('return og.resolveOg({id: "faq", og_image: "og-faq", og_alt: "A calm card."}, ["og-faq", "og-home"]);')
    assert got == {"ogImage": "assets/og-faq.png", "ogAlt": "A calm card.", "fallback": False}
    # ".png" in the entry is accepted too
    got = ok('return og.resolveOg({id: "faq", og_image: "og-faq.png", og_alt: "A."}, ["og-faq"]);')
    assert got["ogImage"] == "assets/og-faq.png"


def test_missing_image_falls_back_to_home_with_home_alt() -> None:
    got = ok('return og.resolveOg({id: "faq", og_image: "og-faq", og_alt: "Alt for a picture not there"}, ["og-home"]);')
    assert got == {"ogImage": "assets/og-home.png", "ogAlt": ok("return og.OG_DEFAULT_ALT;"), "fallback": True}


def test_no_og_image_uses_default() -> None:
    got = ok('return og.resolveOg({id: "x"}, ["og-home", "og-download"]);')
    assert got["ogImage"] == "assets/og-home.png" and got["fallback"] is False


@pytest.mark.parametrize("entry", ['{id: "x", og_image: "../secret"}', '{id: "x", og_image: "OG Home"}',
                                   '{id: "x", og_image: "og-faq"}'])
def test_bad_name_or_missing_alt_fails_loudly(entry: str) -> None:
    # bad names are typos (and a path guard), not "art not here yet"; an image that exists needs alt text
    r = run_og(f"return og.resolveOg({entry}, ['og-faq']);")
    assert r.returncode != 0 and "pages.yaml x" in r.stderr


def test_og_names_lists_only_og_pngs() -> None:
    assert ok('return og.ogNames(["og-home.png", "og-faq.png", "notes.txt", "og-x.svg", "logo.png", "og-..png"]);') \
        == ["og-faq", "og-home"]


def test_pages_yaml_og_entries_are_well_formed() -> None:
    pages = yaml.safe_load((ROOT / "site_src/pages.yaml").read_text(encoding="utf-8"))
    have = {p.stem for p in OG_DIR.glob("og-*.png")}
    assert {"og-home", "og-download"} <= have
    for p in pages:
        if p.get("og_image"):
            name = p["og_image"].removesuffix(".png")
            assert re.fullmatch(r"og-[a-z0-9]+(-[a-z0-9]+)*", name), p["id"]
            assert (p.get("og_alt") or "").strip(), f"{p['id']}: og_image needs og_alt"


def meta(page: str, prop: str) -> str:
    html = (DIST / page).read_text(encoding="utf-8")
    m = re.search(rf'<meta property="{re.escape(prop)}" content="([^"]*)"', html)
    assert m, (page, prop)
    return m.group(1)


@pytest.mark.skipif(not (DIST / "index.html").is_file(), reason="web/dist not built")
def test_build_uses_pages_yaml_og_and_publishes_every_image() -> None:
    assert meta("download/index.html", "og:image") == BASE + "assets/og-download.png"
    assert meta("download/index.html", "og:image:alt") == "Download Free My ID for Windows."
    assert meta("index.html", "og:image") == BASE + "assets/og-home.png"
    assert meta("faq/index.html", "og:image") == BASE + "assets/og-home.png"
    for png in OG_DIR.glob("og-*.png"):
        assert (DIST / "assets" / png.name).read_bytes() == png.read_bytes(), png.name
