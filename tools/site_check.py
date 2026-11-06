#!/usr/bin/env python3
"""Check a built Free My ID site folder. Stdlib only.

    python3 tools/site_check.py site [--base-url https://freemyid.github.io/freemyid/] [--base-path /freemyid/]

Every HTML page must have: lang, CSP meta (script-src 'none', no unsafe-*), referrer meta, a title of
60 characters or less, a meta description of 155 or less, a canonical link, exactly one <h1>.
No asset (stylesheet, image, script, font, iframe...) may come from another origin; no inline <script>
except JSON-LD; no style="" attributes (blocked by the CSP anyway). Internal links and #anchors must
resolve. Every <img> needs alt, width and height. The sitemap must list exactly the indexable pages.
No data from the private full registry (brokers/registry.yaml) may appear in the output.
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
ASSET_ATTRS = {("link", "href"), ("img", "src"), ("script", "src"), ("source", "src"), ("source", "srcset"),
               ("img", "srcset"), ("iframe", "src"), ("embed", "src"), ("object", "data"), ("video", "src"),
               ("audio", "src"), ("video", "poster"), ("track", "src")}
NON_ASSET_LINK_RELS = {"canonical", "alternate", "author", "license", "help", "next", "prev", "search"}


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = ""
        self._in_title = False
        self.metas: list[dict] = []
        self.links: list[dict] = []
        self.h1 = 0
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.assets: list[str] = []
        self.imgs: list[dict] = []
        self.scripts: list[dict] = []
        self._script: dict | None = None
        self.style_attrs = 0
        self.inline_handlers: list[str] = []
        self.forms = 0
        self.iframes = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        if "style" in a:
            self.style_attrs += 1
        for k in a:
            if k.startswith("on"):
                self.inline_handlers.append(f"{tag}[{k}]")
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "h1":
            self.h1 += 1
        elif tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "script":
            self._script = {"attrs": a, "body": ""}
        elif tag == "form":
            self.forms += 1
        elif tag in ("iframe", "embed", "object"):
            self.iframes += 1
        for t, attr in ASSET_ATTRS:
            if tag == t and attr in a:
                if tag == "link" and set(a.get("rel", "").split()) & NON_ASSET_LINK_RELS:
                    continue
                for part in a[attr].split(","):
                    if part.strip():
                        self.assets.append(part.strip().split()[0])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._script is not None:
            self.scripts.append(self._script)
            self._script = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._script is not None:
            self._script["body"] += data

    def meta(self, key: str, value: str) -> str | None:
        for m in self.metas:
            if m.get(key, "").lower() == value.lower():
                return m.get("content")
        return None

    def link(self, rel: str) -> str | None:
        for lk in self.links:
            if rel in lk.get("rel", "").split():
                return lk.get("href")
        return None


def parse(path: Path) -> Page:
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    p.close()
    return p


def resolve(site: Path, page_file: Path, href: str, base_path: str) -> tuple[Path | None, str]:
    """Map an internal href to (file, fragment). Returns (None, '') for external/mailto links."""
    parts = urlsplit(href)
    if parts.scheme or parts.netloc:
        return None, ""
    path, frag = unquote(parts.path), parts.fragment
    if path == "":
        return page_file, frag
    if path.startswith("/"):
        if not path.startswith(base_path):
            return site / "__outside_base_path__", frag
        target = site / path[len(base_path):]
    else:
        target = (page_file.parent / path)
    if path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target, frag


def full_registry_needles() -> list[str]:
    """Opt-out URLs and emails that are in the private full registry but NOT in the public sample.
    Skipped when the full registry isn't present (e.g. after it moves to a private repo)."""
    full = ROOT / "brokers" / "registry.yaml"
    sample = ROOT / "brokers" / "registry.sample.yaml"
    if not full.exists() or not sample.exists():
        return []
    pat = re.compile(r"^\s*(?:opt_out_url|opt_out_email):\s*\"?([^\s\"#]+)", re.MULTILINE)
    full_vals = set(pat.findall(full.read_text(encoding="utf-8")))
    sample_text = sample.read_text(encoding="utf-8")  # anything in the public sample is fine
    return sorted(v for v in full_vals if len(v) > 8 and v not in sample_text)


