# Codex website refresh program

Status: revised per CLAUDE-036 on 2026-11-08; owner tracker/worktree preparation pending

## Goal

Give Free My ID's public website a polished, modern software feel while remaining calm, readable, and credible for older, tech-wary Windows users. Anchor the work on the settled D6 design direction in `docs/WEBSITE_REDESIGN.md`, not on Astro. Treat external sites only as references for broad hierarchy and rhythm. Make original Free My ID design, copy, and artwork. Do not copy source, layouts, assets, brand marks, or wording.

## Design direction

- System sans-serif stack; 20px base body text; navy family with red as a small accent; one thin flag bar; calm white/off-white sections; generous spacing; soft-elevation cards; polished light and dark modes.
- Meet contrast of at least 7:1 for body text and 4.5:1 for other text in both themes. Use existing `var(--...)` tokens only; if a token is missing, report a CHANGE REQUEST for the owner. Do not hard-code colors.
- Use a real product screenshot in the homepage hero, labelled “Example with made-up data” wherever data is visible. Concept illustrations explain ideas only; they never stand in for the product.
- Do not use gradient text, glows, a dark-hero developer-tool look, low-contrast grey-on-grey text, body text under 20px, carousels, marquees, scroll-reveal animation, hover-only affordances, or icon-only buttons.
- Build trust through sourced explanations, never invented statistics, testimonials, customer logos, performance comparisons, or guarantees. Every public claim must be in D8's allowed list or be flagged for owner review.
- D8 claim allowance is limited to encrypted local storage, six short screens, once-a-day checks only while the PC is on and the user is signed in, a printable report containing site names/states/dates, and “Nothing is sent to us” with its documented scope. Do not say “about fifteen minutes”, use unsourced broker counts, claim an audit, promise “free forever”/“always free”, imply paid tiers, or use ratings, reviews, “trusted by”, or counters.
- Preserve script-free CSP, keyboard access, existing content decisions, and reduced-motion preference. No web fonts, JavaScript, external requests, analytics, new dependencies, or shared app/site token changes.
- Validate 320/360/768/1280 CSS px, Windows display scaling at 125% and 150% (about 1024 and 1280 CSS px effective widths), 200% zoom, and tap targets of at least 44px.

## References reviewed

- Astro: https://astro.build/ — hierarchy and rhythm only.
- DeleteMe: https://joindeleteme.com/ — broad process explanation pattern only.
- Incogni: https://incogni.com/ — broad progress-sequence pattern only.
- Optery: https://www.optery.com/ — broad feature grouping pattern only.

References guide design analysis only. Never name or compare these sites on Free My ID's pages. They are not permission to reuse code, copy, logos, screenshots, or claims.

## Existing project constraints

- `docs/WEBSITE_REDESIGN.md` decisions D1–D10, `docs/BRAND.md`, and `docs/POSITIONING.md` remain in force. Preserve the approved home H1: “Take your name off the websites that sell it.” Do not add product claims or pricing.
- Keep all edits in specifically listed page, art, screenshot-output, test, and report paths. Do not edit `web/src/styles/tokens.css`, `global.css`, app files, API/data contracts, global chrome, security/privacy behavior, forms, consent, build/release/CI, or dependencies.
- The refresh foundation must be route-scoped and must not alter styles on non-refresh routes. Prefer `.site-refresh` namespaced selectors and existing assets/components where suitable.
- Each page WO is a separate owner-prepared branch and can be reverted independently. Foundation dependencies are explicit below; do not start dependent page work until its base is owner-prepared.

## Sequence

1. WO-194: design brief (accepted with CLAUDE-036 amendments).
2. WO-195 and WO-196: scoped styling foundation and conceptual SVG art; start together.
3. WO-200 home, WO-201 how-it-works, WO-205 safety, WO-206 download, WO-202 families, WO-207 FAQ, and WO-203 guides.
4. WO-197 developer hub, WO-198 CLI and WO-199 config last.
5. WO-204: independent visual, content, accessibility, CSP, and rollback review after pages are integrated.

Keep WIP at five or fewer. Home, how-it-works, safety, download, families, FAQ, and guides are frozen for in-house web edits while their refresh WOs are active. `/i-do-not-consent/` and `/protect/` are deliberate exclusions for this round, not omissions. CP-37/#165 is superseded by WO-198; CP-42/#170 is superseded by WO-199. Worktrees, issue tracker updates, and pull requests are owner-tooling operations.

## Independent rollback

Each work order uses its own branch and allowed-path list. Revert a single page PR to restore that route; revert WO-195 only after reverting pages that depend on its classes. Artwork can be reverted independently after dependent pages are reverted. No data migration, app contract, shared token, runtime, or production configuration changes are included.
