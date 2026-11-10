# WO-325 vendor status

## Done

Added `tests/grok/test_gk_markdown_a11y.py`. It is an offline guard for Markdown a user or helper reads. `tests/codex/test_cx_app_a11y_sweep.py` checks app screens, not docs. Copilot already checks that links resolve, that `docs/user` pages are linked, and that banned wording stays out. This guard covers the gap: one `# ` title, no skipped heading level, link text that is not "here", "click here", "this", or "link", a header row and separator on every pipe table, no all-caps line longer than three words, and no emoji that is the only signal of meaning. Fenced code and HTML comments are ignored.

Scanned the 16 files that are in this worktree: `docs/user/**/*.md` (7), `FAMILY_QUICK_START.md`, `docs/USER_GUIDE.md`, `docs/CLI.md`, and `distro/**/README.md` (6). Docs were not edited. No `tests/grok/__init__.py` and no `conftest.py`.

## Next

The glossary outline needs a level-2 heading, or the entries need to become level 2. Either change removes the skip. After that lands, delete the strict xfail for `docs/user/GLOSSARY.md` / `heading_skip`. Leaving the marker in place will fail the run (strict xfail, unexpected pass).

## Questions

Should each glossary entry become a level-2 heading, or should one level-2 heading sit above the current level-3 entries? The guard accepts either. Who owns that doc change?

## How to test

From this worktree:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_markdown_a11y.py
../../.venv/bin/ruff check tests/grok/test_gk_markdown_a11y.py
```

Pytest: 102 passed, 1 xfailed (103 collected). The xfail is `test_user_markdown_follows_one_a11y_rule[docs/user/GLOSSARY.md:heading_skip]`. Ruff: all checks passed. `ruff check tests/grok` reported the same.

## Findings

- `docs/user/GLOSSARY.md:12` — heading level 3 (`### People-search site (also called a data broker)`) follows the level-1 title and skips level 2. Later entries stay at level 3 (lines 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, and 68) and are not separate skips. Rule: `heading_skip`. This work order does not edit docs.

The other 15 scanned files passed all six rules. No second strict xfail.
