# Canva briefs: search and sharing images (seo-growth)

Requester: seo-growth lead (Sam Okafor). Reviewer: graphic-designer. Draft for Morgan to turn into Codex work orders (rules: docs/SDLC.md, "Codex with GitHub and Canva"). 2026-11-08.

## Evidence: what shares which image today

- `web/src/pages/assets/[og].png.ts` publishes only two files: `og-home.png` and `og-download.png` (from `web/src/art/og`).
- `web/src/layouts/Base.astro` defaults `ogImage` to `assets/og-home.png`. Only `web/src/pages/download/index.astro` sets its own (`assets/og-download.png`). `grep ogImage=` in `web/src/pages` finds no other page.
- So these all share the generic home image: /developers/, /developers/cli/, /developers/config/, /guides/ and every /guides/<slug>/ (30 per-broker guides plus the two long guides), /protect/ and /protect/credit-freeze/, /families/, /faq/, /how-it-works/, /safety/, /i-do-not-consent/, /whats-coming/.
- The v2 build (`site_src/templates/base.html`) uses one `og.png` site-wide; `site_src/og.html` is its source. `brand/social/og-default.png` and `repo-preview.png` are the generic social images.
- `docs/marketing/seo/content/` holds 5 drafts (phone number, helping a parent, how-to hub, credit freeze checklist outline, why it's free). PLAN.md lists v0.3 articles A to C, which stay unpublished until the features ship. Pinterest is not in PLAN.md, so CBS-06 is optional and `seo:` evidence for it is a guess (see the brief).
- Note for web-developer (separate from Codex): once files are placed, `NAMES` in `[og].png.ts` and each page's `ogImage`/`ogAlt` need a WR. I will open it after graphic-designer places the files. Guide pages in particular need a per-guide image decision (CBS-03 uses one template for all brokers).

## Shared specs (apply to every brief)

- **Palette (from brand/v3/tokens-notes.md and brand/README.md):** navy #1b2f5b (brand, band) on white #ffffff or surface #eef2f7; heading navy #14264a; body text #151b26; muted #414b5c; flag-red accent #a3202e used small only (a rule or dot, never an alarm banner); focus gold #f2b705 not used on images. Dark variant is not needed for OG/Pinterest.
- **Type:** Georgia (serif, the wordmark face; designer substitutes DejaVu Serif if Canva lacks Georgia) for the headline; system sans stack equivalent (Segoe UI or Arial in Canva) for the sub-line. Headline at least 64 px on a 1200x630 canvas so it reads at 300 px wide.
- **Logo:** use only `brand/logo/final/` SVGs (mark plus wordmark lockup), imported as-is. No Canva stock in or near the logo.
- **Imagery:** flat shapes only (cards, a checklist, a simple window frame). No photos of people, no padlocks-on-red or warning imagery, no flags or partisan symbols. Any mock-up shows only Jane Q Testperson, Springfield IL.
- **Copy:** word for word from each brief. No "guaranteed", "erase you from the internet", fear or urgency wording, no identity-theft-protection claims.
- **Export:** PNG (and SVG/PDF where Canva allows) to `brand/codex/<WO>/`; record in `brand/codex/MANIFEST.md` with the Canva link, stock elements and alt text.
- **Safe area:** keep text 60 px from every edge (platforms crop).

## CBS-01: Open Graph, /developers/cli/

- Target: https://freemyid.org/developers/cli/ (`web/src/pages/developers/cli/index.astro`)
- Size/format: 1200x630 PNG, file name `og-developers-cli.png`; target 60 KB or less (hard cap 150 KB).
- On-image text, exact:
  - Headline: `The Free My ID command line`
  - Sub-line: `Scriptable. Local. No account.`
  - Footer: `freemyid.org`
- Visual: navy #1b2f5b panel at right showing a simple terminal window with two lines of sample text, `freemyid status` and `3 requests sent, 1 confirmed` (generic figures, no personal data). White left side with headline.
- Alt text: `Free My ID command line: a terminal window showing a status command. Scriptable, local, no account.`
- Reviewer: graphic-designer.
- Acceptance: legible at 300x158; headline contrast at least 7:1; logo from brand/logo/final; terminal text is a command that exists in `web/src/pages/developers/cli/_commands.json` (check before use); no real data; under size target.

## CBS-02: Open Graph, /developers/config/

- Target: https://freemyid.org/developers/config/ (`web/src/pages/developers/config/index.astro`)
- Size/format: 1200x630 PNG, `og-developers-config.png`; 60 KB target, 150 KB cap.
- On-image text, exact:
  - Headline: `Free My ID settings, in one file`
  - Sub-line: `Plain text. Yours to read and change.`
  - Footer: `freemyid.org`
- Visual: same layout family as CBS-01 (so the two read as a pair), panel shows a short settings file with three generic keys and values (designer takes them from the page's own examples so nothing is invented).
- Alt text: `Free My ID settings file: a short plain-text file with a few options.`
- Reviewer: graphic-designer.
- Acceptance: as CBS-01; sample keys match those on the page; visibly the same family as CBS-01 but distinguishable in a thumbnail grid.

## CBS-03: Open Graph template, per-broker guides (/guides/<slug>/)

- Target: 30 per-broker guides under https://freemyid.org/guides/ (same layout for all). Core SEO asset (PLAN.md goal 2). One Canva template; Codex exports the first 3 as samples (suggest Spokeo, Whitepages, BeenVerified; broker-researcher confirms the list matches shipped guides) so graphic-designer can approve before the rest.
- Size/format: 1200x630 PNG per guide, `og-guide-<slug>.png`; 50 KB target, 120 KB cap each. Also keep the editable Canva template link in MANIFEST.md.
- On-image text, exact pattern (broker name only varies):
  - Small label: `FREE GUIDE`
  - Headline: `Remove yourself from <Broker name>`
  - Sub-line: `Step by step. Free. No account needed.`
  - Footer: `freemyid.org`
- Visual: white background, a navy left rule, a simple three-step checklist glyph at right. Broker name is text only: no broker logos (trademarks, and they look like endorsements).
- Alt text pattern: `Free guide: how to remove yourself from <Broker name>, step by step.`
- Reviewer: graphic-designer.
- Acceptance: longest broker name still fits on at most 2 lines at 64 px or larger; no broker logos; no claim of removal ("remove yourself from" is the guide's own title and matches the page H1; web-developer to confirm); readable at 300 px; template is editable by name only.
- Follow-up: web-developer WR to map slug to image (not part of this work order).

## CBS-04: Open Graph, "Help a parent get their details off people-search sites"

- Target: https://freemyid.org/guides/help-a-parent-remove-their-information/ (draft: `docs/marketing/seo/content/protect-elderly-parents-information.md`). Audience: adult children, so tone is warm and calm.
- Size/format: 1200x630 PNG, `og-guide-help-a-parent.png`; 60 KB target, 150 KB cap.
- On-image text, exact:
  - Headline: `Helping a parent get their details off people-search sites`
  - Sub-line: `A calm, step-by-step guide. Free.`
  - Footer: `freemyid.org`
- Visual: two simple overlapping rounded cards (flat illustration style of brand/illustrations, no faces) on surface #eef2f7, navy headline. No elderly stereotypes, no people.
- Alt text: `Guide: helping a parent get their details off people-search sites, step by step and free.`
- Reviewer: graphic-designer.
- Acceptance: nothing implies the parent is helpless or at risk; no fear imagery; headline legible at thumbnail size; matches the headline wording on the published page (check at placement; the page title may differ and the text must then be updated by the requester).

## CBS-05: Open Graph, credit freeze checklist (/protect/credit-freeze/)

- Target: https://freemyid.org/protect/credit-freeze/ and the planned article B (content/credit-freeze-checklist-for-you-and-your-parents.md; publication pending).
- Size/format: 1200x630 PNG, `og-credit-freeze.png`; 60 KB target, 150 KB cap.
- On-image text, exact:
  - Headline: `Freeze your credit for free`
  - Sub-line: `A checklist for you and your parents`
  - Footer: `freemyid.org`
- Visual: a flat checklist card with three unchecked-then-checked rows labelled with the three bureau names as plain text only (`Equifax`, `Experian`, `TransUnion`). No bureau logos. Navy and success-green #1c6639 ticks.
- Alt text: `Checklist graphic: freeze your credit for free at Equifax, Experian and TransUnion.`
- Source for "for free": FTC, free to place or lift a freeze (https://consumer.ftc.gov/articles/what-know-about-credit-freezes-fraud-alerts), as cited in the content plan; seo-growth re-checks before publishing.
- Reviewer: graphic-designer.
- Acceptance: no identity-theft-protection or fear wording; no bureau logos; green is used only for ticks; thumbnail legible.

## CBS-06 (optional): Pinterest pin, the top guide

- Target: the how-to hub (https://freemyid.org/guides/ plus draft `docs/marketing/seo/content/how-to-remove-yourself-from-people-search-sites.md`). Pinterest is NOT in PLAN.md; any traffic value is a guess (no cited source). Do this only after Morgan agrees to add Pinterest, which needs an owner-created Free My ID account (not ours to make). It then also serves as a tall share image elsewhere.
- Size/format: 1000x1500 PNG (2:3), `pin-how-to-remove-yourself.png`; 150 KB target, 300 KB cap.
- On-image text, exact:
  - Headline: `How to remove yourself from people-search sites`
  - Three steps: `1. Find your listing` / `2. Ask the site to remove it` / `3. Check back and keep a record`
  - Footer: `Free guide at freemyid.org`
- Visual: top 40% headline on navy #1b2f5b with white text (contrast at least 7:1); lower 60% three flat step cards on white. No people, no fear imagery.
- Alt text: `Free guide: how to remove yourself from people-search sites in three steps: find your listing, ask the site to remove it, check back and keep a record.`
- Reviewer: graphic-designer.
- Acceptance: text at least 56 px on the 1000-wide canvas; steps match the order in the published guide (check at placement); no promise that removal will happen; logo from brand/logo/final only, at the bottom.

## Order of work

CBS-01 and CBS-02 first (the new pages, smallest, and they set the developer look), then CBS-03 samples, then CBS-04 and CBS-05. CBS-06 only on Morgan's yes. After graphic-designer places files I open a `seo:` WR for web-developer: add names to `NAMES` in `[og].png.ts`, set `ogImage` and `ogAlt` per page, and keep `og:image:width/height` at 1200x630.
