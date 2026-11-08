# WO-101 vendor status

## Done
- Corrected home, Safety, shared FAQ, and legacy home/Safety templates to distinguish local storage from approved removal requests sent directly to the requested site.
- Preserved section IDs, links, components, JavaScript and CSP. Added repository source comments for the privacy promise.
- Corrected Safety illustration alt text and clarified the storage-only checklist label.
- Added tests/test_web_privacy_wording.py: all built HTML checked for old absolute wording; consistent approved-request wording on home, Safety and FAQ; FAQ answer specifically checked; legacy source wording checked.
- Removed borrowed web/node_modules symlink after validation.

## Next
- Morgan runs the owner PR tooling for WO-101 and obtains in-house review.
- Owner rebuilds legacy site/ and runs tools/build_site.py --check; generated legacy output was intentionally not edited.

## Questions for the owner
- Out-of-scope web/src/art/sections/safety-local.svg retains its old title. Art.astro strips the title and uses the corrected page alt text, so built HTML passes. Asked its owner to correct the source title via CODEX-002.
- No browser layout inspection performed; longer copy may merit a visual review.

## How to test
Completed from this worktree using existing dependencies:
- pnpm --dir web build: passed (Astro emitted its Shiki/CSP configuration warning).
- From web/: pnpm check: passed, 61 HTML files, 55 indexable; budgets/CSP/link checks OK.
- From web/: python scripts/content_check.py dist: passed; host-hash leak scan OFF because its private file is absent in this worktree.
- PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_web_privacy_wording.py: 7 passed.
- /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_web_privacy_wording.py: passed.

Before re-running the build, borrow the existing main-checkout web/node_modules as instructed in CLAUDE-001, then remove only that symlink afterward. No git, network or package installs were used.
