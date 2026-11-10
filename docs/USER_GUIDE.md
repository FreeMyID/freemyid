<!-- Status: copy aligned with docs/POSITIONING.md and the 6-screen plan; resolve TODO verify markers as features land -->

# Free My ID User Guide

This guide is for the person using Free My ID. You don't need to be technical. If you only want the short version, read `FAMILY_QUICK_START.md` first and come back here when you have a question.

> Free My ID works today. Some parts are still being checked. Anything marked **(still being checked)** in this guide may change.

## Contents

1. [What Free My ID does (and doesn't)](#1-what-free-my-id-does-and-doesnt)
2. [Before you start: a separate email address for removals](#2-before-you-start-a-separate-email-address-for-removals)
3. [Setting up](#3-setting-up)
4. [Your first run](#4-your-first-run)
   - [The app window in version 0.3](#the-app-window-in-version-03)
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
5. Click **Test that it works**.

**(still being checked)** Google may change whether new personal accounts can make app passwords. If you can't find **App passwords**, choose **Skip, I'll do these by hand** for now.
<!-- TODO verify: Google still offers app passwords for new personal accounts; Gmail IMAP enabled by default -->

### Outlook / Hotmail

Outlook.com and Hotmail **can't be used** for the reply mailbox: Microsoft no longer lets programs sign in to those mailboxes with a password, and the setup wizard says so on the mailbox screen. Use a new Gmail address instead (or Yahoo, iCloud, or Proton Mail with Bridge). You can still send the "do it with me" letters from Outlook in your web browser: the app gives you an Outlook button for that.

<!-- source: src/freemyid/wizard/ui.py ("Not possible", "Why Outlook.com does not work"), wizard/flows.py presets skip Outlook.com; assisted letters link outlook.live.com compose (engine/outbox.py) -->

### Proton Mail (with Proton Mail Bridge)

Proton encrypts your mail, so other programs can only reach it through the free **Proton Mail Bridge** app on your computer. Bridge requires a paid Proton plan **(still being checked)**. <!-- TODO verify -->

1. Create a new Proton address (or add one to your account).
2. Install **Proton Mail Bridge** from Proton's website and sign in.
3. In Bridge, open the mailbox settings and copy the **Bridge password** it shows you. This is different from your Proton password.
4. In the Free My ID setup wizard, choose **Proton Bridge**. The settings are filled in for you (server `127.0.0.1`, ports 1143 and 1025). Paste the Bridge password.
5. Click **Test that it works**.
6. The first time, Free My ID then shows you the mail app's **security code** (a long row of letters and numbers) and asks whether you trust it. Your Bridge password is not sent until you answer. Only click **Yes** if the code matches the certificate in Bridge: the steps to check it are in [Proton Mail with Bridge](user/mail-proton.md) (a helper can do this with you). Installing Bridge yourself is not enough on its own. If you can't check it, or it doesn't match, click **No** and ask someone you trust. After **Yes**, Free My ID finishes the test by itself.

Free My ID remembers that security code. If it ever changes, Free My ID won't sign in and tells you instead. That usually just means Bridge was reinstalled or reset: run the setup's mailbox step again to trust the new code. If you didn't change anything, don't trust it, and ask someone you trust to check your computer.

This trust step only works for a mail app on your own computer. For Gmail, Yahoo, iCloud and other providers, Free My ID always uses the normal security check and never asks you.

Bridge has to be running whenever Free My ID checks mail, including scheduled background checks.

## 3. Setting up

On Windows you do not need a terminal. Double-click the **Free My ID** icon on your Desktop (or find it in the Start Menu). Free My ID opens in its own window. It runs only on your computer, and your answers are saved only on this computer. Two things do leave your computer before any removal request:

- **The mailbox test.** When you click **Test that it works**, Free My ID signs in to your email company with the removal address and password you typed. That goes only to your email company.
- **Searching for your listings.** In practice mode, Free My ID searches the people-search sites for your name and city to find your listings, the same as typing them into the site's search box yourself.

**No removal request is sent until you choose to start requests.**

The setup has **six screens**. Each asks one thing. Press **Next** to go on, or **Back** if you change your mind.

1. **Welcome.** Choose one of these:
   - **This is for me.**
   - **This is for my child** (I am their parent or guardian, and they are under 18).
   - **This is for an adult who asked me to help.** That adult must sign a short permission form. Free My ID prints one for you to get signed and attach.

   Type your full name to sign, and tick the box. Free My ID won't work on anyone without this step.
2. **Name.** Full name, plus any nicknames or maiden or earlier names. Example: *Jane Q Testperson*, nickname *Janie*, earlier name *Jane Q Example*.
3. **Address.** The city and state where you live now (for example *Springfield, IL*). Add past cities if you like. They help Free My ID recognize *your* listing among people with the same name.
4. **A few details.** Birth year, a phone number and an email. These are **only used on this computer to tell you apart from other people with your name.** Birth year and relatives are never sent to a site. If a site's form asks for an age, it gets only the age that site's own listing already shows, never one worked out from your birth year. That is how the current version works. A phone number goes to a site only if you switch that on.
5. **Email for removals.** The separate mailbox from [section 2](#2-before-you-start-a-separate-email-address-for-removals). Pick your email company and follow the short steps on screen, **or** choose **Skip, I'll do these by hand**. Skipping is fine. Permissions for ID, accounts and phone numbers stay **off** unless you turn them on later in Settings.
6. **Run automatically?** Leave the box ticked so Free My ID keeps checking by itself. Click **Finish**.

**Setting up a family member.** Someone can fill in a profile for a parent and send it as a password-protected file. Tell the parent the password **by phone**, not in the same email as the file. On their computer, they choose **I have a family setup file** on the Welcome screen, check the details, and give their own permission.

**Turning the background check on or off later.** Open **Settings** and use **Turn on** or **Turn off** under **Run automatically**. It catches up if your computer was asleep or off at the usual time.

## 4. Your first run

Version **0.3.1** opens on **Today**. You see one card. The rest of the list is behind **More: safety steps and details**. The buttons, in the app's own words, are in [The app window in version 0.3](#the-app-window-in-version-03).

1. **Practice first.** Free My ID starts in practice mode. It looks for your listings. No removal requests go out until you say so.
2. **Look at Today.** One card is the next step.
3. **Turn on real requests (one time only).** Open **Settings** and click **Start sending real requests**. The next screen asks **Yes, start sending real requests** or **No, stay in practice mode**.
4. **Let it work.** You can close the window. If a site needs you, a card appears on Today.

## For helpers: the command line

Helpers and developers can do the same things in a terminal. Normal users can skip this part.

- `freemyid setup` opens the setup wizard. `freemyid setup --no-web` asks typed questions instead.
- `freemyid profile export Mom mom.freemyid-profile` writes a password-protected family file.
- `freemyid schedule install | status | remove` manages the background check.
- `freemyid run --dry-run` is a practice run. `freemyid config enable-submissions` turns on real requests. `freemyid run` does a real run. Add `-p Mom` for one person or `-b spokeo` for one site.
- `freemyid status`, `freemyid dashboard`, `freemyid todo list`, `freemyid outbox list`, `freemyid report`.
- Full command reference: [CLI.md](CLI.md).
- Mail server details for the presets: Gmail `imap.gmail.com` and `smtp.gmail.com`; Proton Bridge `127.0.0.1` ports 1143 (IMAP) and 1025 (SMTP) with STARTTLS.

## The app window in version 0.3

This page is for the person using Free My ID on their own computer. You do not need to be technical. A family member can read it with you.

The name in the examples is **Jane Q Testperson**, who lives in **Springfield, IL**. That person is made up. Use your own name in the app.

This matches Free My ID **0.3.1**, the app this guide was checked against. The window is the 0.3 app: one next step on **Today**, the rest behind **More**.

<!-- version: src/freemyid/__init__.py:2 -->

## Today: one card, then More

Open Free My ID. The top of the window has four words:

- **Today**
- **Protect yourself**
- **Emails**
- **Settings**

**Today** is the first page. It shows **one** big card. That card is the next thing for you. It does not list every site on this page.

Above the card you may see the small words **Next for you**.

<!-- nav: src/freemyid/wizard/ui.py:43-44 -->
<!-- one card: src/freemyid/wizard/dashboard.py:225-278 -->
<!-- kicker "Next for you": src/freemyid/wizard/dashboard.py:220-222 -->

Under the card is one line of numbers. It looks like this:

**3 requests sent, 1 confirmed, 2 need you**

The numbers change. Here is what the words mean:

- **requests sent** means a removal was requested. The app's own word on a person's site list is **asked**. On the printable page the words are **We asked them to delete it**.
- **confirmed** on this line counts two good outcomes together: the site confirmed, or the site no longer lists you. It does not mean every site on the internet is done.
- **need you** means a card is waiting for a person.

<!-- progress line: src/freemyid/wizard/dashboard.py:213-217 -->
<!-- "confirmed" on that line includes site confirmed and no longer listed: src/freemyid/wizard/dashboard.py:27-28 -->
<!-- chip "asked" and "site confirmed": src/freemyid/wizard/ui.py:24-31 -->
<!-- printable words: src/freemyid/wizard/views.py:26-37 -->

Under that line you always get a button:

**More: safety steps and details**

If more than one thing is waiting, you also get a button like:

**See the full list (3 waiting)**

The number is how many are waiting. One waiting thing does not show **See the full list**. **More** is still there.

<!-- More and the full list: src/freemyid/wizard/dashboard.py:271-275 -->

A short note under the buttons says a site that deleted you has done that for **that one site only**. Details can come back. That is why Free My ID keeps checking.

<!-- src/freemyid/wizard/dashboard.py:276-277 -->

### What the one card can say

The card is whichever of these comes first.

1. **Emails waiting for your OK.** The heading looks like **2 emails waiting for your OK** (or **1 email**). The words under it say: look at each one, then press Approve. The button on this card is **Look at them**. That opens **Emails**. On the Emails page the buttons are **Approve and send** and **Cancel it**. Press **Approve and send** when you want that request to go out. The screen says "press Approve". The button you actually press is **Approve and send**.

2. **One task**, such as "Is this you?" or a phone call. That task fills the card. Any other tasks stay on **More**.

3. **Free My ID is checking now.** The card says this takes about a minute, and the page updates by itself.

4. **Nothing needs you today.** You can close the window. Free My ID keeps checking and will tell you if that changes.

<!-- email card and "Look at them": src/freemyid/wizard/dashboard.py:250-255 -->
<!-- Emails buttons: src/freemyid/wizard/dashboard.py:471-475 -->
<!-- checking and calm cards: src/freemyid/wizard/dashboard.py:261-269 -->

### Practice mode

At the start, a yellow note can say:

**Practice mode:** Free My ID is looking for your listings, but no removal requests go out until you say so.

The note links to **Change this in Settings**. When you are ready, Settings has **Start sending real requests**. The next screen asks **Yes, start sending real requests** or **No, stay in practice mode**.

While practice mode is on, a "yes, this is me" answer still does not send a removal request. The card says: in practice mode no removal requests go out.

<!-- practice banner: src/freemyid/wizard/dashboard.py:236-239 -->
<!-- Settings buttons: src/freemyid/wizard/dashboard.py:509-520 -->
<!-- confirm screen: src/freemyid/wizard/dashboard.py:479-495 -->

### The More page

**More: safety steps and details** opens a page titled **Everything**.

At the top is **Back to Today**.

Then **Waiting for you**, with every card that was not on Today. If the list is empty, it says **Nothing is waiting for you.**

Then **Protect yourself**, with **Steps for** the person's name, and a count of how many safety steps are done. If Google or Bing still needs you, you also see a line like **Google and Bing: 2 steps to do**. That line is gone when both of those steps are done.

Then links for each person: **All the details for** the name, and **What we did for** the name. **Add a person** is there too.

The page says: Free My ID does not change anything on Facebook or Google.

<!-- More page: src/freemyid/wizard/dashboard.py:281-318 -->
<!-- Google and Bing count on More: src/freemyid/wizard/dashboard.py:304-307 and src/freemyid/wizard/server.py:259 -->

## "Is this you?"

Sometimes Free My ID finds a page that **might** be you. The name matches, but that is not enough to be sure. Today shows one card and asks you.

For a person whose short name is Jane, the title looks like:

**Is this Jane? (the site name)**

If the hit was a phone number Jane asked to remove, the title looks like **Is this Jane's phone number? (the site name)**. The same idea is used for an email address.

Jane Q Testperson in Springfield, IL is only the example. Your card uses your short name and the real site name.

<!-- titles: src/freemyid/engine/runner.py:990-1005 -->

The card says why it is only a possible match. If the extra detail is the city, it says the name is the same, and so is the city. It also says: open the page first if you want to look. Only you can say whether it is you.

<!-- why text and "only you": src/freemyid/wizard/dashboard.py:112-126 -->

### The buttons

The app uses these words. They match the labels below.

- **Open the page** — look at the listing first. This button is there when the card has a web page to open. After it opens, the app says: **Opened in your web browser. Come back here when you are finished.**
- **Yes, this is me**
- **No, this is not me**

There is no other yes or no button.

<!-- button labels: src/freemyid/wizard/dashboard.py:121-123 -->
<!-- opened message: src/freemyid/wizard/server.py:52 -->

### What "Yes, this is me" does

Press this only if the page is you.

The card says:

**If you press Yes:** Free My ID will ask this site to take the listing down on its next check. Free My ID may send the request by itself, or ask you to approve an email or do a step, depending on the site and your settings. If a site wants a photo ID, an account or your phone number, Free My ID stops and asks, unless you allowed that in Settings. In practice mode no removal requests go out.

What that means, in order:

1. Free My ID marks the listing as you. That is **your** confirmation. It is not the same as **site confirmed**, which comes later, if the site agrees.
2. The question closes. It leaves Today.
3. On the next check, Free My ID requests removal, if your settings allow it. The thank-you line says: **Thank you. Free My ID will ask that site to remove the listing on its next check, if your settings allow it.**
4. The request might go out by itself, or you might be asked to approve an email, or to do one step on the site.
5. A photo ID, a new account, or your phone number is not shared unless you already allowed that in **Settings**.
6. In practice mode, no removal request goes out.

Your answer stays if Free My ID looks at that site again. Pressing **No, this is not me** afterwards does not undo a yes.

<!-- card text: src/freemyid/wizard/dashboard.py:127-131 -->
<!-- yes marks the listing confirmed as you, and schedules another check: src/freemyid/engine/handoff.py:157-175 and src/freemyid/wizard/server.py:517-548 -->
<!-- thank-you line: src/freemyid/wizard/server.py:60-61 -->
<!-- a later search keeps your yes: src/freemyid/engine/runner.py:169-173 -->

### What "No, this is not me" does

Press this if the page is someone else.

The card tells you the result in its own sentence. In plain words: Free My ID will not request removal for this listing, and it will not ask you about this listing again.

Then:

1. Free My ID marks the listing as not you.
2. The question closes.
3. The thank-you line tells you no request will go out for that listing.
4. A later search keeps your no. The app will not ask about that same listing again.

<!-- No result: src/freemyid/wizard/dashboard.py:132-133 and src/freemyid/engine/handoff.py:167-169 -->
<!-- thank-you is review_no: src/freemyid/wizard/server.py:62 -->
<!-- a later search keeps your no: src/freemyid/engine/runner.py:172-173 -->

### If you press twice

The first answer is the one that counts. A second press does not flip it. The app says:

**That question was already answered. Nothing was changed.**

If you are not sure, press **Open the page** before you press yes or no. There is no button on the card to take an answer back. If you already pressed the wrong one, ask the person who set Free My ID up for you before the next check.

<!-- second press: src/freemyid/wizard/server.py:539-547 -->

## A phone call, and the optional note

A few sites only take a request by phone. The card title looks like **Call (the site) to remove Jane**. The card shows a short script. Read it before you dial.

The script tells you to say you are calling to have your information removed, and to opt out of sale or sharing. If they ask who you are, give only what their listing already shows: your name, city and state if those are on the listing, the age the listing shows if it shows one, the listing page, and the removal email if you set one up.

The script tells you **not** to give your date of birth, Social Security number, payment details, or relatives' names. If sharing a phone number is turned off, it also tells you not to give a phone number. It tells you to ask for a reference number, to write down the date, and never to agree to pay.

<!-- phone card is built from the script: src/freemyid/submitters/assisted.py:133-142 -->
<!-- script text: src/freemyid/templates/phone_script.txt.j2:1-22 -->
<!-- the script is the hint under the title: src/freemyid/wizard/dashboard.py:209-210 -->

You do the call yourself. Free My ID does not place the call.

### The note

Under the script is a box you may leave empty. The label is:

**A short note about the call (optional)**

Under the box:

**Only kept on this computer, as your own record. Please do not write passwords or ID numbers.**

The note can be up to 1000 characters. A reference number and the date are enough. You do not have to type anything.

The note is stored on this computer with your other records. It is your copy of what happened. It is not typed into the phone call for you.

<!-- label, box, and hint: src/freemyid/wizard/dashboard.py:188-192 -->
<!-- length and save: src/freemyid/wizard/proof_input.py:15 and src/freemyid/wizard/proof_input.py:46-56 -->
<!-- a blank note is fine; a save problem does not block the button: src/freemyid/wizard/server.py:373-383 -->

### The button on a phone card

The button is **I finished it**.

If the card has a web page, **Open the page** is there too. A phone card does not show **I couldn't**.

Press **I finished it** after the call, even if the note box is empty. The app says:

**Thank you. Free My ID will carry on.**

That marks the call as done. When the site had a listing to remove, Free My ID records that a removal was requested (the site list shows **asked**). **Site confirmed** is a later step, after the site agrees or the listing is gone. It is not what this button means.

<!-- "I finished it" because the phone task has a resume token: src/freemyid/wizard/dashboard.py:185-186 and src/freemyid/submitters/assisted.py:142 -->
<!-- thank-you: src/freemyid/wizard/server.py:50 and src/freemyid/wizard/server.py:550-567 -->
<!-- phone calls count as requested (asked), not as site confirmed: src/freemyid/engine/handoff.py:193-201 and src/freemyid/engine/handoff.py:224-254 -->
<!-- "asked" vs "site confirmed": src/freemyid/wizard/ui.py:27-28 -->

## Google and Bing

Free My ID does not search Google or Bing for you. Their rules do not allow an automatic search. The app opens their own official page. You do the steps there.

This does not change your Google or Facebook account. It is a separate step, after a people-search site is asked to take a page down.

### Where to find the steps

1. On **More**, look for **Google and Bing: 2 steps to do** (the number can be 1). That link is for one person, such as Jane.
2. Or open **Protect yourself** from the top of the window.

The first block on **Protect yourself** is titled **Google and Bing**. The words under the title are:

Google and Bing can show pages about you, even after a people-search site removes your listing. Free My ID does not search Google or Bing for you: their rules do not allow automatic searches. We open their own official page, and you do the steps there. When you have finished, tick "I did this" so we remember the date.

<!-- intro and the top block: src/freemyid/engine/search_engines.py:33-36 and src/freemyid/wizard/views.py:222-228 -->

Two short cards sit in that block.

**Google:** **Ask Google to hide your phone, address or email from search results**

The line under it says: Google's free tool watches for your phone number, home address and email, and lets you ask Google to stop showing those results.

**Bing:** **Ask Bing to drop old copies of pages that were removed**

The line under it says: After a people-search site removes your page, Bing can keep showing the old copy for a while. Bing's form asks Bing to look at the page again and drop the old copy.

<!-- the two steps and those sentences: src/freemyid/engine/search_engines.py:48-61 -->
<!-- titles come from the checklist: brokers/checklists.yaml:319-320 and brokers/checklists.yaml:342-343 -->
<!-- how the card is drawn: src/freemyid/wizard/views.py:229-247 -->

### Buttons on those two cards

Each card has:

- **Open the page for me** — opens the official page in your browser, and the app remembers that you opened it.
- **Or open the link yourself** — opens the same kind of page, but you opened it. The status can stay **Not done yet** until you press **I did this**.
- **I did this** — press this when you have finished. The status becomes **Done.** and shows **Done on** a date.
- After that, the last button changes to **I have not done this** if you need to undo the tick.

Status words you may see:

- **Not done yet.**
- **You opened the page. Tick "I did this" when you have finished.** Then **Opened on** a date, if you used **Open the page for me**.
- **Done.**

Bing only: if a people-search site removes a listing after you already ticked Bing, the card can ask you to do Bing again. The words are: **A site removed your listing since you last did this. Please do it again so the search engine drops the old page.** The button goes back to **I did this**. Google does not ask you to repeat its step for that reason. Google's tool keeps watching on its own.

When both are done, the **Google and Bing:** line on **More** goes away. If Bing asks you to do it again, that line can come back.

<!-- buttons and status lines: src/freemyid/wizard/views.py:231-247 and src/freemyid/engine/search_engines.py:64-71 -->
<!-- open records the date; a bad or unknown page is not opened: src/freemyid/engine/search_engines.py:141-157 and src/freemyid/wizard/server.py:309-318 -->
<!-- Bing repeat, Google does not: src/freemyid/engine/search_engines.py:45 and src/freemyid/engine/search_engines.py:54 and src/freemyid/engine/search_engines.py:131-134 -->

### The same two topics, lower on the page

Further down **Protect yourself**, the full list repeats Google and Bing, with the steps written out. You can use either place. **I did this** in either place ticks the same step.

On the longer card the open button says **Open the web page**, not **Open the page for me**. The done button is still **I did this**, and later **I have not done this**.

Those longer cards can also say:

**We could not read this company's own page when we prepared these steps, so some details come from trusted consumer-help sites. This is still a good thing to do. Before you type anything in or call a number, check the address and the phone number on the company's own page.**

Read that note. Then check the address on the company's own page before you type anything.

<!-- full cards and the two button labels: src/freemyid/wizard/views.py:191-219 and src/freemyid/wizard/views.py:265-272 -->
<!-- the caution note, shown because these two are marked partial: src/freemyid/wizard/views.py:185-200 and brokers/checklists.yaml:339 and brokers/checklists.yaml:361 -->

**Google, have these ready:** a Google account, and the name, phone number, home address, and email you want Google to watch for. Cost: free. About 10 minutes to set up, then a few minutes per result.

Steps the longer card lists:

1. Open the web address, or open the Google app and tap your picture, then **Results about you**.
2. Sign in and type the details you want watched (name, address, phone, email).
3. Google lists results that match. Open one and choose **Request to remove**.
4. Type your contact info exactly as it shows on that page when asked.
5. Turn on notifications so Google tells you when new matches appear.
6. Check the status later on the same page. The card lists: in progress, approved, denied, or undone.

The card also says Google hides the result from Search only. The page can stay on the other website, so you still ask that site to remove it. Google rarely removes results from government, school, or news sites.

To undo: in Settings, choose **Remove all personal info** to stop watching and delete what you entered. That is Google's own step, as the card states it.

<!-- Google steps shown on the longer card: brokers/checklists.yaml:319-336 rendered by src/freemyid/wizard/views.py:196-218 -->

**Bing, have these ready:** the web address of the page that was removed (copy it from the Bing result), and a Microsoft, Google, or Facebook account to sign in with. Cost: free. A few minutes per page. Bing can take days or weeks to act.

Steps the longer card lists:

1. First make sure the people-search site has removed your page. Open the page. It should be gone, or it should no longer show you.
2. Open the Bing web address. Bing asks you to sign in with a Microsoft, Google, or Facebook account.
3. Follow the form. Paste the web address of the page, then choose whether you are asking Bing to remove the page or to update its old saved copy (the card calls that the cache).
4. If that is not working, or you do not want to sign in, the card points you to Microsoft's **Report a Concern to Bing** page.
5. Come back to Free My ID and tick **I did this**.

The card also says Bing does not control what other websites publish, and that reporting a concern will not necessarily remove a result. It says Bing will not remove a page that is still live just because you ask, so ask the people-search site first. If you live in Europe or the UK, the card says Microsoft also has a separate form to block results shown for searches on your name.

To undo: the card says there is nothing to undo. Bing only refreshes or drops its own copy. The page is not changed anywhere else.

<!-- Bing steps shown on the longer card: brokers/checklists.yaml:342-359 rendered by src/freemyid/wizard/views.py:196-218 -->

## Larger text

At the top of the window, beside the **Dark** or **Light** button, there is a button labeled:

**Larger text**

Press it. The words in the whole app get bigger, about one quarter larger than before. The button then says:

**Normal text**

Press **Normal text** to go back.

Free My ID remembers the choice on this computer. It stays when you open **Today**, **More**, **Protect yourself**, **Emails**, or **Settings**. You can change it any time.

Your computer's own text size still applies. This button is only for the Free My ID window.

<!-- button starts as "Larger text": src/freemyid/wizard/ui.py:59-61 -->
<!-- it switches to "Normal text", and is remembered: src/freemyid/wizard/static/app.js:123-139 and src/freemyid/wizard/static/theme.js:7-9 -->
<!-- size: src/freemyid/wizard/static/style.css:5 -->

## A few words you will see

| The app says | It means |
|---|---|
| **asked**, or **requests sent** | A removal was requested. The site has not necessarily finished. |
| **site confirmed**, or **They confirmed** on the printable page | The site confirmed the request. |
| **not listed now**, or **No longer listed** | A later check did not find the listing on that one site. |
| **confirmed** on the Today number line | Sites that confirmed, plus sites that no longer list you. |
| **needs you** | A person has to do a step. |

A request can be asked and still come back later. Free My ID keeps checking. When a site says it deleted you, that is for that one site only. Free My ID works on people-search sites. It does not change your Facebook account, and the Google and Bing steps above are ones you do yourself on their pages.

<!-- honesty line used in the app: src/freemyid/wizard/ui.py:19-22 -->

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

See these in the dashboard's to-do list, or with `freemyid todo list`. When you've handled one, click the button on the card, such as **I finished it** or **I did it** (or run `freemyid todo done <id>`). If you run Free My ID in the background, you'll get a desktop notification such as "Mom: 2 sites need you". Notifications never include personal details.

### "Prove you're human" checks (CAPTCHA)

Free My ID **never** tries to get around these. It opens the page for you. Tick the box or pick the pictures, then let Free My ID continue (click **I finished it**). If it was a background run, open the dashboard and click **I finished it** on the to-do to pick up where it stopped.

### Possible match: "Is this you?"

The card, the exact buttons, and what each press does are in ["Is this you?"](#is-this-you). Short version:

- **Open the page** lets you look at the listing first.
- **Yes, this is me** marks the listing as you. On the next check, Free My ID requests removal if your settings allow it. In practice mode, no removal request goes out.
- **No, this is not me** means no removal is requested for that listing, and Free My ID does not ask about it again.

The first answer is the one that counts. A second press says **That question was already answered. Nothing was changed.** There is no button on the card to take an answer back.

### ID requests and permission needed

Some sites ask for a photo ID, an account, or a phone number. If you left that permission off (the default), Free My ID stops and asks. You can:

- **Skip that site.** Often the best choice. Many people decide a site isn't worth an ID.
- **Do it yourself** on the site (click **Open the page**, then follow the site's own steps). Click **I finished it** when you're done. Cover your ID number and photo if the site allows it.
- **Turn the permission on** for that person, if you're comfortable with it: open **Settings**, find the person's name, and under **What Free My ID may do** tick the permission, then click **Save**.

### Letters to mail

Some companies only accept requests by post. Free My ID writes the letter for you. Print it, sign it, put it in an envelope with the address shown, and mail it. Then mark the to-do done. Keep a copy, and consider sending it with tracking.

### Phone calls

A few sites only take requests by phone. The card shows a short script. You make the call. Free My ID does not place it. The full script rules and the note box are in [A phone call, and the optional note](#a-phone-call-and-the-optional-note).

Under the script, the box is labeled **A short note about the call (optional)**. You may leave it empty. It stays on this computer. Do not write passwords or ID numbers. The button is **I finished it**.

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

**(still being checked)** The DROP details above may change; the official California site is always right.
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
- **Sites get as little as possible:** only what they already show about you, plus your removal email address. Never your birth date, relatives, or personal email. From version 0.3, if a site asks for an age, it gets only the age its own listing already shows, never one worked out from your birth year (version 0.2.0 can still send an age worked out from your birth year).
- **To delete everything about a person:** `freemyid profile remove <name>`. This removes their profile, screenshots, records and saved mailbox password.

## 11. Questions

**Does this change what Facebook does?** No. Free My ID works on people-search sites. It does not change what Facebook itself does with your account. Facebook has its own privacy settings.

**I posted "I do not consent". Did that work?** You were right to object. On its own that post does not reach the sites that sell your details. Free My ID sends your wish to them directly.

**Will this remove me from Google?** No. Once a site has removed your listing, Google drops the page on its own schedule, which can take a while. Free My ID doesn't contact Google. Google's "Refresh outdated content" tool can speed it up.

**How long does it take?** Some sites remove you within a few days. Where a privacy law applies, a site has up to 45 days to answer, and can take up to 90 if it tells you. Free My ID follows up if a site is slow.

**Does it cost anything?** Free My ID is free in this family version. It never pays a site, and it never uses paid removal services.

**I got an email from a site asking me to do something. Should I?** Check the dashboard first. If Free My ID already handled it, you'll see it there. Never send ID or payment to a site because of an email alone.

**Something looks wrong.** Run `freemyid status` and contact whoever set up Free My ID for you. Free My ID strips personal details out of its logs, but look over a log before sharing it anyway.
