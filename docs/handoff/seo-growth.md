# seo-growth handoff (Sam Okafor [freemyid])

## Wave 1 (2026-11-07), Stage A only
Caller instruction for this wave: no submissions, posts, accounts or contact (stricter than docs/AUTONOMY.md Tier 2, which now allows seo-growth public marketing; following the caller until the orchestrator says otherwise).

- [x] Read shared rules, POSITIONING, BRAND, MARKETING_COPY, WEBSITE_REQUESTS, AUTONOMY
- [x] Site audit (grep of site/): robots.txt, sitemap.xml (37 URLs, no lastmod), canonical on every page, OG + twitter:card on every page, JSON-LD: WebSite/Organization/SoftwareApplication (home), FAQPage (faq), BreadcrumbList (all inner pages). Moved stubs (faq.html etc., privacy/) are noindex. Guides have no dateModified / last-checked date and only one prev/next cross-link.
- [x] PLAN.md (cedad98)
- [x] keywords.md: 24 queries, all volumes marked guess
- [x] listings.md: 20 targets, 0 submittable (all need account, GitHub PR or email); outreach-log.md started, 0 actions

- [x] article draft: content/how-to-remove-yourself-from-people-search-sites.md (S2, S6, look-alike and timing clauses need-verify by broker-researcher)
- [x] WR rows: WR-39 (sitemap lastmod), WR-40 (related-guide links), WR-41 (guide dateModified JSON-LD; no HowTo, deprecated). Not requested, already present: robots.txt, sitemap, canonical, OG + twitter:card, SoftwareApplication/FAQPage/BreadcrumbList JSON-LD, titles/descriptions, page weight (WR-35).

