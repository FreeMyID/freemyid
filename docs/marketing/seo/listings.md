# Listings and backlink targets

Owner: seo-growth. Rules checked 2026-11-07 unless a row says `rules: verify`. Stage B is Tier 2 (docs/AUTONOMY.md), but every row below needs an account, a GitHub PR or email, so none could be submitted this wave:
- GitHub PRs and issues: the only gh login is the owner's personal account, so these are `queued: needs Free My ID GitHub account`.
- Email submissions: `queued: team-mail gateway` (waiting for qa-security).
- Sites that need a login: `queued: needs account <site>`. Only the owner creates accounts.

Log every submission in outreach-log.md. Always submit as "Free My ID" and disclose that we work on it wherever the site asks.

Posting accounts and tokens: see posting-methods.md (updated 2026-11-07). Accounts now exist for AlternativeTo, GitHub, Reddit, X, Bluesky, Mastodon, Google (owner stored them); Hacker News and Microsoft do not. No API tokens exist yet, and no site below has an API we can safely use with a password, so: rows 1, 2, 16 are manual steps for the owner (paste-ready text below); rows 4, 5, 7, 8, 19, 20 become `queued: needs github_token` (fork and PR, one process with GH_TOKEN); row 3 stays queued (no Hacker News account).

## Facts every submission may use (sources)

| Fact | Source |
|---|---|
| Free, open source, AGPL-3.0-or-later | pyproject.toml `license`; https://github.com/FreeMyID/freemyid/blob/main/LICENSE |
| Windows 10 and 11, released v0.1.1 on 2026-11-07 (early release) | site_src/data/release.yaml; https://github.com/FreeMyID/freemyid/releases/tag/v0.1.1 |
| No account; runs on your computer; details go only to the sites you ask to remove you | docs/POSITIONING.md (approved trust line); site /safety/ |
| Three ways per site: email, assisted (step by step with you), automatic browser | docs/PLAN_V1.md; site /how-it-works/ |
| Keeps checking, because sites re-list people | docs/POSITIONING.md rule 2 |
| Never asks for SSN, bank or card details | docs/BRAND.md trust panel |

Never write: removes you from the internet, guaranteed, 100%, identity-theft protection, "they have to".

## Ready-to-paste text

**Short (≤ 120 chars):**
`Free Windows app that asks people-search and data-broker sites to delete your listing. Runs locally, no account.`

**Medium (≈ 250 chars, use where a description field takes it):**
`Free My ID is a free, open-source Windows app that sends removal requests to people-search and data-broker sites for you, by email or the site's own form, and keeps checking because sites re-list people. No account, no cloud. AGPL-3.0.`

**Long (directories with a full description):**
> Free My ID helps you take your name, address and phone number off the people-search and data-broker sites that sell them. It is a free Windows 10/11 app with a six-screen setup. For each site it uses the site's own removal process: an email request, a step-by-step guide it walks you through, or an automatic browser form. Where a state privacy law applies, the email is a formal legal request. It then re-checks on a schedule, because these sites often list people again.
>
> Your details are kept on your computer and go only to the sites you ask to remove you. No account, no cloud, nothing sent to us. It never asks for your Social Security number or bank details. Free and open source (AGPL-3.0). Early release: v0.1.1.
>
> Limits: it works on people-search and data-broker sites only, not on Facebook or Google themselves, and no tool can promise every site will comply.

**Disclosure line (wherever one is needed):** `I work on Free My ID, a free open-source project.`

## Tracker

