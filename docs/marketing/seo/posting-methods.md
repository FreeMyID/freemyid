# Posting methods and owner steps (seo-growth)

Checked 2026-11-07. No token existed in the keyring service `freemyid-social` when checked (bluesky_token, mastodon_token, reddit_token, x_token, github_token all absent), so no post was made. `_index` lists: alternativeto, bluesky, facebook, github, google, mastodon, producthunt, reddit, x.

## What the owner clicks (numbered, in order)

Keyring tip: for every "store" step, use the same service name, `freemyid-social`, and the entry name given. Example: `python -c "import keyring,getpass;keyring.set_password('freemyid-social','bluesky_token',getpass.getpass())"` (type or paste the secret when asked; it is not echoed). Never paste a token into chat.

1. **AlternativeTo (first priority, manual).** Sign in as Free My ID at alternativeto.net. Click your user icon, then "Suggest new application". Paste the text from `listings.md` row 1 (short, medium and long text are in that file; tick Windows, license "Open Source", free). Tick the field that says you are the developer, if shown. Submit, then tell us the link. Nothing to store. After approval, email AlternativeTo support from the Free My ID mailbox with the account username to ask for developer access to the page (their FAQ says to do this).
2. **Mastodon token.** Log in on your Mastodon server in a browser. Go to Preferences, then Development, then "New application". Name it "freemyid-poster". Under scopes, untick everything (read, write, follow, push are ticked or partly ticked by default) and tick ONLY `write:statuses`. Save, open the app, copy "Your access token". Store as `mastodon_token`. Store the server address (for example `https://mastodon.social`) as `mastodon_server`.
3. **Bluesky app password.** In the Bluesky app or site go to Settings, then Privacy and security, then App passwords, then "Add app password". Name it "freemyid-poster". Leave "Allow access to your direct messages" OFF. Copy the password once (xxxx-xxxx-xxxx-xxxx). Store as `bluesky_token`. We use the handle from the `bluesky` entry.
4. **2FA.** Turn on two-factor (authenticator app, not SMS if you can avoid it) on every Free My ID account: GitHub, Google, Reddit, Mastodon, X, Bluesky (email 2FA is available there), Facebook. Save the recovery codes yourself. Do not give us the codes.
5. **GitHub token (for forks and pull requests on awesome-lists and package catalogs).** Signed in as the new Free My ID GitHub account (NOT your personal one): Settings, Developer settings, Personal access tokens, Fine-grained tokens, "Generate new token". Name `freemyid-pr`. Expiration 90 days. Resource owner: the Free My ID account. Repository access: "Public repositories (read-only)" is not enough for forks, so choose "All repositories" (the account has none of value yet) and set only these permissions: Contents = Read and write (needed to push to our fork), Pull requests = Read and write, Metadata = Read (automatic). Add nothing else. Store as `github_token`. If GitHub still refuses the fork call, tell us rather than widening permissions.
6. **Google Search Console.** Sign in with the `google` account at search.google.com/search-console. Click "Add property", pick "Domain", enter `freemyid.org`, Continue. Copy the TXT value that starts `google-site-verification=`. Put it in the shared handoff note (it is public by design; it is not a secret) or send it to devops-engineer. They add it at the apex. Then click Verify, and open Sitemaps and submit `https://freemyid.org/sitemap.xml`.
7. **Bing Webmaster Tools.** Go to bing.com/webmasters, "Sign in" with the Google option. Choose "Import" then "Google Search Console", allow access, tick freemyid.org. No DNS record is needed with this route. (If Bing asks for its own TXT or CNAME instead, copy the value to devops-engineer, same as step 6.) Then submit the sitemap.
8. **Product Hunt (manual, optional, later).** Product Hunt prohibits company accounts, so a launch would have to be from a personal account; our decision: do not launch there until the owner decides. Nothing to store.
9. **Reddit (manual).** Reddit now needs approval for new API apps, and its "script" app needs the account password to sign in, which we will not hold. So no token. If you want a post in r/privacy, read the sidebar rules first and post the medium text from `listings.md` yourself with the disclosure line. We will supply the exact text on request.
10. **X (manual or skip).** X has no free posting tier for new developers; posting is pay-per-use (about $0.015 a post, $0.20 with a link). Paid is outside our rules. Post by hand if wanted. Nothing to store.
11. **Facebook (manual).** Wait for Meta's page verification. Posting to a Page by API needs a Meta developer app and review; not worth it. Post by hand from the Page. Nothing to store.
12. **Tell us when done.** Say which `*_token` entries now exist. We will then make exactly one first post each on Mastodon and Bluesky, and log it in `outreach-log.md`.

