# SEO and growth plan

Owner: seo-growth (Sam Okafor [freemyid]). Started 2026-11-07. Read with docs/POSITIONING.md and docs/BRAND.md ("SEO: what our people actually type").

## Goals (first 90 days after freemyid.org is indexed)

1. **Get indexed and measured.** Google Search Console and Bing Webmaster Tools are verified by DNS TXT (devops-engineer), and the sitemap is submitted. Cloudflare zone analytics is the only traffic source. No client-side analytics, ever.
2. **Rank for "remove myself from <site>" queries.** The 30 per-broker guides are the core asset. They're useful without the app, and every one links to the download.
3. **Own the "I do not consent" question.** /i-do-not-consent/ answers what our primary audience actually searches for, calmly and without mocking anyone.
4. **Earn honest links and listings.** List us in directories and catalogs that welcome free, open-source privacy tools (see listings.md). No bought, swapped or spam links.

## Priorities, in order

| # | Work | Why | Where |
|---|---|---|---|
| 1 | Build-time fixes: sitemap lastmod, a visible "last checked" date plus dateModified on guides, related-guide links | These are cheap, help every guide, and stay inside the static, no-JS rules | WR rows tagged `seo:` |
| 2 | Search Console + Bing verification | We can't measure rankings without them, and keywords.md stays guesses until then | handoff to devops-engineer |
| 3 | Listings: AlternativeTo, the GitHub topics/awesome lists, privacy directories | These are the highest-trust free links and send real visitors | listings.md (ready, awaiting go) |
| 4 | Content: a general how-to hub article, an article on protecting elderly parents, a state-law explainer | These match the "found themselves online" and "for relatives" intents in BRAND.md | content/ drafts for web-developer |
| 5 | Competitor notes (DeleteMe, Incogni, Optery, Kanary) | Only sourced facts | competitors.md (not started) |

## Rules we work by

- Every factual claim in a draft carries a source, or `needs-verify` for broker-researcher.
- Copy follows POSITIONING: don't promise removal, don't sell fear, and don't say "they have to answer" without the state-law qualifier.
- Volume numbers come only from free sources we can cite. Until then, keywords.md marks each one as a guess.
- Stage B (submitting, posting, PRs, contacting anyone) waits until the orchestrator says go, and every action gets logged in outreach-log.md.

## Next

- Once Search Console has 28 days of data, replace the guesses in keywords.md with real impressions and positions.
- Write competitors.md.
- Draft one article per week. Start with the opt-out how-to hub (content/how-to-remove-yourself-from-people-search-sites.md).

## Content plan refresh 2026-11-08: v0.3 "See it, fix it" articles
Publish each only when the matching v0.3 feature ships (ROADMAP.md lines 81, 97, 205; features are planned, not live). Until then drafts stay in content/.

| # | Article | Intent / query (volume: guess) | Feature tie | Key sources |
|---|---|---|---|---|
| A | How to remove your phone number and address from Google search results | "remove my info from google" , "google results about you" | Google/Bing guided removal | Google: Results about you only removes from Google Search; the host site must be contacted separately (https://support.google.com/websearch/answer/9673730) |
| B | Freeze your credit for free: a checklist for you and your parents | "how to freeze my credit", "freeze credit for elderly parent" | Credit freeze checklist | FTC: free to place or lift, lasts until lifted, contact Equifax, Experian, TransUnion (https://consumer.ftc.gov/articles/credit-freezes-and-fraud-alerts); Innovis/ChexSystems/NCTUE/LexisNexis: needs-verify (broker-researcher) |
| C | Search results, people-search sites, credit files: which one to fix first | "what to do after finding myself on a people search site" | Exposure scan + score | internal; sources from A and B |

Outline for B: content/credit-freeze-checklist-for-you-and-your-parents.md (draft).
