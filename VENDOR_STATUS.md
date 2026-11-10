# WO-322 (issue pending)

Vendor: grok
Agent: Ethan Brandt (test-writer)
Status: done

## Done

Added `tests/grok/test_gk_links_gaps.py`. It does not re-check the files covered by `tests/copilot/test_cp_doc_links.py` (`README.md`, `docs/USER_GUIDE.md`, `docs/CLI.md`, and top-level `docs/user/*.md`).

The gap it covers is `FAMILY_QUICK_START.md`, `distro/**/*.md`, and any `docs/user/**/*.md` in a subfolder. For those pages, every relative link must be a file inside the repo, every `#anchor` must match a heading under the same GitHub slug rules as the copilot guard, and every `![...](...)` image must exist and have non-empty alt text. http, https, and mailto links are printed and never fetched.

Fake files under `tmp_path` make a broken link, a broken anchor, a missing image, and empty alt text fail the check. A good page passes, including http, https, and mailto. No `tests/grok/__init__.py` and no `conftest.py`. Docs and `src/` were not edited.

## Next

In-house review of this worktree. No product fix is waiting on this order.

## Questions

None. `docs/user/` has no subfolder Markdown today, so that part of the set is empty until a nested page is added. The test will include it then.

## How to test

From `.vendor-wt/wo-322`:

```bash
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_links_gaps.py
../../.venv/bin/ruff check tests/grok/test_gk_links_gaps.py
```

Exact counts from this session:

- pytest: 22 passed in 0.29s (0 failed, 0 xfailed, 0 skipped)
- ruff `tests/grok/test_gk_links_gaps.py`: All checks passed
- ruff `tests/grok`: All checks passed
- lane files checked: 8 (`FAMILY_QUICK_START.md` plus 7 `distro/**/*.md`; 0 nested `docs/user/**/*.md`)
- web links listed, not fetched: 0 in the lane; 3 sample links in the tmp_path case (http, https, mailto)
- link, anchor, image, and alt problems in the lane: 0

## Findings

None. No broken relative link, broken `#anchor`, missing image, or empty image alt text in the eight lane files. No strict `xfail`. Copilot-covered pages were not scanned again.
