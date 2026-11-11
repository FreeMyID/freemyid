# Free My ID: the road from 0.3.1 to 1.0

Owner/PM: Morgan Reyes (orchestrator). Written 2026-11-11, at v0.3.1.
This file is the release plan. It replaces section 6 ("Release plan") of `docs/ROADMAP.md`; the feature catalogue, editions, prices and principles in `docs/ROADMAP.md` still stand.
Companion files: `DESKTOP.md` (Windows, macOS, Linux), `MOBILE.md` (Android, iOS), `WEBSITE.md` (freemyid.org).

Version numbers below are internal targets, in order. They are not dates and nothing here is a promise to users. The website only ever shows what is in a published release (`site_src/data/release.yaml`).

---

## 1. Where we are (v0.3.1, checked against the code)

| Area | What exists today | Source |
|---|---|---|
| Windows | One-click per-user installer (PyInstaller onedir + Inno Setup), 6-screen wizard, dashboard in a native window, daily scheduled task, splash on first start. Unsigned. | `packaging/windows/`, `.github/workflows/build.yml` |
| macOS, Linux | Run from `pipx install freemyid` or the Docker image. Schedulers are real (launchd agent, systemd user timer, cron fallback). No desktop installer. | `src/freemyid/scheduler/__init__.py`, `packaging/docker/` |
| Engine | Three tiers (Email, Assisted, Automatic browser), "Fill it in for me", outbox with first-email approval, reply matcher, escalation timers, exposure scan and score, state-law letters, California DROP, identity-safety checklists, search-engine guidance. | `src/freemyid/engine/`, `checklists.py` |
| Secrets | OS keyring, passphrase (scrypt) and systemd-creds backends over one AES-GCM store. | `src/freemyid/secret_backends.py` |
| Registry | Public sample of 31 brokers (CC BY-NC). The full registry is private and not in the public repo. Weekly registry health job. A maintainers' broker monitor. | `brokers/registry.sample.yaml`, `registry-health.yml`, `monitor.py` |
| Release engineering | CI on ubuntu, macos and windows; PyPI wheel; cosign-signed GHCR image; CycloneDX SBOM; SHA256SUMS; reproducible-build notes. | `.github/workflows/`, `docs/REPRODUCIBLE.md` |
| Distro recipes | Drafts for AUR, Flatpak, Homebrew, Nix, Scoop, winget with placeholder hashes. None is published. | `distro/`, `distro/CHECKLIST.md` |
| Not built yet | Auto-update or update notice, licence keys, signed feed, payments, helper relay, translations in the app, macOS and Linux installers, mobile apps. | grep of `src/freemyid` |

Tray icon code exists (`wizard/tray.py`) but is off by default and needs the optional `tray` extra. Multiple profiles in one install shipped in 0.2.

---

## 2. What "1.0" means

1.0 is the first release we would hand to a stranger's grandmother without a family member standing by. All nine bars must be met.

