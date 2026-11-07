# WO-003 — Kai Nakamura [freemyid-codex]

## Done
- Updated only the v0.3 section of the Astro /whats-coming/ page. Retained section IDs, metadata, download controls and account-free email feedback.
- Copy keeps “Planned for version 0.3” and explains four steps: find possible listings; review uncertain matches; choose removal requests; check results. Possible matches may belong to someone else; a confirmed match identifies a listing, not a removal. Requests and confirmed results stay separate.
- Explains score coverage, sites needing manual checking and uncertain results. A low score does not mean details are gone everywhere.
- Separates available website protection guides from planned in-app checklists, retaining the /protect/ link.
- Added repository source comments for the changed claims. Sources: docs/ROADMAP.md principles 4–5, sections 3.1–3.5 and 6; docs/POSITIONING.md legal qualifier; docs/handoff/web-v3.md protection-guide availability.
- Added tests against web/dist HTML only: planned label, ordered journey, match/result distinctions, score coverage, planned printable summary, website guide availability and local link target existence. Missing build output fails explicitly rather than silently skipping.

## Next
- Owner environment: supply existing website dependencies, build and run the commands below. No packages were installed and no network or git commands were run by this session.
- Review the copy and resolve the documentation conflict below. Implementation is ready for review; built-page acceptance remains unverified.

## Questions for the owner
- docs/ROADMAP.md section 3.5 still assigns the proof vault and one-page PDF to v0.3; the newer re-scoped release plan in section 6 moves proof vault + PDF to v0.4. Followed section 6, describing only its v0.3 printable summary; flagged the conflict inline. Please reconcile the roadmap outside this work order.
- No other content questions.

## How to test
From the worktree root, with website dependencies already provisioned:

```
pnpm --dir web build
pnpm --dir web check
python web/scripts/content_check.py web/dist
node web/scripts/gen-tokens.mjs --check
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_web_v03_roadmap.py
/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_web_v03_roadmap.py
```

Observed this session:
- Ruff: passed.
- Build: blocked at token generation by missing package `yaml`; web/node_modules is absent.
- New pytest tests: two setup errors because web/dist/whats-coming/index.html has not been built.
- Link/CSP/budget check: cannot run successfully; web/dist is absent.
- Content check: reports missing sitemap.xml and robots.txt because web/dist is absent; private host-hash scan is off in this worktree.
- Token freshness check: blocked by the same missing `yaml` dependency.
- Existing reported issue, not revalidated: docs/handoff/web-v3.md records three protection-guide “15 minutes” content-check hits. No checker or protection-guide changes were made to bypass them.
- Build tooling in web/src/lib/site.ts invokes git for page dates; owner tooling should run the full build under its own policy. The attempted build stopped before Astro ran.
