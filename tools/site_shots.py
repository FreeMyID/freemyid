#!/usr/bin/env python3
"""Screenshot and DOM-audit a served Free My ID preview with Playwright.

    .venv/bin/python tools/build_site.py --out OUT/site
    .venv/bin/python -m http.server -d OUT/site 8765 &
    .venv/bin/python tools/site_shots.py --out OUT/shots [--base http://localhost:8765] [--pages home,safety]
        [--widths 360,768,1280] [--themes light,dark] [--crops]

For every page x width x theme it saves a full-page PNG (and with --crops, viewport-height slices at full
resolution, which are what you should actually look at on phones) and reports: horizontal scroll, h1 count,
skipped heading levels, interactive targets under 24 px (WCAG 2.2 AA minimum; under 44 px is listed as info),
images without alt, width or height. Writes OUT/audit.json and prints a summary. Exit 1 if any hard problem.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_PAGES = {
    "home": "", "safety": "safety/", "download": "download/", "how-it-works": "how-it-works/",
    "faq": "faq/", "families": "families/", "guides": "guides/", "guide-spokeo": "guides/spokeo/",
    "i-do-not-consent": "i-do-not-consent/", "404": "404.html",
}

AUDIT_JS = """
() => {
  const de = document.documentElement;
  const out = {};
  out.hscroll = de.scrollWidth - de.clientWidth;
  out.h1 = document.querySelectorAll('h1').length;
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
  out.skips = []; let prev = 0;
  for (const h of hs) { const l = +h.tagName[1];
    if (prev && l > prev + 1) out.skips.push(`h${prev}->h${l}: ${h.textContent.trim().slice(0,40)}`);
    prev = l; }
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'; };
  out.small = []; out.smallInfo = [];
  for (const e of document.querySelectorAll('a[href],button,summary,input,select,textarea')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect();
    const inline = e.tagName === 'A' && getComputedStyle(e).display === 'inline' &&
      e.closest('p,li,td,dd,figcaption');
    const d = `${e.tagName.toLowerCase()} "${(e.textContent||'').trim().slice(0,30)}" ${Math.round(r.width)}x${Math.round(r.height)}`;
    if (inline) continue;
    if (r.width < 24 || r.height < 24) out.small.push(d);
    else if (r.width < 44 || r.height < 44) out.smallInfo.push(d);
  }
  out.imgs = [...document.images].filter(i => !i.hasAttribute('alt') || !i.getAttribute('width') ||
    !i.getAttribute('height')).map(i => i.getAttribute('src'));
  out.overflowers = [];
  if (out.hscroll > 0) for (const e of document.body.querySelectorAll('*')) {
    const r = e.getBoundingClientRect();
    if (r.right > de.clientWidth + 1 && vis(e)) { out.overflowers.push(e.tagName + '.' + e.className); if (out.overflowers.length > 5) break; } }
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8765")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default="")
    ap.add_argument("--widths", default="360,768,1280")
    ap.add_argument("--themes", default="light,dark")
    ap.add_argument("--prefix", default="", help="URL prefix for every page, e.g. freemyid/ when serving a "
                    "parent folder (the 404 page uses absolute /freemyid/ asset paths)")
    ap.add_argument("--crops", action="store_true", help="also save full-resolution viewport-height slices")
    ap.add_argument("--zoom-check", action="store_true", help="also test 320px wide (400% zoom) for h-scroll")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    pages = DEFAULT_PAGES
    if args.pages:
        pages = {k: v for k, v in DEFAULT_PAGES.items() if k in args.pages.split(",")}
    widths = [int(w) for w in args.widths.split(",")]
    if args.zoom_check and 320 not in widths:
        widths.append(320)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    audit: dict = {}
    hard = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in args.themes.split(","):
            for w in widths:
                ctx = browser.new_context(viewport={"width": w, "height": 800}, color_scheme=theme)
                for name, path in pages.items():
                    pg = ctx.new_page()
                    pg.goto(f"{args.base.rstrip('/')}/{args.prefix}{path}", wait_until="networkidle")
                    res = pg.evaluate(AUDIT_JS)
                    key = f"{name}-{w}-{theme}"
                    audit[key] = res
                    problems = []
                    if res["hscroll"] > 0:
                        problems.append(f"hscroll {res['hscroll']}px {res['overflowers']}")
                    if res["h1"] != 1:
                        problems.append(f"{res['h1']} h1")
                    problems += [f"skip {s}" for s in res["skips"]]
                    problems += [f"tiny target {s}" for s in res["small"]]
                    problems += [f"img attrs {s}" for s in res["imgs"]]
                    if problems:
                        hard += 1
                        print(f"[{key}] " + "; ".join(problems))
                    if w != 320:
                        pg.screenshot(path=str(out / f"{key}.png"), full_page=True)
                    if args.crops and w != 320:
                        h = pg.evaluate("document.documentElement.scrollHeight")
                        for i, y in enumerate(range(0, h, 900)):
                            pg.screenshot(path=str(out / f"{key}-crop{i:02d}.png"),
                                          clip={"x": 0, "y": y, "width": w, "height": min(900, h - y)},
                                          full_page=True)
                    pg.close()
                ctx.close()
        browser.close()
    (out / "audit.json").write_text(json.dumps(audit, indent=1), encoding="utf-8")
    info = sum(len(v["smallInfo"]) for v in audit.values())
    print(f"site_shots: {len(audit)} page/size/theme combos, {hard} with hard problems, "
          f"{info} targets between 24 and 44 px (info). Output: {out}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
