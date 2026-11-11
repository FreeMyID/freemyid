# Free My ID: product roadmap

Owner/PM: Morgan Reyes (orchestrator). Written 2026-11-07, after v0.1.2. This is the master list. `docs/PLAN_V1.md` stays the spec for the shipped v1 core, `docs/POSITIONING.md` governs every word users see, and `docs/AUTONOMY.md` governs what agents may do alone.

Legend. **Tier:** F = Free, P = Plus, Fam = Family, Pro = Pro/self-host, B = Business/Partner. **Phase:** 0.2, 0.3, 0.4, 0.5, 1.0, Later, Dream.

## Roadmaps (added 2026-11-11, at v0.3.1)

This file stays the feature catalogue, the editions and the principles. The release plan and the per-platform plans now live in `docs/roadmap/`:

| File | What it holds |
|---|---|
| [`roadmap/ROADMAP_TO_1.0.md`](roadmap/ROADMAP_TO_1.0.md) | The release train 0.3.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0: scope, exit criteria, who builds it, what "1.0" means, the cross-cutting tracks |
| [`roadmap/DESKTOP.md`](roadmap/DESKTOP.md) | Windows, macOS and Linux: installers, signing, scheduler, keyring, browser, updates, CI and the real-machine test matrix |
| [`roadmap/MOBILE.md`](roadmap/MOBILE.md) | Android and iOS: platform limits, options, recommended architecture, store rules, milestones (after desktop 1.0) |
| [`roadmap/WEBSITE.md`](roadmap/WEBSITE.md) | freemyid.org: pages per release, help centre, search, budgets, hosting |

Where a phase tag in section 3 or 5 below differs from those files, the files in `docs/roadmap/` win. Each of them ends with a table of decisions the owner must make.

---

## 1. What Free My ID is

A program that runs on your own computer and takes your name, address, phone and relatives off the websites that sell them, then keeps checking so the listings stay gone. It is free for individuals, open source (AGPL), and never sends your details to us.

