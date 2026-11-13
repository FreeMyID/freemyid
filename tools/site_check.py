#!/usr/bin/env python3
"""Check a built Free My ID site folder. Stdlib only.

    python3 tools/site_check.py site [--base-url https://freemyid.org/] [--base-path /]

Every HTML page must have: lang, CSP meta (script-src 'none', no unsafe-*), referrer meta, a title of
60 characters or less, a meta description of 155 or less, a canonical link, exactly one <h1>.
No asset (stylesheet, image, script, font, iframe...) may come from another origin; no inline <script>
except JSON-LD; no style="" attributes (blocked by the CSP anyway). Internal links and #anchors must
resolve. Every <img> needs alt, width and height. The sitemap must list exactly the indexable pages.
No data from the private full registry (brokers/registry.yaml) may appear in the output. The one
exception is the public coverage list (brokers/coverage.public.yaml, written by
tools/export_coverage.py): the main-site hostnames in it may be named, as bare hostnames only.
A private opt-out URL, an email address, any other private hostname, and a coverage-list hostname
followed by a path or used as an email domain are all still errors.

The private inputs are looked for beside this checkout. From a worktree or a checkout without them,
point at them with FMID_FULL_REGISTRY (the full registry) and FMID_HOST_HASHES (the hash list from
tools/gen_private_host_hashes.py).
"""
from __future__ import annotations

import argparse
import hashlib
import os
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
    full = Path(os.environ.get("FMID_FULL_REGISTRY") or ROOT / "brokers" / "registry.yaml")
    sample = ROOT / "brokers" / "registry.sample.yaml"
    if not full.exists() or not sample.exists():
        return []
    pat = re.compile(r"^\s*(?:opt_out_url|opt_out_email):\s*\"?([^\s\"#]+)", re.MULTILINE)
    full_vals = set(pat.findall(full.read_text(encoding="utf-8")))
    sample_text = sample.read_text(encoding="utf-8")  # anything in the public sample is fine
    return sorted(v for v in full_vals if len(v) > 8 and v not in sample_text)


HOST_HASHES = Path(__file__).resolve().parent / "private_host_hashes.txt"
HOST_RE = re.compile(r"(?<![a-z0-9-])[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.IGNORECASE)


def private_host_hashes() -> set[str]:
    path = Path(os.environ.get("FMID_HOST_HASHES") or HOST_HASHES)
    if not path.exists():
        return set()
    return {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


COVERAGE = ROOT / "brokers" / "coverage.public.yaml"


def coverage_hosts(path: Path | None = None) -> set[str]:
    """Main-site hostnames in the public coverage list (tools/export_coverage.py). These are public
    by orchestrator decision 2026-11-12, so a page may name them. Stdlib only: the file is one
    `site: "host"` per row."""
    path = path or COVERAGE
    if not path.exists():
        return set()
    hosts = re.findall(r'\bsite: "([^"]+)"', path.read_text(encoding="utf-8"))
    return {h.lower().rstrip(".").removeprefix("www.") for h in hosts}


# Hosts that are in the private registry but are well-known public addresses that a public page
# may name anyway (orchestrator ruling 2026-11-07: /protect/ credit-freeze guides).
PUBLIC_OK_HOSTS = {"consumer.risk.lexisnexis.com"}


_PATH_START = re.compile(r"[/?][A-Za-z0-9%_~.\-]")


def host_leaks(text: str, hashes: set[str], public: set[str] | frozenset[str] = frozenset()
               ) -> list[tuple[str, str]]:
    """Private-registry hostnames in text, as (kind, hash prefix); never the names.

    "private": the hostname is not in the public coverage list. "path": it is, but here it is
    followed by a path or query (how an opt-out URL would look) or it is an email domain. Only the
    bare site name is public."""
    found = set()
    for m in HOST_RE.finditer(text):
        h = m.group(0).lower().rstrip(".")
        h = h.removeprefix("www.")
        if h in PUBLIC_OK_HOSTS:
            continue
        d = hashlib.sha256(h.encode()).hexdigest()
        if d not in hashes:
            continue
        if h not in public:
            found.add(("private", d[:12]))
        elif text[m.start() - 1:m.start()] == "@" or _PATH_START.match(text, m.end()):
            found.add(("path", d[:12]))
    return sorted(found)


def hashed_host_leaks(text: str, hashes: set[str],
                      public: set[str] | frozenset[str] = frozenset()) -> list[str]:
    """Hash prefixes of every hostname host_leaks reports."""
    return sorted({d for _, d in host_leaks(text, hashes, public)})


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
        og = p.meta("property", "og:image")
        if og and (not og.startswith(base_url) or not (site / og[len(base_url):]).is_file()):
            err(f"og:image {og} is not a file in this site")
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
    # Works without the full registry: compare hashed hostnames in the output with the checked-in list.
    # Hostnames in the public coverage list are allowed, as bare hostnames only.
    hashes = private_host_hashes()
    public = coverage_hosts()
    for f in sorted(site.rglob("*")):
        if hashes and f.is_file() and f.suffix in (".html", ".xml", ".txt", ".css"):
            for kind, d in host_leaks(f.read_text(encoding="utf-8"), hashes, public):
                errors.append(
                    f"{f.relative_to(site)}: contains a private-only broker hostname (hash {d}...)"
                    if kind == "private" else
                    f"{f.relative_to(site)}: a coverage-list site is followed by a path or used as an "
                    f"email domain; only the bare site name is public (hash {d}...)")
    for f in sorted(site.rglob("*")):
        if f.is_file() and f.suffix == ".html" and re.search(r"registry\.yaml\b",
                                                              f.read_text(encoding="utf-8")):
            errors.append(f"{f.relative_to(site)}: mentions registry.yaml (link the sample only)")
    errors += content_rules(site)
    return errors


# Copy rules (POSITIONING.md, WEBSITE_REDESIGN.md D5/D7/D8). Visible text only; the noindex styleguide is skipped.
BANNED_PHRASES = [
    (r"\bguarantee[sd]?\b", "guarantee"), (r"\b100\s?%", "100%"), (r"\berase[sd]?\b", "erase"),
    (r"\bforever\b", "forever"), (r"\balways free\b", "always free"),
    (r"\b(fifteen|15)[ -]minutes?\b", "fifteen minutes (never timed, D8)"),
    (r"\baudited\b", "audited (D8)"), (r"\btrusted by\b", "trusted by (D8)"),
    (r"[\u2605\u2606\u2B50]", "star glyph (ratings, D8)"), (r"\b\d(\.\d)?\s*(/|out of)\s*5\b", "x out of 5 rating"),
    (r"\b(five|5)[ -]stars?\b", "star rating"), (r"\b\d[\d,]*\s+(customers|users|reviews|downloads)\b", "counter or social proof"),
    (r"\bhackers\b", "fear selling (POSITIONING rule 3)"), (r"\bidentity theft\b", "fear selling"),
    (r"\bthey have to answer\b|\bthe law makes them\b", "state-law qualifier missing (POSITIONING)"),
]


# The rows of the coverage list on /brokers/: names, hostnames and family names from the public list.
COVERAGE_ROWS = re.compile(r'<ul class="cov-list".*?</ul>', re.DOTALL)


def visible_text(html: str) -> str:
    import html as htmllib
    html = re.sub(r"<(script|style|head)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", html)))


