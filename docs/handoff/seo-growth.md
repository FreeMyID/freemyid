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