**The promise, in one breath:** your details are stored only on your computer and go nowhere except in a removal request you approve, sent straight to that one site; nobody pays with their privacy; and we never scare you into buying. (Wording corrected 2026-11-07: requests necessarily send the person's details to the broker they ask, so 'never leaves your computer' was too absolute.)

### Principles (they decide every tie)
1. **Local-first.** Personal data lives only on the user's device, encrypted. Our servers hold no PII, ever. Anything we host (registry feed, licence check, crash reports) is PII-free by design and test.
2. **Grandma-proof first, power-user second.** Every feature ships with the non-technical path working before the terminal path is polished. The terminal path is never removed to make the simple path simpler.
3. **Honest by default.** No fear pop-ups, fake counters, auto-renew traps or bundled junk. Free means free forever, not a trial.
4. **The user is in charge.** Nothing goes out in their name without consent; practice mode is the default until they say "go".
5. **Evidence over claims.** Every removal has proof attached, and we say "requested", "confirmed" or "relisted", never "erased".
6. **No account, ever, for regular users.** Downloading, installing, using, getting help and giving feedback never require signing up anywhere (not with us, not with GitHub, not with anyone). Regular users never land on github.com: downloads come from freemyid.org addresses, feedback goes through email or a form on our own site. GitHub links are for developers only (developer page, footer "source code"). Paid tiers use a licence key, not a login. (Owner rule, 2026-11-07.)
7. **Open engine, paid freshness.** The code is free and forkable. What we sell is the constantly updated broker knowledge and the convenience around it (the McAfee "virus definitions" model).

### Who it is for
| Persona | Needs | Edition |
|---|---|---|
| **Pat, 72, Windows 10**, sent the link by a grandchild | Big buttons, one decision per screen, never a terminal | Windows app |
| **Dana, 45, does it for both parents** | Several people in one app, sees progress, approves things remotely | Family |
| **Sam, 30, Linux homelab** | pipx/Docker, headless, cron, JSON, no GUI | Developer/Pro |
| **Judge, nurse, cop, survivor** | Higher-risk exposure, faster re-checks, legal letters, proof for court | Plus / via employer |
| **Credit union / MSP / employer** | Offer it to members/staff under their brand, without holding their PII | Business/Partner |

---

## 2. Editions and pricing (owner decisions, 2026-11-07)

| | **Free** | **Plus** | **Family** | **Pro (self-host)** | **Business / Partner** |
|---|---|---|---|---|---|
| Who | Every individual, forever | People who want it fully hands-off | A household, up to 6 people | Tech users running headless | Employers, credit unions, MSPs, insurers |
| Price (decided 2026-11-07, see docs/marketing/competitor-pricing.md) | $0 | $4.99/mo or $39/yr | $69/yr | included in Plus (same licence) | quoted per seat / per member |
| App, wizard, dashboard, CLI | yes | yes | yes | yes | yes, white-label option |
| Email + assisted removals | yes | yes | yes | yes | yes |
| Brokers | core set (~60 biggest, updated monthly) | full feed (400+), updated daily | full | full | full |
| Automatic browser removals | top ~10 | all verified | all verified | all verified | all verified |
| Re-checks | every 90 days | every 7-30 days, smart | same | configurable | policy-set |
| Proof vault + PDF report | basic | full + legal letters | full | full | full + aggregate (PII-free) admin view |
| Profiles | 1 + practice | 1 | 6 | unlimited (local) | per seat |
| Support | community | email, 2 business days | email | community + issues | SLA |

**Decisions made:**
- **The free/paid line is freshness and convenience, never safety.** Credit-freeze guides, breach checks and opt-out checklists are free for everyone. Paying buys the full, daily-updated broker feed, faster re-checks, more automation and family/business management.
- **Forks may self-build the feed** (the code is AGPL). The *data* (full registry) is our product under its own licence; the public sample stays CC BY-NC.
- **No human "we do it for you" service in v1.** It would mean holding customer PII and break principle 1. Revisit only as an opt-in partner service under a separate brand (Dream list).
- **Business is pursued from 0.5**, through partners who distribute (the McAfee site-licence and OEM channel), with the PII still staying on each person's device.
- **Honest terms (decided):** 30-day no-questions refund; reminder email 14 days before any renewal; cancel inside the app in two clicks; your price is locked for as long as you stay subscribed. Prices are not public until the paid tier is announced.
- **Payments:** Stripe or Paddle (merchant of record, handles sales tax) + licence keys verified offline (signed tokens), so the app never needs an account login to work.

---

## 3. Feature catalogue

Each line: feature, tier, phase. Status: **shipped** items are in v0.1.x.

### 3.1 Getting started (onboarding)
- **Shipped:** one-click Windows installer; 6-screen wizard; consent screen with typed signature; practice mode by default; prefill from a file.
- "Find me first" scan before any removal: shows which sites list you, with blurred previews ("we found you on 14 sites") - F - 0.3
- Plain-language "what happens next" timeline after setup - F - 0.3
- Import from a family member's export bundle (encrypted, for helpers) - F - shipped (import) / UX polish 0.4
- Read-aloud and large-text mode across the wizard - F - 0.4
- Spanish UI (then Vietnamese, Tagalog, Chinese) - F - 0.5
- Video walkthrough embedded offline (no YouTube tracking) - F - 0.4
- "Set it up for someone else" flow (helper prepares a bundle, relative double-clicks) - Fam - 0.4

### 3.2 Finding listings (discovery)
- **Shipped:** listing finder for supported brokers; matcher with confirmed/possible/no-match levels; human review of "possible" matches.
- Exposure scan across the full registry, cached and rate-limited, per-broker search adapters - F (core) / P (full) - 0.3
- Exposure score (0-100) with what drives it, trend over time - F - 0.3. Always shown with its coverage: how many sites were checked, how many need checking by hand, how many are uncertain. A low score or zero means 'on the sites we could check', never 'you are safe'.
- Relatives-and-associates view: which listings expose family members - P - 0.4
- Old-address and maiden-name variants, nickname expansion - F - 0.3
- Photo/face exposure check on people-search sites (local face matching, opt-in) - P - Later
- Search-engine exposure: Google/Bing results about you, with removal request links (Google "Results about you") - F - 0.3
- Breach check (Have I Been Pwned) - F - later. Note: HIBP's k-anonymity range API is for *passwords*; the breached-*account* lookup needs a paid API key and sends the email address to HIBP. Until the terms and disclosure are verified, the app links people to the HIBP site to check themselves.

### 3.3 Removing (the engine)
- **Shipped:** 3 tiers (email, assisted "do it with me", automatic browser for verified forms); "fill it in for me"; first-email approval gate; reply matcher; escalation timers; ID-request goes to a human to-do.
- Automatic browser removals for every verified web-form broker, with success signals - P - 0.3 onward (continuous)
- State-law request letters generated per state (CCPA/CPRA, Virginia, Colorado, Texas, Oregon...) with the right statute cited - F - 0.3
- California DROP integration (one request covers all registered CA brokers) - F - 0.3
- Legal escalation pack: complaint to the state AG / CPPA prefilled when a broker ignores a lawful request - P - 0.4
- Smart re-check: relist detection with per-broker cadence learned from history - P - 0.4
- Suppression lists: marketing (DMAchoice), prescreened credit offers (OptOutPrescreen), Do Not Call - F - 0.3
- Data-broker registry states (CA, VT, OR, TX) cross-checked so unknown brokers are found automatically - P (feed) - 0.5
- Phone number and email-only removals (for people who want just those gone) - F - 0.4
- Address confidentiality program helper (state ACP enrolment guidance for survivors) - F - 0.4

### 3.4 Beyond brokers (identity-safety checklists)
- Credit freeze at Equifax, Experian, TransUnion, plus Innovis, ChexSystems, NCTUE, LexisNexis - guided, with reminders - F - 0.3
- IRS Identity Protection PIN, SSA account lock-in, USPS Informed Delivery claim - F - 0.4
- Property-record and voter-record exposure guidance by county/state - F - 0.5
- "Lock down your accounts" checklist (2FA, recovery codes, password manager) - F - 0.4
- Annual "privacy check-up" reminder that walks the list again - F - 0.4

### 3.5 Proof and reporting
- **Shipped:** evidence screenshots; status and report commands; basic report.
- Proof vault: per broker, every email, screenshot and confirmation, dated and hashed - F (basic) / P (full) - 0.4
- One-page PDF "what we did for you" report (plain English, printable for a parent) - F - 0.4 (a printable HTML summary ships in 0.3)
- Court/attorney packet: chronological evidence bundle with hashes - P - 0.4
- Monthly progress email or toast ("3 new removals confirmed, 1 relisted, handled") - F - 0.4

### 3.6 Dashboard and UI
- **Shipped:** server-rendered dashboard; to-do cards; first-run copy; toasts; practice banner.
- Redesign on the v3 look (shared tokens, type, icons, illustrations; still server-rendered, no React runtime in the app) - F - 0.3
- "Today" view: one big card, the next thing to do, nothing else - F - 0.3
- Broker detail page: what they hold, what we sent, what came back, next check - F - 0.3
- Map of exposure (which sites, grouped by type) - F - 0.4
- Accessibility AA throughout, keyboard-only, screen-reader tested, 200% zoom - F - 0.3
- Dark mode in the app - F - 0.3
- Tray/menu-bar icon with status and "check now" - F - 0.4

### 3.7 Family and helpers
- Multiple profiles in one install, each separately consented - F - shipped in 0.2 ("Add a person" in the app, `freemyid profile add`; consent is stored per profile). Corrected 2026-11-08: it was listed as Fam - 0.4.
- Helper mode: a relative's app sends PII-free progress and approval requests to the helper's app via end-to-end encrypted relay; helper approves; the relative's data never leaves their machine - Fam - 0.5
- Shared family to-do list ("Mom has 2 things that need her signature") - Fam - 0.5
- Elder-safety tie-in: scam-call and mail-fraud tips, notify helper if a new listing appears - Fam - 0.5

### 3.8 Platforms and power users
- **Shipped:** Windows x64 (also runs on Windows 11 ARM); CLI with setup/scan/run/fill/status/report/profile/schedule/registry/todo.
- **Linux and macOS, headless or with dashboard** - F - **0.2**
  - `pipx install freemyid`, plus `freemyid doctor` (checks browser, keychain, scheduler, mail)
  - Secrets backend that works without a desktop keychain: passphrase-derived key (scrypt), `FREEMYID_PASSPHRASE_FILE`, or systemd-creds - all with the same encrypted store
  - Schedulers: systemd user timer (Linux), launchd agent (macOS), already rendered by `scheduler/render.py`; make install/remove/status real and tested
  - `--json` on every read command; stable exit codes; `freemyid run --headless` (no prompts, fails closed)
  - YAML config alternative to the wizard (`freemyid setup --from config.yaml`), schema published
- Docker image on GHCR (non-root, read-only rootfs, Playwright Chromium bundled, volume for data) - Pro - 0.2
- Developer page freemyid.org/developers: install for Linux/macOS/Docker, CLI reference, config schema, broker-contribution guide - F - 0.2
- Homebrew tap, AUR, Flatpak, Nix flake - F - 0.3 to Later
- Signed macOS .app with notarization (owner decision: Apple Developer $99/yr) - F - 0.5 (was Later; see roadmap/DESKTOP.md)
- Native Linux desktop packages (.deb/.rpm/AppImage) with the app window - F - 0.5 (was 0.4)
- Plugin API for community submitters (sandboxed, reviewed, signed in the feed) - F - 0.5
- Home Assistant / Prometheus exporter for homelabs - Pro - Later
- Self-hosted multi-profile server for a household (one Docker box, many people, each with own key) - Pro - Later

### 3.9 Broker knowledge (the "virus definitions")
- **Shipped:** 400+ broker registry (private full, public sample), state laws, schema validation, update with signature/size caps, registry health check weekly.
- Signed daily feed for Plus (ed25519 signature, token that is PII-free, CDN-served) - P - 1.0
- Automated broker monitoring: weekly headless check that each opt-out page still works, auto-flag changes - internal - 0.3
- Community broker reports ("this opt-out changed") with review queue - F - 0.5
- New-broker discovery from state registries and web crawl - internal - 0.5

### 3.10 Mail
- **Shipped:** IMAP/SMTP with Gmail app password, Proton Bridge (pinned TLS), other IMAP; reply matching.
- Outlook/Microsoft 365 via OAuth (device code flow) - F - 0.4
- Gmail via OAuth (no app password) - F - 0.4 (needs Google verification)
- Built-in alias addresses (requests sent from a relay address so the user's real email isn't exposed) - P - Later (needs PII-free relay design)

### 3.11 Trust, security, privacy
- Reproducible builds and published SBOM - F - 0.3
- Code signing on Windows - F - not done in 0.2/0.3; recommended at 0.5, required for 1.0. Options and the SignPath status to confirm: roadmap/DESKTOP.md section 2.2
- Opt-in, PII-free crash reports (scrubbed locally, user previews before send) - F - 0.4
- Independent security audit before 1.0 - 1.0
- Transparency page: what we host, what we never see, warrant canary - F - 1.0

### 3.12 Business and partners
- White-label build (partner name/logo, our engine), separate installer per partner - B - 0.5
- Partner portal: licence seats, PII-free aggregate stats (number of removals, not names) - B - 1.0
- Employer benefit landing page and onboarding emails (sent by the employer) - B - 1.0
- High-risk professions programme (judges, healthcare, law enforcement, DV advocates): faster cadence, Daniel's-Law-style state statutes - B/P - 1.0
- Public API for partners (licence, feed, aggregate stats; never PII) - B - Later

---

## 4. UX north star

- **One decision per screen.** If a screen asks two things, split it.
- **Every wait has a reason.** "This takes about a minute" on every spinner; never a silent pause (the installer still has a 10-second silent gap: fix in 0.3).
- **Never a dead end.** Every error says what happened in plain words and offers one button to fix it or one person to ask.
- **Numbers people trust:** "14 requests sent, 9 confirmed, 2 need you" beats any percentage.
- **The terminal is a first-class citizen, not a second app.** Same verbs in CLI and dashboard (`scan`, `run`, `status`, `report`, `todo`).
- **Design system:** one token set shared by site, app and installer (decision 2026-11-07).
- Test every release with the "Pat test": a non-technical person installs and finishes setup unaided, on 1024x768, at 150% scaling.

---

## 5. Engineering roadmap

| Area | Now | Next |
|---|---|---|
| Secrets | OS keyring only (fails on headless Linux) | pluggable backend: keyring, passphrase (scrypt), systemd-creds; same AES-GCM store (0.2) |
| Scheduling | Windows schtasks real; systemd/launchd rendered only | install/remove/status real on all three, tested in CI (0.2) |
| CI | Linux tests + Windows installer | matrix: ubuntu, macos, windows; Docker image build + smoke; pipx install smoke (0.2) |
| Packaging | PyInstaller + Inno Setup | + PyPI wheel, GHCR image (0.2); .deb/.rpm/AppImage (0.4); notarized .app (Later) |
| Config | wizard + prefill | versioned YAML schema in `schema/`, `setup --from` (0.2) |
| Output | human text | `--json` everywhere, exit codes documented (0.2) |
| Engine | runner, tiers, outbox, matcher | exposure scan service, relist detector, per-broker cadence (0.3-0.4) |
| Feed | bundled + update with caps | signed feed, licence tokens, CDN (1.0) |
| Sync | none | E2E-encrypted helper relay, PII-free payloads (0.5) |
| Payments | none | Paddle/Stripe + offline-verifiable licence tokens (1.0) |
| Quality | 650+ tests, ruff, mypy | e2e on all OSes, accessibility tests, fuzzing of parsers, audit (1.0) |

---

## 6. Release plan

> **Superseded 2026-11-11 by [`roadmap/ROADMAP_TO_1.0.md`](roadmap/ROADMAP_TO_1.0.md).** The list below is the earlier three-step plan, kept as a record. Main changes: desktop installers for macOS and Linux get their own release (0.5), the helper relay and Spanish move to 0.6, the signed feed (0.7) and payments (0.8) are split, the audit has its own release (0.9), and Business/Partner and the plugin API are proposed for 1.x.

- **v0.2 "Every platform"** (now): Linux/macOS headless and CLI, secrets fallback, real schedulers, `--json`, YAML config, `doctor`, Docker image, PyPI, developer page, CI matrix. Also: Bluesky poster fixes (SEC-57/58/59) and v0.1.3 installer fixes (uninstall while running, calm Bridge copy, Ready page, password wording).
- **v0.3 "See it, fix it"** (re-scoped 2026-11-07 on the Codex lead's advice): one understandable journey from finding listings to acting on them: exposure scan + score with coverage, 'Is this you?' reviews, state-law letters, DROP, the identity-safety checklists, the app redesign, printable summary, accessibility. Each with its own acceptance gate. Moved to v0.4: proof vault + PDF, Outlook OAuth, broker monitoring.
- **What counts as 'available'**: only what is in a published release (GitHub release + site_src/data/release.yaml). Merged-but-unreleased work is 'coming' on the website.
- **v0.4 "For the family"**: proof vault + PDF report, Outlook OAuth, broker monitoring, helper bundle flow, relist detection, legal escalation pack, monthly summary, tray icon, Linux desktop packages.
- **v0.5 "Together"**: helper relay, white-label build, plugin API, community broker reports, Spanish UI.
- **v1.0 "Sustainable"**: Plus/Family/Pro tiers live, signed daily feed, payments, partner portal, independent audit, transparency page.

---

## 7. Dream list (no promises; the team's wish list)

- Removal that happens *before* listing: monitor new broker scrapes and request suppression the day a record appears.
- A "privacy will" for after death: instructions and requests so a relative can remove a deceased person's listings (identity theft of the deceased is common).
- Browser extension that warns "this site sells people's data; opt out?" and starts the flow.
- Phone app (Android first) for scanning and approving, PII still on the user's own devices. Now planned in roadmap/MOBILE.md: a companion first, after desktop 1.0.
- Local AI helper (runs on-device, no cloud) that reads broker replies and drafts the right follow-up.
- Automatic letters by real mail for brokers that only accept postal requests (print-and-mail partner, opt-in, PII sent only for that letter).
- Collective action: anonymous, aggregated stats on which brokers ignore the law, published for regulators and press.
- Insurance partnership: lower identity-theft premiums for users with a clean exposure score.
- "Privacy score" badge an employer or school can offer as a benefit, with zero PII collected.
- Opt-in alias identity kit (alias email, alias phone, PO box guidance) for survivors.
- Partnerships with state ACPs and DV shelters to ship it free to survivors.
- A kiosk/library edition volunteers can run for seniors at a community centre, wiped after each session.

---

## 8. How we measure success (PII-free only)
- Installs and active installs (from the feed check, anonymous counter).
- Median time from install to first request sent.
- Share of users who finish the wizard (local, opt-in telemetry only, previewed).
- Confirmed removals per user (self-reported in the opt-in summary).
- Free-to-paid conversion and churn (from the payment processor, never joined to app data).

## 9. Open questions for the owner
- Apple Developer account ($99/yr) for a signed Mac app: when?
- Final prices after a sourced competitor check (brand-marketing).
- Business entity, payment processor account, and terms of service: needed before payments open (0.8 in the new plan).
- The full, current list is in the "Decisions the owner must make" tables at the end of each file in `docs/roadmap/`.

## 0.4 order (decided 2026-11-09, project lead; owner delegated full control)
Codex challenge CODEX-149 #6 accepted: 0.4 is built around Pat's journey (72, Windows 10, a grandchild sent the link), in this order:
1. **"Set it up for someone else":** a helper prepares an encrypted setup bundle, and the relative double-clicks it (3.1, Fam). Biggest drop-off risk today is the 6-screen wizard for someone alone.
2. **Large text and read-aloud across the wizard** (3.1, F). Large text exists; read-aloud and a full-wizard pass are new.
3. **One-page printable "what we did for you" report** (3.5, F; the HTML summary from 0.3 becomes a print-ready page, PDF if it stays local and simple).
Then, if time allows: proof vault (3.5), smart re-check (3.3), tray icon "check now" (3.6). Each item ships only with a Windows VM pass, and with the non-technical path working first (principle 2).

### App look (decided 2026-11-09): same family as the website, calmer
The app takes the website's look (tokens.css colours, type, spacing, radius, icons, illustrations, voice) but not its motion effects (spotlight, border beam, animated timelines): the app is a tool for Pat, not a sales page, and stays server-rendered with no React. No animation by default, AA contrast, 44px targets, layouts that hold in large-text mode and at 200% zoom.
- First WO: **app style guide** (Maya + Iris; design values minus motion, a drawn layout for every screen).
- Each 0.4 screen (helper bundle, large text/read-aloud, printable report) gets the new look as it is built, never as a second pass.
- Then one WO per remaining screen (~8-10: Today, more, person page, protect checklists, settings, setup steps, review card, splash/installer pages), each VM-checked in light/dark at 200% zoom.
- Every screen WO has this acceptance line: "a first-time user over 70 finishes it without help (VM, large text on)".
- Vendors: Codex adds accessibility/visual-consistency tests (contrast, targets, tokens only, no stray colours); Grok refreshes user-guide screenshots and wording after each screen; both send design challenges before building.
