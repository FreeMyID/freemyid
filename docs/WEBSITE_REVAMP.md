# Website revamp: direction (in-house, Nov 2026)

Lead: Leo Hart. Branch `inhouse/site-revamp`, baseline ac02e45 (the pre-refresh in-house site). The owner rejected the Codex refresh ("looks way worse"). We revamp from the in-house design: shadcn-style cards and buttons, aceternity-style hero and timeline, magicui accents. Nothing is published until the owner has seen screenshots.

## The look

- **Premium, calm, trustworthy.** A trusted local bank or a National Park Service sign, not a startup. Navy `#1b2f5b`, flag red `#a3202e` used sparingly, gold focus ring, flag bar on top. Lots of white space, one idea per band.
- **shadcn-clean.** Cards: 1px `line` border, `rounded-xl`, soft `shadow-1` (lift to `shadow-2` on hover only as decoration, never as the only cue). Buttons from `ui/button-variants.ts` only: `primary` (one per view: the download), `secondary`, `onBrand` inside brand bands. No ad-hoc button classes on pages.
- **aceternity-style hero and timeline.** Home hero: soft radial spotlight + faint grid/gradient behind the h1, static (the spotlight may drift slowly only with `prefers-reduced-motion: no-preference`). How it works: the three steps as the `aceternity/Timeline`. Inner pages get a quieter version of the spotlight in `PageHead`.
- **magicui accents, sparingly.** `BorderBeam` on the hero download button only (`CtaDownload beam`). `Marquee` once, on home (`#guide-marquee`), paused on hover/focus and static under reduced motion. Nowhere else.
- **No** stock photos, countdowns, red alarm screens, pop-ups, fake counters or "hackers" imagery. Art comes from `web/src/art/*` via `Art.astro`.

## Global chrome (lead)

- **Header:** flag bar, logo, nav (How it works, Guides, Is it safe?, For families, FAQ), and the Download CTA always visible at every width, including 320px. Phone: native popover menu with `<details>` fallback (WR-50/51). Nav targets >= 44px, current page underlined.
- **PageHead:** breadcrumbs, h1, lead, optional art; quiet spotlight background.
- **Section rhythm:** `Section` bands, `py-2xl` (tight `py-l`). Tones go plain -> alt -> plain, with at most one `brand` band per page (usually the closing CTA). Each band: optional kicker, h2, lead (max 44rem), then content.
- **Footer:** four link columns (Product, Learn, Trust, Project), trust panel word for word from `docs/BRAND.md`, "not a government service", one quiet "Source code" link.

## Page-by-page section order

| Page | Order (keep every id) |
|---|---|
| Home `index` | hero (`#hero-title`, tagline, one download CTA with beam, trust line) -> "That post went to the wrong place" -> `#what-it-removes` -> how it works in 3 steps -> `#guide-marquee` -> `#compare` -> helping a parent -> short FAQ -> closing CTA (`#cta-title`, brand band) |
| How it works | PageHead -> `#steps` timeline (`#email`, `#do-it-with-me`, `#fill-it-in`) -> what it does / doesn't do -> CTA |
| Is it safe? | PageHead -> `#local` -> `#updates` -> `#never-asks` / `#never-does` -> `#open-source` / `#verify` -> `#uninstall` -> `#limits` -> `#this-website` |
| Download | PageHead + big CTA, version, size -> `#smartscreen` -> `#checksum` (fingerprint + CopyHash) -> `#release-notes` -> `#remove` |
| What's coming | PageHead -> `#now` -> `#next` -> `#then` -> `#later` (timeline) -> `#promises` -> `#feedback` |
| For families | PageHead -> `#setup` -> `#tell-them` -> `#fridge-card` -> CTA |
| FAQ | PageHead -> `#myths` -> `#common` (FaqList) -> CTA |
| Guides, protect, developers, i-do-not-consent | PageHead with crumbs -> content cards -> "or let Free My ID do it" CTA |

## Shared rules (everyone)

