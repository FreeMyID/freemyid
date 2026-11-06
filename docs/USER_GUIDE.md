<!-- Status: done all sections (first draft) / next: lead review; resolve TODO verify markers as engine, wizard and scheduler land -->

# Vanish User Guide

This guide is for the person using Vanish. You don't need to be technical. If you only want the short version, read `FAMILY_QUICK_START.md` first and come back here when you have a question.

> Vanish is still being built. Anything marked `TODO verify` describes how it is *planned* to work and may change before release.

## Contents

1. [What Vanish does (and doesn't)](#1-what-vanish-does-and-doesnt)
2. [Before you start: a separate email address for removals](#2-before-you-start-a-separate-email-address-for-removals)
3. [Setting up](#3-setting-up)
4. [Your first run](#4-your-first-run)
5. [What each status means](#5-what-each-status-means)
6. ["Needs you" items](#6-needs-you-items)
7. [Approving emails](#7-approving-emails)
8. [If you live in California: DROP](#8-if-you-live-in-california-drop)
9. [When listings come back](#9-when-listings-come-back)
10. [Your privacy](#10-your-privacy)
11. [Questions](#11-questions)

## 1. What Vanish does (and doesn't)

"People-search" sites such as Spokeo, Whitepages and BeenVerified collect your name, age, addresses, phone numbers and relatives, and show them to anyone. Most of them must let you opt out, but doing it by hand across dozens of sites takes hours, and the listings come back.

Vanish does the repetitive part for you, on your own computer:

- It searches each site for you.
- It fills in each site's own removal form, or writes the removal email.
- It clicks the "confirm your request" links that sites send.
- It follows up when a site ignores you.
- It checks again later, and files again if your listing comes back.

Please know these limits up front:

- **"Removed" means removed from that one site,** not from the whole internet. Google results, social media, news articles and government records are not affected.
- **Listings often come back.** Sites buy fresh data and copy one another, so expect some reappearances. Vanish keeps watching for this.
- **Some sites need a real person.** Some sites ask you to prove you're human, mail a letter, make a phone call or show ID. Vanish prepares everything it can and then asks you to do that one step. See [section 6](#6-needs-you-items).
- **Nothing is perfect.** Sites change their pages. If a step fails, Vanish tells you instead of guessing.

## 2. Before you start: a separate email address for removals

Use a **new email address only for removal requests**, not your everyday one. Why:

- Sites need an email address to send confirmation links to. You don't want to hand them your real one.
- Vanish needs to read the confirmation emails in that mailbox. A separate mailbox means it never sees your personal mail.
- If a site sells that address, you just get spam in a mailbox you don't care about.

Create the mailbox first, then give Vanish the details during setup. Vanish stores the mailbox password in your computer's secure password store (Keychain on Mac, Credential Manager on Windows, the system keyring on Linux), never in a plain file.

Pick one of the providers below.

### Gmail

1. Create a new Google account, e.g. `jane.removals@example.com`.
2. Turn on **2-Step Verification**. App passwords require it. In Google Account: **Security** → **2-Step Verification**.
3. Create an **app password**. In Google Account: search "App passwords", name it `Vanish`, and copy the 16-character password it shows you. This is the password you give Vanish, *not* your normal Google password.
4. In the Vanish setup wizard, choose **Gmail**. The server settings are filled in for you (`imap.gmail.com` and `smtp.gmail.com`). Paste the app password.
5. Click **Test connection**.

<!-- TODO verify: Google still offers app passwords for new personal accounts; Gmail IMAP enabled by default -->

### Outlook / Hotmail

1. Create a new Outlook.com account.
2. In the Vanish setup wizard, choose **Outlook** and follow the on-screen instructions.
3. Click **Test connection**.

<!-- TODO verify: Microsoft has been retiring password-based (basic auth) IMAP/SMTP for Outlook.com in favor of OAuth. Confirm Outlook works with a password or app password before release; if not, recommend Gmail or Proton. -->

### Proton Mail (with Proton Mail Bridge)

Proton encrypts your mail, so other programs can only reach it through the free **Proton Mail Bridge** app on your computer. Bridge requires a paid Proton plan. <!-- TODO verify -->

1. Create a new Proton address (or add one to your account).
2. Install **Proton Mail Bridge** from Proton's website and sign in.
3. In Bridge, open the mailbox settings and copy the **Bridge password** it shows you. This is different from your Proton password.
4. In the Vanish setup wizard, choose **Proton Bridge**. The settings are filled in for you (server `127.0.0.1`, ports 1143 and 1025). Paste the Bridge password.
5. Click **Test connection**.

Bridge has to be running whenever Vanish checks mail, including scheduled background checks. <!-- TODO verify: STARTTLS on IMAP needs support in MailboxConfig -->

## 3. Setting up

Open a terminal and run:

```
vanish setup
```

This opens the setup wizard in your web browser. It runs only on your computer (the address starts with `http://127.0.0.1`), and nothing you type is sent to a website. If you prefer typed questions in the terminal, run `vanish setup --no-web`.

The wizard walks you through these steps:

1. **Consent.** Choose one of these:
   - **This is me.**
   - **I'm the parent or guardian of a child under 18.**
   - **I'm an authorized agent for another adult.** That adult must sign a written permission form. Vanish prints one for you to get signed and attach.

   Type your name to confirm. Vanish won't work on anyone without this step.
2. **Names.** Full name, middle name, nicknames, and previous or maiden names. Example: *Jane Q Testperson*, nickname *Janie*, previous name *Jane Q Example*.
3. **Addresses.** At least the city and state of where you live now (e.g. *Springfield, IL*). Add past cities too. They help Vanish recognize *your* listing among people with the same name.
4. **Age or birth date, phones, emails, relatives.** These are **only for recognizing your listings. Vanish never sends them to any site.**
5. **Permissions.** Some sites ask for a photo ID, an account, or a phone number. All three are **off** by default. If a site insists on one, Vanish asks you instead of doing it. Leave them off unless you have a reason to turn them on.
6. **Removal mailbox.** The mailbox from [section 2](#2-before-you-start-a-separate-email-address-for-removals).
7. **Email mode.** Keep **Approve each email** (the default) so you see every email before it's sent.
8. **Schedule.** How often Vanish re-checks in the background. The default is weekly (Sunday 10:00).
9. **Review.** Check everything, then save.

<!-- TODO verify: wizard step wording and layout -->

**Setting up a family member.** You can fill in a profile for a parent and send it to them as a password-protected file (`vanish profile export Mom mom.vanish-profile`). Tell them the password **by phone**, not in the same email as the file. On their computer, they open it during setup, check the details, and give their own consent.

**Turning on the background check.** Run `vanish schedule install`. It catches up automatically if your computer was asleep or off at the scheduled time. Check it with `vanish schedule status`; turn it off with `vanish schedule remove`.

## 4. Your first run

1. **Practice run (sends nothing):**
   ```
   vanish run --dry-run
   ```
   Vanish searches every site and shows what it found and what it *would* do.
2. **Look at the results:** `vanish dashboard` (or `vanish status` in the terminal).
3. **Turn on real requests (one time only):**
   ```
   vanish config enable-submissions
   ```
   Vanish explains what will happen and asks you to confirm.
4. **The real run:**
   ```
   vanish run
   ```
   You can leave this running. If a site needs you, a browser window opens on that page and Vanish waits. Do the step, then click **Done** in the dashboard (or press Enter in the terminal).

To work on one person only, add `-p Mom` (their profile name). For one site only, add `-b spokeo`.

## 5. What each status means

The dashboard shows a colored label for each site. <!-- TODO verify: exact chip labels and colors -->

| You'll see | It means | What you do |
|---|---|---|
| **Not checked yet** | Vanish hasn't searched this site yet. | Nothing. |
| **Not found** | No listing for you right now. | Nothing. Vanish checks again later. |
| **Found** | Your listing is there. A request will be sent on the next real run. | Nothing, unless it also says "needs you". |
| **Submitted** | The removal request was sent. | Nothing. Sites usually take days to weeks. |
| **Pending verification** | The site sent a confirmation email, or will. Vanish clicks the link when it arrives. | Nothing, unless a to-do appears. |
| **Confirmed** | The site accepted the request. Vanish is waiting for the listing to disappear. | Nothing. |
| **Removed** | Vanish searched again and the listing is gone from this site. | Nothing. Vanish keeps checking. |
| **Reappeared** | A removed listing came back. A new request will be filed. | Nothing. This is normal; see [section 9](#9-when-listings-come-back). |
| **Needs you** | Vanish can't go further without a person. | See [section 6](#6-needs-you-items). |
| **Error** | Something went wrong, often because the site changed its page. | Nothing right away. Vanish tries again on the next run. If it stays stuck, tell whoever set up Vanish for you. |

**When a site ignores you.** If a site hasn't acted after its usual processing time plus 15 days, Vanish escalates one step at a time:

1. It sends the request again.
2. It sends a follow-up email citing your state's privacy law, if your state has one.
3. It drafts a formal legal demand. **This always waits for your approval.**
4. It gives you a to-do with links for filing a complaint with your state Attorney General (or California's privacy agency).

## 6. "Needs you" items

See these in the dashboard's to-do list, or with `vanish todo list`. When you've handled one, click **Done** (or run `vanish todo done <id>`). If you run Vanish in the background, you'll get a desktop notification such as "Mom: 2 sites need you". Notifications never include personal details.

### "Prove you're human" checks (CAPTCHA)

Vanish **never** tries to get around these. It opens the page for you. Tick the box or pick the pictures, then let Vanish continue (click **Done**). If it was a background run, open the dashboard and click **Resolve** on the to-do to pick up where it stopped.

### Possible match: "Is this you?"

Vanish found a listing that *might* be you: the name matches, but only one other detail does. Look at the screenshot and confirm or reject it. <!-- TODO verify: confirm/reject controls for REVIEW_MATCH --> Vanish only sends requests on its own for listings it's sure about.

### ID requests and permission needed

Some sites ask for a photo ID, an account, or a phone number. If you left that permission off (the default), Vanish stops and asks. You can:

- **Skip that site.** Often the best choice. Many people decide a site isn't worth an ID.
- **Do it yourself** using the site's steps shown in the to-do. Cover your ID number and photo if the site allows it.
- **Turn the permission on** for that person, if you're comfortable with it.

<!-- TODO verify: how to change a permission flag (wizard edit vs. `vanish profile edit`) -->

### Letters to mail

Some companies only accept requests by post. Vanish writes the letter for you. Print it, sign it, put it in an envelope with the address shown, and mail it. Then mark the to-do done. Keep a copy, and consider sending it with tracking.

### Phone calls

A few sites only take requests by phone. Vanish gives you a short script listing what to say and which details the site already shows (only give those). Note the date and any reference number, then mark the to-do done. Don't give a phone number or other details the site doesn't already have.

### Sites that need an account

Vanish never creates accounts with passwords on its own. The to-do explains the site's steps so you can decide whether to do it.

### Unexpected page

The site showed something Vanish didn't recognize, for example a redesigned form. Open the link in the to-do and follow the site's steps yourself, or mark it done to have Vanish try again next run.

## 7. Approving emails

Many sites take removal requests by email. In **Approve each email** mode (the default), Vanish writes each email but **doesn't send it until you approve it**.

- In the dashboard, open **Outbox**, read the email, and click **Approve** to send it. <!-- TODO verify: dashboard outbox UI -->
- In the terminal, list waiting emails with `vanish outbox list` and send one with `vanish outbox approve <id>`.

Each email comes from your removal mailbox and includes only the details that site already shows about you. A copy of every sent email is kept in your encrypted records.

**Formal legal demands always wait for your approval,** even if you switch to automatic mode.

## 8. If you live in California: DROP

California's **Delete Act** created **DROP** (Delete Request and Opt-out Platform), a free, official state website run by the California privacy agency. One request there goes to every data broker registered in California, and registered brokers must keep checking it and deleting your data.

Vanish can't file DROP for you, because DROP needs an account and identity checks, which Vanish never does on its own. If your profile says you live in California, Vanish gives you a to-do with a link to the official DROP site. Do it once. It covers many companies that Vanish's own list doesn't reach.

- Use only the official government site. Ignore companies that charge to "file DROP for you".
- Vanish still handles the people-search sites directly. DROP and Vanish work well together.

<!-- TODO verify: DROP URL, agency name, and broker processing schedule against the `ca_drop` registry entry and brokers/state_laws.yaml -->

## 9. When listings come back

It's normal, and it doesn't mean Vanish failed. Sites buy fresh data from public records and from one another.

What Vanish does:

- It re-checks each site on a schedule: about weekly while something is in progress, and every month or so after a removal (each site has its own interval).
- When a listing comes back, it's marked **Reappeared**. A new request is filed on the next real run, and the follow-up steps start over.
- Some sites are copies of a bigger site. Vanish sends the request to the parent site and re-checks the copies.

What you can do:

- Keep the background check on (`vanish schedule status`).
- Handle "needs you" items when they appear. That's where most stuck removals are.
- Run `vanish report` now and then to save a record of what was removed and when.

## 10. Your privacy

- **Everything stays on your computer.** Vanish has no account, no cloud and no tracking.
- **Your information is encrypted.** The database and screenshots are encrypted, and the key is kept in your computer's secure password store.
- **Vanish talks only to the removal sites themselves and your removal mailbox.** It's blocked from contacting anything else.
- **Sites get as little as possible:** only what they already show about you, plus your removal email address. Never your birth date, relatives, or personal email.
- **To delete everything about a person:** `vanish profile remove <name>`. This removes their profile, screenshots, records and saved mailbox password.

## 11. Questions

**Will this remove me from Google?** No. Once a people-search page is gone, Google usually drops it over the following weeks, but Vanish doesn't contact Google.

**How long does it take?** Most sites act within a few days to six weeks. Some take longer, and Vanish follows up.

**Does it cost anything?** Vanish is free. It never pays a site, and it never uses paid removal services.

**I got an email from a site asking me to do something. Should I?** Check the dashboard first. If Vanish already handled it, you'll see it there. Never send ID or payment to a site because of an email alone.

**Something looks wrong.** Run `vanish status` and contact whoever set up Vanish for you. Vanish strips personal details out of its logs, but look over a log before sharing it anyway.
