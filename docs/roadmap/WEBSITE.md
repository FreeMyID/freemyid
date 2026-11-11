# Free My ID: freemyid.org roadmap

Owner/PM: Morgan Reyes. Web lead: Leo Hart. Written 2026-11-11, at v0.3.1. Release numbers refer to `ROADMAP_TO_1.0.md`.
This file plans what the site needs for each product release. How the site is built stays in `docs/WEBSITE.md`; the look stays in `docs/WEBSITE_REVAMP.md`; open requests stay in `docs/WEBSITE_REQUESTS.md`.

The site's job: a non-technical person arrives from a search or a relative's link, understands in one screen what Free My ID does, trusts it, and downloads the right file. Everything else on the site supports that.

---

## 1. Current state (checked against the repository)

| Topic | State | Source |
|---|---|---|
| Live build | Site v3: `web/` (Astro, static output), built and deployed by `.github/workflows/pages.yml` to GitHub Pages | `pages.yml` |
| Old build | Site v2: `site_src/` and committed `site/`. Not deployed, known to be stale. `site_src/data/release.yaml`, `site.yaml`, `pages.yaml` and tokens are still read by v3. | `docs/handoff/web-developer.md` |
| Domain and edge | freemyid.org on Cloudflare: DNS, TLS, redirect rules (`/get/windows` to the latest installer; `/get/macos` and `/get/linux` to `/developers/`), a response-header rule (CSP, frame, referrer and other security headers), email routing. Weekly `domain-health` job. | `docs/handoff/devops-engineer.md`, `tools/cloudflare_redirects.py`, `tools/cloudflare_headers.py` |
| Pages | Home, How it works, Is it safe?, Download, What's coming, For families, FAQ, Guides hub with one page per site in the public registry sample plus two articles, Protect hub with one page per checklist, Credit freeze, Developers (with CLI and config reference), I do not consent, 404 | `web/src/pages/` |
| Look | In-house revamp merged and approved by the owner on 2026-11-08. Final QA round left items QA-3 to QA-8 open (sideways scroll at 320px on a few pages, 44px phone menu button). | `docs/WEBSITE_REVAMP.md` |
| Scripts | None, except the "copy the code" button on the download page. Enforced by the page CSP and by `web/scripts/check-site.mjs`. No analytics, cookies or third-party requests. | `check-site.mjs` |
| Budgets | Home first view under 300 KiB, CSS under 20 KiB, script on home under 80 KiB (all gzip), checked in the build | `check-site.mjs` |
| Feedback | By email to `support@freemyid.org`. No form. | `site_src/site.yaml` |
| Release data | `site_src/data/release.yaml` is filled by CI after each release; the download page shows version, size and SHA-256 from it | `build.yml` (site-release-info) |
| Search | Sitemap and structured data are built. Search Console and Bing verification wait for the owner's login. Traffic numbers come only from Cloudflare's own zone analytics. | `docs/marketing/seo/PLAN.md`, `docs/handoff/seo-growth.md` |
| Not on the site | Pricing, terms, privacy policy as its own page, changelog page, help centre, status page, per-OS download pages, Spanish, anything about phones | `web/src/pages/` |

Open items carried into this plan: WR-74 (`/whats-new/`), the revamp QA items, Cloudflare's email obfuscation script being blocked by our CSP on two pages, the stale v2 output, the Bing verification file.

---

## 2. Rules that do not change

