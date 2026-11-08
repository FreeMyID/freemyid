# Ready-to-send queue (owner approval needed; nothing here has been sent)

Drafted 2026-11-08 by Sam Okafor. Session rule: drafts only, no posting, no logins, no PRs. Each entry counts as 1 contact toward the 10/day cap when sent, and gets logged in outreach-log.md. Version in all text: v0.2.0 (released 2026-11-07, see release-posts-v0.2.0.md). Re-check "unsigned" and the release version before sending. Disclosure wherever a site allows: "I work on Free My ID, a free open-source project."

Shared text (from listings.md facts table, all sourced there):
- SHORT: `Free Windows app that asks people-search and data-broker sites to delete your listing. Runs locally, no account.`
- MEDIUM: `Free My ID is a free, open-source Windows app that sends removal requests to people-search and data-broker sites for you, by email or the site's own form, and keeps checking because sites re-list people. No account, no cloud. AGPL-3.0.`

## 1. awesome-python-applications (NEW, best fit, free, no star bar found)
- Target: https://github.com/mahmoud/awesome-python-applications , method: issue using the repo's issue template ("The Easy Way"). A maintainer reviews it.
- Rules checked 2026-11-08 (https://raw.githubusercontent.com/mahmoud/awesome-python-applications/master/CONTRIBUTING.md): entries must be free/open-source; check the project is not already listed; description should not say "Python", "Application", "free" or "open-source" and should focus on architecture, design, features and target userbase; `repo_url` required, `home_url` optional; at least one topic tag plus a target platform. No star or age minimum seen in that file. Template questions not read (template file path not found via API); fill in whatever it asks.
- Sender: FreeMyID-USA (github_token exists, scope public_repo). Needs owner OK.
- Text:
  - Name: `Free My ID`
  - Description: `Windows desktop app with a six-step setup that sends removal requests to people-search and data-broker sites by email, a guided form or an automatic browser step, then re-checks on a schedule. Local storage, no account. Aimed at non-technical users.`
  - repo_url: `https://github.com/FreeMyID/freemyid` , home_url: `https://freemyid.org`
  - Tags: topic privacy (or nearest in tagsonomy); platform windows. Licence AGPL-3.0-or-later (pyproject.toml).
  - Comment: `I work on Free My ID, a free open-source project. It is a v0.2.0 early release; happy to adjust the entry.`

## 2. AlternativeTo (listings.md row 1; owner by hand)
- Target: https://alternativeto.net/ "Suggest new application". Account exists (owner-stored), no API, manual.
- Rules (listings.md row 1, checked 2026-11-07): verified email account; developers may add their own app; no links or emails in descriptions; no unreleased apps; large review backlog; paid priority review exists, we do not pay.
- Text: Name `Free My ID`. Tagline = SHORT. Description = MEDIUM minus the URL (none in it). Platform Windows, licence Open Source (AGPL-3.0), price Free. Alternative to: DeleteMe, Incogni, Optery, Kanary (only list ones we can describe fairly; competitors.md still unwritten, so keep the field to "Incogni, DeleteMe").
- Disclosure in the submitter note if there is a field: `I work on Free My ID.`

## 3. Show HN (listings.md row 3; owner by hand, needs a Hacker News account that does not exist yet)
- Target: https://news.ycombinator.com/submit . Rules (https://news.ycombinator.com/showhn.html, listings.md): must be something people can try; do not ask for upvotes; no landing pages. Download link must work.
- Title: `Show HN: Free My ID, a free local Windows app that sends people-search opt-outs`
- URL: https://github.com/FreeMyID/freemyid (repo, not the marketing page, to follow the "no landing pages" rule; download is on its releases).
- First comment: `I work on this. It is a free, open-source (AGPL-3.0) Windows app aimed at non-technical relatives. For each people-search site it uses the site's own removal path: an email request, a guided form, or an automatic browser step. Your details stay on your computer. No account. v0.2.0 is early: some sites still need a manual step and the app says which. The exe is unsigned, so Windows SmartScreen may warn. Feedback on the broker list welcome.`
- Hold advice: post only when the owner can watch comments for a few hours.

## 4. OpenAlternative (listings.md row 13; account needed; rules unverified)
- Target: https://openalternative.co/submit . Fetch 2026-11-08 showed only a "Submit" link and sign-in (email link, Google, GitHub); no rules, fees or criteria visible. Status: queued: needs account OpenAlternative; owner reads /submit first and tells us if it asks for payment (we do not pay).
- Text: MEDIUM, "alternative to" DeleteMe / Incogni, repo https://github.com/FreeMyID/freemyid, licence AGPL-3.0.

## 5. Chocolatey community repo (HOLD, not ready)
- Target: https://community.chocolatey.org/ . Account plus human moderation. Checked 2026-11-08 (package validator page, https://docs.chocolatey.org/en-us/community-repository/moderation/package-validator/): needs license URL, PackageSourceUrl, checksums validated in scripts. Whether an unsigned installer is accepted was not stated; moderation docs not read.
- Hold until the exe is signed (SignPath pending) and winget (row 7) decision is made, so the installer story is consistent. Text when ready: MEDIUM plus licence URL https://github.com/FreeMyID/freemyid/blob/main/LICENSE.

## Checked and skipped this session
- Awesome-Windows lists: quark-bar/awesome-windows last pushed 2015 and hervehobbes/awesome last pushed 2017-02 with 0 stars (GitHub API, 2026-11-08); both inactive, skip.
- free-for-dev (ripienaar): SaaS free tiers for developers only (its CONTRIBUTING); not a fit.
- Order of preference if the owner approves only some: 1, 2, 3, 4.
