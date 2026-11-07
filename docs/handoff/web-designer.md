# web-designer checkpoint

## R1 design system v2 (D6), started 2026-11-07
Done (committed):
- tokens.yaml v2 (sans stack, step -1..5 fluid, space 3xs..3xl, radius xl, shadow-1..3, new colors card / brand-soft / band-brand / band-brand-ink, 35 contrast pairs all passing).
- CSS split: 50-components (base pieces, buttons), 51-legacy (v1 classes still in old templates; delete per grep), 52-chrome (header/footer), 54-sections (all contract sections), 56-widgets (mockup, SmartScreen, download card, guide list, swatches).
- 30-base sans headings; 40-layout bands + section-head (left-aligned inside .wrap--narrow).
Next: icons.yaml additions, styleguide rewrite with every contract component, screenshots, print CSS update, final legacy cleanup only if grep clean.
Preview: .venv/bin/python tools/build_site.py --out <scratch>/designer/site ; shots script in scratch/designer/shots.py