def check_site(site: Path, base_url: str, base_path: str) -> list[str]:
    errors: list[str] = []
    site = site.resolve()
    pages: dict[Path, Page] = {}
    for f in sorted(site.rglob("*.html")):
        pages[f.resolve()] = parse(f)

    indexable: set[str] = set()
    for f, p in pages.items():
        rel = f.relative_to(site).as_posix()
        err = lambda msg, rel=rel: errors.append(f"{rel}: {msg}")
        if p.lang != "en":
            err("missing <html lang=\"en\">")
        csp = p.meta("http-equiv", "Content-Security-Policy")
        if not csp:
            err("missing Content-Security-Policy meta")
        else:
            if "script-src 'none'" not in csp and "script-src 'self'" not in csp:
                err("CSP must set script-src 'none' (or 'self')")
            if "unsafe-" in csp:
                err("CSP must not allow unsafe-inline/unsafe-eval")
            if "default-src 'self'" not in csp:
                err("CSP must set default-src 'self'")
        if p.meta("name", "referrer") != "no-referrer":
            err("missing <meta name=\"referrer\" content=\"no-referrer\">")
        title = p.title.strip()
        if not title:
            err("missing <title>")
        elif len(title) > 60:
            err(f"title is {len(title)} chars (max 60): {title!r}")
        desc = p.meta("name", "description")
        if not desc:
            err("missing meta description")
        elif len(desc) > 155:
            err(f"description is {len(desc)} chars (max 155)")
        canon = p.link("canonical")
        if not canon:
            err("missing canonical link")
        elif not canon.startswith(base_url):
            err(f"canonical {canon} is not under {base_url}")
        if p.h1 != 1:
            err(f"has {p.h1} <h1> elements (need exactly 1)")
        if p.style_attrs:
            err(f"{p.style_attrs} style=\"\" attribute(s) (blocked by CSP; use style.css)")
        if p.inline_handlers:
            err(f"inline event handlers: {p.inline_handlers}")
        if p.forms:
            err("contains a <form> (the site must not send data anywhere)")
        if p.iframes:
            err("contains an iframe/embed/object (no embeds)")
        for s in p.scripts:
            if s["attrs"].get("src"):
                continue  # judged by the asset-origin check below
            if s["attrs"].get("type") != "application/ld+json":
                err("inline <script> that is not JSON-LD")
        for a in p.assets:
            sp = urlsplit(a)
            if sp.scheme in ("http", "https") or a.startswith("//"):
                err(f"asset from another origin: {a}")
            elif sp.scheme == "data":
                err(f"data: URI asset (blocked by CSP img-src 'self'): {a[:40]}")
        for img in p.imgs:
            for attr in ("alt", "width", "height"):
                if attr not in img:
                    err(f"<img src={img.get('src')!r}> missing {attr}")
        robots = (p.meta("name", "robots") or "").lower()
        if "noindex" not in robots:
            indexable.add(rel)
        for href in p.hrefs:
            if href.startswith(("mailto:", "tel:")):
                continue
            target, frag = resolve(site, f, href, base_path)
            if target is None:
                continue
            target = target.resolve() if target.exists() else target
            if not target.exists():
                err(f"broken link {href!r}")
                continue
            if frag:
                tp = pages.get(target)
                if tp is not None and frag not in tp.ids:
                    err(f"broken anchor {href!r}")
        for a in p.assets:
            sp = urlsplit(a)
            if sp.scheme or a.startswith("//"):
                continue
            target, _ = resolve(site, f, a.split("?")[0], base_path)
            if target is not None and not target.exists():
                err(f"missing asset {a!r}")

    # Sitemap must list exactly the indexable pages.
    sm = site / "sitemap.xml"
    if not sm.exists():
        errors.append("sitemap.xml missing")
    else:
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text or "" for e in ET.parse(sm).getroot().findall("s:url/s:loc", ns)]
        listed = set()
        for loc in locs:
            if not loc.startswith(base_url):
                errors.append(f"sitemap: {loc} not under {base_url}")
                continue
            r = loc[len(base_url):]
            listed.add(r + "index.html" if r == "" or r.endswith("/") else r)
        for r in sorted(indexable - listed):
            errors.append(f"sitemap: indexable page {r} not listed")
        for r in sorted(listed - indexable):
            errors.append(f"sitemap: lists {r}, which is missing or noindex")
    robots_txt = site / "robots.txt"
    if not robots_txt.exists() or "Sitemap:" not in robots_txt.read_text(encoding="utf-8"):
        errors.append("robots.txt missing or has no Sitemap line")

    # CSS must not pull anything from another origin.
    for css in site.rglob("*.css"):
        for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", css.read_text(encoding="utf-8")):
            if re.match(r"(https?:)?//", u) or u.startswith("data:"):
                errors.append(f"{css.name}: external or data: url() {u[:50]}")
        if re.search(r"@import\s", css.read_text(encoding="utf-8")):
            errors.append(f"{css.name}: @import not allowed")

    # No private full-registry data in the output.
    needles = full_registry_needles()
    if needles:
        for f in sorted(site.rglob("*")):
            if f.is_file() and f.suffix in (".html", ".xml", ".txt", ".css"):
                text = f.read_text(encoding="utf-8")
                for n in needles:
                    if n in text:
                        errors.append(f"{f.relative_to(site)}: contains full-registry-only value {n}")
    for f in sorted(site.rglob("*")):
        if f.is_file() and f.suffix == ".html" and re.search(r"registry\.yaml\b",
                                                              f.read_text(encoding="utf-8")):
            errors.append(f"{f.relative_to(site)}: mentions registry.yaml (link the sample only)")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a built Free My ID site folder.")
    ap.add_argument("site", nargs="?", default=str(ROOT / "site"))
    ap.add_argument("--base-url", default="https://freemyid.github.io/freemyid/")
    ap.add_argument("--base-path", default="/freemyid/")
    args = ap.parse_args(argv)
    errors = check_site(Path(args.site), args.base_url, args.base_path)
    for e in errors:
        print("ERROR:", e)
    n = len(list(Path(args.site).rglob("*.html")))
    print(f"site_check: {n} HTML pages, {'OK' if not errors else str(len(errors)) + ' problem(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