| # | Bar | Test |
|---|---|---|
| 1 | **Feature-complete core.** Find listings, send removals in three tiers, re-check, keep proof, for 1 to 6 people on one computer, with background runs, helper setup and helper view. | Every item marked "1.0 core" in section 6 is in a published release. |
| 2 | **Three desktops.** Installers for Windows, macOS and Linux that a non-technical person can use, each with scheduler, keyring and browser working out of the box. | `DESKTOP.md` test matrix green on real machines or VMs. |
| 3 | **Signed everywhere.** Windows Authenticode, macOS Developer ID plus notarization, Linux packages and AppImage with published signatures and checksums. Update files are signed and verified before use. | Fresh install on each OS shows no "unknown publisher" style warning that needs a workaround. |
| 4 | **Stability.** No open P1 bug. No data-loss bug in the two releases before 1.0. In-place upgrade from every stable release since 0.3 is tested. A release candidate has run for at least 30 days with family and beta testers. | Upgrade matrix and soak log in `docs/RELEASE_v1.0.md`. |
| 5 | **Security and privacy.** Independent audit done, every high and critical finding fixed, report published. No open MED+ item in `docs/SECURITY_REVIEW.md`. The privacy-proof test suite (epic E7) is green. Threat model published. | Audit report linked from the site's trust page. |
| 6 | **Sustainable.** Plus and Family can be bought without an account, the signed feed is live, refunds and renewals work. | End-to-end purchase test in the processor's live mode. |
| 7 | **Docs and support.** User guide per OS, help centre on the site, Spanish UI and guide, CLI and config reference. Support mail answered within two business days for paid users by an automated process (no staff, see bar 9); only what automation cannot answer reaches the owner. | Help centre covers the 15 most common problems; support process written down. |
| 9 | **Hands-off, no staff (paid 1.0 goal, owner 2026-11-11).** After setup, a paid user never has to act: the app finds listings, sends removals end to end, follows up, re-checks on a schedule, catches re-listings, tracks every legal deadline and keeps proof, on its own. There are no human operators behind the product: no support desk, no removal agents. Everything a competitor does with staff, we engineer (section 7a). Shared rule 5 still stands: we route around human checks, we never break them. | Owner stage-2 test plus beta: median **0** person actions per person per quarter after setup; worst case at most **1 batched click per quarter**; every remaining human-only step listed by broker on the transparency page with the plan to remove it. No support ticket that a self-repair or automated answer could have closed. |
| 8 | **Stable contracts.** CLI verbs, exit codes, `--json` documents, the config schema and the registry schema are versioned and frozen. From 1.0 we follow semantic versioning. | Contract tests; a written deprecation policy. |

**Not in 1.0** (recommended, see decision D8): Business/Partner edition (white-label build, MSI, partner portal), the community plugin API, mobile apps, languages beyond Spanish. They follow in 1.x.

---

## 3. The release train

