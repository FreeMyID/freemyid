# WO-346

Tracker: WO-346 (freemyid-pm#266).

## Done

A broken custom submitter no longer raises into the runner. `get_submitter` still returns a `Submitter`. `load_submitter` returns that submitter plus a reason code.

- Import error (including a syntax error), missing class, a class that raises on construction, and a wrong type each fall back to `generic_submitter` for the tier.
- Reason codes: `import_error`, `missing_class`, `construct_error`, `wrong_type`, `path_refused`. None when the custom plugin loaded, or when no custom plugin was requested.
- A plugin file is executed only if it resolves inside the data folder (`paths.home()` or `paths.bundled_data_dir()`) or the repo. A path outside those roots, including a symlink that lands outside, is `path_refused` and is not imported.
- A `broker.submitter` string that is not `freemyid.submitters.<module>:<Class>` is refused before import. A missing `freemyid.submitters.<leaf>` module may be supplied by `<data>/plugins/<leaf>.py`. The file is loaded under a private module name, so a sibling file is not imported.
- Logs are the broker id, the reason code, and the exception type name. Not the message and not the path.
- No contract change. `get_submitter(broker, tier)` is unchanged for the runner.

## Next

Nothing on this work order. In-house review.

## Questions for the owner

- The runner still calls `get_submitter` and does not read the reason. Switching that one call to `load_submitter` would record the code. That is `runner.py`, which this work order does not allow. Say if you want that follow-up.
- Entry points for installed packages still load. That is the existing entry-point step. Filesystem paths and `freemyid.submitters.*` origins are limited to the data folder, the repo, or the submitters package.
- `tests/test_qa_v03_review.py:256` (`test_exposure_check_events_are_pii_free`) flakes when the substring `555` appears in event JSON (random ids or timestamps). Isolated, 19 passed and 1 failed, and it does not need this change. One full-suite run hit it. The run recorded below did not. Not caused by WO-346.

## How to test

From `.vendor-wt/wo-346`. Fake person only (Jane Q Testperson, Springfield IL). No network.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_plugins_robust.py
```

24 passed.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests -k "plugins"
```

24 passed, 2699 deselected.

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests
```

2512 passed, 206 skipped, 5 xfailed. Exit 0. The warning is the existing Starlette/httpx deprecation from FastAPI's test client.

The 206 skipped tests were not executed. Browser tests in that skip count are not passes.

The 5 xfailed are pre-existing. They are not caused by this change.

```
../../.venv/bin/ruff check tests/grok src/freemyid/engine/plugins.py
```

All checks passed.

```
../../.venv/bin/mypy src/freemyid/engine/plugins.py
```

Success: no issues found in 1 source file.
