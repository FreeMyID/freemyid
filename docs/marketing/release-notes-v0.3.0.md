# Release notes v0.3.0 (DRAFT, held until release)

**Status: DRAFT. HELD.** Do not publish, post or paste anywhere until v0.3.0 is tagged by the owner, the GitHub release is published and `site_src/data/release.yaml` shows it. Nothing here is posted. Owner approval is needed (docs/AUTONOMY.md, Tier 3).
Author: Jordan Ellis, 2026-11-09. Refreshed for the FINAL 0.3.0 against main b3b5013 (`git log v0.2.0..b3b5013`; rc1 shipped from f14203a, and everything on main since `v0.3.0rc1` also ships). Every bullet's commit was checked to be an ancestor of b3b5013 and not in v0.2.0, and each new bullet was checked against the code path a normal user reaches (wizard or cli.py, not behind an off-by-default switch). Bullets marked NEW-FOR-FINAL were added in this pass. Every bullet carries a commit tag in the comment after it; delete the comments and the NEW markers before publishing. If a commit is reverted or the item does not ship, delete the bullet.
Earlier passes: first draft from 996d300, refreshed against rc commit 18eaa65 on 2026-11-08.

Correction to earlier drafts: the v3 look, dark mode, the Today screen and the Protect checklists were already in v0.2.0 (`theme.js`, `tokens.css` and the Today screen are in the v0.2.0 tag). They are NOT listed as new here. What is new on the accessibility side is small and is described as small.

<!--
CHECK BEFORE PUBLISHING (delete this block):
- Version string, asset names and SHA256SUMS on the release match the text below.
- Windows installer upgrade-in-place still works (same AppId as 0.2.0).
- Bing step: checklist is marked "partial" (URLs not yet opened by us, 12baff6). Keep the "check it opened the right page" sentence.
- Previous-name search is OFF by default (ac559fd). Do not say it is on.
- State laws are registry data (brokers/state_laws.yaml 2026.11.2), shipped with the release only if the registry in the build carries that version.
- Do NOT add: proof vault, PDF report, Outlook sign-in, broker monitoring, relist detection, tray icon, price, Docker.
- Re-checked 2026-11-09 against b3b5013:
  - MOVED IN: generational-suffix matching (9554104; the setup screen has a "Jr., Sr., III" box, wizard/ui.py:285, and matcher.name_score uses it on every scan). Exposure trend note (6f930b2 + 2d6fbcd): printed by `freemyid exposure` (cli.py:452-462), so it goes in the command-line section only; the Windows app does not show it.
  - STILL OUT: phone-only/email-only removal (BL-IN-08): no wizard, CLI or setup-file path sets `removal_scope`. Monthly progress notification (BL-IN-25): wired by default (wizard/desktop.py:166, cli.py:324), but the Windows toast has not been seen on a real Windows install, so not claimed until it is. `freemyid monitor` (cb641ea, c0e84d2): a maintainers' tool that checks each site's opt-out page against our list; it is "broker monitoring" in the do-not-add list's words and does nothing for a person's own listings, so not claimed. Mailing-receipt upload (a9cc27a): wired, but the public build ships only registry.sample.yaml, which has no mail-only site, so no normal user sees it. Credit-freeze printable page and fridge card: site items, not app. Website refresh (WO-195..209, revamp commits): website only, left out.
  - Accessibility since rc1: WO-213 (0b469b8) adds tests only; the a11y fixes since rc1 are on the website. No new app accessibility claim.
- The "Is this you?" card has a practice-mode line that says no data at all goes out (wizard/dashboard.py, _review_card). Practice mode still searches. That is app copy (wizard-packager), flagged in the report; the release notes do not repeat it.
-->

---

## GitHub release body (paste from the next line)

# Free My ID 0.3.0

Free My ID asks the people-search and data-broker sites that list your name, address and phone number to take your details down, and keeps checking. It runs on your own computer. You do not need a Free My ID account, and your details are not sent to us.

## If you use Windows (most people)

Download the installer from freemyid.org and run it like before. If you already have Free My ID, the new installer updates it.

**New in this version**