def release_is_null() -> bool:
    f = ROOT / "site_src" / "data" / "release.yaml"
    if not f.exists():
        return True
    m = re.search(r"^version:\s*(\S+)", f.read_text(encoding="utf-8"), re.MULTILINE)
    return not m or m.group(1) in ("null", "~", "''", '""')


def content_rules(site: Path) -> list[str]:
    errors: list[str] = []
    no_release = release_is_null()
    for f in sorted(site.rglob("*.html")):
        rel = f.relative_to(site).as_posix()
        raw = f.read_text(encoding="utf-8")
        if rel.startswith("styleguide/"):
            continue
        # The coverage list rows are company and site names from brokers/coverage.public.yaml (data, not
        # our claims): a broker called "Five Star ..." is not a star rating. Everything around the rows
        # is still checked.
        copy = COVERAGE_ROWS.sub(" ", raw) if rel == "brokers/index.html" else raw
        text = visible_text(copy)
        for pat, label in BANNED_PHRASES:
            # /protect/ pages quote third-party time estimates ("about 15 minutes online" at a credit
            # bureau). D8 forbids timing *our app's* setup, not quoting how long someone else's site takes.
            if rel.startswith("protect/") and label.startswith("fifteen minutes"):
                continue
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                errors.append(f"{rel}: banned phrase [{label}]: ...{text[max(0, m.start() - 40):m.end() + 40]}...")
        # Product pictures must say they are made-up data, inside the same <figure>.
        for im in re.finditer(r"<img\b[^>]*assets/screenshots/[^>]*>", raw):
            fig = [m for m in re.finditer(r"<figure\b.*?</figure>", raw, re.DOTALL) if m.start() < im.start() < m.end()]
            if not fig:
                errors.append(f"{rel}: screenshot not inside a <figure> with a caption: {im.group(0)[:80]}")
            elif "made-up data" not in visible_text(fig[0].group(0)).lower():
                errors.append(f"{rel}: screenshot caption lacks 'made-up data': {im.group(0)[:80]}")
        # D5: no download CTA to a release while release.yaml has no version.
        if no_release:
            for m in re.finditer(r"<a\b[^>]*\bhref=\"([^\"]*)\"[^>]*>", raw):
                href, tag = m.group(1), m.group(0)
                if re.search(r"/releases/(latest|download)|\.exe($|[?#])", href):
                    errors.append(f"{rel}: link to a release asset while release.yaml version is null: {href}")
                elif re.search(r"/releases/?$", href) and re.search(r'class="[^"]*\bbtn\b', tag):
                    errors.append(f"{rel}: button to the releases page while release.yaml version is null: {href}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a built Free My ID site folder.")
    ap.add_argument("site", nargs="?", default=str(ROOT / "site"))
    ap.add_argument("--base-url", default="https://freemyid.org/")
    ap.add_argument("--base-path", default="/")
    args = ap.parse_args(argv)
    errors = check_site(Path(args.site), args.base_url, args.base_path)
    for e in errors:
        print("ERROR:", e)
    n = len(list(Path(args.site).rglob("*.html")))
    print(f"site_check: {n} HTML pages, {'OK' if not errors else str(len(errors)) + ' problem(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
