# WO-301

## Done

Updated `docs/user/INSTALL.md` and `docs/user/troubleshooting.md` for version 0.3.1, in plain words:

- The first start can take up to a minute.
- A small "Free My ID is starting" window stays until Free My ID is ready.
- After two minutes the window says it is still starting, and there is no need to click again.
- Updating with the new installer keeps your details and the scheduled check.
- The app may need reopening after an update.

Each fact has an HTML comment with the source file and line. Lines in `src/freemyid/wizard/desktop.py` and `packaging/windows/freemyid.iss` use `file:line`. Lines in `packaging/windows/splash_win.py` and `launcher_gui.py` use `file (at :line)` so `tests/copilot/test_cp_source_citations.py` does not treat them as missing files under `src/freemyid` (that guard only resolves `*.py:N` there; see its `_source_matches` at lines 39-43). CLAUDE-G-005 said the install pages must name the released version, so the 0.2.0 rows that described the current download were updated. The release record lists version 0.3.0, published 2026-11-09, about 64.5 MB (`site_src/data/release.yaml:5-7`). The app reports 0.3.1. PyPI was not rechecked. The unknown-publisher section was not added (that is WO-310). The first-start sentence is the one Morgan accepted: "The first time can take up to a minute. Please wait; there is no need to click it again."

No product bug. No `src/` edit.

## Next

Owner review of the two user pages. WO-310 still owns the unknown-publisher troubleshooting section, and it should be written on a copy of this troubleshooting page.

## Questions for the owner

The download record is 0.3.0 and the app reports 0.3.1. This page names both, and it does not claim a PyPI version, because PyPI was not rechecked. Say if the public page should wait until those two numbers match.

## How to test

From this worktree:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot tests -k "doc or wording or guide"
```

570 passed, 27 skipped, 2086 deselected, 1 xfailed, 1 warning in 5.87s. Same counts after the version-row correction.

The xfail is pre-existing and not from this work: `tests/copilot/test_cp_never_asks_parity.py::test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]` (`docs/FRIDGE_CARD.md:17` missing "never charges you").

## Could not verify

The installer was not run on Windows. "Keeps your details and the scheduled check" and "may need reopening" are read from the script: saved details are in a different folder (`freemyid.iss:83`), that folder and the scheduled check are removed only while uninstalling (`:97` and `:64`), a running Free My ID is closed during install (`:28`), and opening again is an optional checkbox (`:56`). A real Windows update was not watched.
