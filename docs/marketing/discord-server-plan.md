# Free My ID official Discord server: plan

Status: draft 2026-11-07, Jordan Ellis. Owner creates the server (account and setup need a human). Nothing here is posted. Audience: older, non-technical, scam-wary people (docs/POSITIONING.md), so it is small, calm and quiet by default. Server icon: `brand/social/avatar/discord-icon-512.png`.

## Principles
1. Safe first: nobody should ever need to type personal details here. Say so at the top, in pinned text, and enforce it.
2. Read-only where possible. Fewer places to post means fewer places for scammers.
3. Staff are always labelled "Free My ID Team". We never DM first, never ask for a password, code or SSN, and say that in the welcome.
4. Not discoverable at launch (see "Search indexing"). Invite-link only, shared from freemyid.org and our own posts.

## Channels (in this order)
| Category | Channel | Who can post | Purpose |
|---|---|---|---|
| START HERE | #welcome | nobody (read-only) | Welcome message, what the server is, safety warning |
| START HERE | #rules | nobody (read-only) | The rules below |
| START HERE | #announcements | team only (Discord "Announcement" channel) | Releases, fixes, honest status. No marketing |
| HELP | #help | members | Questions about using Free My ID. Pinned warning (below) |
| HELP | #broker-reports | members | "This site is not honoring removals / its opt-out page changed." Site name and link only. Never your own details |
| TALK | #feedback | members | Ideas, confusing screens, what would help your parents |
| TALK | #off-topic | members | Friendly chat. No politics or party talk, no selling |
| TEAM | #mod-chat | moderators only | Private; not visible to members |

Start with these seven public channels. Add nothing else until people ask. No voice channels, no forum, no threads-for-everyone. No "self-promo" or "ads" channel.

## Roles
| Role | Who | Permissions |
|---|---|---|
| Free My ID Team | staff accounts | Admin-lite: manage messages, timeout, announcements. Not Administrator; no "manage server" except owner |
| Moderator | trusted volunteers (later) | Manage messages, timeout members, view #mod-chat |
| Member | everyone who passes verification | Read all public channels, post in #help, #broker-reports, #feedback, #off-topic |
| (no role) | new joiners | See only #welcome and #rules until they click the "I read the rules" button |

Deny Members the "Mention @everyone, @here and All Roles" permission, and deny "Create Invite". Keep the rest at defaults.

## Rules text (paste into #rules)
> **Free My ID server rules. Short and plain.**
> 1. **Never post personal details here.** No full name with address, no phone number, email, date of birth, Social Security number, passwords, codes or photos of documents. Not even if someone asks. We will never ask.
> 2. **We will never message you first.** The Free My ID Team never asks for money, passwords, codes or your details by private message. If someone claims to be us and does, block them and tell a moderator.
> 3. **Be kind.** No insults, no mocking people for the questions they ask. Every question here is a good one.
> 4. **No politics or party talk.** People of every view are welcome. Keep it about protecting your privacy.
> 5. **No selling, ads or links to other servers.** No "investment", "recovery" or "removal service" offers. These are removed and the poster is banned.
> 6. **Be careful with links.** Only trust downloads from freemyid.org. If a link is anywhere else, treat it as unsafe.
> 7. **We cannot promise results.** Free My ID asks sites to remove you, and some sites do not comply. Please do not ask for legal or medical advice here.
> The team can remove messages and members to keep this a safe place. Questions: ask in #help.

## Pinned warning (#help and #broker-reports, pin and also put in the channel topic)
> **Do not post personal details in this channel.** No full name, address, phone number, email, date of birth, Social Security number or passwords, and no screenshots that show them. If you must describe a problem, say "a site listed my address" and leave out the actual address. A moderator will delete any message with personal details and may ask you to change a password that was posted.

Channel topic for #help: `Questions about Free My ID. Never post personal details. We never message first.`

