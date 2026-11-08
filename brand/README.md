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

## Product screenshots (R4 / D7)

Real app, fake persona only (Jane Q Testperson, Springfield IL), 2x, cropped to app content. Throwaway home, in-memory keyring, network blocked, no scheduler. Regenerate: `capture_screenshots.py <scratch> <raw>` then `finish_screenshots.py <raw> brand/screenshots` (both in `src/`). Each has `.png` and `.webp` (WebP is the one to ship).

| File | Size (px) | WebP | Alt text |
|---|---|---|---|
| `screenshots/wizard-name.webp` | 2000x1650 | 48 KB | Free My ID setup, step 2 of 6: "What is the person's name?" with first, middle and last name boxes filled in with a made-up name, and large Back and Next buttons. |
| `screenshots/wizard-address.webp` | 2000x1400 | 59 KB | Free My ID setup, step 3 of 6: "Where do they live?" asking only for a city and state, Springfield, IL. |
| `screenshots/dashboard.webp` | 2000x2090 | 119 KB | The Free My ID home screen. A plain sentence says 7 sites have confirmed or no longer list you, 3 are waiting and 2 need you, followed by a card with copy-and-paste details and large buttons for the one step left. |
| `screenshots/report.webp` | 1800x2440 | 143 KB | The printable progress report: a table of each people-search site, its status (site confirmed, asked, not listed now, needs you), when it was last checked and when the request was made. |

Social images (`og-default.png`, `repo-preview.png`) now use the official logo A dark mark (`logo/final/mark-dark.svg`, WR-24).

## v0.2 additions (Iris Novak)
Built by `brand/src/build_platform_art.py`. Platform app icons: `brand/icons/platforms/` (see its README). Illustrations (light and dark SVG + PNG each):
| File | Size | Use | Alt |
|---|---|---|---|
| v3/developers/developers-{light,dark}.svg/.png | 640x480 | /developers/ | A terminal on your own computer connected to a small home server, inside a house outline, with a clock for the schedule. |
| v3/features/find-me-first-{light,dark} | 320x250 | "find me first" scan page | A magnifying glass over a web page, finding a person's listing. |
| v3/features/proof-report-{light,dark} | 320x250 | proof report page | A progress report with checked rows and a star seal. |
| v3/features/family-helper-{light,dark} | 320x250 | family helper mode page | A grown child and a parent sharing one laptop with two name cards. |

## WO-170..179 art (Iris Novak, in-house; hand-authored HTML rendered by Playwright)
Replaces the Codex/Canva plan: no `brand/codex/` or MANIFEST; files sit in `social/` and `web/` next to the existing art. Shared helpers `src/wo17_common.py`; each `src/build_wo17x_*.py` rebuilds its files (run from `brand/src` with the repo venv). Logo is always the unaltered `logo/final/wordmark-lockup.svg` (dark colours on navy). Headlines are the site's bold sans, not the SEO brief's Georgia (the site has had no serif headings since v2; the logo carries the serif).
| File | Size | Use | Alt text |
|---|---|---|---|
| `social/og/og-developers-cli.png` | 1200x630, 14 KB | WO-170 OG image for /developers/cli/ (not wired). | Free My ID command line: a terminal window showing a status command. Scriptable, local, no account. |
| `social/og/og-developers-config.png` | 1200x630, 17 KB | WO-171 OG image for /developers/config/, pair of WO-170 (grey ground, file tab instead of window dots). Keys taken from the page example. | Free My ID settings file: a short plain-text file with a few options. |
| `social/posts/cb01-a-wrong-place-{1080x1080,1080x1350}.png` | 25 KB each | WO-175 post A (Facebook/Instagram), after owner approval. The 1350 version keeps all content in the middle 1080 square. | Free My ID. That post went to the wrong place. The sites that list your name, address and phone number are people-search sites, and Free My ID asks them to take your details down. |
| `social/posts/cb01-b-scope-*` | 22 KB each | WO-175 post B. | Free My ID takes your name off people-search sites. It does not change what Facebook does with your account. |
| `social/posts/cb01-c-keeps-checking-*` | 18 KB each | WO-175 post C. | Free My ID keeps checking. Sites sometimes list people again, which is why it keeps checking. |
| `social/posts/cb01-d-download-*` | 18 KB each | WO-175 post D. "Windows 10 and 11" matches the download page and release.yaml; release manager re-checks before posting. | Free My ID is free for Windows 10 and 11. No account, no cloud, runs on your own computer. Download at freemyid.org. |
| `social/posts/cb04-never-ask-{1080x1080,1080x1350}.png` | 34 / 36 KB | WO-177 "what we never ask for" trust card. Copy is the /safety/ list (Morgan's override), plain navy dash markers, no red. | Free My ID will never ask for your Social Security number, your bank or card details, a payment of any kind, your full birthday, or the password to your everyday email. If something says it is us and asks, it isn't. Stop and ask someone you trust. |
| `social/carousel/cb03-carousel-{1..5}-of-5-1080x1350.png` + `cb03-carousel-1080x1350.pdf` | 18-36 KB each; PDF 379 KB | WO-176 "How it works in 3 steps" carousel. Slides 2-4 use unaltered crops of `screenshots/app-v3` (fake persona). | 1: Free My ID works in 3 steps. Free, open source, and it runs on your own computer. 2: Step 1. Tell it who to look for. A name, and the city and state you live in. Screenshot of the Free My ID app with a made-up person. 3: Step 2. It asks the sites to take you down. It uses each site's own removal process. If a site needs you to tick "I'm not a robot", it shows you a card and you do it. Screenshot of the Free My ID app with a made-up person. 4: Step 3. It keeps checking. You see what is confirmed, what is waiting and what needs you. Screenshot of the Free My ID app with a made-up person. 5: No account. No cloud. It never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime. |
| `web/steps/step-{1-who,2-sent,3-checked}-{light,dark}.svg` and `.png` (12 files) | SVG 320x250 viewBox, PNG 640x500 (2x), 5-7 KB each | WO-178 "How it works" spot art for the homepage and download page; transparent background (a soft ellipse is part of the art), same 3.5 stroke as `v3/features`, no text, one red accent. Leo places after approval; not wired. Build `src/build_wo178.py`. | 1: A name card in front of a small house. 2: A page with an arrow going out to a web page. 3: A magnifying glass over a list with check marks. |
