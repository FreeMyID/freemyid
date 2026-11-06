# web-developer handoff

Owner of `site/**`, `site_src/**`, `tools/build_site.py`, `tools/site_check.py`, `.github/workflows/pages.yml`,
`docs/WEBSITE.md`, this file. Orchestrator decisions (2026-11-06): plain HTML/CSS, no JS, system fonts,
jinja2 build `site_src/` -> committed `site/`, clean folder URLs + redirect stubs at old `*.html`,
priorities: audit, design system, pipeline, landing, core pages, broker guides, "I do not consent" page.
Skip "Who's buying your data?" and pricing.

## Phase 1: audit (DONE 2026-11-06)

Site before: 6 hand-written pages (index, how-it-works, privacy, faq, download, 404), one 3.9 KB CSS, no build.

Gaps vs the checklist:
- SEO: home `<title>` is just "Free My ID" (no clarifier); no og:image, no Twitter card, no JSON-LD,
  no sitemap.xml, robots.txt has no Sitemap line; `.html` URLs, not clean.
- Drift risk: header/footer copy-pasted into 6 files (nav already differs on 404).
- 404 uses absolute `/freemyid/...` paths (right for Pages, must come from config so a custom domain works).
- A11y: nav links ~0.9rem with no padding (tap target < 48px); gold focus ring alone is ~1.7:1 on white
  (needs a dark companion ring for 3:1 non-text contrast); how-it-works jumps h1 -> h3 (no h2);
  no reduced-motion handling (nothing animates yet, fine); no print stylesheet.
- CSS: no layers, no light-dark(), no container queries, no fluid type; dark theme is a token swap only.
- Content gaps: no per-broker guides, no "I do not consent" explainer, no Windows SmartScreen visuals,
  no version / size / SHA256 block on download, no "Helping a parent?" path on home.
- Claims check: all existing claims match PLAN_V1 / POSITIONING (state-law qualifier present; "scammers and
  stalkers" sourced to CFPB 2024). "Source code" links point at a still-private repo (launch-day item,
  already in LAUNCH_CHECKLIST section 3).
- Quick wins carried into the rebuild: descriptive titles, shared partials, focus ring, tap targets,
  heading order, print CSS, OG image, sitemap.

## Phases 2-6 progress (2026-11-06)
Commits: 1bf1d98 build+check tools, 63372e2 design system, bae9350 core pages, a78c1d1 "I do not consent",
9be5aca site_check fix, f8b2a7e broker guides (29) + index. `tools/build_site.py` -> OK, 0 problems.
- Source layout: site_src/{site.yaml,tokens.yaml,pages.yaml,css/*.css,data/*.yaml,templates/,static/}.
- Nav/footer links render only for pages present in pages.yaml (lets pages land one at a time).
- Git rule: commit by explicit path only (`git commit -- <paths>`), one page per commit, never push.
Next: og.png (referenced in meta, NOT yet created), styleguide/ page, docs/WEBSITE.md, pages.yml
`--check` step, then verify (keyboard, 200/400% zoom, print, weights) and report.
