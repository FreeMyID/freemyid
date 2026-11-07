"""Run the v2 checker (tools/site_check.py) on the v3 build: copy rules (POSITIONING banned phrases),
private-registry leak scans, links, meta, CSP presence, img attributes.

    python web/scripts/content_check.py web/dist [--tools DIR]

The one v2 rule v3 knowingly differs on: v2 has no JavaScript at all, so it flags every inline
<script>. v3 pages with islands carry Astro's inline island bootstrap, which check-site.mjs verifies
is covered by a sha256 hash in that page's CSP. Only that message is filtered, and only on pages
that load an island (astro-island element present).
--tools points at another checkout's tools/ (for example the main checkout, which has the
private host-hash list and the full registry for the leak scan). Stdlib only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--tools", type=Path, default=ROOT / "tools")
    a = ap.parse_args()
    sys.path.insert(0, str(a.tools.resolve()))
    import site_check

    errors = site_check.check_site(a.dist, "https://freemyid.github.io/freemyid/", "/freemyid/")
    kept = []
    for e in errors:
        page, _, msg = e.partition(": ")
        if msg == "inline <script> that is not JSON-LD":
            html = (a.dist / page).read_text(encoding="utf-8")
            if "<astro-island" in html:
                continue
        kept.append(e)
    for e in kept:
        print("ERROR:", e)
    leak_scan = "on" if site_check.private_host_hashes() else "OFF (no tools/private_host_hashes.txt here)"
    print(f"site_check on {a.dist}: {len(errors) - len(kept)} island-script notes filtered, "
          f"host-hash leak scan {leak_scan}. {'OK' if not kept else str(len(kept)) + ' problem(s)'}")
    return 1 if kept else 0


if __name__ == "__main__":
    raise SystemExit(main())
