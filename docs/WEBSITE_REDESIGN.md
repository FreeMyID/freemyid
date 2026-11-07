# Website redesign v2: decisions, component contract, crew board

Owner: orchestrator (decisions) and web-developer (web lead; keeps the board current). Started 2026-11-07.
Input: `docs/marketing/redesign-teardown-messaging.md` (brand-marketing teardown, IA and draft copy).
Goal: the site reads as real, trusted software instead of a civic/hobby page, **without** weakening any
honesty, privacy or copy rule (POSITIONING.md, BRAND.md, web-developer.md privacy rules all still apply).

## Orchestrator decisions (settled; don't re-open, raise a CHANGE REQUEST if one is wrong)

- **D1 Nav:** `logo | How it works | Guides | Is it safe? | For families | FAQ | [Download]`. "What it removes"
  is a home section plus the guides index, not a page. Header Download is the only filled button in the header.
- **D2 /safety/** ("Is it safe?") replaces /privacy/: merges privacy, "what it never asks for", open source,
  verify-your-download and uninstall. Add `privacy/` to the old-URL redirects in `site.yaml`.
- **D3 No /free/, /compare/, /open-source/ pages this round.** The "$0" card and "Why is it free" live on home;
  open-source and verify-download live on /safety/.
- **D4 Comparison table** (home section 7): build it with the Free My ID and "By hand" columns from facts we
  own. The "Paid removal services (typical)" column ships **only** for rows broker-researcher has sourced in
  `brokers/SOURCES.md` ("Website claims: comparison"). Unsourced rows are left out, not softened by guesswork.
  Never name a competitor. Keep the "where paid services are better" line.
- **D5 No dead download button.** `data/release.yaml` version is null today. Every Download CTA goes through one
  partial (`partials/cta-download.html`): release set → "Download Free My ID" to the release asset; unset →
  "Windows download: coming soon" linking to `download/` (which keeps the WR-9 "opens soon" state). The
  header button follows the same rule (label "Download" or "Coming soon").
- **D6 Visual direction:** clean product look. System sans-serif stack for headings and body (drop the civic
  serif), 20px base, the same navy/red family but red as a small accent only, **one** small flag accent (the
  thin flag bar) and no star rows/stripes as decoration. Calm white/off-white sections, generous space, cards
  with soft elevation, a real product picture in the hero. Still: no web fonts, no JS, CSP unchanged,
  contrast >= 7:1 body / >= 4.5:1 other in both themes, polished dark mode.
- **D7 Product pictures:** graphic-designer captures real screenshots of the wizard, dashboard and printable
  report with the fake persona (Jane Q Testperson, Springfield IL) into `brand/screenshots/`, labelled
  "Example with made-up data". Until they land, pages use the existing `partials/mockup.html` (labelled).
- **D8 Verified claims you may use** (orchestrator checked the code 2026-11-07):
  - "Your details are stored encrypted on your computer" (AES-256-GCM, key in the Windows credential store:
    `src/freemyid/crypto.py`, `storage/db.py`).
  - "Six short screens" (`wizard/draft.py` STEPS). "Checks once a day" (PLAN_V1 D4, Task Scheduler, only when
    the PC is on and the user is signed in: say so where it matters).
  - "Printable progress report" with site names, states and dates only (`wizard/report.py`).
  - "Nothing is sent to us": app talks only to the listed sites, the user's own email and the public site list
    (`netpolicy.py`, shared rule 4).
  - **Not allowed:** "about fifteen minutes" (never timed), any broker count other than build-derived numbers
    (guide count, sample-registry count from the data at build time), "audited", "free forever"/"always free",
    any paid-tier hint, star ratings, reviews, "trusted by", counters.
- **D9 "$0" card:** one plan only: label, "$0", "Free. No trial. No card.", checklist of verified features, a
  D5 Download CTA, and "Why is it free?" (two sentences from the teardown, section 9). No second column.
- **D10 Home order:** teardown section 4: Hero, Trust bar, Proof picture, How it works, What it removes,
  The post, Comparison, Safety (with the does-not box), $0 card, Helpers, FAQ (8 on home), Final CTA. Copy =
  the teardown draft, minus anything D8 disallows. The hero H1 stays "Take your name off the websites that sell it."

## Component contract (page builders write this markup; web-designer styles it)

Builders use only these classes (plus existing utilities). Designer may restyle anything but must not rename.
Need a new component? Add it here in the same commit as its first use and tell the lead.

| Component | Markup (root class, children) | Notes |
|---|---|---|
| Section band | `section.band` + `.band--alt` / `.band--brand`; inner `.wrap` (`.wrap--narrow` for prose) | alternate bands down the page |
| Section header | `.section-head` > `p.kicker` + `h2` + `p.lead` | kicker optional |
| Hero | `section.hero` > `.hero__text` (kicker, h1, `p.hero__lead`, `.hero__actions`, `p.hero__note`) + `figure.hero__media` (img/mockup + `figcaption.caption`) | two columns >= 900px, stacked below |
| Buttons | `a.btn.btn--primary` / `.btn--secondary` / `.btn--ghost`; `.btn--large`; `.btn--small` | one primary per screen |
| Trust bar | `ul.trustbar` > `li.trustbar__item` > `{{ icon() }}` + `span` | 4 items, links to /safety/ anchors |
| Steps | `ol.steps` > `li.step` > `span.step__num` + `h3` + `p` | 3 steps |
| Card grid | `ul.cards` (`.cards--3`, `.cards--4`) > `li.card` > `.card__icon` + `h3` + `p` | auto-fit, container query |
| Proof figure | `figure.proof` > `img`/mockup + `figcaption.caption` | "Sample ... made-up data" caption mandatory |
| Compare table | `.table-scroll` > `table.compare` with `th[scope]`; `td.yes` / `td.no` / `td.partial` | must reflow or scroll at 320px without page scroll |
| Callout | `aside.callout` + `.callout--info` / `.callout--note` | calm, never red alarm |
| Does / doesn't | `.dodont` > `.dodont__col.dodont__col--do` / `--dont` > `h3` + `ul` | existing honesty box |
| Price card | `.price-card` > `p.price-card__label`, `p.price-card__price`, `p.price-card__sub`, `ul.checklist`, CTA | one card, centered |
| Checklist | `ul.checklist` > `li` | check icon via CSS mask-free SVG background is not allowed (no data: URIs): use `{{ icon('check') }}` |
| FAQ | `.faq` > `details.faq__item` > `summary` + `.faq__body` | first two `open` on home |
| Final CTA | `section.cta-final` > h2, p, D5 CTA, `p.cta-final__note` | |
| Header | `header.site-header` > `.brand`, `nav.site-nav` (no-JS menu via `details.menu`), `.site-header__cta` | sticky, D1 |
| Footer | `footer.site-footer` > `.footer-cols` (Product, Learn, Trust, Project) + `.footer-legal` | "No account. No login. No tracking, no cookies." line |

## Crew (agents in `.claude/agents/`; the orchestrator dispatches, the web lead integrates)

| Agent | Owns (edit only these) |
|---|---|
| **web-developer** (web lead) | `tools/build_site.py`, `site_src/site.yaml`, `site_src/templates/base.html`, `redirect.html`, `.github/workflows/pages.yml`, `docs/WEBSITE.md`, this board, **the committed `site/` output** (only the lead commits `site/`) |
| **web-designer** | `site_src/css/**`, `site_src/tokens.yaml`, `site_src/data/icons.yaml`, decorative SVG partials (`brand-mark.svg`, `hero-stars.svg`, `star-rule.html`), `templates/pages/styleguide.html` |
| **web-builder** | `site_src/templates/pages/*` (not styleguide), other `templates/partials/*`, `site_src/pages.yaml`, `site_src/data/{faq,guide_intros,release}.yaml` (release: structure only, values are the orchestrator's). A dispatch may split pages between two builders: then each owns only the pages named in its prompt, and partials/pages.yaml belong to builder #1 |
| **web-qa** | `tools/site_check.py`, `tools/site_shots.py`, `docs/handoff/web-qa.md`. Read-only everywhere else: reports findings as WR rows |

Everyone: preview with `.venv/bin/python tools/build_site.py --out <your scratchpad>/site` (never into `site/`),
commit only your own source files by explicit path, and checkpoint in `docs/handoff/<agent>.md`.

## Board (round 1)

| # | Task | Agent | Status |
|---|---|---|---|
| R1 | Design system v2 (D6): tokens, type/space scale, all contract components, light+dark, styleguide | web-designer | open |
| R2 | IA + chrome: header/nav (D1), footer, cta-download partial (D5), pages.yaml, /safety/ (D2) | web-builder | open |
| R3 | Home rebuild (D10, D9, D4 without the paid column) | web-builder | open |
| R4 | Real screenshots (D7) + WR-24 | graphic-designer | open |
| R5 | Source the comparison "paid services (typical)" rows (D4) | broker-researcher | open |
| R6 | Integrate: rebuild site/, docs/WEBSITE.md, fix seams between R1-R3, commit site/ | web-developer | after R1-R3 |
| R7 | Verify: site_check extensions, screenshots 360/768/1280 light+dark, keyboard, zoom, claim audit | web-qa | after R6 |
| R8 | Security/privacy sign-off | qa-security | after R7 |
