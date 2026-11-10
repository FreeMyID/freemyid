# WO-250 (issue pending) — App string inventory

## Done
- Added `docs/i18n/STRINGS_APP.md`: 32 inventory rows and 45 source-citation spans.
- [x] Inventoried fixed visible English from `views.py`, `report.py`, `tray.py` and `firstrun.py` in the requested Source / Visible string(s) / Context / Plural / variable notes table format.
- [x] Reviewed all six requested modules. Documented that `protect.py` only delegates checklist operations and adds no visible copy; `desktop.py` uses the shared product title and adds no fixed splash or error-dialog wording. Log messages, callbacks, comments and packaging text are not invented UI entries.
- [x] Compared every row with local `STRINGS.md` and the delivered WO-232 (issue pending) `STRINGS_CLI.md`, read-only from the permitted sibling worktree. Linked both inventories; shared exposure-card, brand, navigation, status, guided-step introduction/status, and honesty copy are referenced rather than duplicated. No exact row repeats either inventory.
- [x] Used brace placeholders instead of personal values, noted singular/plural branches and leading/trailing spaces, and flagged legal/privacy/security wording `owner review before translation`.
- [x] Stated plainly that no Spanish interface ships yet and cited the roadmap's future Spanish release.
- [x] Manually checked all 45 citation spans, including every range, against the current worktree source for meaning and wording. Corrected the tray tooltip citation to lines 118 and 125 during this review.
- Only the new inventory and this status file were written. No source changes, personal values, network access, package installation or git commands.

## Next
- Ready for Owen Brooks's independent read-only review, then in-house integration and tracker sync.
- The forthcoming WO-255 (issue pending) adds this document to automatic citation coverage. The existing required citation test does not include this new file in its DOCS tuple; manual review and the explicit helper invocation below cover it for this handoff.

## Questions for the owner
- Tracker issue ID is pending; no entry for WO-250 appears in the supplied issue map.
- Integrate delivered WO-232 (issue pending) so the relative `STRINGS_CLI.md` link resolves in the combined checkout. This worktree's earlier base does not contain that file, and it is outside this WO's writable scope.
- No in-scope splash/error-dialog strings exist in `desktop.py`; any packaging/launcher inventory needs a separate authorized scope. No text was invented to fill that gap.

## How to test
- Required: `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_dev_source_citations.py` — **14 passed**, 0 skipped, 0 xfailed (final run 0.15s).
- Explicit new-document citation validation:
  ```bash
  ../../.venv/bin/python -c 'import runpy; from pathlib import Path; g = runpy.run_path("tests/codex/test_cx_dev_source_citations.py"); p = "docs/i18n/STRINGS_APP.md"; findings = g["document_findings"](p); count = sum(g["parse_citation"](s) is not None for s in g["CODE_SPAN"].findall(Path(p).read_text())); print(f"{count} citation spans; {len(findings)} findings"); assert not findings'
  ```
  Result: **45 citation spans; 0 findings**. This checks syntax, file existence and bounds; manual source review checked meaning for all 45 spans.
- Manual row comparison: **32 rows, 0 exact duplicate rows** against the two predecessor inventories. Reused strings are mapped to their existing inventory instead of copied as new rows.
- Documentation-only change: no browser, native Windows, screen-reader or actual translation validation claimed.
