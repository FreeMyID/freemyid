# WO-324 VENDOR_STATUS

## Done

- Added `tests/grok/test_gk_never_asks_user_docs.py`. It names `tests/copilot/test_cp_never_asks_parity.py` and covers the gap that test skips.
- Root `FAMILY_QUICK_START.md` is checked for a Social Security number, bank details, and card details in one "never asks" sentence or list, plus never paying or charging. The base file already says this at `FAMILY_QUICK_START.md:8-9` ("bank or card details" and "never charges you"). No xfail.
- Every `docs/user/*.md` page is read. A Free My ID "never asks" promise must name all three items in one sentence or one list. No page may say Free My ID will ask for a Social Security number, a bank or card number, or a password, except an app, bridge, or other removals-mailbox password.
- Fake cases: a full promise passes; a promise that names only the Social Security number fails; "never asks" split across two paragraphs fails. A full list passes. Asking for those secrets fails. An app password for the removals mailbox passes.
- Did not edit `tests/copilot/`, the docs, or `src/`. Did not add `tests/grok/__init__.py` or a `conftest.py`.

## Next

- In-house: point `tests/copilot/test_cp_never_asks_parity.py` at repo-root `FAMILY_QUICK_START.md`. This WO does not edit that test.
- Nothing left in this vendor's allowed paths.

## Questions

- None.

## How to test

From `.vendor-wt/wo-324`:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_never_asks_user_docs.py`

24 passed in 0.28s. 0 failed. 0 xfailed. 0 skipped.

`../../.venv/bin/ruff check tests/grok/test_gk_never_asks_user_docs.py`

All checks passed.

Not run on Windows. The test uses `pathlib` from `Path(__file__).resolve().parents[2]` and does not write outside the process. Fake cases are strings, not a live app.

## Findings

- `tests/copilot/test_cp_never_asks_parity.py:19` and `:91` look for `docs/FAMILY_QUICK_START.md`. The file is `FAMILY_QUICK_START.md` at the repo root (promise at `FAMILY_QUICK_START.md:8-9`). Confirmed skips: `:77`, `:98`, and `:108`, each "missing named copy: docs/FAMILY_QUICK_START.md" (3 skipped, 17 deselected on `-k FAMILY_QUICK_START`). That test also does not read `docs/user/`. In-house owns `tests/copilot/`; not edited here.
- No strict xfail. No `docs/user/*.md` page currently says Free My ID "never asks", so the three-item rule has nothing to fail on those pages. Mail pages mention passwords only for the person's own removals mailbox, and none say Free My ID will ask for a Social Security number or a bank or card number.
