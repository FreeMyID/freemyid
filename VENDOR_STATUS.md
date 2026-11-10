# WO-321 (issue pending) vendor status

## Done

Added `tests/grok/test_gk_reading_level.py`. It scores `docs/user/*.md` (glob, not a
fixed name list), `FAMILY_QUICK_START.md`, and `docs/USER_GUIDE.md` with the
Flesch-Kincaid grade written in the test:

`0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59`

Syllables are a simple count: vowel groups in aeiouy, a trailing silent e
dropped, and a trailing "le" after a consonant kept. Words of three letters or
fewer, words with no vowel, and numbers count as one. Standard library and
pytest only.

Skipped: fenced code, tables, HTML comments, link targets, and headings. A
section whose heading says it is for helpers (the live one is
`docs/USER_GUIDE.md` "For helpers: the command line") is skipped until the next
heading of the same or higher level. Inline code is counted. New pages under
`docs/user/*.md` are picked up with no name list.

Checked `tests/copilot/test_cp_wording_guard.py` (banned words and unreleased
channels; it does not score grade and does not read `FAMILY_QUICK_START.md`)
and `tests/codex/test_cx_app_practice_wording.py` (app strings only).
`tests/grok/` did not exist in this worktree. This guard does not duplicate them.

The ceiling is grade 8. `BASELINE` is empty: no live page is over 8, so nothing
was rounded up. A baseline page would fail only if it got worse by more than
0.5, or if it dropped under 8 (the failure says to remove it from `BASELINE`).
The failure text prints every page's score. Fake cases: a short plain paragraph
passes (grade about -1.45); a long jargon paragraph fails; code blocks and
tables do not count; a `tmp_path` page named `fresh-page.md` is scored without
being named in the test.

No doc page was edited. `src/` was not edited. No `tests/grok/__init__.py` and
no `conftest.py`. No xfail.

## Baseline pages and scores

No page is in `BASELINE`. Printed scores (two decimals, same as the failure
message). Raw grades are in parentheses. Ceiling is 8.

| Page | Score |
| --- | --- |
| `FAMILY_QUICK_START.md` | 3.46 (3.4572) |
| `docs/USER_GUIDE.md` | 5.03 (5.0298) |
| `docs/user/GLOSSARY.md` | 4.56 (4.5593) |
| `docs/user/HELPING.md` | 4.51 (4.5140) |
| `docs/user/INSTALL.md` | 5.79 (5.7872) |
| `docs/user/mail-gmail.md` | 4.36 (4.3567) |
| `docs/user/mail-other.md` | 4.26 (4.2556) |
| `docs/user/mail-proton.md` | 4.69 (4.6869) |
| `docs/user/troubleshooting.md` | 4.45 (4.4462) |

Highest is `docs/user/INSTALL.md` at 5.79. Margin under the ceiling is about 2.2
grades.

## Findings

None. No live page is over grade 8, so there is no file:line reading-level
defect and no strict xfail. Pages were not edited.

## Next

In-house review. If a later edit pushes a page over 8, either simplify that
page in a docs work order or add it to `BASELINE` with today's score rounded
up and a one-line reason. If a baselined page later scores under 8, remove it
from `BASELINE` or the test fails on purpose.

`docs/vendor/GROK_BOARD.md` and `docs/vendor/GROK_TO_CLAUDE.md` were not
updated. This work order allows only the test file and this status.

## Questions

- Table cells are not scored. The six setup screens in `FAMILY_QUICK_START.md`
  live in a table. Confirm that skip is what you want.
- Headings are not scored. The long quoted errors in
  `docs/user/troubleshooting.md` are headings, so they do not raise the grade.
- `docs/user/INSTALL.md` section "For developers: install from source" is
  scored. The heading does not say it is for helpers. Say if developer
  sections should be skipped too.
- Inline code counts, including source citations such as `` `ui.py:389` ``.
  Only fenced blocks are skipped. Say if citation code spans should be skipped.

## How to test

From this worktree, with `../../.venv`:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_reading_level.py
```

```
........                                                                 [100%]
8 passed in 0.28s
```

8 passed, 0 failed, 0 xfailed, 0 skipped.

```
../../.venv/bin/ruff check tests/grok/test_gk_reading_level.py
```

```
All checks passed!
```

`../../.venv/bin/ruff check tests/grok` also reports `All checks passed!`
(the directory contains only this test).

## Could not verify

- Not run on Windows. The tests use `tmp_path` and `pathlib` only. Repo paths
  are read from `Path(__file__).resolve().parents[2]`. Extra pages are joined
  with `PurePosixPath` parts so `docs/USER_GUIDE.md` is not one filename.
- Pages from WO-311..320 are not in this worktree. The glob was proven with a
  temporary `docs/user/fresh-page.md`, not those files.
- The simple syllable count was not compared to another readability library.
  No new dependency was added. No network, subprocess, git, or app run.
- The rest of the suite was not run.
