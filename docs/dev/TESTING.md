# Running developer tests

This guide describes the test setup in the public checkout. Pytest discovers tests under `tests/` and supports `-k` name filters and `-m` marker filters (`pyproject.toml:80-92`). Use focused runs while working, then run the checks required by your work order before handoff.

## Run tests from the checkout you are changing

**SEC-124 worktree guard:** the shared development environment can have an editable install of the main checkout. `tests/conftest.py:27-36` checks the imported `freemyid` package path and raises `pytest.UsageError` when it resolves to another checkout's `src/`; an installed package from `site-packages` is allowed (`tests/conftest.py:29-36`). This prevents a worktree test from silently exercising main's code. From the root of the checkout or worktree, set `PYTHONPATH` to that checkout's source:

```bash
# From the checkout or worktree root, with its test environment active:
PYTHONPATH="$PWD/src" python -m pytest -q
PYTHONPATH="$PWD/src" python -m pytest -q tests/test_registry_split.py
PYTHONPATH="$PWD/src" python -m pytest -q -k "registry and not update"
```

For a worktree with a shared virtual environment, use that environment's pytest executable and keep `PYTHONPATH="$PWD/src"`; do not point it at another checkout's `src/` (`tests/conftest.py:27-36`). Standard environment setup and Ruff commands are in [README.md, “Dev environment”](../../README.md#for-developers-and-contributors).

From a vendor worktree directly under `.vendor-wt/`, the shared environment is two levels up, so the command is:

```bash
PYTHONPATH="$PWD/src" ../../.venv/bin/pytest -q
```

The general development environment and standard full-suite/Ruff commands are also listed in `README.md:61-68`.

## Browser tests

Tests marked `browser` use Playwright Chromium. The session fixture probes whether headless Chromium can launch; if it cannot, browser tests skip by default. Set `FREEMYID_REQUIRE_BROWSER=1` to turn a missing browser into a failure (`tests/conftest.py:51-101,175-184`). To install the browser in a local development environment, run `python -m playwright install chromium`; the CI workflow installs Chromium before its test job and sets the required-browser flag (`.github/workflows/build.yml:41-52,79-84`). To select browser tests:

```bash
PYTHONPATH="$PWD/src" FREEMYID_REQUIRE_BROWSER=1 python -m pytest -q -m browser
```

The flag requires a usable browser; it does not install one. The browser probe is bounded to 30 seconds (`tests/conftest.py:54-58,76-101`).

## Built website tests (`web_dist`)

`tests/conftest.py:144-154` marks every file named `test_web_*.py`. It also marks `test_*.py` files under `tests/codex/` and `tests/copilot/` when their source matches `web/dist`, a quoted `dist` path, or a `test_web_` helper name (`tests/conftest.py:140-160`). Therefore Codex/Copilot tests that read built output or reuse a `test_web_*` helper receive `web_dist` too.

**CI behavior:** when `web/dist/index.html` is missing, `tests/conftest.py:175-180` skips each `web_dist` test by default; `FREEMYID_REQUIRE_WEB_DIST=1` changes that skip to a failure. The `build.yml` Python matrix installs Python requirements and runs pytest without a web build step (`.github/workflows/build.yml:17-40,79-84`), so `web_dist` tests skip there if no build exists. In contrast, `pages.yml:74-79` builds and checks `web/dist`; then `pages.yml:83-101` runs `pytest -q -m web_dist` with `FREEMYID_REQUIRE_WEB_DIST=1`, so missing build output fails that job.

The Python `build.yml` matrix runs `pytest -q` but does not build the website (`.github/workflows/build.yml:17-40,79-84`), so missing-site tests can skip there. The Pages workflow installs the web tools, builds and checks the site, runs the copy/leak checker, and then runs `pytest -q -m web_dist` with `FREEMYID_REQUIRE_WEB_DIST=1` (`.github/workflows/pages.yml:61-79,83-101`).

To build and check locally, from the repository root:

```bash
cd web
pnpm install --frozen-lockfile
pnpm build
pnpm check
python scripts/content_check.py dist
cd ..
PYTHONPATH="$PWD/src" FREEMYID_REQUIRE_WEB_DIST=1 python -m pytest -q -m web_dist
```

`pnpm build` generates tokens, builds Astro output, and tightens CSP; `pnpm check` validates the built site (`web/package.json:12-16`). The local build and checker commands are also described in `docs/handoff/web-v3.md:39-48`. `content_check.py` runs the copy rules and leak scan; in the Pages workflow it runs before the built-site tests (`.github/workflows/pages.yml:74-79`).

## Platform and real-scheduler markers

These markers restrict a test to a compatible operating system. They do not choose an operating system for you (`pyproject.toml:84-91`; `tests/conftest.py:104-112,157-165`).

- `windows_only`: Windows.
- `posix_only`: Linux or macOS.
- `macos_only`: macOS.
- `linux_only`: Linux.

Select a group with `-m`, for example `PYTHONPATH="$PWD/src" python -m pytest -q -m linux_only`.

Tests marked `real_scheduler` can install or remove a real scheduled job. They need a matching OS marker and run only when `CI=true`; otherwise collection skips them (`tests/conftest.py:113-126,157-172`). An autouse fixture blocks real scheduler calls in other tests (`tests/conftest.py:346-357`). Do not trigger or install a real scheduler in a local test run; use fake-based tests.

## Full registry and sample-registry runs

The full `brokers/registry.yaml` is private; a public checkout may have only `brokers/registry.sample.yaml`. Tests use the full registry when it is present unless `FREEMYID_TEST_NO_FULL_REGISTRY=1` is set; that setting simulates a public checkout without moving or renaming the private file (`tests/conftest.py:38-49,368-375`). Use the sample-registry mode to check behavior that must work in a public checkout:

```bash
PYTHONPATH="$PWD/src" FREEMYID_TEST_NO_FULL_REGISTRY=1 python -m pytest -q
```

## Test isolation

The shared fixture gives each test a temporary `FREEMYID_HOME`, a test-only key, and an in-memory keyring; it blocks outbound socket connections except loopback (`tests/conftest.py:336-364,359-388`). Keep tests offline and use fake people and fixtures, as the conftest requires (`tests/conftest.py:1-2`).

## Before you deliver vendor work

After building the site, run the complete website regressions and Codex tests, not only the new focused test. Any failure blocks delivery under the vendor handoff rule (`docs/vendor/CLAUDE_TO_CODEX.md:705-708,731`). From your worktree root:

```bash
cd web && pnpm build && pnpm check && cd ..
PYTHONPATH="$PWD/src" FREEMYID_REQUIRE_WEB_DIST=1 ../../.venv/bin/pytest -q tests/test_web*.py tests/codex/
PYTHONPATH="$PWD/src" ../../.venv/bin/ruff check tests/codex
```

Confirm that tests used the active worktree's source (`tests/conftest.py:27-36`), inspect any skip or failure rather than treating a skipped built-site test as a pass, and record the exact commands/results and remaining verification limits in the worktree `VENDOR_STATUS.md`.
