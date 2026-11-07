# Free My ID brand assets

Sources live in `brand/src/`; re-render with `.venv/bin/python brand/src/render_og.py` (needs Playwright + Pillow). Fonts are system fonts (Georgia / DejaVu); no embedded rasters or external assets. Palette from `site_src/tokens.yaml` (navy #1b2f5b, flag red #a3202e).

| File | Size | Use | Alt text |
|---|---|---|---|
| `social/og-default.png` | 1200x630, ~13 KB | Open Graph / Facebook link preview (WR-2). Web-developer copies to `site/og.png`. | Free My ID. Take your name off the websites that sell it. |
| `social/repo-preview.png` | 1280x640, ~14 KB | GitHub repository social preview (Settings > Social preview). Source `src/repo-preview.html`, render `src/render_repo_preview.py`. | Free My ID. Take your name off the websites that sell it. Free, open source, runs on your own computer. |
| `logo/options.html` | page | Three logo/wordmark proposals (A star badge, B ID card, C open ring) at favicon, nav and hero size, light and dark (WR-1). Proposal only until the user picks. | n/a |
| `logo/options-preview.png` | ~1384 px wide | Static preview of the options page for review. | Three logo directions for Free My ID shown on light and dark backgrounds. |
| `logo/final/mark.svg` | 24-unit viewBox, 0.3 KB | Final logo A (star badge), light pages: nav brand (WR-18). | Free My ID |
| `logo/final/mark-dark.svg` | 24-unit viewBox, 0.3 KB | Same mark for dark backgrounds (light-blue tile). | Free My ID |
| `logo/final/favicon.svg` | 24-unit viewBox, 0.4 KB | Primary favicon; switches colors via `prefers-color-scheme`. | n/a (decorative) |
| `logo/final/favicon-16.png`, `-32.png`, `-48.png` | 16/32/48 px, 0.4-1.1 KB | PNG favicon fallbacks, transparent corners. | n/a |
| `logo/final/favicon.ico` | 16+32+48, 2.3 KB | Legacy `/favicon.ico`. | n/a |
| `logo/final/apple-touch-icon.png` | 180x180, 2.6 KB | iOS home-screen icon, opaque navy, full bleed. | n/a |
| `logo/final/wordmark-lockup.svg` | 118x24 viewBox, 0.7 KB | Mark plus "Free My ID" (Georgia/DejaVu Serif system font, adapts to dark mode). | Free My ID |

Logo A final assets are rebuilt with `.venv/bin/python brand/src/render_logo.py`.
