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

## State at handoff (2026-11-06, stopped on coordinator request)

DONE and committed (build_site.py --check OK, site_check OK, ruff clean):
1bf1d98 build+check tools | 63372e2 design system | bae9350 core pages | a78c1d1 "I do not consent" page |
9be5aca site_check fix | f8b2a7e 29 broker guides + index | 7e74ce4 og.png | 03fb690 styleguide/ |
e21d90b pages.yml --check job | 7ddda4e 320px/400% zoom fixes | 544fe5f docs/WEBSITE.md.
Half-done: nothing.

Commands: `.venv/bin/python tools/build_site.py` (rebuild site/ + check), `--check` (CI, no writes),
`python3 tools/site_check.py site`, preview `.venv/bin/python -m http.server -d site 8000`.
Edit site_src/, never site/ by hand. Full design system, component names and partials: docs/WEBSITE.md.
Key partials: header.html (nav_items; links shown only for pages in pages.yaml), footer.html, trust.html,
crumbs.html, mockup.html, smartscreen.html (ss_step 1|2), star-rule.html, brand-mark.svg.
Helpers in templates: url('path/'), asset('style.css'), icon('name', cls), render(html_with_url_calls).

Verified: 320px no horizontal scroll on every page (light+dark); keyboard tab order logical with 3px gold
focus ring; no-JS menu works; print CSS shows link URLs; zero external requests; CSS 6.6 KB gzip, largest
HTML 6.0 KB gzip (home), og.png 55 KB. Screenshot scripts: scratchpad shots.py / verify.py (not committed).

Decisions for the next session:
- Git: commit by explicit path (`git add P && git commit -m ... -- P`), one page per commit, never push.
- No native CSS nesting (iOS 16); light-dark() with @supports fallback; no JS; system fonts only.
- 404 uses absolute base_path links (looks unstyled on a local server; fine on Pages).
- og.png is an interim image; swap for brand/social/og-default.png when WR-2 lands (copy to site_src/static/).
- Guide steps are the registry's verbatim app steps; covered_by guides get generated text linking the parent.

## Builder round (2026-11-06): WR-4..7, 9..18 done (shas in docs/WEBSITE_REQUESTS.md)

New: /families/ page + assets/free-my-id-fridge-card.pdf (copied from docs/assets), download "opens soon" state
(flips on when data/release.yaml version is set), final logo A (favicon set + nav mark with light-dark fills).
Tooling: FMID_SAMPLE_REGISTRY env var pins the registry copy (use it if a peer has an uncommitted registry edit,
else guide pages pick it up). WR-1 closed by user pick; WR-8 still blocked (repo private).

NEXT: real SmartScreen screenshots; fill data/release.yaml at first release; WR-8 at launch; AVIF only if rasters added.

## Builder round 2 (2026-11-06): WR-19..23 done (1b41d10, ff06e58, df4f69a, 272c75a, 54ff2fb)

build_site.py refuses unsafe FMID_SAMPLE_REGISTRY (`--selftest` shows it). site_check leak scan now also uses
tools/private_host_hashes.txt (SHA-256 of private-only hostnames; regenerate with tools/gen_private_host_hashes.py
while brokers/registry.yaml exists locally; hashes only). Remember to ship SHA256SUMS.txt with the first release (WR-19).

## Orchestrator checkpoint (data-removal-00), 2026-11-07, handed to data-removal-e8 for the redesign

**State:** the site is live at https://freemyid.github.io/freemyid/ (repo public, Pages deploy green on origin/main). `tools/build_site.py --check` passes (55 files, 29 broker guides); qa-security website review PASS (docs/SECURITY_REVIEW.md "Website").
**Note:** the SHAs in docs/WEBSITE_REQUESTS.md status cells for WR-4..WR-23 are from before the history rewrite. Find the commits by subject (`git log --grep "WR-<n>"`).

**WR queue:** WR-1 to WR-23 are done. WR-21's hash file (tools/private_host_hashes.txt) is untracked and gitignored (unsalted hashes are reversible), so the check runs only where the file exists locally. The WR-20 build guard is the real protection. Only **WR-24 is open**: re-render og-default.png and repo-preview.png with the official logo A dark mark (brand/logo/final/mark-dark.svg); both currently show a white tile with a red star.

**Open brand and marketing work:**
- The user still has to upload brand/social/repo-preview.png under GitHub Settings > Social preview.
- README reorder (dev material lower, honest limits higher): docs/marketing/readme-proposal.md. The project lead wants it as a ready patch.
- data/release.yaml: fill in the version, size and SHA256 at v0.1.0 to switch on the download button (the release job ships SHA256SUMS.txt).
- After the full registry leaves the repo, rerun tools/gen_private_host_hashes.py locally whenever the private-only broker list changes.

**Rules learned (in _shared-rules.md 11–13):**
- Commit by explicit path only; never `git add -A` or stash in the shared tree.
- To untrack a file: `git rm --cached`, check that `git diff --cached` shows only that file, then a plain commit.
- Pin the registry for builds with FMID_SAMPLE_REGISTRY if a peer has uncommitted registry edits.
- Never weaken the claims or privacy rules, whatever look the redesign takes (no trackers, third-party assets or fake social proof; POSITIONING copy rules apply). Competitor sites are for benchmarking only: don't copy their copy, art or claims, and in particular don't copy SaaS dark patterns such as countdowns or "X people protected" counters.

## R6 integration (2026-11-07, web lead dispatched alone): DONE

Commits: f23f88d privacy.html + privacy/ -> safety/ in site.yaml (temporary pages.yaml entry gone) |
dcf235f home paid-services line per ruling | v1 -> contract migration (steps--list, cards, section-head,
callout--note/info), table-scroll region a11y, 51-legacy.css + star-rule.html + hero-stars.svg deleted |
5b026bc home visual pass (proof capped 40rem x 30rem with fade, hero 0.9fr/1.1fr, bands xl, band--tight
trust strip, compact does/doesn't, stronger trust bar, home/phone/calendar icons) | site/ rebuild | docs.
Checks: build --check OK (60 files), site_check 44 pages OK, ruff tools clean, no horizontal scroll on any
page at 320 or 1280 (light+dark). Home 1280: 12,037 -> 10,591px. Home weight ~280 KB (263 KB WebP).
New contract pieces (board updated): `.steps--list`, `.band--tight`, table-scroll attributes.
Screenshots + scripts: scratchpad lead/ (shots.py, sweep.py; before-*/after-* home, mig-* other pages).
Next: R7 web-qa verify; R8 qa-security. Open: `.section`/`.section--alt` v1 layout helpers are still used
by how-it-works/download/safety bodies (not in the R6 list; migrate to `.band` next round). Compare table
Free My ID column is wide relative to the others at 1280 (cosmetic, designer).
