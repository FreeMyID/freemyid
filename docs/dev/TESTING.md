# Running developer tests

This guide describes the test setup visible in the public checkout. The test suite defaults to `tests/` and uses pytest's `-k` and `-m` selectors, so you can run a relevant slice while working and the full suite before a handoff.

## Common commands

The development setup and standard full-suite and Ruff commands are listed in [README.md, “For developers and contributors” → “Dev environment”](../../README.md#for-developers-and-contributors). From the repository root, they are:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src tests
```

To focus pytest on one file, pass its path, for example:

```bash
.venv/bin/pytest -q tests/test_registry_split.py
```

To select tests by a name fragment, use pytest's `-k` expression:

```bash
.venv/bin/pytest -q -k "registry and not update"
```

To select tests carrying a marker, use `-m`, such as `.venv/bin/pytest -q -m browser`. The configured test directory, asyncio mode, and registered markers are in [`pyproject.toml`, `[tool.pytest.ini_options]`](../../pyproject.toml). The commands above are documented examples; they were not run as part of this documentation-only change.

## Browser tests

Tests marked `browser` need Playwright Chromium. `tests/conftest.py` probes whether Chromium can launch headlessly. When it cannot, the affected test skips by default. Set `FREEMYID_REQUIRE_BROWSER=1` to make that missing prerequisite a failure, for example:

```bash
FREEMYID_REQUIRE_BROWSER=1 .venv/bin/pytest -q -m browser
```

This makes browser-dependent results required; it does not install Chromium. Browser flows also have bounds and use the shared test helpers described in `tests/conftest.py`.

## Built website checks

Tests whose filenames start with `test_web_` are automatically marked `web_dist` and read the built site under `web/dist`. If `web/dist/index.html` is missing, those tests skip by default. Build the site from `web/` with `pnpm build` (the command named in the skip message in `tests/conftest.py`), then run the marked tests. Setting `FREEMYID_REQUIRE_WEB_DIST=1` makes a missing build fail instead of skip:

```bash
(cd web && pnpm build)
FREEMYID_REQUIRE_WEB_DIST=1 .venv/bin/pytest -q -m web_dist
```

The test fixture checks for `web/dist/index.html`; it does not build the site itself. The Python test job's distinction from the page build is described in the comments around `WEB_DIST` and `pytest_runtest_setup` in `tests/conftest.py`.

## Operating-system markers

`pyproject.toml` registers these platform markers, and `tests/conftest.py` skips a marked test on other platforms:

- `windows_only`: Windows.
- `posix_only`: Linux or macOS.
- `macos_only`: macOS.
- `linux_only`: Linux.

Use pytest's marker selector to focus on one group, for example `.venv/bin/pytest -q -m linux_only`. These markers describe where a test is eligible to run; they do not select an operating system for you.

## Real scheduler tests

Tests marked `real_scheduler` touch the host scheduler. They run only when `CI=true` and the test also has a matching OS marker. Without either condition, collection setup skips them. The general test fixture blocks scheduler calls for other tests. Do not install or trigger a real scheduler locally; use the existing fake-based tests for local work. The marker registration and gates are in `pyproject.toml` and `tests/conftest.py` (`REAL_SCHEDULER`, `pytest_collection_modifyitems`, and `_no_real_scheduler`).

## Shared test isolation

The public `tests/conftest.py` says each test gets a temporary `FREEMYID_HOME` and test key, an in-memory keyring, and blocked outbound network connections. It also replaces scheduler calls for tests not marked `real_scheduler`. Tests should continue using fake people and fixtures. These are the isolation measures visible in that public conftest; this guide makes no claims about private test configuration.

## Source references

- [`README.md`, developer environment commands](../../README.md#for-developers-and-contributors)
- [`pyproject.toml`, pytest configuration and markers](../../pyproject.toml)
- [`tests/conftest.py`, browser availability and required-browser behavior](../../tests/conftest.py) (`no_browser`, `chromium_probe`, and `pytest_runtest_setup`)
- [`tests/conftest.py`, built-site behavior](../../tests/conftest.py) (`WEB_DIST`, `pytest_collection_modifyitems`, and `pytest_runtest_setup`)
- [`tests/conftest.py`, platform and real-scheduler gates](../../tests/conftest.py) (`OS_MARKERS`, `REAL_SCHEDULER`, and `pytest_collection_modifyitems`)
- [`tests/conftest.py`, fixture isolation](../../tests/conftest.py) (`freemyid_env` and `_no_real_scheduler`)
