# WO-305 vendor status

## Done

Added `tests/grok/test_gk_user_doc_claims.py` (and `tests/grok/__init__.py`). It scans only
`docs/user/**/*.md`, `docs/USER_GUIDE.md`, `FAMILY_QUICK_START.md` and `docs/HELPER_GUIDE.md`
for stale claims the other guards do not cover:

- a first-start promise of "15 seconds" (splash and installer now say up to a minute);
- "Coming in v0.x", "Version 0.x isn't out" / "isn't finished until v0.x", and
  "0.x when it comes out", when that 0.x is already `<=` `site_src/data/release.yaml`
  (`0.3.0`). A line that still names a different version as the one `release.yaml` or
  PyPI publishes is a `version_pin`. A bare "in version 0.2.0 the button said…" is not;
- "nothing is sent" / "sends nothing", including "nothing is actually sent". Allowed, as
  on the website and in the app: "to us", "to the project", "to Free My ID",
  "until you click", and "sends nothing about you".

Not duplicated: `tests/copilot/test_cp_wording_guard.py` (guarantee/erase/100%/never sent,
and unreleased channels; it does not read `FAMILY_QUICK_START.md`), the `tests/test_web_*`
claim tests (website only), `tests/codex/test_cx_app_practice_wording.py` (app strings),
and `tests/test_wizard_desktop.py` (splash text).

Fake fixtures pass for real: bad samples are flagged, clean samples (including a future
"Coming in v0.4", "15 days", and the quoted-example marker) are not. README.md is not
scanned. User docs were not edited. `src/` was not edited.

No live "15 seconds" first-start hit. `FAMILY_QUICK_START.md` and `docs/HELPER_GUIDE.md`
already say the first open can take up to a minute.

## Live-doc findings

Each line is a strict xfail on `test_known_stale_user_doc_claim`. The reason names the file.
`test_live_docs_have_no_unlisted_stale_claims` fails if a new hit appears.

1. `docs/USER_GUIDE.md:113` (`coming_shipped`) — "update to 0.3 when it comes out".
   `site_src/data/release.yaml` version is `0.3.0` (published 2026-11-09). Line 250 of the
   same guide already describes 0.3 as current.
2. `docs/USER_GUIDE.md:177` (`nothing_sent`) — "While practice mode is on, nothing is actually
   sent." Practice mode still searches (`docs/USER_GUIDE.md:99`). The app says "no removal
   requests go out" (`src/freemyid/wizard/dashboard.py:131`).
3. `docs/USER_GUIDE.md:180` (`nothing_sent`) — "nothing is sent until the next check."
   Unqualified. The lookup has already gone out (`docs/USER_GUIDE.md:99`).
4. `docs/HELPER_GUIDE.md:53` (`nothing_sent`) — "Nothing is sent except in a request you
   approve." Name and city searches go out before any removal request (`docs/USER_GUIDE.md:99`).
5. `docs/HELPER_GUIDE.md:62` (`nothing_sent`) — practice mode "sends nothing." Searches still
   go out. Approved wording is "no removal requests go out" (`src/freemyid/wizard/dashboard.py:131`).
6. `docs/HELPER_GUIDE.md:72` (`nothing_sent`) — "Nothing is sent until they press OK."
   Automatic sending can send without that OK. The website no longer uses this line.
7. `docs/user/GLOSSARY.md:10` (`version_pin`) — says `release.yaml` lists version 0.2.0.
   The file's `version` is `0.3.0`.
8. `docs/user/INSTALL.md:12` (`version_pin`) — "It lists version 0.2.0". `release.yaml` is `0.3.0`.
9. `docs/user/INSTALL.md:16` (`version_pin`) — "version 0.2.0 is on PyPI".
10. `docs/user/INSTALL.md:48` (`version_pin`) — "Version 0.2.0 is about 64.4 MB".
    `release.yaml` says `0.3.0` and `size_mb` `64.5`.
11. `docs/user/INSTALL.md:72` (`version_pin`) — "version 0.2.0 is in `site_src/data/release.yaml`".
12. `docs/user/INSTALL.md:78` (`version_pin`) — command-line tool "version 0.2.0, from PyPI".

Not findings (allowed on purpose):

- `FAMILY_QUICK_START.md:9` — "nothing is sent to us."
- `FAMILY_QUICK_START.md:37` and `docs/HELPER_GUIDE.md:29` — button label in 0.2.0 versus 0.3.
- `docs/user/GLOSSARY.md:25` — "sends no removal requests" (not "sends nothing").

## Next

Rewrite the twelve lines above in the docs work orders that own those files. Do not edit them
in this lane. When a line is fixed, delete its strict xfail. Leaving the xfail in place after
the fix fails the test (`strict=True`). A new stale line fails
`test_live_docs_have_no_unlisted_stale_claims` with no xfail.

## Questions for the owner

- Keep "nothing is sent to us" allowed in user docs? It matches the website and app exception.
  `FAMILY_QUICK_START.md:9` uses it and is not flagged.
- `docs/HELPER_GUIDE.md:53` sits in the optional-details paragraph (birth year, phone,
  relatives). It was flagged because the sentence is absolute. Say if a narrower reading
  should be allow-listed.
- Keep the 0.2.0 versus 0.3 button-label notes until 0.2.0 is unsupported?
- `pyproject.toml` version is `0.3.1` and `release.yaml` is `0.3.0`. "Coming in v0.3.1" is
  not flagged. Confirm 0.3.1 is not the published release.
- PyPI was not queried (no network). Confirm whether the PyPI package is still 0.2.0 or
  already 0.3.0 before rewriting `docs/user/INSTALL.md:16` and `:78`.

## How to test

From this worktree, with `../../.venv`:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok/test_gk_user_doc_claims.py
```

```
.......xxxxxxxxxxxx                                                      [100%]
7 passed, 12 xfailed in 0.31s
```

```
../../.venv/bin/ruff check tests/grok
```

```
All checks passed!
```

Fake bad text is flagged and fake clean text passes. The 12 xfails are the live-doc findings
above. They are expected failures, not product-code failures.

## Could not verify

- Not run on Windows. The tests use `tmp_path` and `pathlib` only (no hard-coded `/tmp`).
- PyPI and GitHub were not opened. Version pins compare the docs to `site_src/data/release.yaml`
  in this worktree (`version: "0.3.0"`, `date: 2026-11-09`, `size_mb: 64.5`).
- The rest of the suite was not run. Only `tests/grok/test_gk_user_doc_claims.py` and
  `ruff check tests/grok`.
