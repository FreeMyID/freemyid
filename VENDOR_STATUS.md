# WO-247 (tracker issue pending) — Data folder and wipe-target rules across platforms

## Done
- Added `tests/codex/test_cx_paths_cross_platform.py`; inspected existing test areas first. No duplicate direct guard for Windows `home()` behavior or `is_safe_wipe_target` boundaries was found.
- Acceptance checklist:
  - [x] Windows `%APPDATA%/FreeMyID` path, directory creation and marker.
  - [x] Windows fallback under `Path.home()/AppData/Roaming` when `APPDATA` is missing.
  - [x] `FREEMYID_HOME` override takes precedence.
  - [x] Existing unrelated directory does not get a marker; existing directory with `freemyid.db` does.
  - [x] Wipe-target rejection for user home, every ancestor within `tmp_path`, filesystem anchor, shallow path and unmarked folder; acceptance for marker/database folders.
  - [x] `OWNED_ENTRIES` contains the basename returned by each of `db_path`, `config_path`, `registry_cache_path`, `evidence_dir`, `artifacts_dir` and `logs_dir`, plus the marker and every created directory entry. Each helper's returned parent is the fake data folder.
  - [x] All test-created files and folders are under `tmp_path`; no symlink or mode-bit assumptions.
- No product defect or out-of-lane finding identified; no xfails were needed.
- Addressed Owen Brooks's AC5 review finding: ownership assertions now cover returned file paths even when the helper does not create a file. Removing any helper's basename from `OWNED_ENTRIES` fails the guard.

## Next
- Ready for Owen Brooks's read-only re-review after the AC5 fix. In-house can run the same test on native Windows CI.

## Questions for the owner
- Tracker issue ID is pending in-house sync; it is not present in `docs/pm/issue_map.json` in this worktree.

## How to test
- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_paths_cross_platform.py` — **10 passed**, 0.15s, after the review fix.
- `../../.venv/bin/ruff check tests/codex` — **passed**, after the review fix.
- The tests emulate the Windows platform branch on this host; this run is not a native Windows execution. The test code uses `tmp_path` and `pathlib` for Windows CI.