1. **Audience:** non-technical older adults on Windows. 20px base text; targets >= 44px; body contrast >= 7:1, other text >= 4.5:1, light and dark; works at 320px and at 200% zoom with no sideways scroll; keyboard-friendly; visible focus (gold ring).
2. **Script-free.** CSP is `script-src 'none'` in the page meta, apart from the existing CopyHash handling. CSS-only motion, always behind `prefers-reduced-motion: no-preference`. No React islands, no new npm dependencies, no external fonts or assets.
3. **Copy:** keep the approved wording. Follow `docs/POSITIONING.md`: plain words, no absolute promises ("erase", "100%", "guaranteed"), legal claims carry the state-law qualifier. Daily checks only "when your PC is on and you're signed in". The never-asks list stays exact. Keep every existing `id` and `href`, the D5 download/release logic (`CtaDownload`) and the fingerprint/checksum content. Keep line 1 `---` in every `.astro` file.
4. **Tests:** `tests/test_web_*.py` encode owner-approved contracts. Pages must keep passing. Change a test only when a contract genuinely moved, and say why in the commit.
5. **Build through the lock:** `flock /tmp/revamp-build.lock sh -c 'cd web && pnpm -s build && pnpm -s check'`. Run screenshots and tests that read `web/dist` inside the same flock. Don't touch `web/node_modules`. Use `builtin cd`. Tests: `PYTHONPATH=$PWD/src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest tests/test_web_*.py`.
6. **Commits:** small steps, `git commit <explicit paths>` only (shared index; retry if `index.lock` exists), `-c "user.name=<Your Name> [freemyid]" -c user.email=242299803+GrayManSam@users.noreply.github.com`. No AI attribution, no push, no merge.
7. **Ownership:** Maya: `styles/*`, `components/{ui,magicui,aceternity}/*`. Owen A: index, how-it-works, safety, download, whats-coming. Owen B: families, faq, guides/*, developers/*, protect/*, i-do-not-consent, assets. Ruth: screenshots, checks, `tests/test_web_*.py`, WR rows. Leo: `layouts/*`, shared components (Header, Footer, PageHead, Section, CtaDownload, Crumbs, BrandMark, Art, Icon, RichText, CheckList, FaqList, SmartScreen, CopyHash), `lib/*`, art placement, this doc. Need a change in someone else's file? Add a line under Lead notes.

## Lead notes

(Cross-page requests to owners go here, newest first.)

- **Leo (consistency pass 1, screenshots of all 13 pages at 320/768/1024/1280, light + dark):** chrome is consistent everywhere; PageHead and 404 now use Maya's `Spotlight` (quiet, grid); header keeps its right gutter at 1024 (fc54d45). Requests:
  - **Owen A (download, 1024px):** the two cards sit side by side too early: "After you click Download" is squeezed to ~180px ("Downl/oad" breaks mid-word, list text runs past the card) and the page scrolls sideways 4px at 1024. Please stack them below ~70em, or give the side card `minmax(18rem, ...)`.
  - **Owen A (whats-coming) and Owen B (i-do-not-consent):** the body is narrow but the PageHead is wide, so the h1 sits left of the text below it. Pass the new `narrow` prop: `<PageHead narrow ...>` (7cc142b).
  - **All:** please re-run your pages at 1024px; it's the common Windows laptop width at 125% scaling (1093-1229px) and the one we tested least.

- **Owen B (status):** families, faq, guides index + `[slug]` + both topic guides, developers (index, cli, config), protect (hub, `[id]`, credit-freeze) and i-do-not-consent revamped (c06204b..eb9240b). Every id/href and the approved copy kept; closing CTAs are the one `brand` band per page (`CtaDownload look="onBrand"`). Guide articles gain a visible `#sources` section (verification line + registry line; entry source URLs stay in the HTML comment, so no third-party/GitHub links on guide pages). Developers pages use a docs layout: sticky "On this page" sidebar from 60em, plain `<section id>` blocks (not `Section` bands: tests regex-match non-nested `<section id>`). All 168 web tests pass on my last build.
- **Owen B -> Maya:** (1) done (8965b05, 74ba2a1): families uses `icon-tile` and `Timeline surface="bg-alt"`, the CLI phone index uses `Disclosure`. (2) Would a `doc-nav` sidebar style (card, 44px rows, current-section hover) and a `code-block` style for `<pre>` (border, surface, p-m, shadow-1, `overflow-x:auto`) belong in components.css? Developers index/cli/config each repeat the same utility strings for both.
- **Owen B -> Leo/Ruth (FYI):** `check` reported `index.html: missing anchor /how-it-works/#does` on one of my builds mid-afternoon (Owen A's move); it was clean on the next build.

- **Leo -> Owen A (done f614cea):** SmartScreen drawing text is now `text-body` (20px).
- **Leo -> all (new library pieces):** `Stat`/`StatGroup` only with sourced, real numbers (comment with the source); no counters or "N people protected". `ShimmerButton` and `AnimatedGradientText` count as accents like BorderBeam: at most once per page, never on body text, static under reduced motion, and the download stays `CtaDownload`. `Tabs`/`Disclosure` must work with JS off (radio/details), with all content reachable when printed.
- **Leo (404):** I took the unowned 404 page; it uses the PageHead backdrop and a card. When Maya's `Spotlight` lands I'll move PageHead and 404 onto it (`tone="quiet"`).

- **Owen A -> Leo (SmartScreen.astro):** the owner wants the download walk-through readable at 20px. The drawing's body text is `text-[0.85rem]` (17px). Please raise it to `text-body` (20px; the box is already `[overflow-wrap:anywhere]` and fits 320px at that size in my test) and the "More info"/buttons with it. Fixed colours and the CA-5 ratios stay as they are.
- **Owen A (done):** download card at 320px fixed (beam + button full width on phones, label wraps). Home hero now has the real v0.2.0 screenshot (`web/src/art/screenshots/`, 42 KB WebP) and the PageHead backdrop layers; the "does / does not" box moved to `/how-it-works/#does`.

- **Chrome landed (87cad8b).** Header: ghost-pill nav, current page = soft pill + red underline, no wrap at 1024px. Footer: brand row with one `onBrand` Download, uppercase column labels, 44px links, trust panel in a bordered card. PageHead: static spotlight + fading grid. Crumbs: chevrons, 44px links. Section kicker is now a pill. Build your pages on these; don't restyle them locally.
- **Maya (global.css, phone header):** under 34em `.header-row .menu-btn`, `.menu-fallback > summary` and `.header-cta a` are 2.5rem (40px). Please raise to 2.75rem (44px, our target). The popover top offset assumes a 4rem header row; I keep `min-h-[4rem]`, so leave that calc alone.
- **Owen A (download):** at 320px the hero download card's button ("Download FreeMyIDSetup.exe") runs past the card's right edge (see 320 light/dark). Please let it wrap or go full-width inside the card.

## QA findings (Ruth Kim, final round, HEAD af00865)

Method: baseline (ac02e45, built from `git archive`) vs current tree, 62 routes x 360/768/1280 x light/dark, each page scrolled once so scroll-reveal content renders. Scripts live outside the repo in `/tmp/revamp-shots/` (`shoot.py`, `round.py`, `run_round.sh`, `gallery.py`). Gallery: `/tmp/revamp-shots/index.html`.

**Passed (baseline and after, no regressions):** body text 20px on all 372 page/size/theme shots; no text under 14px; contrast (computed fg over resolved bg, 7:1 for body text, 4.5:1 other) has no failures, the only flag is the hero pill gradient text (`.gradient-text`), which is a text-clip false positive and reads dark navy in the screenshots; no horizontal scroll at 360, 768, 1280 or at a 640px viewport (200% zoom); one h1 per page; no image without alt; keyboard order on home is skip link, logo, 5 nav links, header Download, then the page (all links show a 3px outline plus shadow); scripts are only the same inline set as the baseline (no new scripts); no page lost an id or an href versus the baseline; `pnpm check` and `content_check.py` OK; HTML/CSS first view 17-19 KiB gzip per page.

**Claims audit:** no banned words (guarantee, 100%, erase, forever, audited, trusted by, ratings). Home stats are sourced: 29 guides = the 29 broker guide pages built from the registry, 6 setup screens = `STEPS` in `wizard/draft.py` (consent, name, address, about, mailbox, finish), 0 "Free My ID accounts to create" is qualified (some broker sites do need an account, stated on the guides). Trust row under both Download buttons says "no removal requests go out until you say so" (approved wording).

| ID | Sev | Page / size / theme | Finding | Owner |
|----|-----|---------------------|---------|-------|
| QA-1 | P2 | /families/ (all sizes, both themes), timeline step 5 | "Free My ID first looks for listings but sends nothing." Practice mode still searches people-search sites, so "sends nothing" is false. Fails the new `test_no_nothing_sent_claim_in_sources/build` in `tests/test_web_absolute_claims.py`. Suggested: "Practice mode looks for your listings. No removal requests go out until you say so." | Owen B |
| QA-2 | P2 | /how-it-works/ source comment line 101 quotes the USER_GUIDE heading "Practice first (sends nothing)". Comment only, not shown to users, but the doc heading is the same false claim | docs/USER_GUIDE.md owner (wizard-packager) to reword; no page change |  Leo |
| QA-3 | P2 | /developers/cli/ at 320 (also at baseline) | Page scrolls sideways (scrollWidth 331): command cards overflow, and `.spotlight__beam` reaches x=359. Add `min-w-0` or `overflow-x-clip` to the card grid and the spotlight beam | Owen A / Maya |
| QA-4 | P2 | /protect/bing_content_removal/, /protect/freeze_lexisnexis/, /protect/freeze_nctue/ at 320 (also at baseline; nctue is 377 wide) | Long list items (`li.ps-2xs`) with unbroken strings push the page sideways. Add `overflow-wrap:anywhere` on the step lists | Owen B / Maya |
| QA-5 | P2 | 8 broker guide pages at 320: familytreenow (342), peoplefinders (326), fastpeoplesearch, optoutprescreen, peoplesearchnow, searchpeoplefree, truepeoplesearch | The full-width "Open X's removal page" button (`a.inline-flex`) does not wrap at 320. The same button on spokeo fits. Give the guide button `whitespace-normal`/`max-w-full` (wrap the label) | Maya (button) / Owen B |
| QA-6 | P3 | Header phone menu button, 360 | Maya's note (40px targets under 34em) is still open unless Maya raised it in the last commit; the audit at 360 reports only the 5 `INPUT` elements as under 44px (hidden menu/filter controls). Verify the visible menu button is 44px | Maya |
| QA-7 | P3 | Home and download trust row | "No Free My ID account to create" reads awkwardly. Suggested: "No Free My ID account" | Owen A |
| QA-8 | P3 | Contrast tooling | The hero pill gradient text cannot be measured by script. Keep the pill text colours at or above 4.5:1 against the lightest and darkest gradient stops | Maya |

Test state: `pytest -q tests/test_web*.py` is 180 passed, 2 failed (QA-1 only). Counts: P1 0, P2 5 (QA-1 to QA-5, QA-2 is doc-only), P3 3.
