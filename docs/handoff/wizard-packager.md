# wizard-packager handoff

## Done (written, import check pending unless noted)
- wizard/draft, ui, dashboard, server, flows (import ok), static/

## In progress
- TestClient test not yet written

## Exact next step
1. Write wizard/flows.py: setup_cli, edit_cli, export_family_bundle, load_bundle(bytes, passphrase)->Draft.
2. Import-check wizard modules, then TestClient test in wizard/_test_drafts/.
3. Then: notify.py, scheduler/ (render.py + __init__.py), wizard/report.py, wizard/firstrun.py,
   packaging/, .github/workflows/build.yml, FAMILY_QUICK_START.md, ruff.
