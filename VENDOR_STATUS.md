# WO-007 — Kai Nakamura [freemyid-codex]

## Done
- Updated only the developer page and its new regression test, plus this required status file.
- First run links the existing version 1 setup schema and fake example YAML using site.repo_url. Shows validation first, then terminal confirmation; states that validation saves nothing.
- Corrected the old terminal-wizard/no-questions description against docs/CLI.md. No permission, mailbox or practice-mode instructions changed.
- JSON example is read-only `freemyid status --json`; explains one object on stdout, human messages on stderr, versioned schemas and additive fields. Retains the CLI exit-code reference link.
- Kept coming labels, section IDs, metadata, downloads, account-free support and other sections. Added repository source comments.
- Four built-HTML regression tests cover links, command order/confirmation, JSON guidance and unreleased labels. They never execute examples or use legacy output.
- Ruff passed for the new test using the owner-provided virtualenv.

## Next
- Owner environment needs existing web dependencies provisioned before build and rendered-HTML verification can complete. No packages were installed.
- Re-run required checks below; CSP, links and budgets remain unverified because no build output exists.

## Questions for the owner
- Existing first-run copy conflicted with docs/CLI.md: setup opens a web wizard, while file import requires confirmation. Updated this section to match the CLI reference. No unresolved conflict found within the changed claims.
- VENDOR_STATUS.md is required by the session rules and completion instruction, though omitted from the work order's allowed-path list; it is the only additional authored file.

## How to test
- `pnpm --dir web build`: attempted; fails because web/node_modules is missing (cannot resolve yaml), before output generation.
- `pnpm --dir web check`: attempted; fails because web/dist is missing. CSP/link/budget checks could not run.
- `python web/scripts/content_check.py web/dist`: attempted; reports missing sitemap.xml and robots.txt. Host-hash scan OFF because private list is absent. These are missing-build results, not content findings.
- `.venv/bin/pytest -q tests/test_web_developer_first_run.py`: attempted; local .venv is absent.
- `PYTHONPATH=src /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/pytest -q -p no:cacheprovider tests/test_web_developer_first_run.py`: ran; four fixture errors explicitly report missing web/dist/developers/index.html. No rendered assertions could run.
- `/home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_web_developer_first_run.py`: passed.

Sources: docs/CLI.md (doctor, setup --from, --json rules, status/1, Exit codes); schema/setup-config.schema.json; docs/examples/setup-config.example.yaml; docs/ROADMAP.md 3.8 for release status. No network, git, package installation or page-example execution used.
