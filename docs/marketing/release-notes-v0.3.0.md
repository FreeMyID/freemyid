# Release notes v0.3.0 (DRAFT, held until release)

**Status: DRAFT. HELD.** Do not publish, post or paste anywhere until v0.3.0 is tagged by the owner, the GitHub release is published and `site_src/data/release.yaml` shows it. Nothing here is posted. Owner approval is needed (docs/AUTONOMY.md, Tier 3).
Author: Jordan Ellis, 2026-11-08. Built from `git log v0.2.0..HEAD` on main (HEAD 996d300). Every bullet carries a commit tag in the comment after it; delete the comments before publishing. If a commit is reverted or the item does not ship, delete the bullet.

Correction to earlier drafts: the v3 look, dark mode, the Today screen and the Protect checklists were already in v0.2.0 (`theme.js`, `tokens.css` and the Today screen are in the v0.2.0 tag). They are NOT listed as new here. What is new on the accessibility side is small and is described as small.

<!--
CHECK BEFORE PUBLISHING (delete this block):
- Version string, asset names and SHA256SUMS on the release match the text below.
- Windows installer upgrade-in-place still works (same AppId as 0.2.0).
- Bing step: checklist is marked "partial" (URLs not yet opened by us, 12baff6). Keep the "check it opened the right page" sentence.
- Previous-name search is OFF by default (ac559fd). Do not say it is on.
- State laws are registry data (brokers/state_laws.yaml 2026.11.2), shipped with the release only if the registry in the build carries that version.
- Do NOT add: proof vault, PDF report, Outlook sign-in, broker monitoring, relist detection, tray icon, price, Docker.
-->

---

## GitHub release body (paste from the next line)

# Free My ID 0.3.0

Free My ID asks the people-search and data-broker sites that list your name, address and phone number to take your details down, and keeps checking. It runs on your own computer. There is no account and nothing is sent to us.

## If you use Windows (most people)

Download the installer from freemyid.org and run it like before. If you already have Free My ID, the new installer updates it.

**New in this version**

- **Google and Bing steps.** Your name can also show up in search results. Free My ID now walks you through asking Google, and Bing, to remove results about you. It opens each company's own request page, and you tick the step off when you have sent it. It does not search for you or send anything for you. Whether a search engine removes a result is up to that company. <!-- bd6fb4d, 535fb7a, 0f57972, 12baff6 -->
- **A line on your Today screen.** The Today screen now tells you when a Google or Bing step is waiting. Steps are kept per person if more than one person uses the app. <!-- 535fb7a, 6386dd6 -->
- **Finds people who go by another name.** If you are listed as "Bob" and your records say "Robert", Free My ID now looks for both. It uses a short list of common nicknames. A nickname match alone is never enough: it still needs a second detail that fits (like your age, phone or email) before it counts as you. <!-- 78e6af1, dc18764 -->
- **Older names (optional, off by default).** You can turn on one extra search under a previous name, such as a maiden name. Because that sends the old name to the people-search sites, it stays off until you choose it. <!-- e385232, ac559fd, ae936e8 -->
- **A "what happens next" timeline.** The last screen of setup now says, in plain steps, what happens right after you finish and over the next weeks. Sites answer at their own pace, often two to six weeks. <!-- 924b9f0 -->
- **A heads-up that the first start is slow.** The installer's last page now says that the first start can take a little while, so you are not left wondering. <!-- 07fdbcc -->
- **Updated state-law information.** The state privacy-law notes behind the removal letters were re-checked and now name the specific sections of each law. North Carolina, South Carolina and Arizona have no state privacy law in force today, so letters for those states are polite requests that do not claim a legal right. Many sites do not have to act on a request under these laws, for example because of their size or because the data is public record. <!-- 040a13a -->
- **Safety checklists re-checked.** The steps for freezing your credit and for cutting down junk mail and prescreened credit offers were checked again against the official pages. <!-- 040a13a, dd93a77 -->

**What's better**

- **Easier to use with a keyboard, a screen reader or a big text size.** Checkbox rows on the checklists now have a larger area to tap. Page headings on the checklists are in a proper order for screen readers. When a form field has an error, the message is now tied to that field. These are improvements, not a promise that every screen is perfect. If something is hard to use, tell us. <!-- c966a00, 7c3b470, 58f7128 -->
- **Under the hood.** Tighter limits on how much data the early listing check will read from a site, a clearer "this site was too slow" message instead of a silent miss, and more tests. Nothing for you to click. <!-- bc058b3, 0c5f419 -->

**What has not changed**

- No account, no cloud, no tracking. Your details are stored on your computer and go only to the sites you ask to remove you, in the removal request.
- Free My ID never asks for your Social Security number, bank details or a card.
- It is free and open source (AGPL).

## What it does not do

- It works on people-search and data-broker sites. It does not change anything on Facebook or other social sites.
- Sites can list you again, which is why it keeps checking.
- Some sites need a step from you. The app tells you which.
- A low score or zero on the listing check means "on the sites we could check". It never means you are safe.
- The installer is not yet code-signed, so Windows may show a blue "unknown publisher" box. The download page explains how to check the file.
- It is not identity-theft protection and it cannot promise any site will remove you.

## If you use Linux or Mac (command line)

New command: `freemyid search-engines` lists the Google and Bing steps, opens the official page, and records when you have sent each one (`list`, `open`, `done`, `undo`). The listing check also reads the nickname and previous-name options above, and `freemyid exposure` ends with a Google and Bing line. See docs/CLI.md for the exact options. <!-- 0f57972, e385232 -->

## Thanks

Questions or something confusing? Use "Tell us what confuses you" on freemyid.org. You do not need an account.
