# WO-303 vendor status

## Done

`docs/CLI.md` was checked against `freemyid <command> --help` for every visible command and
subcommand, with `FREEMYID_HOME` set to a new empty directory from `tempfile.mkdtemp` and
`PYTHONPATH` set to this worktree's `src` (the venv script otherwise imports the main
checkout, which matched this tree's CLI files at the time of the check). `--help` did not
create a database in that directory.

Brought the reference in line with that help text and the current source:

* `search-engines` lists steps when the action is left out. There is no `list` word;
  `freemyid search-engines list` exits 2. Documented `open`, `done` and `undo`, the human
  lines, and that `--json` keeps those lines on stderr (`cli.py:895`, `cli.py:903-966`).
* `exposure --old-addresses` matches the help line (one extra previous-address page per
  site, off unless the flag is passed). Omitting it leaves the choice to config
  `exposure_old_addresses`. There is still no previous-name flag.
* The score-change line is `trend.note`. Text prints it only when there are 2 or more
  points, and it is printed after the drivers, not between the coverage note and the
  drivers (`cli.py:458-463`, `engine/exposure.py:847-865`). Up, down, same, fewer-sites
  and formula-change wording is quoted.
* Coverage wording is the real `coverage_note` and `headline` sentences, including "does
  not mean you are safe" and the cases that do not say "on the N sites we could check"
  (`exposure_models.py:98-114`, `engine/exposure_score.py:197-215`).
* `monitor` help: repeatable `--broker`, `--browser` opens the page only, human summary,
  and `monitor/1` built at `monitor.py:376-386` (the old `358-368` citation was the fetch
  loop). A `--previous` file that cannot be read is not compared, same as a bad schema.
* Also corrected: `fill --timeout` default 600, the full `wipe` question and the exit 2
  refusal, `secrets migrate --remove-keychain-key`, `profile remove --yes`, optional
  `registry validate` path, and the file:line list under "Where this table comes from".

No product bug was turned into a strict xfail. Tests are outside the allowed paths, and
the mismatches below are missing help strings, not a wrong result.

## Next

None for this work order. In-house can add the missing command help strings in `src/`
if they want `--help` to describe every command.

## Questions for the owner

* Several commands and options have no help string, so `--help` shows a bare name:
  `schedule install`, `schedule remove`, `schedule status`, `registry update`,
  `registry validate`, `config set`, `profile add`, `profile edit`, `todo done`,
  `outbox approve`, plus `-p` / `-b` / `--yes` / `--timeout` / `--plain` / `profile add
  --prefill` (`cli.py` at those commands). Is that worth a follow-up in `src/`?
* `cli_json.py:32-33` documents timestamps as UTC but `_ts` only calls `isoformat()`.
  This check did not prove every stored value is UTC. Leave the public UTC promise as it
  is unless you want that traced.
* `run/1` still quotes the dry-run summary from `engine/runner.py:106` ("Dry run: nothing
  was sent or submitted."). That is the program text, not a new promise. Say if you want
  the example shortened so the reference does not repeat it.

## How to test

From this worktree, the same way the help pages were taken: set `FREEMYID_HOME` to a new
empty directory created with `tempfile` (do not hard-code a temp path in the docs) and
`PYTHONPATH` to `$PWD/src`, then `../../.venv/bin/freemyid <command> --help`.

Required check, from this worktree:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_docs_match_cli.py tests -k "cli and doc"
```

Result: `219 passed, 1 skipped, 2471 deselected, 1 warning in 3.75s`.

The skip is `tests/test_web_developer_release_status.py::test_status_separates_shipped_cli_from_planned_desktop_and_docker`
(`tests/conftest.py:180`): `web/dist/index.html` is not in this worktree. Building it needs
`pnpm`, which this work order does not run. It is not a CLI reference failure.

Do not run `run`, `send`, or `schedule install` without `--help`. `send` is not a command.
`monitor` was not run (it would fetch broker pages). `search-engines open`, `done` and
`undo` were not run (open would launch a browser). Exposure text was not run for a person;
the wording is from the source lines above. `tests/test_exposure_coverage.py` and
`tests/test_cli_old_addresses.py` were read and were not part of this pytest selection.
