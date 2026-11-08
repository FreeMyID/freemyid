# Release notes v0.2.0 (draft, not posted)

Status: DRAFT for the orchestrator. Do not publish until v0.2.0 is tagged and the owner OKs it (docs/AUTONOMY.md, Tier 3). Facts here are checked against merged commits and docs; unchecked items are listed in the report to Morgan, not in the text.

<!--
CHECK AFTER RELEASE (for Morgan, delete before publishing):
- PyPI shows 0.2.0 and `pipx install freemyid` works on a clean machine
- ghcr.io/freemyid/freemyid is PUBLIC and :v0.2.0 / :latest pull without login
- Docker image size still about 2 GB
- FreeMyIDSetup.exe, FreeMyIDSetup-0.2.0.exe and SHA256SUMS.txt are on the release
- Upgrade-in-place: AppId in packaging/windows/freemyid.iss is identical in v0.1.2 and now (90CB7231-...), so Inno Setup upgrades the existing install
-->

---

## GitHub release body (paste from the next line)

# Free My ID 0.2.0

Free My ID asks the people-search and data-broker sites that list your name, address and phone number to take your details down, and keeps checking. It runs on your own computer. There is no account and nothing is sent to us.

## If you use Windows (most people)

You do not need to do anything special. Download the installer from freemyid.org and run it like before. If you already have Free My ID, the new installer updates it.

**New, early: see where you are listed (more coming in 0.3)**

- **A "Today" screen** shows what needs you now, plus a page for each site Free My ID knows about.
- **Where are you listed?** An exposure check looks up your name on the people-search sites it can read, before anything is sent, and gives a score from 0 to 100 with plain reasons. The score always says how many sites it could actually check. It is based only on the sites checked, and a low score does not mean you are safe. Sites that block automated visits are listed with a link so you can check by hand. Free My ID never gets around a site's bot protection.
- **"Is this you?"** If a site shows only a possible match, you are asked to confirm before anything is done.
- **Protect yourself checklists.** Free step-by-step guides for things like freezing your credit, ticked off in the app. Your ticks are stored encrypted on your computer. The same guides are on freemyid.org/protect/ (printable).
- **Older addresses (optional, off by default).** You can turn on one extra search under a previous address.
- **California:** if you live in California, the app points you to the state's free DROP request first.
- **A printable summary** of what was found and done.

This part is new and early. It reads a limited set of sites, and the rest of the journey is coming in 0.3.

**What's better in this version**

- **Uninstalling is smoother.** If Free My ID is open when you uninstall it, the uninstaller now closes it for you.
- **Calmer wording.** The email-setup screen (the "Bridge" step for Proton Mail users) uses plainer, less alarming words.
- **A clearer password hint.** The hint on the password screen now says what it actually does.
- **The "Ready" page stays.** The final screen that tells you everything is set up is kept on purpose, so you can see that it worked.
- **Safer handling of your saved details.** Your details are stored encrypted on your computer. This version tightens how the key to that store is kept and how it is wiped if you ask to delete everything.
- **Under the hood.** Many reliability and security fixes from our own review. Nothing for you to click.

**What has not changed**

- No account, no cloud, no tracking. Your details go only to the sites you ask to remove you, in the removal request.
- Free My ID never asks for your Social Security number, bank details or a card.
- Nothing real is sent until you say so.

## Checking the download

Each release lists a checksum file (SHA256SUMS.txt). The freemyid.org download page shows how to compare it, with pictures.

Windows may show a blue "Windows protected your PC" box. That is because we have not bought a publisher certificate yet, not because anything is wrong. The download page shows exactly what to click.

## For technical users (Linux, macOS, Docker)

0.2 is the "every platform" release. The command line and the background scheduler now work beyond Windows.

- **Install from PyPI:** `pipx install freemyid`. The package ships the small sample broker list only; the full list is not in the wheel.
- **Docker:** a non-root, read-only-friendly headless image at `ghcr.io/freemyid/freemyid` (about 2 GB, approximate, because it includes Chromium).
- **Schedulers:** real systemd user timer (Linux) and launchd agent (macOS) install, remove and status.
- **`freemyid doctor`:** says what is ready on this computer and how to fix what is not. `--json` and `--offline` supported.
- **`--json`** on the read commands, with versioned documents (for example `doctor/1`). Documented exit codes. See docs/CLI.md.
- **Headless runs:** `freemyid run --headless` for cron, systemd or Docker. It fails closed (stops and says why) if something needed is missing.
- **Set up without the wizard:** `freemyid setup --from setup.yaml` (versioned config, explicit consent, `--yes`, `--check`, `--update`).
- **Secrets without a desktop keyring:** pluggable backends (OS keyring, passphrase file, systemd-creds). `freemyid secrets status` and `freemyid secrets migrate`.
- **`freemyid exposure`** (`--profile`, `--json`, `--offline`, `--refresh`, `--headless`): the exposure check from the command line. The JSON document is `exposure/1` (score, coverage, coverage note, `drop_first`, `first_checklist`, `old_address_checked`). `--offline` fetches nothing. Results from the last 24 hours are reused.
- **`freemyid checklist list|show|done|undo`** (`--json`): the Protect checklists. `list` starts with `ca_drop` for Californians.
- **Practice first:** `freemyid run --dry-run` searches and reports, sends nothing.
- **Mail:** the computer's hostname is no longer sent in the SMTP greeting.
- Licence: AGPL code. The public sample broker data is CC BY-NC.

