<!-- Status: copy aligned with docs/POSITIONING.md and the 6-screen plan; resolve TODO verify markers as features land -->

# Free My ID User Guide

This guide is for the person using Free My ID. You don't need to be technical. If you only want the short version, read `FAMILY_QUICK_START.md` first and come back here when you have a question.

> Free My ID works today. Some parts are still being checked. Anything marked `TODO verify` may change.

## Contents

1. [What Free My ID does (and doesn't)](#1-what-free-my-id-does-and-doesnt)
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

## 1. What Free My ID does (and doesn't)

**That post didn't stop anyone. This does.** If you ever posted "I do not give permission to use my information", you were right to object. That post goes to your friends' feeds, though, and nobody who sells your details has to read it. Free My ID sends the same wish to the right place, through each site's own removal process (a formal legal request where your state has a privacy law).

"People-search" sites (also called data brokers) such as Spokeo, Whitepages and BeenVerified collect your name, age, addresses, phone numbers and relatives, and show them to anyone. Many of them have a way to ask them to take your details down, but doing it by hand across dozens of sites takes hours, and the details come back.

**No account. No cloud. Free My ID never asks for your Social Security number or bank or card details, and never charges you. It is free and open source, and you can uninstall it anytime.**

Free My ID does the repetitive part for you, on your own computer:

- It asks the sites to delete your details, through each site's own removal process. Where your state has a privacy law, sites must answer. Elsewhere many sites honor the request, but they do not have to.
- It searches each site for you.
- It fills in each site's own removal form, or writes the removal email.
- It clicks the "confirm your request" links that sites send.
- It follows up when a site ignores you.
- It checks again later, and files again if your listing comes back.

Please know these limits up front:

- **When a site says it deleted you, that is for that one site only,** not the whole internet. Google results, social media, news articles and government records are not affected.
- **Free My ID does not change what Facebook does.** It works on people-search sites. It does not change what Facebook (or Google) does with your account.
- **Details often come back.** Sites buy fresh data and copy one another, so expect some reappearances. Free My ID keeps watching for this.
- **Some sites need a real person.** Some sites ask you to prove you're human, mail a letter, make a phone call or show ID. Free My ID prepares everything it can and then asks you to do that one step. See [section 6](#6-needs-you-items).
- **Nothing is perfect.** Sites change their pages. If a step fails, Free My ID tells you instead of guessing.

## 2. Before you start: a separate email address for removals

Use a **new email address only for removal requests**, not your everyday one. Why:

- Sites need an email address to send confirmation links to. You don't want to hand them your real one.
- Free My ID needs to read the confirmation emails in that mailbox. A separate mailbox means it never sees your personal mail.
- If a site sells that address, you just get spam in a mailbox you don't care about.

Create the mailbox first, then give Free My ID the details during setup. Free My ID stores the mailbox password in your computer's secure password store (Keychain on Mac, Credential Manager on Windows, the system keyring on Linux), never in a plain file.

Pick one of the providers below.

### Gmail

1. Create a new Google account, e.g. `yourname.removals@gmail.com` (pick your own; this is only an example).
2. Turn on **2-Step Verification**. App passwords require it. In Google Account: **Security** → **2-Step Verification**.
3. Create an **app password**. In Google Account: search "App passwords", name it `Free My ID`, and copy the 16-character password it shows you. This is the password you give Free My ID, *not* your normal Google password.
4. In the Free My ID setup wizard, choose **Gmail**. The server settings are filled in for you (`imap.gmail.com` and `smtp.gmail.com`). Paste the app password.
5. Click **Test connection**.

<!-- TODO verify: Google still offers app passwords for new personal accounts; Gmail IMAP enabled by default -->

### Outlook / Hotmail

Outlook.com and Hotmail **can't be used** for the reply mailbox: Microsoft no longer lets programs sign in to those mailboxes with a password, and the setup wizard says so on the mailbox screen. Use a new Gmail address instead (or Yahoo, iCloud, or Proton Mail with Bridge). You can still send the "do it with me" letters from Outlook in your web browser: the app gives you an Outlook button for that.

<!-- source: src/freemyid/wizard/ui.py ("Not possible", "Why Outlook.com does not work"), wizard/flows.py presets skip Outlook.com; assisted letters link outlook.live.com compose (engine/outbox.py) -->

### Proton Mail (with Proton Mail Bridge)

Proton encrypts your mail, so other programs can only reach it through the free **Proton Mail Bridge** app on your computer. Bridge requires a paid Proton plan. <!-- TODO verify -->

1. Create a new Proton address (or add one to your account).
2. Install **Proton Mail Bridge** from Proton's website and sign in.
3. In Bridge, open the mailbox settings and copy the **Bridge password** it shows you. This is different from your Proton password.
4. In the Free My ID setup wizard, choose **Proton Bridge**. The settings are filled in for you (server `127.0.0.1`, ports 1143 and 1025). Paste the Bridge password.
5. Free My ID shows you the mail app's **security code** (a long row of letters and numbers) and asks you once whether to trust it. If you just installed and started Bridge yourself, click **Yes**.
6. Click **Test connection**.

Free My ID remembers that security code. If it ever changes, Free My ID won't sign in and tells you instead. That usually just means Bridge was reinstalled or reset: run the setup's mailbox step again to trust the new code. If you didn't change anything, don't trust it, and ask someone you trust to check your computer.

This trust step only works for a mail app on your own computer. For Gmail, Yahoo, iCloud and other providers, Free My ID always uses the normal security check and never asks you.

Bridge has to be running whenever Free My ID checks mail, including scheduled background checks.

## 3. Setting up

On Windows you do not need a terminal. Double-click the **Free My ID** icon on your Desktop (or find it in the Start Menu). Free My ID opens in its own window. It runs only on your computer, and nothing you type is sent to a website.

The setup has **six screens**. Each asks one thing. Press **Next** to go on, or **Back** if you change your mind.

1. **Welcome.** Choose one of these:
   - **This is for me.**
   - **This is for my child** (I am their parent or guardian, and they are under 18).
   - **This is for an adult who asked me to help.** That adult must sign a short permission form. Free My ID prints one for you to get signed and attach.

   Type your full name to sign, and tick the box. Free My ID won't work on anyone without this step.
2. **Name.** Full name, plus any nicknames or maiden or earlier names. Example: *Jane Q Testperson*, nickname *Janie*, earlier name *Jane Q Example*.
3. **Address.** The city and state where you live now (for example *Springfield, IL*). Add past cities if you like. They help Free My ID recognize *your* listing among people with the same name.
4. **A few details.** Birth year, a phone number and an email. These are **only used on this computer to tell you apart from other people with your name.** Birth year and relatives are never sent to a site. If a site's form asks for an age, it gets only the age that site's own listing already shows, never one worked out from your birth year. A phone number goes to a site only if you switch that on.
5. **Email for removals.** The separate mailbox from [section 2](#2-before-you-start-a-separate-email-address-for-removals). Pick your email company and follow the short steps on screen, **or** choose **Skip, I'll do these by hand**. Skipping is fine. Permissions for ID, accounts and phone numbers stay **off** unless you turn them on later in Settings.
6. **Run automatically?** Leave the box ticked so Free My ID keeps checking by itself. Click **Finish**.

**Setting up a family member.** Someone can fill in a profile for a parent and send it as a password-protected file. Tell the parent the password **by phone**, not in the same email as the file. On their computer, they choose **I have a family setup file** on the Welcome screen, check the details, and give their own permission.

**Turning the background check on or off later.** Open **Settings** and use **Turn on** or **Turn off** under **Run automatically**. It catches up if your computer was asleep or off at the usual time.

## 4. Your first run

1. **Practice first (sends nothing).** Free My ID starts in practice mode. It looks for your details on each site and shows what it found and what it *would* do.
2. **Look at the results** on the Home page.
3. **Turn on real requests (one time only).** Open **Settings** and click **Start sending real requests**. Free My ID explains what will happen and asks you to confirm.
4. **Let it work.** You can close the window. If a site needs you, a card appears on the Home page with one big button. Do the step, then click **I did it**.

## For helpers: the command line

Helpers and developers can do the same things in a terminal. Normal users can skip this part.

- `freemyid setup` opens the setup wizard. `freemyid setup --no-web` asks typed questions instead.
- `freemyid profile export Mom mom.freemyid-profile` writes a password-protected family file.
- `freemyid schedule install | status | remove` manages the background check.
- `freemyid run --dry-run` is a practice run. `freemyid config enable-submissions` turns on real requests. `freemyid run` does a real run. Add `-p Mom` for one person or `-b spokeo` for one site.
- `freemyid status`, `freemyid dashboard`, `freemyid todo list`, `freemyid outbox list`, `freemyid report`.
- Full command reference: [CLI.md](CLI.md).
- Mail server details for the presets: Gmail `imap.gmail.com` and `smtp.gmail.com`; Proton Bridge `127.0.0.1` ports 1143 (IMAP) and 1025 (SMTP) with STARTTLS.

## 5. What each status means

The dashboard shows a colored label for each site.

| You'll see | It means | What you do |
|---|---|---|
| **Not checked yet** | Free My ID hasn't searched this site yet. | Nothing. |
| **Not found** | No listing for you right now. | Nothing. Free My ID checks again later. |
| **Your details are listed** | Your listing is there. A request will be sent on the next real run. | Nothing, unless it also says "needs you". |
| **Asked** | The request was sent. | Nothing. Some sites finish in a few days. Where a privacy law applies, a site has up to 45 days to answer, and up to 90 if it tells you it needs more time. |
| **Waiting for the site to reply** | The site sent a confirmation email, or will. Free My ID clicks the link when it arrives. | Nothing, unless a to-do appears. |
| **Site confirmed** | The site accepted the request. Free My ID is waiting for the listing to disappear. | Nothing. |
| **Not listed now** | Free My ID searched again and your listing was not on this site. That is for this one site only. | Nothing. Free My ID keeps checking. |
| **Reappeared** | A listing that had gone came back. A new request will be filed. | Nothing. This is normal; see [section 9](#9-when-listings-come-back). |
| **Needs you** | Free My ID can't go further without a person. | See [section 6](#6-needs-you-items). |
| **Error** | Something went wrong, often because the site changed its page. | Nothing right away. Free My ID tries again on the next run. If it stays stuck, tell whoever set up Free My ID for you. |

**When a site ignores you.** If a site hasn't acted after its usual processing time plus 15 days, Free My ID escalates one step at a time:

1. It sends the request again.
2. It sends a follow-up email citing your state's privacy law, if your state has one.
3. It drafts a firmer letter. **This always waits for your approval.**
4. It gives you a to-do with links to file a complaint with your state, if you want to.

## 6. "Needs you" items

See these in the dashboard's to-do list, or with `freemyid todo list`. When you've handled one, click **Done** (or run `freemyid todo done <id>`). If you run Free My ID in the background, you'll get a desktop notification such as "Mom: 2 sites need you". Notifications never include personal details.

### "Prove you're human" checks (CAPTCHA)

Free My ID **never** tries to get around these. It opens the page for you. Tick the box or pick the pictures, then let Free My ID continue (click **Done**). If it was a background run, open the dashboard and click **Resolve** on the to-do to pick up where it stopped.

### Possible match: "Is this you?"

Free My ID found a listing that *might* be you: the name matches, but only one other detail does. Look at the screenshot and confirm or reject it. <!-- TODO verify: confirm/reject controls for REVIEW_MATCH --> Free My ID only sends requests on its own for listings it's sure about.

### ID requests and permission needed

Some sites ask for a photo ID, an account, or a phone number. If you left that permission off (the default), Free My ID stops and asks. You can:

- **Skip that site.** Often the best choice. Many people decide a site isn't worth an ID.
- **Do it yourself** using the site's steps shown in the to-do. Cover your ID number and photo if the site allows it.
- **Turn the permission on** for that person, if you're comfortable with it: open **Settings**, select the person, tick the permission, and click **Save**.

### Letters to mail

Some companies only accept requests by post. Free My ID writes the letter for you. Print it, sign it, put it in an envelope with the address shown, and mail it. Then mark the to-do done. Keep a copy, and consider sending it with tracking.

### Phone calls

A few sites only take requests by phone. Free My ID gives you a short script listing what to say and which details the site already shows (only give those). Note the date and any reference number, then mark the to-do done. Don't give a phone number or other details the site doesn't already have.

### Sites that need an account

Free My ID never creates accounts with passwords on its own. The to-do explains the site's steps so you can decide whether to do it.

### Unexpected page

The site showed something Free My ID didn't recognize, for example a redesigned form. Open the link in the to-do and follow the site's steps yourself, or mark it done to have Free My ID try again next run.

## 7. Approving emails

Many sites take removal requests by email. In **Approve each email** mode (the default), Free My ID writes each email but **doesn't send it until you approve it**.

- On the Home page, open **Emails**, read the email, and click **Approve and send**.

Each email comes from your removal mailbox and includes only the details that site already shows about you. A copy of every sent email is kept in your encrypted records.

**Firmer letters always wait for your approval,** even if you switch to automatic mode.

## 8. If you live in California: DROP

California's **Delete Act** created **DROP** (Delete Request and Opt-out Platform), a free, official state website run by the California privacy agency. One request there goes to every data broker registered in California, and registered brokers must keep checking it and deleting your data.

Free My ID can't file DROP for you, because DROP needs an account and identity checks, which Free My ID never does on its own. If your profile says you live in California, Free My ID gives you a to-do with a link to the official DROP site. Do it once. It covers many companies that Free My ID's own list doesn't reach.

- Use only the official government site. Ignore companies that charge to "file DROP for you".
- Free My ID still handles the people-search sites directly. DROP and Free My ID work well together.

<!-- TODO verify: DROP URL, agency name, and broker processing schedule against the `ca_drop` registry entry and brokers/state_laws.yaml -->

## 9. When listings come back

It's normal, and it doesn't mean Free My ID failed. Sites buy fresh data from public records and from one another.

What Free My ID does:

- It re-checks each site on a schedule: about weekly while something is in progress, and every month or so after a removal (each site has its own interval).
- When a listing comes back, it's marked **Reappeared**. A new request is filed on the next real run, and the follow-up steps start over.
- Some sites are copies of a bigger site. Free My ID sends the request to the parent site and re-checks the copies.

What you can do:

- Keep the background check on (see Settings).
- Handle "needs you" items when they appear. That's where most stuck removals are.
- Helpers can run `freemyid report`, or use **Download report** on a person's page, to save a record of what was asked and when.

## 10. Your privacy

- **Free My ID never asks for your Social Security number or bank or card details, and never charges you.** Full list: the website's Is it safe? page (https://freemyid.org/safety/).
- **Everything stays on your computer.** Free My ID has no account, no cloud and no tracking.
- **Your information is encrypted.** The database and screenshots are encrypted, and the key is kept in your computer's secure password store.
- **Free My ID talks only to the removal sites themselves and your removal mailbox.** It's blocked from contacting anything else.
- **Sites get as little as possible:** only what they already show about you, plus your removal email address. Never your birth date, relatives, or personal email. If a site asks for an age, it gets only the age its own listing already shows, never one worked out from your birth year.
- **To delete everything about a person:** `freemyid profile remove <name>`. This removes their profile, screenshots, records and saved mailbox password.

## 11. Questions

**Does this change what Facebook does?** No. Free My ID works on people-search sites. It does not change what Facebook itself does with your account. Facebook has its own privacy settings.

**I posted "I do not consent". Did that work?** You were right to object. On its own that post does not reach the sites that sell your details. Free My ID sends your wish to them directly.

**Will this remove me from Google?** No. Once a site has removed your listing, Google drops the page on its own schedule, which can take a while. Free My ID doesn't contact Google. Google's "Refresh outdated content" tool can speed it up.

**How long does it take?** Some sites remove you within a few days. Where a privacy law applies, a site has up to 45 days to answer, and can take up to 90 if it tells you. Free My ID follows up if a site is slow.

**Does it cost anything?** Free My ID is free in this family version. It never pays a site, and it never uses paid removal services.

**I got an email from a site asking me to do something. Should I?** Check the dashboard first. If Free My ID already handled it, you'll see it there. Never send ID or payment to a site because of an email alone.

**Something looks wrong.** Run `freemyid status` and contact whoever set up Free My ID for you. Free My ID strips personal details out of its logs, but look over a log before sharing it anyway.
