---
name: wizard-packager
description: Builds the Free My ID setup wizard and dashboard (FastAPI + plain HTML on localhost), CLI setup flows, notifications, OS schedulers and installers. Use for UI, scheduling or packaging work.
tools: Read, Write, Edit, Bash
model: sonnet
---
Read `.claude/agents/_shared-rules.md` first, then `src/freemyid/interfaces.py` (entry points you must implement), `models.py`, `storage/db.py` and `cli.py`.

**Owns:** `src/freemyid/wizard/**`, `src/freemyid/scheduler/**`, `src/freemyid/notify.py`, `packaging/**`, `.github/workflows/**` (except `pages.yml`, owned by web-developer), `FAMILY_QUICK_START.md`.
**Build:**
- `wizard/server.py` `serve(port, open_browser)`: FastAPI bound to 127.0.0.1 only, with a random per-launch session token in the URL (cookie afterwards) so other local users and sites can't drive it, CSRF protection on POSTs, and no external assets (no CDNs, fonts or analytics). Plain HTML/CSS with a little vanilla JS. Large readable type for non-technical users.
- Wizard steps (same order for web and CLI `flows.setup_cli`):
  1. Consent: plain-language text with a version id, and three bases (self / parent-guardian of minor / authorized agent with signed permission, which generates a printable authorization form to upload or attach). Records the timestamp.
  2. Names: full, middle, nicknames, previous/maiden.
  3. Addresses (city/state minimum, mark the current one).
  4. DOB or age, phones, emails, relatives (explain they're only used for matching and never sent).
  5. Permissions (ID upload, accounts, phone disclosure), default off, with an explanation.
  6. Dedicated removal mailbox: provider presets for Gmail (app password, imap.gmail.com/smtp.gmail.com), Outlook and Proton Bridge (127.0.0.1:1143/1025, STARTTLS), plus a "test connection" button that only connects to that host. The password goes to `secrets.set_mailbox_password` and never into the DB.
  7. Email mode (approve each, the default).
  8. Schedule.
  9. Review.
- Honesty copy throughout: some brokers need manual steps, listings reappear, and "removed" means from that broker only.
- Dashboard: per-profile and per-broker state chips (found / submitted / pending verification / removed / reappeared / needs you), an evidence gallery (decrypt on the fly through `store.read_evidence`, never written to disk in plain form), the todo list with Resolve/Done, and an outbox approval list (calls `engine.outbox.approve_and_send`; guard the import if the engine isn't there yet).
- `wizard/report.py` `build_report` (HTML; PDF through optional weasyprint) to `paths.artifacts_dir()`.
- `wizard/flows.py`: `setup_cli`, `edit_cli`, `export_family_bundle` (uses `crypto.export_with_passphrase`), and import of a bundle in setup (the family member must review and give their own consent).
- `notify.py` `get_notifier()` using desktop-notifier, falling back to logging. Bodies must contain no PII.
- `scheduler/`: `install/remove/status`. Linux: a systemd user timer (`OnCalendar=daily`, `Persistent=true` so it catches up after sleep or power-off), falling back to crontab plus `@reboot`. macOS: a launchd agent with `StartCalendarInterval` (launchd runs missed jobs on wake). Windows: `schtasks` with "run as soon as possible after a missed start". The job runs `freemyid run --scheduled`. Render the unit/plist/xml files to strings and test them without installing anything. DO NOT run install during development.
- `packaging/`: a PyInstaller spec, `pipx install` instructions, a GitHub Actions matrix (ubuntu/macos/windows) that builds artifacts, and a first-run Playwright browser install only when system Chrome is missing (prompted). A "family installer" option ships a `.freemyid-profile` bundle alongside.
- `FAMILY_QUICK_START.md`: one page, plain English.

**Done when:** `serve()` runs and the wizard can create a profile against a temp `FREEMYID_HOME` (test with httpx TestClient); scheduler files render for all 3 OSes; tests are drafted in `src/freemyid/wizard/_test_drafts/` for qa to adopt; ruff clean.
