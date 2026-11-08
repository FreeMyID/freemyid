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
dcf235f home paid-services line per ruling | 3af12fd v1 -> contract migration (steps--list, cards, section-head,
callout--note/info), table-scroll region a11y, 51-legacy.css + star-rule.html + hero-stars.svg deleted |
5b026bc home visual pass (proof capped 40rem x 30rem with fade, hero 0.9fr/1.1fr, bands xl, band--tight
trust strip, compact does/doesn't, stronger trust bar, home/phone/calendar icons) | d2ea997 site/ rebuild | 9d67abe docs.
Checks: build --check OK (60 files), site_check 44 pages OK, ruff tools clean, no horizontal scroll on any
page at 320 or 1280 (light+dark). Home 1280: 12,037 -> 10,591px. Home weight ~280 KB (263 KB WebP).
New contract pieces (board updated): `.steps--list`, `.band--tight`, table-scroll attributes.
Screenshots + scripts: scratchpad lead/ (shots.py, sweep.py; before-*/after-* home, mig-* other pages).
Next: R7 web-qa verify; R8 qa-security. Open: `.section`/`.section--alt` v1 layout helpers are still used
by how-it-works/download/safety bodies (not in the R6 list; migrate to `.band` next round). Compare table
Free My ID column is wide relative to the others at 1280 (cosmetic, designer).

## R11 (2026-11-07, web lead alone): DONE

efc7997 WR-29: while `release.version` is null, fingerprint lines say "will come with", no page links the empty
GitHub releases page, FAQ answers get `release` in `render()` (FAQPage JSON-LD now uses the rendered answer), and
SoftwareApplication `downloadUrl` is added only with a version. d58dad5 removed the v1 `.section` CSS (and print entry).
ab9b709 rebuilt site/ (round 2 + R11). Board: R9, R10, R11 done, round 2 rulings recorded; WEBSITE.md has srcset,
data-label, WR-29 and web-qa copy-rule notes. `--check` OK (64 files), ruff clean, site_shots 360/1280 light+dark clean.
Leftovers: `dashboard.webp`, `report.webp`, `wizard-*.webp` are copied into site/ but unused (about 380 KB of repo,
no page weight); drop them from site_src/static or use them. NEXT: R12 web-qa re-verify, then R8 qa-security.

## R13 post-v0.1.0 (2026-11-07, web lead alone): DONE

605fe27 release.yaml v0.1.0 (64.0 MB, sha256 bb4a36153a1a99955bbe4d224d505f43ade678763f2c8b38ee43e203099b7bbe, hashed from the
downloaded asset, matches SHA256SUMS.txt; releases/latest/download/FreeMyIDSetup.exe 302s to the v0.1.0 asset) | 9093bd4 WR-8
"Read the source code" re-added to the home final CTA (lost in the redesign) | c3ecdb9 download button label wraps as one flex item |
e6d4e2f + b174f6c WR-37 (ODNI replaces the withdrawn CFPB rule) and WR-38 (released-version copy) | 953d3f3 site/ rebuild (includes
SEC-41 report-600/900.webp from 450bb34). Unused dashboard/report/wizard webps were already dropped in 2bf6680.
Checks: build --check OK (60 files), site_check 44 pages OK, ruff clean, site_shots 360/1280 light+dark + 320 zoom: only the
known unprefixed-404 artefacts (clean with --prefix freemyid/). Home 7.4 KB gzip, download 4.3 KB gzip.
Open: broker-researcher SOURCES.md entry for the home "what they list" cards (relatives isn't a sample-registry field);
LAUNCH_CHECKLIST line 48 can be ticked by the orchestrator; real SmartScreen screenshots still pending (VM).

## v3 P3 round (2026-11-07, web lead alone; site is web/ Astro now, not site_src/templates)

9f70271 home hero: actions side by side at 768-899px (one-column hero); stacked below 768 and at 900+ (two-column
hero, ~400-570px column can't fit both at lead size); WR-53 brand rule kept; WO-103 test gained a 768 row case |
acd514a WR-60/SEC-65 check-site handler + javascript: URL guard | 12d93b1 WR-58/SEC-62 web/pnpm-workspace.yaml |
320b9ba SEC-66 page part: CSP meta right after <meta charset>, enforced by check-site | 0f29745 React-free CopyHash,
React deps and integration removed (lockfile: removals only) | 5e7fed1 WR-53/55/58/60/70 closed (55 and 70 were done by
vendor WO-102/WO-101, 53 by WO-103, rows hadn't been updated).
Checks: pnpm build + check OK (61 HTML, 55 indexable), content_check OK (leak scan on), pytest tests/test_web_*.py 46 passed.
Shots: scratchpad hero/before, hero/after (360/600/768/1024/1280 light+dark).
Open: SEC-66 header CSP/frame-ancestors (host move), SEC-67 + Dependabot (devops), WR-51 tab-out note, WR-61/62/63
(broker-researcher), WR-69 HOLD, /protect/ "15 minutes" rule ruling + freeze_lexisnexis HOLD (orchestrator).

## v0.3 wave availability pass (2026-11-08, web lead alone)

Rule: "available" = in published v0.2.0 (ROADMAP 6, site_src/data/release.yaml). Checked feature list =
docs/marketing/release-notes-v0.2.0.md; its source commits (9934dfd Today/Protect/summary, a407f66..519f384 exposure,
18bf7df checklist CLI, bb2cf2a installer fixes) are all ancestors of tag v0.2.0. Merged after v0.2.0 (unreleased):
Google/Bing guided step (bd6fb4d, 0f57972, 535fb7a), per-person Today card, SEC/a11y fixes.
e64f7db /whats-coming/: "Available now, version {release.version}", "New in version 0.2, and still early" list
(listing check + score with coverage and limits, "Is this you?", app checklists, printable summary); #next section is now
"Also available: Linux, Mac and home servers" (command line only; Docker image + desktop apps not yet); v0.3 lead says 0.2
has an early version; checklist card says app checklists shipped in 0.2, Google/Bing step "Coming next".
tests/test_web_v03_roadmap.py (WO-003 file, not reserved this wave) assertion updated from the now-false
"checklists are planned inside the app". 6a40368 FAQ Mac answer: no Mac app or phone version; Mac command line via
/developers/. WR-68 status note updated. Section IDs, header/nav and families untouched.
WR queue: nothing buildable. WR-61/62 still need broker-researcher clearance (needs-verify rows not cleared in
SOURCES.md or its handoff), WR-63 waits on them, WR-69 HOLD (paid tier).
Checks: pnpm build + check OK (62 HTML, 56 indexable), content_check OK (leak scan on), pytest tests/test_web_* 71 passed,
/whats-coming/ 360+1280 light/dark no horizontal scroll.
For the crew: web-qa: re-sweep /whats-coming/ and /faq/ screenshots after the next merge; web-builder: when the next
release ships, move the "Coming next" Google/Bing line and the v0.3 section per the page's header comment.
Open (orchestrator): ROADMAP 3.7 puts "multiple profiles" in 0.4, but v0.2.0 already has "Add a person" in the wizard
(dashboard.py) and `profile add` in the CLI, and the FAQ says you can protect several family members from one computer.
/whats-coming/ "Planned for 0.4: family profiles, each giving their own consent" reads as the consent-per-person part;
please confirm or reword ROADMAP 3.7. Legacy site/ (not deployed; Pages builds web/) still has the old FAQ text.

## Absolute-claims pass + CLI-A04 note (2026-11-08, web lead alone)

63ce16e absolute claims made literally true for the shipped app (v0.2.0 code read, not docs):
- The listing check sends name + city/state/zip to people-search search pages (engine/exposure.py,
  submitters/web_form.search_url), outside any "request you approve". /developers/ and /whats-coming/ now say details go
  only to the people-search sites (a name-and-town lookup, then removal requests you approve); "Nothing is sent to us".
- Practice mode still looks people up: home + /how-it-works/ "nothing is sent until you say so" -> "no removal requests go out".
- Email approval: EmailMode.AUTO is opt-in, so /families/ says "Unless they switch on automatic sending, no email goes out
  until they press OK".
- Desktop notice: shipped text is "Free My ID needs 5 minutes of your help" / "N things need you" (runner.py, no name);
  /families/ example "Mom: 2 sites need you" replaced with the real text.
- Home "Never a phone number or ID unless you choose to" (the wizard does ask for an optional phone) -> "It gives a site
  your phone number only if you switch that on" (tiers.py/base.py/letters.py gate on allow_phone_disclosure).
- /safety/ "Fenced in" now lists our public list of sites (registry update URL) alongside sites + mailbox.
- Checked and kept (true): never SSN/bank/card (filler skips SSN fields), never pays, never solves robot checks, never
  creates accounts / uploads ID (no code does either even with the permission on), consent gate (runner re-checks), "we will
  never email you an installer or call you" (policy), guides "never have to pay".
Guard: tests/test_web_absolute_claims.py (fixed phrases in source + build; banned phrases on every built page and in astro
sources with comments stripped); WO-107 test expectations updated. Legacy site_src/templates not touched (not deployed).
OPEN for Morgan (WO-101 scope, test-guarded, so not changed): the PROMISE "They go out only in a removal request you
approve, sent straight to that one site" (home, /safety/, FAQ) is not literally true either: the listing check sends name
and town to each site's search page first. Proposed: "Your details are stored only on your computer. They go out only to
the people-search sites themselves: your name and town to look you up, and removal requests you approve." Needs your OK,
then a change to tests/test_web_privacy_wording.py PROMISE, home, safety, faq.yaml and the legacy templates in one commit.

### CLI-A04 recommendation (web prefill wiring; decision for Morgan, not implemented)
Facts: `freemyid setup --prefill X` defaults to --web, and the web branch calls serve() and silently ignores X. Only
--no-web passes it to setup_cli. `profile add --prefill X` already forces the terminal. The web wizard already has its own
import screen (/wizard/import: file picker or the bundle shipped next to the exe, passphrase typed in the browser, consent
re-asked, mailbox never imported). Docs (CLI.md, README via WO-120) already document the --no-web spelling.
Options:
A. Wire it: pass the path into serve(), open the browser at /wizard/import with that file pre-selected. Needs cli.py
   (contract) + server.py; the local server would read a path handed in from argv (new surface, small); the passphrase
   still has to be typed in the browser.
B. Make it honest, not wired: `--prefill` implies the terminal (same rule as profile add: `web = web and prefill is None`,
   which needs the web option default to become None so an explicit `--web --prefill` can be refused with "use the
   'Use a family setup file' button in the wizard, or --no-web"). ~5 lines in cli.py + one test.
C. Docs only (current state): leaves a silent no-op that a helper will hit.
Pick: B. The silent ignore is the real bug; GUI users already have /wizard/import and the family-installer bundle, and the
people who type `setup --prefill` are at a terminal anyway. A adds a path-into-server hop for no audience. Revisit A only if
the family installer ever launches setup with a bundle argument. No website change either way (web/ never mentions --prefill).
Task 3 (P3 backlog, smallest first): web-v3 P3s left are SEC-66 headers (host), SEC-67 (devops), WR-51 tab-out (needs JS,
site stays script-free) and WR-61/62/63. Broker-researcher cleared WR-61 S2 at 11eb5fb, so 344b8f0 publishes
/guides/help-a-parent-remove-their-information/ (pages.yaml v3_only entry, FAQ-style H2s, BreadcrumbList Home > Opt-out
guides > Help a parent, linked from /families/ bottom and the /guides/ "Before you start" box; test_web_help_a_parent.py).
Shots: /tmp/claude-shots/parent-{360,1280}-{light,dark}.png, no horizontal scroll. Note: full-page shots without
reduced motion show `.reveal` cards blank (scroll-driven animation); existing behavior site-wide, not a page bug.
Next: WR-62 (S2 not cleared: use the research doc's per-listing wording, "often" -> "can"), then WR-63 link.
Checks at 344b8f0: pnpm build + check OK (63 HTML, 57 indexable), content_check OK (leak scan on), pytest tests/test_web_* 111
passed with FREEMYID_REQUIRE_WEB_DIST=1, legacy build_site --out tmp OK.

## Morgan approvals (2026-11-08): promise wording + WR-62/63 (web lead alone)
00e8976 WO-101 promise replaced everywhere (home, /safety/, faq.yaml, legacy home/safety templates, test PROMISE):
"Your details are stored only on your computer. They go out only to the people-search sites themselves: your name and town
to look you up, and removal requests you approve." Legacy templates also got the notice, practice-mode, phone and fenced-in
fixes from 63ce16e. The old sentence is on the banned list in test_web_absolute_claims.py.
Note: committed legacy site/ was already stale before this (build_site --check: 4 problems); build.yml rebuilds it before
--check, so not regenerated here.
f94979d WR-62 /guides/get-your-phone-number-off-people-search-sites/ (per-listing S2 wording, "can" not "often", FTC Do Not
Call wording with donotcall.gov / reportfraud.ftc.gov plain links) + WR-63 /guides/ link; test_web_phone_number_guide.py.
CLI-A04 option B approved; Nina implements (not web).
Checks at f94979d: pnpm build + check OK (64 HTML, 58 indexable), content_check OK (leak scan on), web tests 113 passed,
legacy build to tmp OK. Shots /tmp/claude-shots/phone-{360,1280}-{light,dark}.png, no horizontal scroll.
Web-v3 P3 left: SEC-66 headers (host), SEC-67 (devops), WR-51 (needs JS, won't do), WR-69 HOLD.

## Backlog lane IN (2026-11-08, web lead alone)
1. CSP for Dana's response header (no request from her yet). Built pages carry exactly two meta strings:
   63 pages: default-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; object-src 'none'; frame-src 'none';
   form-action 'none'; base-uri 'none'; script-src 'none'; style-src 'self'
   /download/ only: the same with script-src 'self' (CopyHash module). A header can add frame-ancestors 'none' (meta can't).
2. BL-IN-81 BLOCKED (sources first): guides are built only from brokers/registry.sample.yaml (31 entries; private registry
   never feeds site output). Of the full registry entries not in the sample, the only `verified` ones are B2B/background
   brokers (lexisnexis, zoominfo, apollo, lusha, innovis), and their notes say the removal form itself was not loaded.
   Every people-search broker not yet covered (checkpeople, socialcatfish, privateeye, usa_people_search, peekyou, pipl,
   veripages, searchquarry, ...) is `unverified`, none with a browser check. CHANGE REQUEST to broker-researcher (Priya):
   browser-verify the top people-search candidates with citations, then add them to registry.sample.yaml (LICENSE-DATA
   terms); each then gets a guide page automatically, and I add a per-guide test.
3. /developers/cli/ + config/ links: waiting for Morgan (Codex lane).
4. P2 WR: WR-73 done (e64f7db meets it), WR-72 (P3, but the stale text was LIVE in the v3 meta description) done 8cdfa89.
   WR-71 waits for the v0.3 release (brand note: fill from release-notes-v0.3.0.md, with WR-74), WR-74 HOLD until release.
Checks at 8cdfa89: build + check OK (64 HTML, 58 indexable), content_check OK, web tests 113 passed, legacy build OK.

## Guide art + credit freeze checklist (2026-11-08, web lead alone)
663ee92 brand/illustrations phone-number + help-a-parent copied unchanged to site_src/static/assets/art/, <picture> with a
prefers-color-scheme dark <source> (same pattern as /whats-coming/; the site has no data-theme toggle, so no JS needed),
README alt text, 320x250; test_web_guide_art.py (bytes match brand/, no script).
f882daa /protect/credit-freeze/ "Credit freeze checklist": what a freeze does, printable checkbox list for the three big
bureaus (linking the existing /protect/freeze_* step pages), optional smaller files, federal timing (15 USC 1681c-1(i)),
lift-only-where-checked (FTC), protected-consumer freeze for a parent (1681c-1(j), FTC), fraud alert vs freeze (FTC),
SSN note. Only page-level facts from docs/research/credit-freeze-specifics-2026-11.md; TransUnion/ChexSystems snippet facts
and the conflicting ChexSystems phone numbers are not used (test guards the numbers). Linked from the /protect/ credit section.
Checks at f882daa: build + check OK (65 HTML, 59 indexable), content_check OK, web tests 117 passed, legacy build OK.
Shots: /tmp/claude-shots/art-*-{360,1280}-{light,dark}.png, cf-{360,1280}-{light,dark}.png (full page), no horizontal scroll.

## Contrast audit CA-2/3/5/6 (2026-11-08, web lead alone; CA-1/CA-4 = Copilot WO-126)
c868a3c. Ratios recomputed from tokens.css, light / dark:
- CA-2 Section tone="brand": `[&_a]` -> `[&_a:not(.no-underline)]` (button links always carry no-underline). Before: onBrand
  1:1 / 1:1 (ink on ink), primary text 12.27 / 1.57. After: onBrand 13.09 / 13.44, primary text 12.27 / 10.45, prose links in
  the band 13.09 / 13.44. No page uses tone="brand" today; primary vs the band itself is 1.07:1, so the comment says use onBrand.
- CA-3: no change needed (gold 1.82 / 10.24 vs bg; inner ring 17.26 / 16.44; gold vs inner 9.49 light). Added "do not remove
  the inner ring" note; test checks the pair on bg, bg-alt, card, band-brand in both themes and that the box-shadow stays.
- CA-5 SmartScreen: unchanged on purpose (imitates Windows): #fff on #0b5394 7.84, gold ring on #0b5394 4.31. Comment + test.
- CA-6: `@media (forced-colors: active)` in global.css: focus outline 3px Highlight (box-shadow dropped), 2px currentColor
  border on button links, buttons and number bubbles. Playwright forced_colors="active" test checks the CTA border and the
  focus outline on the built home page.
Test: tests/test_web_contrast_inhouse.py (14 cases, browser ones offline-routed). Checks: build + check OK (65 HTML, 59
indexable), content_check OK, gen-tokens --check OK, web tests 131 passed.