| # | Target | URL | Site's rules (source) | Text to use | Status |
|---|---|---|---|---|---|
| 1 | AlternativeTo | https://alternativeto.net/ ("Suggest new application") | Account with verified email required; developers may add their own app; review backlog of "several thousand", many declined; no links/emails in descriptions; no unreleased apps; paid priority review exists but **we don't pay** (https://alternativeto.net/faq/). Add as an alternative to DeleteMe, Incogni, Optery, Kanary. | Long, minus any links; tags: privacy, data-removal, opt-out, open-source | queued: needs account AlternativeTo |
| 2 | Product Hunt | https://www.producthunt.com/launch | Login required; **company accounts are prohibited** (personal accounts only); makers may hunt their own product; don't ask for upvotes, ask people to visit and comment (https://www.producthunt.com/launch) | Tagline: short. Description: medium. First comment: long + disclosure | queued: owner decision (personal account required, conflicts with "act as Free My ID") |
| 3 | Show HN (Hacker News) | https://news.ycombinator.com/submit | Must be something people can try, built by you; no landing pages; don't ask friends to upvote (https://news.ycombinator.com/showhn.html). Account needed to submit. | Title: `Show HN: Free My ID – free, local Windows app that sends people-search opt-outs`; link to repo; first comment: long + how it works technically | queued: needs account Hacker News |
| 4 | BADBOOL (yaelwrites/Big-Ass-Data-Broker-Opt-Out-List) | https://github.com/yaelwrites/Big-Ass-Data-Broker-Opt-Out-List | Contribute by PR or email to the maintainer; has an "Additional Options (Paid and Free)" section listing services; CC BY-NC-SA content (README, fetched 2026-11-07) | One line for "Additional Options": `Free My ID (free, open source, Windows): sends opt-out requests to people-search sites from your own computer and re-checks them. https://freemyid.org/` + disclosure in PR body | submitted 2026-11-07: PR #131; CLOSED by maintainer 2026-11-07 15:37Z with no comment. Do not resubmit; revisit only if she invites it |
| 5 | Lissy93/awesome-privacy | https://github.com/Lissy93/awesome-privacy | Edit `awesome-privacy.yml` only; self-promotion OK if it fits; declare affiliation; open source; **first stable release must be over 4 months old**; 50–250 char objective description incl. drawbacks; human-written (CONTRIBUTING.md) | `Free, open-source Windows app that sends opt-out requests to people-search and data-broker sites and re-checks them. Windows only; early release.` | queued: eligible after 2027-03-07 (4-month rule), plus needs Free My ID GitHub account |
| 6 | pluja/awesome-privacy | https://github.com/pluja/awesome-privacy | No data-removal section seen in README contents (fetched 2026-11-07); contribution guide at misc/Contributing.md, rules: verify | Short | queued: rules verify; needs Free My ID GitHub account |
| 7 | winget (Windows Package Manager) | https://github.com/microsoft/winget-pkgs | GitHub PR of a manifest; installer must come directly from the publisher's release location, support non-interactive install, install/uninstall cleanly for non-admins, pass AV scans; Microsoft may refuse (https://learn.microsoft.com/en-us/windows/package-manager/package/repository) | Manifest ShortDescription = short text; needs wizard-packager to confirm `/VERYSILENT` works | held 2026-11-07: needs wizard-packager silent-install check; exe is unsigned (SignPath pending), so a PR would likely fail AV/SmartScreen review. Revisit after signing |
| 8 | Scoop "extras" bucket | https://github.com/ScoopInstaller/Extras | GitHub PR of a JSON manifest; rules: verify (CONTRIBUTING) | Short | held 2026-11-07: Scoop contributing guide (ScoopInstaller/.github) requires an issue and maintainer approval before a new-package PR; repo has 1 star, so notability likely unmet; unsigned exe. Revisit later |
| 9 | Chocolatey community repo | https://community.chocolatey.org/ | Account + human moderation queue; rules: verify | Medium | queued: needs account Chocolatey |
| 10 | SourceForge (GitHub import) | https://sourceforge.net/ | Account required to create a project; can mirror GitHub releases; rules: verify | Long | queued: needs account SourceForge |
| 11 | Softpedia | https://www.softpedia.com/ | Submission page returned 403 to our fetcher; reportedly per-platform submit forms (unofficial source); rules: verify | Long | queued: rules verify (likely needs email, so team-mail gateway) |
| 12 | MajorGeeks | https://www.majorgeeks.com/ | rules: verify (submission method not found) | Long | queued: rules verify |
| 13 | OpenAlternative | https://openalternative.co/submit | Sign-in (email link, Google or GitHub) appears required; free option and criteria not stated (fetched 2026-11-07) | Medium; list as alternative to DeleteMe/Incogni | queued: needs account OpenAlternative |
| 14 | Privacy Guides | https://discuss.privacyguides.net/ | "only considers projects brought forward by our community members via the forum"; prefers open source and active projects (https://www.privacyguides.org/en/about/criteria/) | n/a | skip: no self-submission. Earn it, don't ask |
| 15 | GitHub topics on our own repo | https://github.com/topics/data-removal (and the others in docs/marketing/repo-meta.md) | Our own repo metadata; draft by brand-marketing; orchestrator applies it | docs/marketing/repo-meta.md (c) | done 2026-11-07: description, homepage and all 11 topics live (orchestrator); social preview image is a manual upload by the owner |
| 16 | r/privacy (Reddit) | https://www.reddit.com/r/privacy/ | Account required; subreddit self-promotion rules: verify in sidebar before posting | Medium + disclosure | queued: needs account Reddit; rules verify |
| 17 | Slant ("best data removal services") | https://www.slant.co/ | Account required; rules: verify | Medium | queued: needs account Slant |
| 18 | LibHunt | https://www.libhunt.com/ | Indexes GitHub projects; rules: verify | Short | queued: rules verify |
| 19 | Awesome-Windows (Awesome-Windows/Awesome) | https://github.com/Awesome-Windows/Awesome | GitHub PR; rules: verify (CONTRIBUTING) | Short | skip until 50 stars: Awesome-Windows/Awesome is gone (404). Active list is 0PandaDEV/awesome-windows, CONTRIBUTING requires 50+ GitHub stars (we have 1), 'awesome' bar, rejects low-quality PRs. Revisit at 50 stars |
| 20 | awesome-humane-tech (humanetech-community) | https://github.com/humanetech-community/awesome-humane-tech | GitHub PR; privacy section; rules: verify | Short | skip: repo archived (GitHub API, pushed 2022-11-13) |

Not targeted on purpose: paid directories, "submit to 500 sites" tools (PAD blasters), link exchanges, and any site that wants a reciprocal link.


## Wave 3 notes (2026-11-07)
- Row 6 pluja/awesome-privacy: Contributing.md requires 6+ months of work, real user base; skip until about 2027-05.
- Row 20 awesome-humane-tech: repo archived (GitHub API); skip.
- Row 19 Awesome-Windows/Awesome: GitHub API returned 404; re-find the current repo before a PR.
- Row 4 BADBOOL: README accepts PR or email; its stated bar is that users can verify a broker holds their data, so a tool line in 'Additional Options' is at the maintainer's discretion; PR once github_token exists.
- All PRs blocked: no github_token in keyring.

## Wave 5 notes (2026-11-07)
- PR #131 closed by maintainer without comment 10 minutes after opening. Accepted; no follow-up.
- Rows 5, 7, 8, 19, 20 all ineligible today (reasons in the tracker). 0 PRs opened. Re-check when: repo has 50+ stars, exe is signed, 2027-03-07 (row 5).
