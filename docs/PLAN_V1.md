# Vanish v1 plan (project lead, 2026-11-06)

## Goal
A relative double-clicks `VanishSetup.exe`, clicks Next a few times, answers simple questions in a
window that looks like a normal app, and is done. After that Vanish runs by itself on a schedule and
only bothers them when a human really has to do something, with one big button per task.

## Review findings (why the plan changed)
1. **No end-to-end loop exists yet.** Contracts, storage, wizard screens, matcher and letters are
   built, but there's no runner, no submitter, no outbox. Nothing removes anyone yet.
2. **58 of 63 brokers are `web_form`, and most of them block bots** (the researcher got 403s).
   Writing and maintaining 58 Playwright scripts that we can't test live is the wrong bet: they'll
   break silently and a non-technical user can't fix them.
3. **Packaging hasn't started**, and an exe can't be built on Linux. It needs a Windows build machine
   (GitHub Actions `windows-latest`).
4. **The mailbox step (IMAP app passwords) is the hardest thing for an older user.** It can't be the
   one step that blocks everything else.
5. Housekeeping: 2 failing tests, 32 ruff errors.

## Decisions
### D1. Three tiers per broker, chosen automatically from the registry
| Tier | How | When |
|---|---|---|
| **Email** (automatic) | Privacy/deletion request letter (CCPA or state-law template) sent from the removal mailbox. IMAP watcher clicks confirmation links on `confirmation_domains` only. | Broker has `opt_out_email` (primary or alt). Most effective per unit of work. |
| **Assisted** ("Do it with me") | Dashboard opens the opt-out page in the user's **own** browser, with a big side card: numbered steps from the registry, one Copy button per field (only the fields the broker needs), and "I did it" / "I couldn't" buttons. No bot detection, because a real person is doing it. | Default for every `web_form`, `account_required` and captcha broker. |
| **Automatic browser** | Playwright with data-driven `Broker.search` + `Broker.form` steps, system **Microsoft Edge** (`channel="msedge"`, already on every Windows 10/11 machine, so there's no Chromium download). Any challenge, unexpected page or error drops to Assisted. | Only brokers whose registry entry has `form` steps **and** `verification_status: verified`. Start with 3 to 5. |

No per-broker Python classes unless the data-driven path really can't work.

### D2. Mailbox is optional
- With a mailbox: the Email tier is fully automatic, and confirmation links get auto-clicked.
- Without one: Email-tier brokers become Assisted. Vanish shows the letter and offers "Open in Gmail /
  Outlook / Yahoo" compose links (prefilled `to`/`subject`/`body`), plus Copy.
- Guided presets: Gmail and Yahoo (app password, with screenshots-style help), iCloud (app-specific
  password), Proton Bridge, and Other. Outlook.com is labeled "use Assisted mode" (basic auth retired).

### D3. California DROP first for CA residents
If the current address is in CA, the first "To do" is the DROP portal (one request reaches 600+
registered brokers). That's a GOVERNMENT_PORTAL todo with plain-language steps.

### D4. Scheduled runs do the cheap, reliable things
A per-user Windows Task Scheduler job (`schtasks`, no admin) runs `vanish run --scheduled` daily:
check IMAP for confirmations, send due follow-ups and escalations, re-scan the Automatic-tier
brokers on `recheck_interval_days`, and raise one desktop notification if there are to-dos
("Vanish needs 5 minutes of your help"). Clicking it opens the dashboard. Quiet otherwise.

### D5. App shape on Windows
- PyInstaller **onedir**, two executables: `Vanish.exe` (windowed: launcher + wizard/dashboard) and
  `vanish-cli.exe` (console; used by the scheduled task with `--scheduled`, which shows no window).
  The scheduled task should run windowless (use the windowed exe with the subcommand, or the `pythonw` equivalent).
- The launcher shows the wizard/dashboard in a native window via **pywebview (Edge WebView2)**, with
  the default browser as a fallback. The user never sees "localhost" or a terminal.
- **Inno Setup**, per-user install (`PrivilegesRequired=lowest`), Start Menu + Desktop "Vanish"
  shortcut, launches the app at the end of setup. The uninstaller removes the scheduled task and asks
  before deleting data.
- Built by GitHub Actions on `windows-latest`. The artifact is `VanishSetup-<ver>.exe`.
- Unsigned for family testing (SmartScreen: "More info → Run anyway", covered in the Quick Start).
  Before wider release, use Azure Trusted Signing.

### D6. Wizard = 6 big screens
1. Welcome + consent (who is this for: me / my child / someone who asked me).
2. Name (plus "any other names?").
3. Home address (plus "lived anywhere else in the last 10 years?").
4. Birth year, phone, email: "only used to recognize you, never sent".
5. Email for removals: "Use an email account" (guided) or "Skip, I'll do these by hand".
6. "Run automatically?" (one checkbox, default on) → Finish → first run starts, then the dashboard.
Permissions (ID upload, accounts, phone) stay off and live under Settings, not in the wizard.
18px+ text, one question per screen, progress dots, Back always works, no jargon.

### D7. Dashboard = "what's left for me to do"
The top shows a single status ("Vanish is working. 23 sites done, 12 waiting, 4 need you").
Under it is a list of to-do cards, each with one big primary button. Details sit behind "More".

## Ownership for this wave
- **automation-engineer**: `engine/runner.py`, `engine/outbox.py`, submitters `email`, `assisted`,
  `web_form` (data-driven), the `vanish run --scheduled` behavior, Edge channel default on Windows,
  and the dev fixture server + devrun (dry run end to end).
- **wizard-packager**: D5, D6, D7, D2 UI, `FAMILY_QUICK_START.md`, `.github/workflows/build.yml`.
- **broker-researcher**: add `opt_out_email` (+ `alt_methods: [email]`) with citations for every broker
  that accepts privacy requests by email; write `form`/`search` steps for 3 to 5 high-priority brokers
  that can be verified; keep `steps` prose short and plain for Assisted cards.
- **qa-security**: fix the failing tests and ruff, then review each wave; end-to-end dry-run test.
- **Orchestrator**: contract changes (models/cli/interfaces/pyproject), integration, sign-off.

## Done means (v1)
On a clean Windows 11 VM: install without admin → wizard in under 10 minutes → first dry run
→ dashboard shows tiers per broker → scheduled task present → uninstall cleans up. Plus
`pytest` and `ruff` green on Linux and Windows CI.

## Registry decisions (2026-11-06, after research wave)
- 29/63 brokers now have `opt_out_email`. 21 of those come from the CA data-broker registry
  "primary contact" field: we use them as best-effort letters, and the dashboard keeps these
  brokers on a re-check and never shows them as "removed" just because a letter went out.
- `covered_by` sites: submit only through the parent; ignore the covered site's own email.
- `form` steps that end in `human` with `has_captcha: true` are page-health checks only → ASSISTED.
  AUTOMATIC needs real fill/click steps, so no broker qualifies yet. Selectors need a real-browser
  inspect session (later, with the user's OK, against opt-out pages only).
- Off-domain contact emails (e.g. BeenVerified's moneybot5000.com) stay excluded for v1.