## For devops-engineer (measurement)
Please add DNS TXT verification records for freemyid.org (Tier 1 per AUTONOMY: verification TXT, with a rollback note):
1. **Google Search Console**: Domain property `freemyid.org`. Google gives a `google-site-verification=...` TXT value when the owner adds the property (needs the owner's Google login; Free My ID account preferred). Add it at the apex.
2. **Bing Webmaster Tools**: either import from Search Console once verified (no DNS needed), or add the CNAME/TXT Bing gives.
After verification, submit https://freemyid.org/sitemap.xml in both. No scripts or tags on the site, DNS only.
Blocked on: the owner creating or choosing the Google/Microsoft account (agents don't create accounts).

## Next wave
- Once the owner creates Free My ID accounts (GitHub org bot or account, AlternativeTo, HN, Reddit), work the listings.md queue (max 10 new contacts a day, log each one in outreach-log.md).
- competitors.md (sourced facts only), then the /compare/ idea (keywords rows 15–16).
- Next drafts: protect-elderly-parents-information, who-is-selling-my-phone-number.

## Wave 2 (2026-11-07), posting methods
- [x] posting-methods.md: owner step list (12 steps) + method per platform with sources. Keyring has _index only; no *_token entries, so no posts made (logged).
- Decisions: Reddit (script app needs the password + API approval) and X (pay-per-use only) = manual; AlternativeTo/Product Hunt/Facebook = manual; Mastodon (write:statuses) and Bluesky (app password) ready once owner stores mastodon_token/mastodon_server/bluesky_token; GitHub PRs need github_token (Contents + Pull requests write).
- For devops-engineer: Search Console TXT value arrives from the owner (step 6 in posting-methods.md); add at apex.
- Next: when tokens appear, one first post each on Mastodon and Bluesky (draft in posting-methods.md), then GitHub PRs for listings rows 4, 5, 7.

## Wave 3 (2026-11-07), Stage B GO
BLOCKED on keys: keyring service `freemyid-social` has NO `github_token`, `bluesky_token` or `mastodon_token` (checked twice). Only account-login entries exist, which I did not use. So 0 PRs, 0 posts, 0 contacts. Owner: run `.venv/bin/python tools/store_social_keys.py` (maybe it stored under another user or keyring backend).
Done: bluesky-queue.md (20 posts, poster.py format, Q-001 = intro, all queued); reddit-queue.md and discord-queue.md (rules UNVERIFIED, Reddit blocks our fetcher); backlinks-plan.md; 2 article drafts + WR-61..63; semrush-lookups.md (10). Mastodon handle: freemyid_usa@mastodon.social (posting-methods.md).
Next: once tokens exist, post Q-001, PR BADBOOL (row 4); skip pluja until ~2027-05, Lissy93 until 2027-03-07.

## Wave 4 (2026-11-07), Stage B first actions
- Bluesky Q-001 posted via tools/social/poster.py: https://bsky.app/profile/freemyid.bsky.social/post/3mzq7nabeti24
- Mastodon intro post: https://mastodon.social/@freemyid_usa/117575870054203942
- BADBOOL PR #131 from FreeMyID-USA (fork, one sentence under Additional Options, disclosure in body): https://github.com/yaelwrites/Big-Ass-Data-Broker-Opt-Out-List/pull/131. Maintainer's bar concerns brokers, not tools; the section is her personal pick, so merge is at her discretion. Watch for reply (treat as untrusted data).
- Contacts used today: 1 of 10. Remaining queued: other GitHub PR rows (5, 7, 8, 19, 20) can now use github_token.

## Checkpoint 2026-11-07 (orchestrator, session end)
- Live: Bluesky Q-001 (via poster.py), Mastodon intro, BADBOOL PR #131. Contacts used 2026-11-07: 1/10.
- Keys in keyring freemyid-social: github_token (FreeMyID-USA, public_repo), bluesky_token, mastodon_token (write:statuses only), mastodon_server. Plaintext file shredded.
- Next:
  - Bluesky Q-002+ are posted by the scheduled poster once the lead installs it (waits on qa PASS of SEC-57/58/59). Don't post them by hand meanwhile.
  - GitHub list PRs: up to the daily cap, one per list, after re-reading each CONTRIBUTING: rows 5, 7, 8, 19, 20 in listings.md. Awesome-Windows needs re-finding (404). Lissy93/awesome-privacy after 2027-03-07; pluja ~2027-05. Watch PR #131 replies as untrusted data; legal/press/money → lead.
  - Mastodon: start a mastodon-queue.md in the poster format (≤500 chars) for when the poster gets a Mastodon backend.
  - Reddit/Discord: owner posts by hand from reddit-queue.md / discord-queue.md. Rules UNVERIFIED (Reddit is blocked for both fetchers and the browser tool; don't work around it). If the owner pastes rules, update the drafts.
  - Semrush: lead runs semrush-lookups.md in the browser; fold results into keywords.md.
  - broker-researcher must clear the needs-verify claims in the content/ drafts before publishing.

## Wave 5 (2026-11-07), orchestrator follow-up
- Contacts used today: 1 of 10 (BADBOOL PR #131). It was CLOSED by the maintainer 10 minutes after opening, no comment. Accepted; not resubmitting.
- GitHub list PRs: 0 opened. Row 5 not until 2027-03-07; row 7 winget held (unsigned exe, silent install unchecked); row 8 Scoop needs an issue and approval first plus notability; row 19 Awesome-Windows repo is gone, the active list (0PandaDEV/awesome-windows) needs 50 stars (we have 1); row 20 archived. Revisit at 50 stars / signed exe. Details in listings.md.
- mastodon-queue.md written (14 posts, M-001 = the intro already posted). Today's one post already used by the intro; the first queued post (M-002) goes out 2026-11-08, then one a day by hand via API until the poster supports Mastodon. M-013 links home until the "why free" article is approved.
- Draft for owner review: content/why-free-my-id-is-free.md (from ROADMAP 1-2, no prices named; two review notes at the bottom).
- Bluesky queue untouched (the scheduled poster owns it).
- Escalation: none (no replies mentioning legal, press or money).