## Welcome message (#welcome)
> **Welcome to Free My ID.**
> Free My ID is a free, open-source app that asks the people-search and data-broker websites that sell your name, address and phone number to take your listing down, then checks that they did. It runs on your own computer. No account. Nothing is sent to us.
> **This server is for questions and feedback.**
> - Download only from **https://freemyid.org**.
> - **Never post personal details here**, and we will never message you first or ask for a password, code or Social Security number.
> - Read the short rules in #rules, then press the button below to join in.
> - Honest limits: it works on people-search and broker sites only. It does not change what Facebook or Meta does, it cannot stop phone listening or hacking, and sites can re-list people, which is why the app keeps checking.
> A real person from the Free My ID Team will answer in #help.

## Verification and AutoMod
These use only built-in Discord features; no bot is needed.
- **Verification level: Medium** (account registered on Discord for more than 5 minutes) or **High** (member of the server for more than 10 minutes). Start with Medium. Scammers use brand-new accounts.
- **Explicit media content filter:** scan messages from all members.
- **Default notifications:** Only @mentions.
- **Rules screening / membership screening** (Community server feature): shows the rules and requires "I agree" before access. Required to unlock the Member role.
- **2FA requirement for moderator actions:** on (Server Settings > Safety Setup).
- **Raid protection / DM-spam protection:** on. Disable "Allow direct messages from server members" default for new joiners, if offered.
- **AutoMod rules (Server Settings > AutoMod):**
  1. Block messages with likely spam, mention spam (limit 3 mentions) and suspected spam content.
  2. Custom keyword block + alert in #mod-chat: `discord.gg`, `discord.com/invite`, `nitro`, `airdrop`, `crypto`, `recovery`, `wallet`, `investment`, `telegram`, `whatsapp` (cuts invite spam and common scams).
  3. Pattern block + alert for personal data: a US SSN (`\b\d{3}-\d{2}-\d{4}\b`), a 16-digit card number, and US phone numbers (`\b\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b`). Custom message shown to the sender: "Please do not post personal details here. Message removed." Alert to #mod-chat. (Discord AutoMod supports regex; test the patterns on fake numbers only.)
  4. Block links from members in #announcements and #welcome (they are read-only anyway).
- **Timeout** (not ban) as the first response for rule 1 breaches; delete the message immediately.
- No bots that read message content, no logging bot for message text. Keep stored data minimal; Discord's own audit log is enough.

## Search indexing and privacy
Reports say Discord will let Discoverable servers' channel summaries be indexed from 16 Nov 2026 and messages from mid-December (source: https://godisageek.com/2026/10/discord-discoverable-servers-web-search-opt-out/, verify on Discord's help centre). So: keep the server out of Server Discovery, do not enable "Web Presence/Discoverable", and say in #welcome nothing that implies messages are private beyond Discord's own rules. Our rule 1 means a leak of a post would not hold personal data.

## Moderation routine (small)
- The team checks #help once a day. Answer plainly, point to the matching guide on freemyid.org, never ask for details.
- If someone posts personal details: delete, post "Message removed because it had personal details. Please see the pinned note." and do not quote the content.
- If a broker report is accurate, copy site name and link into the broker-researcher queue (no personal data).
- Anything about legal action, press or money goes to escalation (docs/AUTONOMY.md).

## Launch order
1. Owner creates the server as "Free My ID" (Community server on, not discoverable), sets the icon, and pastes the texts above.
2. Add the invite link to the website footer/Contact page (request to web-developer after the owner sends the permanent invite; use an invite with no expiry and no max uses, set to "never expires").
3. Announce once from our official social accounts. No outbound pushing into other servers from here.

## Is a bot worth it?
Not at launch. Release announcements into our own #announcements are better done with a built-in Discord **Channel Follow** or a plain channel webhook (a URL that only posts into one channel; no bot account, no permissions beyond that channel, nothing to host). A GitHub webhook can send release events straight to that channel (GitHub repo Settings > Webhooks, Discord's `/github` suffix), or the owner can post by hand, which at a few releases a month is fine. If a real bot is ever wanted, it needs only the scopes `bot` with the permissions View Channel, Send Messages and Embed Links in #announcements, and no Message Content intent, no Administrator, no DM ability, no access to #help, so it can never read member messages. It would run only in our own server; it never joins others and never posts from a user account (self-bots violate Discord's ToS). The cost is a token to protect and a host to keep up, which is not worth it for this audience yet. Creating the webhook is an owner task; store the URL as a secret and never in the repo.