## Honest limits

- Free My ID works on people-search and data-broker sites. It does not change what Facebook or Meta does with your account, and it does not stop hacking, wiretaps or phone "listening".
- It asks sites to remove you. Some must answer under their state's law and many do not have to; some will not reply. Sites also re-list people, which is why it keeps checking.
- The Windows installer is not signed yet (the blue box above). The macOS and Linux desktop apps and packages are not part of this release; macOS and Linux are command line only.
- The macOS scheduler has been tested on CI but not yet on real Mac hardware. The Windows installer and scheduled task have not been re-checked on a fresh Windows 10/11 VM for this release. Docker has not been tested with a persistent data folder over many runs.
- In a bare container with no keyring, `doctor` reports the secrets check as failed (exit 1) until you give it a passphrase file or systemd-creds.
- The exposure check only reads sites that allow a plain visit (some need a browser; some are "check by hand"). It is a first look, not a full audit. It shows listings; it does not remove them.
- The first run is on the free sample list of brokers; the larger list is a later, separate step.

Full details: freemyid.org.

(end of release body)

---

## Discord #announcements (3 lines)

Free My ID 0.2.0 is out. Windows: a new, early "where am I listed?" check with a score and free protect-yourself checklists, plus a smoother uninstall.
Linux and macOS users: `pipx install freemyid` or the Docker image, plus `exposure`, `checklist`, `doctor`, `--json` and a real systemd/launchd scheduler. Command line only for now.
It works on people-search sites only, the Windows installer is still unsigned (the blue box is expected), and results vary by site. Details and checksums at freemyid.org.

<!--
SOURCES (hidden; verify before publishing)
- v0.1.3 installer fixes (uninstall closes app, calm Bridge copy, honest password hint, Ready page kept): commit bb2cf2a; docs/ROADMAP.md section 6
- Release scope (Linux/macOS headless+CLI, secrets fallback, real schedulers, --json, YAML config, doctor, Docker, PyPI): docs/ROADMAP.md section 6
- PyPI sample-only wheel: commit b2d6405; docs/RELEASE_v0.2.md "Passed"
- Docker non-root, read-only, ~2.1 GB, doctor exit 1 without keyring: commit 9c9800a; docs/RELEASE_v0.2.md "Passed"
- ghcr.io/freemyid/freemyid, rc/latest rule: docs/RELEASE_v0.2.md "Workflow review"; GHCR public visibility is a post-rc owner step
- systemd/launchd schedulers: commit f8470f3; docs/ROADMAP.md line ~131
- doctor, --offline, --json: commit 6d9d2ba; docs/CLI.md (doctor/1, Exit codes)
- --json on read commands, run/scan --headless, exit codes, fail-closed: commits 0770a5a, 4b28241; docs/CLI.md
- setup --from: commit 777d4ba
- secrets backends, status/migrate: commits 9a81313, acf467b; docs/CLI.md
- Encrypted store/key hardening, wipe sweeps secrets files: commits 81f9940, ee216b9, 4550cc5, 74616a9, 75b613b
- SMTP EHLO hostname: commit 5932635
- --dry-run: docs/CLI.md top block
- Not tested list: docs/RELEASE_v0.2.md "NOT tested"
- Unsigned installer / blue box: site_src/data/faq.yaml (SmartScreen entry); memory/docs on SignPath pending
- No account / nothing sent to us / not "never leaves your computer": docs/POSITIONING.md; commit c4912b9
- Never asks for SSN/bank/card: docs/POSITIONING.md rule 4 and trust panel
- Scope limits (not Facebook, not wiretaps), state-law qualifier: docs/POSITIONING.md
- AGPL / CC BY-NC sample: docs/ROADMAP.md section 2, docs/RELEASE_v0.2.md (LICENSE-DATA.md)
- "Nothing real is sent until you say so": docs/CLI.md line ~256 (enable-submissions)
- macOS/Linux desktop packages later: docs/ROADMAP.md lines 137, 191
- Today view, broker detail, Protect checklists, printable summary: commit 9934dfd; ROADMAP 3.5 ("printable HTML summary in 0.3")
- Exposure scan, score, coverage note, old addresses, DROP first, 24h cache, bot-protection rule: docs/EXPOSURE.md; commits a407f66, 5318639, 736b96b, 0a2d8c8, 519f384
- Checklist CLI: commit 18bf7df, docs/CLI.md; /protect/ pages: commits 2d64912, fce3fc5 (live status of /protect/ on freemyid.org not checked)
- Upgrade in place: AppId identical in freemyid.iss at v0.1.2 and now
- freemyid.org/contact/ returned 404 on 2026-11-07, so no contact line
-->
