"""Website build guards (SECURITY_REVIEW "Website v2 (redesign)")."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
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


@pytest.fixture(scope="module")
def build_site():
    return _load("build_site")


def _pages() -> list[Path]:
    return sorted(SITE.rglob("*.html"))


def test_out_inside_repo_is_refused(build_site, capsys):
    target = ROOT / "site_tmp_should_not_exist"
    assert build_site.main(["--out", str(target)]) == 2
    assert not target.exists()
    assert "outside the repo" in capsys.readouterr().out


@pytest.mark.xfail(strict=True, reason="SEC-W2-01: --out rmtree's any existing path outside the repo")
def test_out_never_deletes_a_non_site_directory(build_site, tmp_path):
    victim = tmp_path / "Documents"
    victim.mkdir()
    (victim / "taxes.txt").write_text("not a site build")
    build_site.main(["--out", str(victim)])
    assert (victim / "taxes.txt").exists()


def test_string_templates_autoescape(build_site):
    env = build_site.Site().env
    assert env.from_string("{{ x }}").render(x="<script>") == "&lt;script&gt;"


def test_every_page_has_the_strict_csp_and_no_inline_code():
    pages = _pages()
    assert pages
    csps = set()
    for f in pages:
        html = f.read_text(encoding="utf-8")
        m = re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', html)
        assert len(m) == 1, f
        csps.add(m[0])
        assert not re.search(r"\sstyle=", html), f
        assert not re.search(r"\son[a-z]+=", html), f
        assert "javascript:" not in html.lower(), f
        for tag in re.findall(r"<script\b[^>]*>", html):
            assert tag == '<script type="application/ld+json">', f
        assert not re.search(r'(src|srcset)="(https?:)?//', html), f
        for link in re.findall(r"<link\b[^>]*>", html):   # canonical points at our own URL, never fetched
            if 'rel="canonical"' not in link:
                assert not re.search(r'href="(https?:)?//', link), (f, link)
        assert "data:image" not in html and 'src="data:' not in html, f
    (csp,) = csps
    csp = csp.replace("&#39;", "'")
    for d in ("default-src 'self'", "script-src 'none'", "connect-src 'none'", "object-src 'none'",
              "frame-src 'none'", "form-action 'none'", "base-uri 'none'"):
        assert d in csp
    assert "unsafe" not in csp and "http" not in csp and "data:" not in csp


def test_jsonld_is_data_only_and_has_no_unreleased_download():
    release = (ROOT / "site_src" / "data" / "release.yaml").read_text(encoding="utf-8")
    unreleased = re.search(r"^version:\s*(null|~)?\s*(#.*)?$", release, re.MULTILINE) is not None
    n = 0
    for f in _pages():
        for body in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                               f.read_text(encoding="utf-8"), re.DOTALL):
            data = json.dumps(json.loads(body))
            n += 1
            assert "<" not in data and "javascript:" not in data, f
            if unreleased:
                assert "downloadUrl" not in data and "softwareVersion" not in data, f
    assert n


def test_css_has_no_external_or_data_urls():
    css = (SITE / "style.css").read_text(encoding="utf-8")
    for u in re.findall(r"url\(([^)]*)\)", css):
        assert not re.match(r"\s*['\"]?(https?:|//|data:)", u), u
    assert "@import" not in css
