# Brand — Free My ID

Decided by the user 2026-11-06. Replaces "Vanish", which clashed with Reckitt's stain remover. Read with docs/POSITIONING.md.

## Name and usage

- **Free My ID**: in prose, always with three words and capitals.
- **freemyid**: package, command, repo, domains and handles.
- Never "FreeMyID™" or "®" until a mark is actually filed.
- **Required clarifier:** the name can make people think "identity-theft protection". The tagline or first sentence must always say what it really does.

## Taglines (pick per context)

1. **Take your name off the websites that sell it.** (default, literal)
2. That post didn't stop anyone. This does. (Facebook-crowd landing and welcome screen only, never on the printable report)
3. Your information. Off the market. (short, patriotic tone)
4. No cloud. No account. Nothing leaves your computer. (trust line)

## Trust panel (welcome screen, site footer, store listings)

> No account. No cloud. Never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime.

## SEO: what our people actually type

Plain-language, long-tail queries this audience uses (to verify with free tools such as Google Search Console or Google Trends once the site exists):

| Intent | Example queries |
|---|---|
| The Facebook post | "does posting i do not consent on facebook work", "facebook privacy notice post real", "how to actually stop facebook using my information" |
| Found themselves online | "how to remove my address from the internet", "remove my name from people search sites free", "why is my phone number on the internet" |
| Specific sites | "remove myself from whitepages / spokeo / beenverified / truepeoplesearch" (one page per broker generated from brokers/registry.yaml, each one an honest how-to whether or not they use the app) |
| Fear / patriotic | "is my personal information being sold to china", "do government agencies buy personal data", "how to stop data brokers selling my information" |
| For relatives | "how to protect elderly parents personal information online", "remove my mom's address from internet" |

Content plan (free):
- A static site on GitHub Pages (free) at freemyid.org once that domain is registered. Until then use the github.io URL.
- Per-broker opt-out guides generated from the registry. They're useful without the app, rank for the "remove myself from X" queries, and build trust.
- A "Does the 'I do not consent' post work?" explainer, plus myth-vs-fact pages.
- A "Who's buying your data?" page with cited facts only (verify citations first; see POSITIONING.md).

## Free setup checklist

| Item | Status | Who |
|---|---|---|
| Rename the codebase vanish → freemyid | Coordinating with the other active session | orchestrator |
| Rename the GitHub repo the old personal repo → freemyid (stays private) | After the code rename | orchestrator |
| GitHub org `freemyid` (free) | Needs the user's GitHub web login (orgs can't be created via the CLI) | user, ~2 min |
| PyPI name `freemyid` | Wait: reserving it means publishing a public package, so do it at launch | at launch |
| Social handles (Facebook page, X, YouTube) `freemyid` | Need the user's accounts; free | user |
| Domains freemyid.org, getfreemyid.com | Paid, so on hold per the user | user, later |
| Trademark attorney clearance (MYID, MyIDCare risk) | Paid, so before public launch | user, later |
