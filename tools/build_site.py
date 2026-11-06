#!/usr/bin/env python3
"""Build the Free My ID website: site_src/ (jinja2 templates + YAML data) -> site/.

    .venv/bin/python tools/build_site.py           # rebuild site/ (then runs site_check)
    .venv/bin/python tools/build_site.py --check   # CI: fail if site/ is stale or site_check fails

site/ is committed so it stays readable and GitHub Pages can publish it as-is. The build is
deterministic: no timestamps, sorted inputs, the only dates come from YAML data.

Data: only the PUBLIC sample registry (brokers/registry.sample.yaml, CC BY-NC 4.0) is read.
Never point this at brokers/registry.yaml: the full registry is private.
Stdlib + jinja2 + PyYAML only.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
from pathlib import Path

import jinja2
import yaml
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site_src"
OUT = ROOT / "site"
# public sample ONLY. FMID_SAMPLE_REGISTRY lets a builder pin a committed copy (never the full registry).
SAMPLE_REGISTRY = Path(os.environ.get("FMID_SAMPLE_REGISTRY") or ROOT / "brokers" / "registry.sample.yaml")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_check

CSP = ("default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; "
       "connect-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'")


# --------------------------------------------------------------------------- helpers
def load_yaml(path: Path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check_contrast(tokens: dict) -> list[str]:
    errors = []
    colors = tokens["color"]
    for fg, bg, minimum in tokens["pairs"]:
        for i, theme in enumerate(("light", "dark")):
            r = contrast(colors[fg][i], colors[bg][i])
            if r < minimum:
                errors.append(f"contrast {theme}: {fg} on {bg} = {r:.2f} < {minimum}")
    return errors


def tokens_css(tokens: dict) -> str:
    """The `tokens` cascade layer. light-dark() where supported, a media-query fallback otherwise.
    The data-theme="light|dark" attribute on <html> overrides the system setting in both paths."""
    colors = tokens["color"]
    lines = ["@layer tokens {", "  :root {"]
    for name, (light, dark) in colors.items():
        lines.append(f"    --color-{name}: light-dark({light}, {dark});")
    for group, prefix in (("space", "space"), ("step", "step"), ("radius", "radius")):
        for k, v in tokens[group].items():
            lines.append(f"    --{prefix}-{k}: {v};")
    for k, v in tokens["misc"].items():
        lines.append(f"    --{k}: {v};")
    lines.append("  }")
    light = "\n".join(f"    --color-{n}: {v[0]};" for n, v in colors.items())
    dark = "\n".join(f"    --color-{n}: {v[1]};" for n, v in colors.items())
    lines += [
        "  /* Fallback for browsers without light-dark() (before ~2024). */",
        "  @supports not (color: light-dark(#000, #fff)) {",
        "    :root {", light, "    }",
        "    @media (prefers-color-scheme: dark) {",
        "      :root:not([data-theme=\"light\"]) {", dark.replace("    --", "        --"), "      }",
        "    }",
        "    :root[data-theme=\"dark\"] {", dark, "    }",
        "  }",
        "}",
        "/* Styleguide swatches (generated; the CSP forbids style=\"\" attributes). */",
        "@layer pages {",
    ]
    lines += [f"  .sw--{n}-l {{ background: {v[0]}; }} .sw--{n}-d {{ background: {v[1]}; }}"
              for n, v in colors.items()]
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_css(tokens: dict) -> str:
    parts = []
    for f in sorted((SRC / "css").glob("*.css")):
        parts.append(f.read_text(encoding="utf-8").rstrip() + "\n")
        if f.name.startswith("00-"):
            parts.append(tokens_css(tokens))
    return "\n".join(parts)


def slugify(text: str) -> str:
    text = text.lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def ld_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def rel_url(from_out: str, target: str) -> str:
    """Relative link from the page whose output path is `from_out` ("" = home, "download/",
    "guides/spokeo/", "404.html") to a site-relative target ("" = home, "faq/#x", "style.css")."""
    frag = ""
    if "#" in target:
        target, frag = target.split("#", 1)
        frag = "#" + frag
    from_dir = from_out if from_out.endswith("/") or from_out == "" else posixpath.dirname(from_out)
    from_dir = from_dir.rstrip("/") or "."
    tgt = target.rstrip("/") or "."
    rel = posixpath.relpath(tgt, from_dir)
    if target == "" or target.endswith("/"):
        rel = "./" if rel == "." else rel + "/"
    if rel == "./" and frag:
        return frag
    return rel + frag


# --------------------------------------------------------------------------- broker guides
PEOPLE = {"people_search", "background_check", "family_tree"}
GROUPS = [
    ("people", "People-search sites", PEOPLE),
    ("data", "Marketing data companies", {"data_broker"}),
    ("other", "Official tools and other opt-outs", {"other"}),
]
FIELD_LABELS = {
    "listing_url": "the web address of your listing on {name} (you find it by searching for yourself)",
    "email": "an email address for removals (a separate one just for this is best)",
    "full_name": "your name, as it shows on the listing",
    "first_name": "your first name, as it shows on the listing",
    "last_name": "your last name, as it shows on the listing",
    "street_address": "the street address that shows on your listing",
    "city": "your city",
    "state": "your state",
    "zip": "your ZIP code",
    "dob": "your date of birth",
    "phone": "a phone number the site can call or text with a code",
}


def display_name(name: str) -> str:
    n = name.split(" (")[0].strip()
    return re.sub(r",? Inc\.?$", "", n).strip()


def load_guides() -> tuple[list[dict], dict]:
    reg = load_yaml(SAMPLE_REGISTRY)
    intros = load_yaml(SRC / "data" / "guide_intros.yaml") or {}
    raw = [b for b in reg["brokers"] if b.get("enabled", True) is not False]
    by_id: dict[str, dict] = {}
    for b in raw:
        name = display_name(b["name"])
        steps = list(b.get("steps") or [])
        g = {
            "id": b["id"],
            "slug": slugify(name),
            "name": name,
            "full_name": b["name"],
            "category": b.get("category", "other"),
            "group": next(key for key, _, cats in GROUPS if b.get("category", "other") in cats),
            "method": b.get("method"),
            "home_url": b.get("url"),
            "opt_out_url": b.get("opt_out_url"),
            "opt_out_host": (b.get("opt_out_url") or "").split("/")[2] if b.get("opt_out_url") else None,
            "email": b.get("opt_out_email") if b.get("method") == "email" else None,
            "has_email": bool(b.get("opt_out_email")),
            "covered_by_id": b.get("covered_by"),
            "steps": steps,
            "steps_mention_app": any("Free My ID" in s for s in steps),
            "needs_email_verification": bool(b.get("needs_email_verification")),
            "has_captcha": bool(b.get("has_captcha")) or any("captcha" in s.lower() for s in steps),
            "needs_id_upload": bool(b.get("needs_id_upload")),
            "days": b.get("typical_processing_days"),
            "verified": b.get("verification_status") == "verified" and b.get("last_verified"),
            "last_verified": str(b.get("last_verified") or ""),
            "ca_registered": bool(b.get("ca_registered")),
            "source_urls": [str(u) for u in (b.get("source_urls") or [])],
            "priority": int(b.get("priority") or 0),
            "intro": intros.get(b["id"]),
        }
        g["required"] = [FIELD_LABELS[f].format(name=name) for f in (b.get("required_fields") or [])
                         if f in FIELD_LABELS]
        by_id[g["id"]] = g
    slugs = [g["slug"] for g in by_id.values()]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    if dupes:
        raise SystemExit(f"duplicate guide slugs: {sorted(dupes)}")
    for g in by_id.values():
        g["covered_by"] = by_id.get(g["covered_by_id"]) if g["covered_by_id"] else None
        g["covers"] = sorted((o for o in by_id.values() if o["covered_by_id"] == g["id"]),
                             key=lambda o: o["name"].lower())
        g["out"] = f"guides/{g['slug']}/"
    guides = sorted(by_id.values(), key=lambda g: (-g["priority"], g["name"].lower()))
    meta = {"updated": str(reg.get("updated", "")), "version": str(reg.get("version", ""))}
    return guides, meta


# --------------------------------------------------------------------------- structured data
def jsonld_for(kind: str, ctx: dict, page: dict) -> dict:
    site, base = ctx["site"], ctx["site"]["base_url"]
    if kind == "organization":
        return {"@context": "https://schema.org", "@type": "Organization", "name": site["name"],
                "url": base, "sameAs": [site["repo_url"]],
                "description": "Free, open-source software that asks people-search sites to remove your listing."}
    if kind == "website":
        return {"@context": "https://schema.org", "@type": "WebSite", "name": site["name"], "url": base,
                "inLanguage": "en-US"}
    if kind == "software":
        d = {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": site["name"],
             "operatingSystem": "Windows 10, Windows 11", "applicationCategory": "UtilitiesApplication",
             "description": site["tagline"] + " Free, open source, runs on your own computer.",
             "url": base, "downloadUrl": site["download_url"], "isAccessibleForFree": True,
             "license": "https://www.gnu.org/licenses/agpl-3.0.html",
             "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
        rel = ctx["release"]
        if rel.get("version"):
            d["softwareVersion"] = str(rel["version"])
        return d
    if kind == "faq":
        return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": strip_tags(q["q"]),
             "acceptedAnswer": {"@type": "Answer", "text": strip_tags(q["a"])}} for q in ctx["faq"]]}
    if kind == "breadcrumbs":
        return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": label, "item": base + out}
            for i, (label, out) in enumerate(page["crumbs"])]}
    raise ValueError(kind)


# --------------------------------------------------------------------------- build
class Site:
    def __init__(self) -> None:
        self.cfg = load_yaml(SRC / "site.yaml")
        self.tokens = load_yaml(SRC / "tokens.yaml")
        self.pages = load_yaml(SRC / "pages.yaml")
        self.faq = load_yaml(SRC / "data" / "faq.yaml")
        self.release = load_yaml(SRC / "data" / "release.yaml") or {}
        self.icons = load_yaml(SRC / "data" / "icons.yaml")
        self.guides, self.guides_meta = load_guides()
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(SRC / "templates")),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True,
            keep_trailing_newline=True)

    def render_all(self) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        css = build_css(self.tokens)
        files["style.css"] = css.encode()
        css_v = hashlib.sha256(css.encode()).hexdigest()[:10]
        for f in sorted((SRC / "static").rglob("*")):
            if f.is_file():
                files[f.relative_to(SRC / "static").as_posix()] = f.read_bytes()
        files[".nojekyll"] = b""

        base = self.cfg["base_url"]
        pages = [dict(p) for p in self.pages]
        by_id = {p["id"]: p for p in pages}
        for g in (self.guides if "guides" in by_id else []):
            pages.append({"id": "guide:" + g["id"], "out": g["out"], "template": "pages/guide.html",
                          "label": g["name"],
                          "title": f"Remove yourself from {g['name']}: free steps"[:60],
                          "description": self._guide_description(g),
                          "parent": "guides", "jsonld": ["breadcrumbs"], "guide": g})
        by_id.update({p["id"]: p for p in pages})
        for p in pages:
            p.setdefault("noindex", False)
            p.setdefault("absolute", False)
            p.setdefault("jsonld", [])
            p.setdefault("nav", None)
            crumbs = [("Home", "")]
            if p.get("parent"):
                parent = by_id[p["parent"]]
                crumbs.append((parent["label"], parent["out"]))
            if p["id"] != "home":
                crumbs.append((p["label"], p["out"]))
            p["crumbs"] = crumbs
            p["canonical"] = base + p["out"]

        sitemap = []
        for p in pages:
            out_path = p["out"] + "index.html" if p["out"] == "" or p["out"].endswith("/") else p["out"]
            ctx = self._ctx(p, css_v, by_id)
            ctx["jsonld"] = [ld_json(jsonld_for(k, ctx, p)) for k in p["jsonld"]]
            html_out = self.env.get_template(p["template"]).render(**ctx)
            files[out_path] = html_out.encode()
            if not p["noindex"]:
                sitemap.append(base + p["out"])

        for old, new in sorted(self.cfg["redirects"].items()):
            target = by_id[new]
            p = {"id": "redirect:" + old, "out": old, "title": f"Moved: {target['label']}",
                 "description": f"This page moved to {base + target['out']}",
                 "label": target["label"], "noindex": True, "absolute": False, "nav": None, "jsonld": [],
                 "crumbs": [], "canonical": base + target["out"], "target": target}
            ctx = self._ctx(p, css_v, by_id)
            ctx["jsonld"] = []
            files[old] = self.env.get_template("redirect.html").render(**ctx).encode()

        files["sitemap.xml"] = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                                "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
                                + "".join(f"  <url><loc>{html.escape(u)}</loc></url>\n" for u in sorted(sitemap))
                                + "</urlset>\n").encode()
        files["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n".encode()
        return files

    def _guide_description(self, g: dict) -> str:
        what = "your listing" if g["group"] == "people" else "your information"
        d = f"How to remove {what} from {g['name']}, step by step, for free. Or let Free My ID do it for you."
        return d if len(d) <= 155 else d[:152].rsplit(" ", 1)[0] + "..."

    def _ctx(self, page: dict, css_v: str, by_id: dict) -> dict:
        out = page["out"]

        def url(target: str) -> str:
            if page["absolute"]:
                return self.cfg["base_path"] + target
            return rel_url(out, target)

        def asset(name: str) -> str:
            return url(name) + (f"?v={css_v}" if name == "style.css" else "")

        def icon(name: str, cls: str = "icon") -> Markup:
            body = self.icons[name]
            return Markup(
                f'<svg class="{cls}" viewBox="0 0 24 24" width="24" height="24" fill="none" '
                f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                f'aria-hidden="true" focusable="false">{body}</svg>')

        def render(src: str) -> Markup:
            return Markup(self.env.from_string(src).render(url=url))

        swatches = [{"name": n, "light": v[0], "dark": v[1],
                     "on_bg": (round(contrast(v[0], self.tokens["color"]["bg"][0]), 1),
                               round(contrast(v[1], self.tokens["color"]["bg"][1]), 1))}
                    for n, v in self.tokens["color"].items()]
        return {"page": page, "site": self.cfg, "csp": CSP, "url": url, "asset": asset, "icon": icon,
                "render": render, "faq": self.faq, "release": self.release, "guides": self.guides,
                "guides_meta": self.guides_meta, "groups": GROUPS, "pages": by_id,
                "tokens": self.tokens, "swatches": swatches, "icon_names": sorted(self.icons)}


def write_tree(files: dict[str, bytes], dest: Path) -> None:
    for rel, data in files.items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


def existing_files(d: Path) -> set[str]:
    return {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()} if d.exists() else set()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if site/ differs from a fresh build or checks fail")
    args = ap.parse_args(argv)

    s = Site()
    errors = check_contrast(s.tokens)
    files = s.render_all()

    if args.check:
        have = existing_files(OUT)
        want = set(files)
        for rel in sorted(want - have):
            errors.append(f"stale site/: missing {rel} (run tools/build_site.py)")
        for rel in sorted(have - want):
            errors.append(f"stale site/: extra file {rel} (run tools/build_site.py)")
        for rel in sorted(want & have):
            if (OUT / rel).read_bytes() != files[rel]:
                errors.append(f"stale site/: {rel} differs from source (run tools/build_site.py)")
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(files, Path(tmp))
            errors += site_check.check_site(Path(tmp), s.cfg["base_url"], s.cfg["base_path"])
    else:
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(files, Path(tmp))
            if OUT.exists():
                shutil.rmtree(OUT)
            shutil.copytree(tmp, OUT)
        errors += site_check.check_site(OUT, s.cfg["base_url"], s.cfg["base_path"])

    for e in errors:
        print("ERROR:", e)
    total = sum(len(v) for v in files.values())
    print(f"{len(files)} files, {total / 1024:.0f} KB, {len(s.guides)} broker guides. "
          f"{'OK' if not errors else str(len(errors)) + ' problem(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
