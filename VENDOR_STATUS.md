# WO-008 — Hannah Cole [freemyid-codex]

## Done
Added tests/test_cli_json_serialization_edges.py after reviewing the existing
command-level coverage in tests/test_cli_json_headless.py and docs/CLI.md.
No product code or existing tests changed.

Gap-to-test matrix:

| Gap | New direct coverage |
| --- | --- |
| Empty collections and schema versions | All four serializers; required JSON types with additive object fields permitted |
| Status order and display names | All six permutations of three fake brokers; unknown name falls back to full broker ID |
| Status optional values | Null tier and optional timestamps; populated UTC timestamps; all three tiers; empty broker list |
| Required row fields | Full fixed IDs, integer counts, enum strings, to-do request ID null/string, report html/pdf |
| Skipped rows | Supplied rows and reasons preserved in status, todos and reports, including their supplied order |
| Escaping | Unicode, quotes, backslashes and embedded newlines in fake labels, titles and report paths round-trip |
| Determinism and mutation | Repeated calls with deep snapshots for all four serializers; inputs unchanged |
| stdout contract | Single emit call produces one unwrapped parseable JSON object and one newline, no stderr; short and long titles; document unchanged |

## Next
Ready for in-house review. No remaining implementation work.

## Questions for the owner
None. No contract defects found; no xfail markers or expected failures.
VENDOR_STATUS.md is updated under the explicit session-end instruction, although
WO-008's allowed-path list names only the new test file.

## How to test
Ran the owner-provided virtualenv executables from this worktree:

```sh
PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_cli_json_serialization_edges.py tests/test_cli_json_headless.py
/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_cli_json_serialization_edges.py
```

Results: 49 passed in 1.06s; Ruff: All checks passed.
New tests use in-memory fake objects and fixed UTC dates, without store fixtures,
registry loading, subprocesses, network access or real keychain access.