| Rule | Detail |
|---|---|
| **Script-free** | Every page ships with `script-src 'none'`, except pages on a short allowlist in `check-site.mjs` (today: the download page's copy button). Adding a page to that list needs the web lead and qa-security. |
| **No analytics, no cookies, no third-party requests** | No beacon, no pixel, no embedded video, no web fonts from other hosts, no chat widget. Numbers come from Cloudflare zone analytics and from the search consoles. |
| **No account** | Nothing on the site asks anyone to sign up. Regular users are never sent to github.com; the "source code" link is for developers. |
| **Only what is released** | A feature appears as available only when it is in a published release and `release.yaml` shows it. Everything else lives on "What's coming", with no dates. |
| **Honest copy** | `docs/POSITIONING.md` governs every sentence. Claims carry a source comment in the page source. |
| **Built for older eyes and hands** | 20px base text; targets at least 44px; body contrast at least 7:1 and other text 4.5:1 in light and dark; no sideways scroll at 320px or at 200% zoom; full keyboard use; visible focus; motion only behind `prefers-reduced-motion: no-preference`. |
| **Tested contracts** | `tests/test_web_*.py` hold owner-approved wording and structure. Change a test only when the contract really moved. |

How new needs are met without scripts:

| Need | Script-free answer |
|---|---|
| "Which download is mine?" | Three clear cards (Windows, Mac, Linux) and one page each. No device sniffing. |
| Monthly or yearly price | Both prices shown side by side. |
| Buying | A plain link to the payment processor's own checkout page. Nothing of theirs is embedded in ours. |
| Help search | A well-ordered topic index and the browser's own find. |
| Language | Plain links between `/` and `/es/` pages, with `hreflang`. |
| Status | A static page rebuilt by CI from the health jobs. |
| Feedback form | A plain HTML form posting to our own small endpoint, or email only (decision W-5). |

---

## 3. Pages needed, by release

| Release | New or changed pages | Who |
|---|---|---|
| **0.3.2** | `/whats-new/` (WR-74) with 0.3 and 0.3.1 in plain words; fix revamp QA-3 to QA-8; retire or resync the v2 output (W-3); settle the email obfuscation conflict (W-4) | Owen, Maya, Leo; Dana |
| **0.4** | `/families/` gains "Set it up for someone else" with real screenshots; `/how-it-works/` mentions large text and read-aloud; a sample of the printable report on home and download; help pages for the new screens published from `docs/user/` (start of the help centre at `/help/`); FAQ entries for relisting and the monthly update | Owen, Jordan, Iris; Grok writes the user pages |
| **0.5** | Download hub with three cards and `/download/windows/`, `/download/mac/`, `/download/linux/`, each with file, size, checksum, "how to check it", first-start steps and uninstall; `/get/macos` and `/get/linux` redirects point at real files; signing explained (what the Windows and Mac prompts will say now); developer page lists the published package channels; `/help/` complete for install and first run on each OS; update-notice explanation on `/safety/` | Leo, Owen, Maya; Dana for redirects; Codex for the developers section |
| **0.6** | `/families/` explains the helper link: what the helper sees, what stays on the relative's computer; `/safety/` gains "what our relay can see" (network address, time, message size, nothing readable); Spanish pages under `/es/` for home, how it works, is it safe, download, families, FAQ and the core help pages; a "this guide is out of date" report path on every guide (email, or the form if W-5 says yes) | Jordan, Owen; native-speaker review; Dana for the endpoint |
| **0.7** | `/safety/` and FAQ explain the update feed and that the request carries no personal details; guides hub states coverage honestly (how many sites have a guide, how many the app knows); "Free and Plus" comparison drafted but not public; status page `/status/` (site, downloads, feed freshness) if W-8 is yes | Jordan, Owen, Dana |
| **0.8** | `/pricing/` from `docs/marketing/pricing-page-draft.md`; `/terms/`, `/privacy/` (a real policy page; today `/privacy` redirects to `/safety/`), `/refunds/`; "I bought it, now what" help pages (enter the key, lost key, renew, cancel, refund); `/families/` shows the Family plan; home gains one calm line about Plus, never a pop-up | Jordan, Owen, Leo; attorney review (owner) |
| **0.9** | `/security/`: how to report a problem, the audit report, SBOM, reproducible-build steps, signing keys and how to verify each download; transparency page (what we host, what we never see); accessibility statement; every page re-read against the frozen app | Leo, Marcus, Ruth |
| **1.0** | Home, download and What's coming move to the 1.0 story; `/whats-new/` 1.0 entry; press and listing kit (logos, screenshots, plain facts) | Jordan, Iris, Sam |
| **After 1.0** | `/phone/` when the companion reaches the stores (`MOBILE.md` M3), with store links and a direct Android file; `/business/` when the Business edition exists | Later |

Phones before that point: "What's coming" may say a phone app is planned after the computer version is finished, with no date and no store badge.

### Site map at 1.0
```
/                      home
/how-it-works/         three tiers, what it does and does not do
/safety/               is it safe, what stays local, what the relay and feed see
/security/             report a problem, audit, verify downloads, transparency
/download/             hub -> /download/windows/  /download/mac/  /download/linux/
/whats-new/            changelog in plain words
/whats-coming/         now, next, later, promises
/families/             helper setup, helper link, Family plan
/pricing/  /terms/  /privacy/  /refunds/
/help/                 help centre: install, first run, mail setup, each screen, trouble
/guides/               one page per site, plus articles
/protect/              identity-safety checklists
/faq/  /i-do-not-consent/
/developers/           install, CLI, config, contribute a broker
/status/               (if decided)
/es/...                Spanish for the core pages
```

---

## 4. Help centre

- Source: `docs/user/*.md` (install, mail setup, troubleshooting, helping, glossary) and `docs/USER_GUIDE.md`. They are written by the user-docs team (Grok while the Copilot team is out) and guarded by the wording and doc-link tests.
- Build: the site renders those files into `/help/` pages at build time, so there is one source for the app's help links, the repository and the site. The web crew owns the templates; the docs team owns the words.
- Order: by task ("Install on Windows", "Connect your email", "A site put my details back"), never by feature name. The 15 most likely problems come first.
- Every help page ends with "Still stuck? Write to support@freemyid.org", no account, no ticket portal.

---

## 5. Search and growth

Owner: Sam Okafor (seo-growth). Plan and queues: `docs/marketing/seo/`.

| Release | Tie-in |
|---|---|
| 0.3.2 | Search Console and Bing verification (needs the owner's login, W-6); serve the Bing verification file; sitemap submitted |
| 0.4 | Publish the "protect elderly parents" article and link it from `/families/`; guides for the most-searched sites not yet covered (BL-IN-81), sources first |
| 0.5 | Per-OS download pages target "for Mac" and "for Linux" searches; start listings (`listings.md`) once an installer is signed, so the install story is consistent; winget and Homebrew pages count as listings |
| 0.6 | Spanish pages with `hreflang`; Spanish guide titles for the most-searched sites |
| 0.7 | Replace keyword guesses in `keywords.md` with real impressions; publish articles only for shipped features |
| 0.8 | Pricing page; honest comparison with paid services, sourced (`competitor-pricing.md`) |
| 1.0 | Press and listing kit; ask existing listings to update |

Rules: every factual claim has a source; no bought or swapped links; outreach waits for the orchestrator's go and is logged in `outreach-log.md`; no client-side measurement of any kind.

---

## 6. Accessibility and performance budgets

| Budget | Today | Through 1.0 |
|---|---|---|
| Home first view | under 300 KiB gzip | keep; a new hero image must fit inside it |
| CSS | under 20 KiB gzip | keep |
| Script | none on every page but the allowlist | keep; the allowlist does not grow without review |
| Any new page type (download per OS, pricing, help, `/es/`) | n/a | first view under 300 KiB; one `h1`; passes `check-site.mjs` |
| Screenshots | WebP | each under 150 KB, with made-up data only |
| Screens checked | 360, 768, 1280, light and dark, 200% zoom | add 320 for every new page |
| Assistive technology | keyboard pass | from 0.9: NVDA and VoiceOver read-through of home, download, pricing and one help page |

web-qa (Ruth) runs the screenshot rounds and the claim audit after every page or style change and files findings as WR rows.

---

## 7. Hosting and infrastructure

| Piece | Today | Plan | Release |
|---|---|---|---|
| Static site | GitHub Pages behind Cloudflare | Stay, unless W-1 says move. A move to Cloudflare's own static hosting would give real header and redirect files and remove the dependence on the repository being public. | decide by 0.7 |
| Installers | `/get/windows` redirects to the GitHub release file | Keep GitHub Releases as the origin of record. From 0.7 consider serving copies from our own storage on Cloudflare so a download never leaves freemyid.org (W-2). Checksums and signatures are published either way. | 0.7 |
| Registry feed and update manifest | none | Static, signed files on a Cloudflare-served address; the request carries no identifier | 0.7 |
| Helper relay | none | A small Cloudflare Worker with short-lived encrypted mailboxes; no logs with addresses | 0.6 |
| Licence webhook | none | A small endpoint that stores key id and expiry only | 0.8 |
| Feedback and "guide is wrong" form | email only | Optional plain-form endpoint that forwards to the support mailbox (W-5) | 0.6 |
| Security headers | Cloudflare response-header rule mirrors the page CSP | Add a header check to `domain-health`; turn off the email obfuscation feature or write addresses so it is not triggered (W-4) | 0.3.2 |
| Status | weekly `domain-health` and `registry-health` jobs | Static `/status/` page built from those jobs, plus feed freshness | 0.7 |

Every Cloudflare change is made by devops (Dana) through the scripted tools or the `cf` command-line tool, with a dry run first and a saved rollback file. DNS and mail-routing changes are Tier 3 in `docs/AUTONOMY.md`. Each service above that touches user traffic must be described on `/safety/` in plain words before it goes live.

---

## 8. Who does what

| Work | Team |
|---|---|
| Page templates, layout, integration, deploy workflow | Leo (web lead), Owen (builder) |
| Tokens, components, light and dark themes | Maya (web-designer) |
| Screenshots, illustrations, social images | Iris (graphic-designer) |
| Copy, pricing and release wording, requests to the web crew | Jordan (brand-marketing) |
| Search plan, listings, article drafts | Sam (seo-growth) |
| Checks, screenshots rounds, claim audit | Ruth (web-qa) |
| Edge rules, endpoints, status data | Dana (devops) |
| Developer section pages and their tests | Codex team |
| Help-centre source pages | Grok team (user docs) |
| Security and privacy sign-off on every new endpoint and every allowlisted script | Marcus (qa-security) |

---

## 9. Milestones aligned with the product

| Release | The site is done when |
|---|---|
| 0.3.2 | `/whats-new/` is live; no sideways scroll at 320px anywhere; one site build in the repository |
| 0.4 | A helper can read on `/families/` how to set it up for a parent, with real screenshots; `/help/` exists |
| 0.5 | A Mac or Linux user reaches the right file in two clicks from home and can check it |
| 0.6 | The core pages read naturally in Spanish; the safety page says what the relay sees |
| 0.7 | Feed and status are explained; coverage numbers on the site match the build |
| 0.8 | A person can buy, get a key and find help for it without creating an account anywhere on our side |
| 0.9 | `/security/` holds the audit report and verification steps; accessibility statement published |
| 1.0 | Every page describes the released 1.0 and nothing else |

---

## Decisions the owner must make

| # | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| W-1 | Where the static site is hosted | Stay on GitHub Pages behind Cloudflare; move to Cloudflare's static hosting | Stay for now; decide again at 0.7 when the feed and relay already live on Cloudflare | Nothing before 0.7 |
| W-2 | Where installer files are served from | GitHub Releases through our redirect (today); copies on our own Cloudflare storage | Our own storage from 0.7, GitHub Releases stays the origin of record | Download pages at 0.7 |
| W-3 | The old v2 site (`site_src/` templates and committed `site/`) | Retire the v2 output and its check, keeping the data files v3 reads; keep both | Retire | 0.3.2 cleanup |
| W-4 | Cloudflare email obfuscation | Turn it off; keep it and write addresses so it is not triggered | Turn it off | 0.3.2 |
| W-5 | Feedback and "this guide is wrong" form | Email only; a plain form posting to our own endpoint | Plain form at 0.6, email stays as the fallback | Community reports in 0.6 |
| W-6 | Search Console and Bing verification | The owner signs in and adds the DNS record; skip search data | Do it now; it needs only the owner's login | Search numbers from 0.3.2 on |
| W-7 | When prices become public | At 0.8 with the pricing page; earlier on "What's coming" | At 0.8 | `/pricing/` |
| W-8 | Public status page | Build a static one; none | Build it at 0.7 | `/status/` |
| W-9 | Legal pages | Attorney-reviewed terms, privacy policy and refund policy; unreviewed templates | Attorney review (same as D6 in `ROADMAP_TO_1.0.md`) | 0.8 |
| W-10 | Spanish pages | Core pages only; whole site including guides | Core pages and help at 0.6, guides later | `/es/` in 0.6 |
| W-11 | An "about" page that names who is behind Free My ID | Name the company only; name people; no page | Company name once the entity exists | Trust pages at 0.8 |
| W-12 | Listings and outreach | Go now; wait for a signed installer | Wait for the signed installer (0.5) | Growth work in 0.5 |
