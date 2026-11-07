# WO-004 — Amara Okoye [freemyid-codex]

## Done

- Audited the shared FAQ. Native details/summary, items/openFirst, IDs,
  answer rendering and initial open-state expressions are unchanged.
- Added component-scoped `overflow-wrap: anywhere` and a zero minimum inline
  size for question flex children so long questions and answer links can wrap.
- Made the minimum target dimensions explicit (44px width, at least 44px
  height, retaining the larger tap token).
- Added a 3px inset keyboard focus outline using heading ink. The inset keeps
  the outline within the row; no clipping or overlay is needed. Existing
  reduced-motion handling remains in place; no JavaScript was added.
- Added built-HTML regression tests for home and FAQ pages: ordered IDs,
  question text, native semantics without ARIA overrides, decorative icons,
  answer elements/links, and home-first-two/FAQ-all-closed initial states.
- Added checks of the actual generated token pairs used for question text,
  answer text, links and focus against card/hover backgrounds in both themes.

## Next

- Owner builds the website in an environment with dependencies already
  available, then runs the built-HTML tests and site gates below.
- Complete the manual verification matrix before acceptance. Implementation
  is ready for review; acceptance is pending these checks.

## Questions for the owner

- Please provide build/gate and browser/assistive-technology results at the
  next check-in. This worktree has neither web/node_modules nor web/dist.
  Installing packages/network access is prohibited. The normal build also
  invokes Git through web/src/lib/site.ts; vendor rules prohibit running Git.
  No build helper or other out-of-scope file was changed to bypass that rule.

## How to test

Executed:

```sh
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_web_faq_accessibility.py
/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_web_faq_accessibility.py
```

- Pytest: **8 passed, 2 failed**. Both failures explicitly report missing
  built HTML (web/dist/index.html and web/dist/faq/index.html). The tests do
  not silently skip missing build prerequisites.
- Ruff: **passed**.
- Build, CSP/link/budget checks, content checks: **not run**, prerequisites
  unavailable and build invokes prohibited Git. No inherited site failure
  has been verified; do not interpret the missing-build failures as one.

Owner commands after dependencies are available (no install requested):

```sh
cd web
pnpm build
pnpm check
python scripts/content_check.py dist
node scripts/gen-tokens.mjs --check
```

Then run the pytest/Ruff commands above from the repository root. Build output
is needed: these tests inspect Astro HTML, not the legacy site/ pages.

| Verification | Light | Dark | Browser / assistive technology |
| --- | --- | --- | --- |
| Token contrast for text/link/focus | Pass, >=4.5:1 | Pass, >=4.5:1 | Python calculation; no browser |
| Rendered focus visibility and target dimensions | Unverified | Unverified | None available for a built site |
| Tab navigation, Enter/Space toggle | Unverified | Unverified | None used |
| 360px viewport, long questions/answer links | Unverified | Unverified | None used |
| 1280px viewport at actual 200% browser zoom | Unverified | Unverified | None used |
| Expanded/collapsed state announcement | Unverified | Unverified | No screen reader used |
| Reduced motion, rendered behavior | Unverified | Unverified | Existing motion-reduce class retained |

Manual procedure: serve the built site locally; visit home and /faq/ in both
themes. Tab through every summary and answer link, check the focus outline,
and toggle with Enter and Space. With a screen reader, confirm the question
and expanded/collapsed state are announced. Record browser, screen reader
and versions. Repeat at 360px and at 1280px with actual 200% zoom, including
long unbroken question/link text inserted locally with developer tools;
confirm no FAQ-caused horizontal scrolling. Check reduced motion enabled.
Native disclosure behavior is retained but is not a substitute for these
manual checks. WCAG reference: https://www.w3.org/TR/WCAG22/
