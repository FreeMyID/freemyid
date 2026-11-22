# Web fonts (design-direction arms only)

Loaded only by the A/B/C test arms in `web/dist/x/<direction>/` (docs/AB_TEST.md). The normal site and the control arm
use the system font stack and load none of these. Self-hosted: no request ever goes to Google or any other host.

Latin subsets as served by Google Fonts (downloaded 2026-11-21), unchanged. All are licensed under the
SIL Open Font License 1.1 (https://openfontlicense.org), which allows bundling and serving them with a website.

| File | Family | Copyright |
|---|---|---|
| `libre-caslon-400.woff2`, `libre-caslon-400-italic.woff2`, `libre-caslon-700.woff2` | Libre Caslon Text | The Libre Caslon Project Authors |
| `source-sans-3-var.woff2` (weights 400-700) | Source Sans 3 | Adobe (Source is a trademark of Adobe) |
| `zilla-slab-600.woff2`, `zilla-slab-700.woff2` | Zilla Slab | The Zilla Slab Project Authors (Mozilla) |
| `oswald-var.woff2` (weights 500-600) | Oswald | The Oswald Project Authors |
| `archivo-condensed-800.woff2` (width 75, weight 800) | Archivo | The Archivo Project Authors |
| `public-sans-var.woff2` (weights 400-800) | Public Sans | The Public Sans Project Authors (USWDS) |

The fonts keep their original names inside the files; the CSS family names match the originals except
"Archivo Condensed", a local alias for the width-75 Archivo cut (no Reserved Font Name is involved).