## Method per platform

| Platform | Method | Token / entry | Status | Source |
|---|---|---|---|---|
| AlternativeTo | No API. Manual submission by owner via "Suggest new application"; developer access by emailing support | none | manual step (step 1) | https://alternativeto.net/faq |
| Mastodon | `POST {server}/api/v1/statuses` with `Authorization: Bearer <user token>`; needs scope `write:statuses` only | `mastodon_token`, `mastodon_server` | waiting for owner (step 2) | https://docs.joinmastodon.org/methods/statuses/ ; scopes https://docs.joinmastodon.org/api/oauth-scopes/ |
| Bluesky | `com.atproto.server.createSession` with handle plus an app password, then `com.atproto.repo.createRecord` with collection `app.bsky.feed.post` (fields `$type`, `text`, `createdAt`) | `bluesky_token` | waiting for owner (step 3) | https://docs.bsky.app/blog/create-post |
| Reddit | Script app uses the password grant (account password needed) and new apps need Reddit approval since Nov 2025. Rejected: manual only | none | manual (step 9) | https://github.com/reddit-archive/reddit/wiki/OAuth2 (script app, password grant); approval: Reddit r/redditdev announcement mirrored at https://r.datuan.dev/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/ (secondary source, verify) |
| X | Pay-per-use only: Post create $0.015, with URL $0.200. No free posting tier for new developers (third-party sources say closed 2026-02-06; secondary). Paid is not allowed, so manual or skip | none | manual or skip (step 10) | https://docs.x.com/x-api/getting-started/pricing |
| GitHub | Fork then PR using a fine-grained PAT passed as `GH_TOKEN` for that single process only. Never `gh auth login` or `gh auth switch`. Fork needs one of Administration (write), Contents (read), or Repository creation (write); PR needs Pull requests (write). We use Contents + Pull requests | `github_token` | waiting for owner (step 5) | https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens |
| Google Search Console | Domain property verified by DNS TXT at the apex; devops-engineer adds it | none (TXT value is public) | waiting for owner (step 6) | https://support.google.com/webmasters/answer/9008080 (verify wording; secondary guides agree) |
| Bing Webmaster | Import from Search Console, no DNS needed | none | waiting for owner (step 7) | https://blogs.bing.com/webmaster/september-2019/Import-sites-from-Search-Console-to-Bing-Webmaster-Tools |
| Product Hunt | No posting API for us; company accounts prohibited (see listings row 2) | none | held (step 8) | listings.md row 2 |
| Facebook | Manual from the Page after Meta verification | none | manual (step 11) | n/a |

## Rules we follow when a token exists
- Read the token from the keyring in memory, send it only to the platform's API host, never print or log it, never write it to a file or env file.
- One first post per platform, then wait for the wave report. Copy per POSITIONING: plain words, no fear, no "erase you from the internet", no guarantees, include "I work on Free My ID, a free open-source project" style disclosure ("We make Free My ID"). Account is "Free My ID".
- No hashtag spam, no follow/unfollow, no replies to strangers' posts, no automation beyond the single post.

## Draft first posts (for use once tokens exist)
Account: Mastodon freemyid_usa@mastodon.social. Mastodon/Bluesky (under 300 chars, one link):
`Free My ID is a free, open-source Windows app that asks people-search and data-broker sites to delete your listing, and keeps checking because sites re-list people. It runs on your computer. No account. Early release (v0.1.1): https://freemyid.org`
