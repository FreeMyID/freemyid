# Reddit queue (owner posts by hand)

Refreshed 2026-11-07 (Jordan Ellis). Agents never touch reddit.com (blocked); this research used search snippets and third-party mirrors only, so **rules below are second-hand until the owner reads the live sidebar**. Rules page for any sub: https://www.reddit.com/r/<name>/about/rules . Post as u/FreeMyID, open with "I work on Free My ID, a free open-source project", lead with the useful guide, one post per sub, max one sub a day, never ask for upvotes, answer every comment, no copy-paste cross-posts. Reddit's common norm is "participate, don't only promote" (about 90/10; secondary source https://redship.io/blog/reddit-self-promotion-rules-2026). Log each post in `outreach-log.md`.

| # | Subreddit | Rule found (source) | Allowed post | Status |
|---|---|---|---|---|
| R1 | r/privacy | r/privacy's own rules were not retrievable; read the sidebar. | Guide share, if sidebar allows | ASK-MOD-FIRST (modmail) |
| R2 | r/degoogle | Not retrievable; read the sidebar. | Guide share (Google results guide only) | ASK-MOD-FIRST |
| R3 | r/opensource | New rules reported 24-25 Oct 2026: promoted projects must be "actively maintained for at least a year", and projects that "use AI, are made by AI, or are intended for AI" are excluded (https://runtimewire.com/article/r-opensource-bars-ai-projects-and-requires-a-year-of-maintenance-for-promotion , second-hand). Free My ID is under a year old. | none | **NO** (replaces the earlier R3 draft) |
| R4 | r/Windows10 / r/windows | Not retrievable; likely strict. | none | NO unless sidebar allows tool posts |
| R5 | r/Scams | Likely bans promotion. | Answer "how do I remove myself from people search" questions only if rules allow, with disclosure | NO (post); comments ASK-MOD-FIRST |
| R6 | r/cybersecurity | Mirror of its promotion rule: promotion "under 10% of your posts and comments", at most once a week per promoted entity (https://redlib.hbubli.cc/r/cybersecurity/wiki/rules/promotion , second-hand). A new account with no history fails the 10% test. | none now | NO until the account has real participation |
| R7 | r/SeniorCitizens, r/techsupport | Not retrievable. r/techsupport is a help sub: do not post, only answer if someone asks about people-search removal and rules allow links. | comments only | ASK-MOD-FIRST |

Realistic plan: build the account first by genuinely helping in R1/R5/R7-type threads for a few weeks (answers that work without our link), then ask r/privacy mods via modmail before sharing the guide. A cold link post from a brand-new brand account is the main way to get banned.

## R1 r/privacy: guide share (only after modmail says yes)
Title: `A plain step-by-step for getting off Spokeo, Whitepages and TruePeopleSearch (free, no account)`
Body:
> I work on Free My ID, a free open-source project, so take that into account. We wrote step-by-step guides for the removal pages of the common people-search sites, because the steps are scattered and change. They work without our software: https://freemyid.org/guides/ . For each site: where the opt-out page is, what it asks for (never an SSN or card), and how long to wait. Sites can re-list people, so check again in a few months. If a guide is wrong or out of date, tell me and I'll fix it.

## R2 r/degoogle: guide share (only after modmail says yes)
Title: `Walkthrough: Google's "Results about you" tool for removing your phone number and address from search`
Body:
> I work on Free My ID (free, open source). We wrote up Google's "Results about you" tool, what it can and cannot remove, and why you also need to remove the source page: https://freemyid.org/guides/google-results-about-you/ . Corrections welcome.

## Modmail text (R1, R2, R7)
> Hi mods, I work on Free My ID, a free open-source Windows app for removing your listing from people-search sites. We have plain step-by-step guides that work without the app. Would a single post sharing them fit this sub, or would you prefer I do not? I will follow your decision.

Follow-up: record each post URL in outreach-log.md.

## Owner-ready pack (2026-11-08): top 3, polished
Status: waiting on API keys (reddit_client_id, reddit_client_secret, reddit_refresh_token are NOT in keyring freemyid-social). All subreddit rules below are UNCONFIRMED: I cannot read reddit.com. Every sub must be checked at https://www.reddit.com/r/<name>/about/rules before posting. Flair: unknown for all three until the sidebar is read; pick the closest "Guide / Resource / Discussion" flair if one is required, and never a "Question" flair.

Do not post cold. Order: 1) r/privacy (modmail first), 2) r/degoogle (modmail first), 3) r/SeniorCitizens (modmail first; it is the audience closest to our users). One sub per day.

1. r/privacy. Rules: not confirmed (self-promotion and link-post rules unknown). Flair: unknown. Send the "Modmail text" above first. If mods say yes, post the R1 title/body above.
2. r/degoogle. Rules: not confirmed. Flair: unknown. Modmail first, then the R2 title/body above (Google "Results about you" guide only).
3. r/SeniorCitizens. Rules: not confirmed. Flair: unknown. Modmail first. If allowed:
   Title: `A plain guide to getting your name and address off people-search sites (free, no account)`
   Body: `I work on Free My ID, a free open-source project, so please weigh that. We wrote plain step-by-step guides for removing your listing from the common people-search sites. They work with or without our software: https://freemyid.org/guides/ . Each guide says where the opt-out page is and what it asks for (never a Social Security number or card). Sites can re-list people, so check again in a few months. If something is wrong or out of date, tell me and I will fix it.`

Owner steps:
1. Log in to reddit.com as u/FreeMyID. Go to https://www.reddit.com/prefs/apps and choose "create another app".
2. Name "Free My ID", type "script", redirect URI http://localhost:8080 , create. Note the client id (under the app name) and the secret.
3. Run `.venv/bin/python tools/store_social_keys.py` and enter reddit_client_id, reddit_client_secret and reddit_refresh_token (the script flow needs a refresh token or the account password per tools/store_social_keys.py; follow its prompts). Note: Reddit's Responsible Builder / API access approval may be needed; if the app page asks for approval, request it describing a non-commercial, owner-supervised account.
4. Tell Sam; the first action will be the modmail to r/privacy through the API, not a post.
