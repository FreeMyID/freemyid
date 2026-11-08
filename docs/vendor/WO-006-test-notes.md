# WO-006 test notes

Hannah Cole — test-quality. Product code and existing fixtures are unchanged.

## Coverage matrix

| Area | Regression coverage |
| --- | --- |
| States | All ten ListingState members, with an exhaustive matrix guard; exact row wording and separate good, waiting, and not-found counts |
| Omitted rows | Unknown and not-found states have no table row; not-found still increments its own count |
| Counts | Zero, one, and two requests, good sites, waiting sites, person steps, and not-found sites; empty results have explanatory text and no table |
| Internal IDs | `_consent`, `_checklist`, and a future underscore-prefixed ID in every state leave the entire output unchanged |
| Ordering | Case-insensitive site-name order, missing-name fallback, parenthesized suffix removal, reversed input order |
| Dates and repeatability | Fixed report date; submitted date preferred over updated date; updated-date fallback; repeated renders match; status objects and names remain unchanged |
| Privacy | Distinctive fake street, city, ZIP, phone, email, birth date in several common formats, and private surname absent; profile label and site name present |
| Escaping | Hostile label and site name survive as decoded text without injected image, event attribute, or inline script |
| HTML semantics | Print button has button type and print hook; non-print control container; Site/What happened/Date headings use column scope |

The new tests call the renderer directly: no Store, registry, keychain, network,
mail, or browser submissions. Shared test isolation is unchanged. `sent` and
`n_todos` are caller-provided totals; these tests do not claim to verify their
route-level calculation or filtering of request records.

## Automated checks

Run from the worktree with the owner's virtualenv:

```sh
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_wizard_summary_regressions.py
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_wizard_v03.py::test_summary_is_printable_and_pii_light
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_wizard_protect_tips.py::test_summary_page_skips_internal_ids
/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_wizard_summary_regressions.py
```

New regressions: **48 passed, 0 failed, 0 expected failures**. Existing internal-ID
summary test: **1 passed**. Ruff: **all checks passed**.

The existing v0.3 HTTP summary test stalled in this sandbox. A standalone retry
bounded by `timeout 15s` also timed out (exit 124). This is an incomplete check,
not a passing test or an established product defect. The initial combined run
also contained invalid broker-ID test data; the new fixtures were corrected to
use permitted underscores and the standalone 48-case run above passed.

## Manual print-preview check (not performed here)

Generate a disposable fake-data preview from the regression fixture. This command
is for the reviewer, from the worktree using the owner's Python interpreter:

```sh
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/python - <<'PY'
import runpy
import shutil
import tempfile
from pathlib import Path

ns = runpy.run_path('tests/test_wizard_summary_regressions.py')
views = ns['views']
views.utcnow = lambda: ns['NOW']
p = ns['fake_profile'].__wrapped__()
status = ns['status']
state = ns['ListingState']
rows = [status(p, 'fake_alpha', state.SUBMITTED),
        status(p, 'fake_beta', state.CONFIRMED),
        status(p, 'fake_gamma', state.NOT_FOUND)]
names = {'fake_alpha': 'Alpha Fake Site', 'fake_beta': 'Beta Fake Site',
         'fake_gamma': 'Gamma Fake Site'}
folder = Path(tempfile.mkdtemp(prefix='wo006-preview-'))
shutil.copytree('src/freemyid/wizard/static', folder / 'static')
html = views.summary_page(p, rows, names, 0, 1)
page = folder / 'summary.html'
page.write_text(html.replace('/static/', './static/'), encoding='utf-8')
print(page.as_uri())
PY
```

1. Open the printed local file URL in a browser. Confirm the fake label, fixed
   report date, two alphabetized rows, one waiting result, one confirmed result,
   and one checked/not-listed result. Gamma should contribute only to the count.
2. Activate “Print this page”. If local-file browser restrictions prevent the
   script from running, open print preview using the browser's Print command and
   record that limitation separately.
3. In portrait preview, check readable text, unclipped columns, wrapping of the
   long fake label, and absence of navigation and print/back controls.
4. Check landscape and a smaller paper size for clipping. Repeat with enough fake
   rows for multiple pages and inspect page breaks; HTML assertions do not prove
   pagination quality or repeated headings.
5. Cancel printing. Remove the disposable preview folder when finished.

This checks browser print preview only. It does not establish PDF export support
or verify a printer, browser, or paper size that has not actually been tested.
