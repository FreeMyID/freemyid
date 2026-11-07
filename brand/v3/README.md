# brand/v3 (site v3 art)

Regenerate: `.venv/bin/python brand/src/build_v3.py` (SVGs) and `brand/src/render_og_v3.py` (OG PNGs). Theme notes: `tokens-notes.md`.
Each SVG carries light and dark palettes via `prefers-color-scheme` and reads optional page variables `--fmi-ink --fmi-paper --fmi-tint --fmi-brand --fmi-red --fmi-ok --fmi-line --fmi-sun` when inlined.
Use inline `<svg>` (or an `<img>`; `<img>` follows the OS scheme only). Icons use `currentColor`.

| File | Use | Alt text |
|---|---|---|
| hero.svg | home hero | A person at home, with their name card coming back from three web pages. |
| sections/step-install.svg | how it works 1 | A laptop installing the Free My ID app. |
| sections/step-who.svg | how it works 2 | A simple form asking for a name and town. |
| sections/step-send.svg | how it works 3 | Letters going from a laptop to three web pages. |
| sections/step-report.svg | how it works 4 | A printable progress report with checked-off rows. |
| sections/safety-local.svg | /safety/ | Your details stay on your computer, not in the cloud. |
| sections/families-help.svg | /families/ | A grown child helping a parent at a laptop. |
| icons/*.svg | 24px lucide-style: people-search-site, opt-out-letter, removal-report, practice-mode, windows-install | decorative (aria-hidden) |
| og/og-home.png, og/og-download.png | 1200x630 Open Graph | Free My ID: take your name off the websites that sell it. / Download Free My ID for Windows. |
