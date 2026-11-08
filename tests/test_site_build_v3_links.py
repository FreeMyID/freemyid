"""Legacy site builder: links to v3-only pages point at the live site (SEC-102)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
pytest.importorskip("jinja2")


def _load(name: str):
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)


def _yaml(rel: str):
    return yaml.safe_load((ROOT / "site_src" / rel).read_text(encoding="utf-8"))


PAGES = _yaml("pages.yaml")
BASE_URL = _yaml("site.yaml")["base_url"]
V3_ONLY = [p["out"] for p in PAGES if p.get("v3_only")]
NORMAL = [p["out"] for p in PAGES if not p.get("v3_only") and p["out"].endswith("/")]


@pytest.fixture(scope="module")
def build_site():
    return _load("build_site")


@pytest.fixture(scope="module")
def render(build_site):
    """Render a template string the way site_src content does, from the home page."""
    site = build_site.Site()
    site.render_all()  # fills in the v3-only page list
    home = next(p for p in site.pages if p["id"] == "home")
    page = {**home, "absolute": False}
    by_id = {p["id"]: p for p in site.pages}
    return site._ctx(page, "x", by_id)["render"]


def test_manifest_has_v3_only_and_normal_pages():
    assert V3_ONLY, "pages.yaml no longer has v3_only pages; this test needs updating"
    assert NORMAL


@pytest.mark.parametrize("out", V3_ONLY)
def test_v3_only_link_points_at_live_site(render, out):
    assert str(render(f"{{{{ url('{out}') }}}}")) == BASE_URL + out


@pytest.mark.parametrize("out", V3_ONLY)
def test_v3_only_fragment_is_kept(render, out):
    assert str(render(f"{{{{ url('{out}#json') }}}}")) == BASE_URL + out + "#json"


def test_developers_link_when_listed_as_v3_only(render):
    if "developers/" not in V3_ONLY:
        pytest.skip("developers/ is no longer v3_only")
    assert str(render("{{ url('developers/') }}")) == "https://freemyid.org/developers/"


def test_normal_page_link_stays_relative(render):
    out = NORMAL[0]
    link = str(render(f"{{{{ url('{out}') }}}}"))
    assert link == out
    assert not link.startswith(("http://", "https://"))


def test_legacy_build_passes_its_link_check(build_site, tmp_path, capsys):
    out = tmp_path / "site"
    assert build_site.main(["--out", str(out)]) == 0
    assert " OK" in capsys.readouterr().out
    for v3 in V3_ONLY:
        assert not (out / v3 / "index.html").exists()