| Release | Theme | Headline scope | Main builders |
|---|---|---|---|
| **0.3.2** | Patch | Splash fallback for old WebView, hash-locked Windows build dependencies, reopen after upgrade, Playwright bump | In-house (Nina, Dana) |
| **0.4** | For the family (Pat's journey) | Set it up for someone else; large text and read-aloud; printable "what we did for you"; smart re-check; delivery reliability | In-house screens; Codex and Grok epics E1 to E12 |
| **0.5** | Every desktop | macOS app and Linux packages; update notice; Windows signing; package channels published; proof vault; Outlook sign-in | In-house (Dana, Nina); Grok mail; Codex tests |
| **0.6** | Together | Helper relay (end-to-end encrypted, PII-free by default); shared family to-do; Spanish UI; community broker reports | In-house protocol and screens; vendors for tests, client plumbing, docs |
| **0.7** | Fresh feed | Signed registry feed; offline licence tokens (no payments yet); registry at 400+ scale; wider Automatic tier; broker monitoring automated | In-house contracts and security core; Codex finding side; Priya registry |
| **0.8** | Plus and Family | Payments through a merchant of record; buy and activate without an account; pricing and legal pages; support process | In-house; Jordan and web crew; owner for legal |
| **0.9** | Hardening | Independent security audit and fixes; accessibility audit; fuzzing; upgrade matrix; contract freeze; transparency page; 1.0 release candidates | Everyone; outside auditor |
| **1.0** | Sustainable | Signed installers on three desktops; audit report published; contracts frozen | Everyone |
| 1.x | After 1.0 | Mobile companion, Business/Partner, plugin API, more languages | See `MOBILE.md` and decision D8 |

Changes from `docs/ROADMAP.md` section 6: the old plan had three steps (0.4, 0.5, 1.0) and put desktop packaging, the relay, the feed, payments and the audit into two of them. That is too much per release to test honestly. Desktop packaging gets its own release (0.5), the relay and Spanish move to 0.6, the feed and payments are split (0.7, 0.8), and the audit gets a release of its own (0.9).

---

## 4. The gate every release passes

These apply to every minor release. Per-release exit criteria in section 5 add to them.

1. **Tests on the exact commit.** Full `pytest`, `ruff` and `mypy` green on ubuntu, macos and windows CI for the SHA that will be pushed (`docs/SDLC.md`). Vendor browser tests are rerun outside the vendor sandbox before they count.
2. **Security review.** qa-security (Marcus) reviews the range. No open MED+ finding. Every finding has an owner, a code fix and a test (`docs/REVIEW_LOOP.md`).
3. **Release candidate first.** `X.Y.0rc1` goes out as a pre-release that does not move "latest" on GitHub, PyPI or GHCR.
4. **Real-machine check before the tag.** On the rc: fresh install, upgrade over the last stable, single instance, uninstall while running. Windows 10 and Windows 11 always; macOS and Linux from 0.5 (matrix in `DESKTOP.md`). Fake data only (Jane Q Testperson, Springfield IL).
5. **The Pat test.** A non-technical person installs and finishes setup unaided at 1024x768 and 150% scaling, with large text on.
6. **Build hygiene.** Hash-locked build dependencies, SBOM and SHA256SUMS published, `tools/ci/check_distro_hashes.py` exit 0 before any package channel is submitted.
7. **Truth check.** Release notes list only what a normal user can reach. The website changes only after `release.yaml` shows the release.
8. **Owner's go.** A minor release is Tier 3 in `docs/AUTONOMY.md`. The owner approves and pushes the tag. A checklist file `docs/RELEASE_vX.Y.md` records the gate.

---

## 5. Releases in detail

### 0.3.2: patch
- **Scope:** old-pywebview splash fallback; hash-locked Windows installer dependencies; per-vendor route guard; the app reopens after an upgrade; Playwright 1.65 after a CI and VM run; the held Dependabot updates from `docs/RELEASE_v0.3.md`.
- **Exit:** Windows 11 VM upgrade over 0.3.1, first start with the splash, uninstall while running.
- **Built by:** in-house (Nina, Dana), Marcus review.
- **Owner decisions:** none beyond the tag.

### 0.4: for the family (Pat's journey)
Order decided 2026-11-09 (`docs/ROADMAP.md`, "0.4 order").

| Priority | Item | Who |
|---|---|---|
| Must 1 | **Set it up for someone else.** A helper prepares an encrypted setup file; the relative double-clicks it, types the passphrase, sees what will be imported, consents. | Grok: bundle checks, dry-run summary, round-trip tests (E1). In-house: typed errors and a format version byte in `crypto.py`, the `bundle check` command and schema, both screens. |
| Must 2 | **Large text and read-aloud across the whole wizard.** | In-house (Nina, Maya). Codex: accessibility and visual-consistency tests. |
| Must 3 | **One-page printable "what we did for you".** | Codex and Grok: report facts (E5). In-house: the page, print styles, schema and CLI command. |
| Must | **App style guide** and the new look on each screen as it is built. | In-house (Maya, Iris, Nina). |
| Should | Smart re-check and relist detection wired into `state.next_check_at` behind a flag (E2). | Codex helpers; in-house wiring. |
| Should | Delivery reliability: mail polling, retries, run budgets, scheduler messages (E4, E6, E8). | Grok, Codex. |
| Should | Escalation and complaint-pack data (E3); phone-only and email-only removals (E12); yearly check-up backend (E11). | Codex, Grok; in-house templates and screens. |
| Should | Privacy proofs: tests that a request carries only what the listing shows (E7). | Codex, Grok. |
| Should | Tray icon on by default after a VM pass; monthly summary seen on real Windows. | In-house (Nina). |
| Should | User pages for each new screen (E9). Spanish groundwork: string inventories and glossary (E10). | Grok docs; Codex i18n. |

- **Exit, on top of the gate:** each shipped item has a Windows 10 VM pass with large text on, and the line "a first-time user over 70 finishes it without help" is checked. A wrong passphrase, a damaged file and "not a setup file" give three plain messages. The bundle check output holds no personal values. Blocked work orders (WO-505, 506, 516, 526 to 529, 416, 417, 424) are either unblocked by in-house contracts or moved to 0.5 by name.
- **Owner decisions:** D11 (address-confidentiality helper: build it or not, with a safety review).

### 0.5: every desktop
Detail in `DESKTOP.md`.

- **macOS:** `.app` in a `.dmg` built in CI; launchd agent that repairs itself if the app moves; Keychain; menu-bar icon. Signed and notarized if D2 is yes; otherwise it stays a labelled preview for technical users and macOS does not count toward bar 2.
- **Linux:** AppImage plus `.deb` and `.rpm` with a launcher entry and the systemd user timer; AUR, Homebrew, Nix, Scoop and winget recipes published through the hash gate. Flatpak only after a sandbox spike (see `DESKTOP.md`).
- **Windows:** code signing if D1 is decided; winget and Scoop published; Windows 11 ARM check.
- **All three:** an update notice in the app (PII-free version check; it opens the download page); `freemyid doctor` gives the same advice on each OS; browser detection per OS.
- **Carried from the old 0.4 list:** proof vault (per broker: every email, screenshot and confirmation, dated and hashed); Outlook and Microsoft 365 sign-in by device code; legal escalation pack screens on the E3 data; remaining app screens in the new look.
- **Built by:** in-house (Dana: CI and packaging; Nina: launchers, tray, update notice; Marcus: installer and updater review). Grok: Outlook mail flow, scheduler messages, install guides per OS. Codex: doctor checks, installer smoke tests, proof-vault data tests.
- **Exit:** CI installer smoke on three OSes (silent install, first start, schedule install, status, remove, uninstall). Real-machine checks: Windows 10 and 11, one Apple Silicon Mac, Ubuntu LTS and Fedora. Upgrade over 0.4 on Windows. Pat test on Windows and on the Mac.
- **Owner decisions:** D1 (Windows signing), D2 (Apple Developer account), D12 (a Mac to test on), D16 (Microsoft app registration for Outlook sign-in).

### 0.6: together
- **Helper relay.** Two installs pair with a QR code or a short code. The relative's app sends progress and "needs you" items to the helper's app through a relay that only ever holds ciphertext. Default payloads carry no personal details (counts, site ids, to-do types). The helper can nudge and can approve what the relative delegated; consent itself stays on the relative's device.
- **Shared family to-do** ("Mom has 2 things that need her") and a notice to the helper when a new listing appears.
- **Spanish UI:** message catalogue in the app, wizard, dashboard, notifications and user guide in Spanish, reviewed by a native speaker. Letters follow D9.
- **Community broker reports:** "this opt-out page changed", sent by email or a site form without an account, into a review queue.
- **Mobile spike** (time-boxed, see `MOBILE.md` M0): the relay protocol is designed so a phone can be the helper's device later.
- **Built by:** in-house: protocol, crypto, pairing and helper screens, relay service (Dana), threat model (Marcus). Codex: protocol fuzz and property tests, Spanish inventories and guards. Grok: client retry and queue plumbing in its lane, Spanish and helper user pages.
- **Exit:** written threat model for the relay. Tests prove the relay stores only ciphertext with a time limit and size cap, keeps no request logs with addresses, and that a tampered pairing is detected. The site's safety page says plainly what the relay can see (network address, time, message size). No English text left on the Spanish wizard path. Native-speaker sign-off recorded.
- **Owner decisions:** D9 (letters in Spanish or English), D10 (what helpers may see), D13 (relay hosting and cost).

### 0.7: fresh feed
- **Signed registry feed:** versioned, ed25519-signed, served from a CDN; the app pins the root key; rollback, replay and oversize files are refused. Key handling written down: offline root key, online signing key, rotation, revocation.
- **Licence tokens, no payments yet:** a signed token with plan, expiry and a random id; no name, email or device data. Verified offline. Test keys for family. A plan setting gates the Free and Plus lines from `docs/ROADMAP.md` section 2.
- **Registry at scale:** the full registry loads, scans and re-checks inside time budgets; the broker monitor runs weekly and flags changed pages automatically; new brokers are found by cross-checking the state registries (CA, VT, OR, TX).
- **Wider Automatic tier:** verified form steps for the most common people-search sites, each with a success signal. Needs real-browser inspection of opt-out pages with the owner's OK.
- **Opt-in crash reports** that are scrubbed on the device and shown to the user before sending (only if D15 is yes).
- **Built by:** in-house: feed and licence contracts, signature checks, plan gating screens (Morgan, Theo, Nina, Marcus). Priya: registry growth and verification. Codex: finding-side scale and monitor tests. Grok: feed download and retry in the delivery lane. Dana: CDN, signing job, key ceremony runbook.
- **Exit:** tamper, rollback, replay, expiry and clock-skew tests. A network capture test shows the feed request carries the token and nothing else. The Free build works with no network from the bundled registry. An expired licence never deletes data or switches off a safety feature.
- **Owner decisions:** D14 (licence enforcement model), D15 (crash reports), who holds the root signing key.

### 0.8: Plus and Family
- **Buying without an account:** checkout on a merchant-of-record page linked from freemyid.org; the key is shown on the receipt page and emailed by the processor; the app takes the key by paste or file. Renewal reminder 14 days ahead, cancel in two clicks, 30-day refund, price lock (all decided in `docs/ROADMAP.md` section 2).
- **Family:** one key for a household of up to 6 profiles, helper relay included. **Pro:** the same key by file or environment variable for headless installs.
- **Site:** pricing page, terms, privacy policy, refund policy (see `WEBSITE.md`).
- **Support:** who answers `support@freemyid.org`, within what time, from which templates.
- **Built by:** in-house (Morgan: contracts; Nina: licence screens; Dana: processor webhook that stores only key id and expiry; Jordan: pricing and terms copy; web crew: pages; Marcus: review). Grok: user pages for buying, renewing and refunds.
- **Exit:** purchase to activation tested in the processor's sandbox and once in live mode with a refund. Design review and a test show payment data is never joined to app data. A lost key can be recovered from the receipt email without an account. Legal pages read by an attorney.
- **Owner decisions:** D3 (business entity), D4 (payment processor), D5 (final prices), D6 (attorney for terms), D7 (trademark), D17 (support).

### 0.9: hardening (release candidates for 1.0)
- **Independent security audit.** Scope: the encrypted store and secret backends, the setup bundle format, the relay protocol and service, feed and licence verification, the updater, the network allowlist, the installers. Fix every high and critical finding; publish the report.
- **Accessibility audit** against WCAG 2.2 AA with NVDA, VoiceOver and Orca, keyboard only, 200% zoom.
- **Fuzzing** of the mail, registry, bundle and HTML-selector parsers in CI.
- **Upgrade matrix:** every stable release since 0.3 to the 1.0 candidate, with database migrations.
- **Contract freeze** and deprecation policy. **Transparency page** (what we host, what we never see) and published threat model. A second party rebuilds a release and matches the hashes.
- **Soak:** at least 30 days on a release candidate with family and beta testers, no P1.
- **Built by:** everyone, plus an outside auditor. Codex: fuzz and contract suites. Grok: doc freeze. In-house: fixes.
- **Owner decisions:** D18 (audit firm and budget; book it during 0.7).

### 1.0: sustainable
All nine bars in section 2 met. The owner tags. The site moves to its 1.0 state (`WEBSITE.md`).

---

## 6. Where the catalogue items land

Items from `docs/ROADMAP.md` section 3 that are not named above.

| Item (section) | Lands in | 1.0 core? |
|---|---|---|
| Relatives-and-associates view (3.2) | 0.7, Plus | no |
| Map of exposure by site type (3.6) | 0.5 if the screen work allows, else 1.x | no |
| Court and attorney packet (3.5) | 0.8, Plus | no |
| Video walkthrough, offline (3.1) | 0.5 | no |
| IRS PIN, SSA, USPS checklists (3.4) | data exists in `brokers/checklists.yaml`; yearly check-up in 0.4 | yes |
| Property-record and voter-record guidance (3.4) | 1.x | no |
| Gmail sign-in without an app password (3.10) | 1.x (decision D19) | no |
| Docker image, PyPI, developer page (3.8) | shipped | yes |
| Plugin API for community submitters (3.8) | 1.x, after the audit | no |
| White-label build, partner portal, employer pages (3.12) | 1.x | no |
| High-risk professions programme (3.12) | 1.x | no |
| Alias addresses, photo check, breach check (3.2, 3.10) | Later | no |

---

## 7a. Zero-touch engine: how we remove the person and the staff

The goal in bar 9 is an engineering problem, not a staffing one. The tracks below are how we get there. Each becomes work orders; the lead is Morgan unless noted.

**Pick the route a machine can finish (route planner).** For every broker and person, the engine chooses the most automatable lawful route and falls back in order:
1. **Email from the person's own mailbox** (Email tier). The engine reads the reply in the same mailbox, follows the broker's confirmation link only when it is on that broker's allowlisted domain, and answers routine follow-ups from templates.
2. **Search-free forms** that take name and state instead of a listing URL (WO-614: PeopleSearchNow's state-law form and others).
3. **Parent-company requests.** One request to the owner of a site family (for example the nine Tornado Alley sites) covers its sister sites; re-scans prove which ones it really cleared (WO-616).
4. **State-law requests** (deletion and opt-out of sale) under the person's state law, sent by email or postal letter, with the statutory clock tracked.
5. **Postal letters sent by a print-and-mail API** for brokers that accept only mail. The paid plan covers postage; nobody prints or posts anything.
6. **One-request platforms** where the person qualifies (California DROP today; Connecticut's when it opens), filed automatically.
7. **The background home-browser session** (WO-612) for brokers whose pages only open in a real browser: off-screen, read-only.
8. **A batched human click** only for a step a site reserves for people (CAPTCHA, phone call). That residual is counted, published, and attacked broker by broker by moving the broker up this list.

**Close the loop without anyone watching.**
- Scheduled re-checks prove each removal: a confirmed removal, a re-listing (resubmitted automatically), or no answer.
- Escalation ladder with the legal clock: polite follow-up, then a statutory-deadline letter, then a pre-filled state attorney-general complaint sent where the AG takes it without a human check.
- A per-request timeline with proof (sent mail, replies, page snapshots) and a plain monthly report.
- The scheduler catches up after sleep, missed days or a reboot, runs when on battery only if the user allows it, and reports itself broken before the user notices.

**Read broker replies like a person would.** A local reply classifier sorts each answer (done / needs more info / verify identity / refused / auto-reply). It uses rules first, with an optional on-device model later, and never a cloud call with PII. "Verify identity" requests get a template answer that cites the statute and offers only the fields the person allowed (rule 6); handing over an ID document is never automatic.

**A registry that heals itself (no staff curating it).**
- Nightly canary searches with fake names on each broker, from in-house home machines, detect layout drift.
- Drift opens a work order automatically. Agents patch the spec, qa reviews it, and the signed feed (0.7) ships the fix to every install within a day.
- Opt-in, PII-free outcome counts (route, broker, result; no names, no addresses) tell us which routes stopped working. Off by default; the site stays script-free.

**Support without a desk.**
- `doctor --fix` self-repair for the known failure classes (keyring, scheduler, mailbox login, browser missing).
- In-app answers drawn from the help centre.
- Inbound support mail classified and answered from tested templates by the mail gateway. Only what automation cannot answer reaches the owner, and each such case becomes a template, a self-repair or a bug fix, so the owner queue shrinks every release.

**Metrics in the release gate (from 0.6).** Person actions per person per quarter; share of brokers with a fully automatic route; median days to a confirmed removal; re-listing catch time; support mails per 100 users that reached a human. Each release must not make any of them worse.

## 7b. Leverage: make obstruction cost more than compliance

Detail in `LEVERAGE.md` and `../EVIDENCE_ENGINE.md`. Lawful and honest only: no evasion, no false data, no load for its own sake, no unauthorized practice of law.

- **0.5 Compliance-evidence engine** (WO-620 to 626): blocked lawful requests become confirmed obstruction records, tamper-evident evidence bundles and pre-filled regulator complaints the person approves.
- **0.6 Access-then-delete audit** (WO-627/628): a right-to-know request within the legal frequency cap; the export is parsed on the person's own computer; a plain "what they held" report; a cited deletion; proof of deletion afterwards. Genuinely wrong data (mixed-up identities) is corrected with true information.
- **0.8 Attorney handoff** (WO-629): an opt-in export of a case bundle to an attorney the person chooses. Free My ID never files claims.
- **1.x Privacy-preserving identity proof** (WO-630): mDL / Verifiable Credentials selective disclosure, plus a machine-readable privacy-request endpoint proposal for regulators.
- **Rejected:** synthetic "corrections" (false data, harms the person in background checks) and automated mass arbitration (no contract with the people listed; risk of unauthorized practice of law).

## 7. Cross-cutting tracks

| Track | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 to 1.0 | Lead |
|---|---|---|---|---|---|---|---|
| **Broker registry coverage** | Keep the sample and full registry verified; checklists | Guides for the most-searched sites | Community reports queue | 400+ at scale, state-registry cross-check, weekly monitor flags | Daily feed for Plus | Coverage numbers published with their limits | Priya, Theo |
| **Engine reliability** | E4, E6, E8 | Same behaviour on three OSes | Relay transport retries | Feed download, wider Automatic tier | Licence edge cases | Fuzzing, soak | Theo, Codex, Grok |
| **Security and privacy** | E7 privacy proofs; bundle format review | Installer and update-notice review | Relay threat model | Feed and key ceremony review; audit booked | Payment separation review | Independent audit, report published | Marcus |
| **i18n** | Inventories, glossary (E10); catalogue mechanism chosen | Catalogue wired, English only | Spanish UI and guide | Spanish for feed and licence screens | Spanish pricing and legal pages | Freeze | Codex, Nina |
| **Accessibility** | Large text, read-aloud, app style guide | New installers and screens at AA | Helper screens at AA | Same | Checkout handoff readable and keyboard-safe | Outside audit with three screen readers | Maya, Nina, Ruth |
| **Paid tiers and licensing** | none | none | none | Offline tokens, plan gating | Payments live, no account | Refund and renewal drill | Morgan |
| **Family edition** | Helper setup file | Family install guide per OS | Helper relay, shared to-do | Family test keys | Family plan sold | Phone companion follows (`MOBILE.md`) | Nina |
| **Release engineering** | rc and VM check before each tag | Three-OS installers and smoke tests, package channels | Relay deploy and rollback | Feed signing job | Webhook service | Reproducible build checked by a second party; signing on three OSes | Dana |

Rules that hold on every track: no personal data on our servers, no account for regular users, honest copy (`docs/POSITIONING.md`), the non-technical path works first.

---

## 8. Risks

| Risk | Effect | What we do |
|---|---|---|
| Unsigned Windows installer through most of the 0.x line | The blue "unknown publisher" box is the biggest drop-off for Pat | Recommend signing at 0.5 (D1), not waiting for 1.0 |
| Bot protection on broker sites tightens | Fewer Automatic removals | Assisted and "Fill it in for me" stay the default; never work around protection |
| Two vendor teams change backend code in parallel | Merge collisions, quiet regressions | Lanes in `AGENTS.md`, one file per open work order, full suite on the merged SHA |
| The relay or the feed leaks metadata | Breaks the central promise | PII-free payloads by default, capture tests, both in audit scope |
| Legal setup slips (entity, terms, trademark) | Payments cannot open | Start D3, D6 and D7 during 0.6, not at 0.8 |
| Audit finds deep issues late | 1.0 slips | Book early (0.7), run an internal pre-audit in 0.8 |
| Support load at paid launch | Slow answers hurt trust | Help centre first, measured support hours per week, widen sales slowly |

---

## Decisions the owner must make

| # | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| D1 | Windows code signing | (a) Apply again to SignPath Foundation (free; `PROGRESS.md` on 2026-11-09 records the first application as declined, older notes say pending: please confirm); (b) Azure Trusted Signing, about $10 a month, needs identity validation; (c) a certificate from a commercial CA; (d) stay unsigned until 1.0 | (b) at 0.5 | 0.5 (recommended), 1.0 (required) |
| D2 | Apple Developer Program, 99 USD a year | Join now; join at 0.9; never (Mac stays a preview) | Join at the start of 0.5 | macOS in 0.5 and 1.0; iOS later |
| D3 | Business entity and bank account | LLC now; later; sell under the owner's own name | Form it during 0.6 | 0.8; also helps D1, D2 and store accounts |
| D4 | Payment processor | Paddle or another merchant of record (handles sales tax); Stripe plus a tax service | A merchant of record | 0.8 |
| D5 | Final prices | Keep $4.99 a month or $39 a year, Family $69 a year (decided 2026-11-07); revisit | Confirm once before the pricing page ships | 0.8 |
| D6 | Attorney for terms, privacy policy and refund policy | Pay for a review; use templates unreviewed | Pay for one review | 0.8 |
| D7 | Trademark clearance for "Free My ID" (open in `docs/LAUNCH_CHECKLIST.md`) | Clear it before selling; accept the risk | Clear it before 0.8 | 0.8 |
| D8 | Is Business/Partner and the plugin API part of 1.0? | In 1.0 (old plan); in 1.x | 1.x: 1.0 is for people and families | Scope of 0.7 to 1.0 |
| D9 | Letters for Spanish-speaking users | English letter with a Spanish explanation beside it; letters in Spanish too | English with explanation (US brokers answer in English) | Spanish in 0.6 |
| D10 | What a helper may see through the relay | Counts and to-do types only; or, with the relative's consent, encrypted details too | Counts only in 0.6; details as an opt-in later | 0.6 |
| D11 | Address-confidentiality programme helper | Build with a safety review; leave out | Build, shown on the device only, never in reports | That item in 0.4 or 0.5 |
| D12 | A Mac to test on | A Mac the owner or family already has; a rented cloud Mac; buy a used one | Any Apple Silicon Mac the owner can reach | 0.5 |
| D13 | Relay hosting and cost | Cloudflare Workers on our zone; another host; no relay (local network only) | Cloudflare Workers | 0.6 |
| D14 | Licence enforcement | Offline token only (honour system, the feed is rate-limited); a PII-free activation counter | Offline only | 0.7 |
| D15 | Opt-in crash reports | Build with preview-before-send; do not build | Build, off by default | That item in 0.7 |
| D16 | Microsoft app registration for Outlook sign-in | Register under an owner-controlled Microsoft account; keep "use Assisted mode" for Outlook | Register | Outlook sign-in in 0.5 |
| D17 | Who answers support mail at paid launch | The owner; agents through the mail gateway with owner review; a part-time person | Agents draft, owner approves at first | 0.8 |
| D18 | Security audit firm and budget | Paid firm; a funded programme for open-source projects if we qualify; community review only | Paid or funded firm; community review alone does not meet bar 5 | 0.9 and 1.0 |
| D19 | Gmail sign-in without an app password | Go through Google's verification for restricted mail scopes (assessment costs to be checked); stay on app passwords | Stay on app passwords for 1.0 | Nothing in 1.0 |
| D20 | Each minor release tag | Go or no-go after the gate | Per release | Every release |
