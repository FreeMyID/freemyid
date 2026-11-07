# web-designer checkpoint

## R1 design system v2 (D6): DONE 2026-11-07 (commits e9bd160..445f835)
- tokens.yaml v2: one sans system stack, type steps -1..5 (clamp), space 3xs..3xl, radius sm..xl, shadow-1..3,
  new colors card / brand-soft / band-brand / band-brand-ink; 39 contrast pairs, all pass in both themes.
- CSS files (all in @layer components except base/layout/print):
  50 base pieces + buttons, 51 legacy v1 (still used: h2.section-head, btn--pending, card-grid, steps--big,
  callout--gold/myth/fact), 52 header/footer, 54 contract sections, 56 widgets.
- Header: CTA stays visible on phones (compact), icon-only menu toggle under 34em, logo-only brand <= 336px.
- Styleguide shows every contract component. Icons +13 (no-account, eye-off, card-off, key, home, phone,
  calendar, at, question, chevron-down, list, tag, fingerprint).
- CSS 10.3 KB gzip. No horizontal scroll at 320/360 on any page.
Unused decorative partials (mine): partials/star-rule.html, partials/hero-stars.svg: nothing includes them; delete when the lead agrees.
Next round: drop 51-legacy rules as builders migrate the remaining v1 pages (grep first).

## R2 QA fixes WR-31..34: DONE 2026-11-07 (commits ed89017, 293ef2b, 822299d, 3d810ef)
- WR-31 compare: fixed layout (first col 22%, others equal), edge-shadow scroll cue (background-attachment local/scroll),
  tighter phone sizing; stacked cards under 34em via `.compare:has(td[data-label])` (styleguide demos it).
  Home needs `data-label` on its tds (CR to web-builder); contract row updated.
- WR-32 cards--4: 2x2 compact under 34em. WR-33: callout inside a card has no margin and less padding; icon floats on phones.
- WR-34: `h1 + :where(*)` gets space-s (base layer).
- `.section`/`.section--alt` still used by download.html:42 and how-it-works.html:22: rules kept (40-layout, 90-print).
- CSS 11.06 KB gzip (limit 12). Remaining legacy: 51-legacy rules, .section rules, unused star-rule/hero-stars partials.