- **Google and Bing steps.** Your name can also show up in search results. Free My ID now walks you through asking Google, and Bing, to remove results about you. It opens each company's own request page, and you tick the step off when you have sent it. You fill in and send the request yourself; Free My ID does not do it for you. Whether a search engine removes a result is up to that company. <!-- bd6fb4d, 535fb7a, 0f57972, 12baff6 -->
- **A line on your Today screen.** The Today screen now tells you when a Google or Bing step is waiting. Steps are kept per person if more than one person uses the app. <!-- 535fb7a, 6386dd6 -->
- **Finds people who go by another name.** If you are listed as "Bob" and your records say "Robert", Free My ID now looks for both. It uses a short list of common nicknames. A nickname match alone is never enough: it still needs a second detail that fits (like your age, phone or email) before it counts as you. <!-- 78e6af1, dc18764 -->
- **Older names (optional, off by default).** You can turn on one extra search under a previous name, such as a maiden name. Because that sends the old name to the people-search sites, it stays off until you choose it. <!-- e385232, ac559fd, ae936e8 -->
- **A "what happens next" timeline.** The last screen of setup now says, in plain steps, what happens right after you finish and over the next weeks. Sites answer at their own pace, often two to six weeks. <!-- 924b9f0 -->
- **A heads-up that the first start is slow.** The installer's last page now says that the first start can take a little while, so you are not left wondering. On Windows a small "starting" window now shows while it waits. <!-- 07fdbcc, 79c2a8d -->
- **Updated state-law information.** The state privacy-law notes behind the removal letters were re-checked and now name the specific sections of each law. North Carolina, South Carolina and Arizona have no state privacy law in force today, so letters for those states are polite requests that do not claim a legal right. Many sites do not have to act on a request under these laws, for example because of their size or because the data is public record. <!-- 040a13a -->
- **Safety checklists re-checked.** The steps for freezing your credit and for cutting down junk mail and prescreened credit offers were checked again against the official pages. <!-- 040a13a, dd93a77 -->
- **A simpler Today screen.** Today now shows one card with the next thing to do and a link to "more". The full list, the safety steps and the details moved to that page, so the first screen is less crowded. <!-- bddad26 --> NEW-IN-REFRESH
- **A plainer listing score.** The listing check now gives a short headline and the top three reasons behind the score, in plain words. It always says it covers "the sites we could check" and never says you are safe. <!-- afd7399, 17684e3 --> NEW-IN-REFRESH
- **Letters wait for the legal window.** A follow-up letter no longer quotes a state law before the time that law allows a site to answer. Until then it is a friendly reminder. If a site says it needs more time, the app notes that. <!-- 0992333 --> NEW-IN-REFRESH
- **Only the age a site already shows.** Your birth year is not used to fill in an age. A site's form or letter gets only the age that site's own listing shows, and no age at all if the listing shows none. <!-- 5f01a9c, f1e0a13 --> NEW-IN-REFRESH
- **Answer "Is this you?" with one button.** When a site shows someone who might be you, the card now has two buttons: "Yes, this is me" and "No, this is not me". It also says why it might be you, for example the same name and city, and what each button does. You can open the page first to look. If you press Yes, Free My ID asks that site to take the listing down on its next check, if your settings allow it. If you press No, it does not ask about that listing again. <!-- cff7918, 9874e62, 7d41982 --> NEW-FOR-FINAL
- **Jr., Sr. and III.** If your name has a Jr., Sr. or a number like III, and a site shows the same one, that no longer lowers the match. A different one, like Sr. instead of Jr., does not make the match stronger. <!-- 9554104 --> NEW-FOR-FINAL
- **A note about a phone call.** For a site you have to phone, you can now type a short note about the call when you mark the step done. It is optional. The note is saved, encrypted, on your computer with the site's other records. Very few sites need a phone call. <!-- a9cc27a --> NEW-FOR-FINAL

**What's better**

- **Big text stays on.** The large-text setting is now remembered, and the pages were fixed so wide text does not push the page sideways on a small screen. <!-- 5e38b9d --> NEW-IN-REFRESH
- **Easier to use with a keyboard, a screen reader or a big text size.** Checkbox rows on the checklists now have a larger area to tap. Page headings on the checklists are in a proper order for screen readers. When a form field has an error, the message is now tied to that field. These are improvements, not a promise that every screen is perfect. If something is hard to use, tell us. <!-- c966a00, 7c3b470, 58f7128 -->
- **Under the hood.** Tighter limits on how much data the early listing check will read from a site, a clearer "this site was too slow" message instead of a silent miss, and more tests. Nothing for you to click. <!-- bc058b3, 0c5f419 -->

**What has not changed**

- No Free My ID account, no cloud, no tracking. Your details are stored on your computer. Free My ID uses them to search the people-search sites, and puts them in the removal requests. Practice mode still searches, but it sends no removal requests.
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

New command: `freemyid search-engines` lists the Google and Bing steps, opens the official page, and records when you have sent each one (`list`, `open`, `done`, `undo`). The listing check also reads the nickname and previous-name options above, and `freemyid exposure` ends with a Google and Bing line and prints the headline and top three reasons. `freemyid exposure --old-addresses` also searches each site once at your previous address (off unless you ask). See docs/CLI.md for the exact options. <!-- 0f57972, e385232, 17684e3, 61d65f8 -->

After two or more checks, `freemyid exposure` also prints one line on how your score changed since the last check, and warns when fewer sites could be checked that time. <!-- 6f930b2, 2d6fbcd --> NEW-FOR-FINAL

## Thanks

Questions or something confusing? Use "Tell us what confuses you" on freemyid.org. You do not need an account.

(end of release body)

---

<!--
HISTORY (not for pasting): the 0.3.0rc1 release used the title "Free My ID 0.3.0 release candidate 1 (test version)" and a paragraph above the body telling people to stay on 0.2.0 unless a helper asked them to try it, and the Windows line said "the 0.2.0 one, unless a helper told you otherwise". All three were removed for the final 0.3.0.
-->
