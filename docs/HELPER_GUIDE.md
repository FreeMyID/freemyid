# Free My ID: helper's guide

*For the family member setting Free My ID up for someone else, in person or over the phone. Print this and keep it by the computer. Allow about half an hour the first time.*

**What it does, in one sentence:** Free My ID asks people-search sites (websites that publish names, addresses and phone numbers, also called data brokers) to delete a person's details, in the written form those sites have to answer, and then keeps checking.

**What it doesn't do:** it doesn't change what Facebook itself does with their account, and it can't remove news stories or government records. Some sites take weeks, and some list people again later. That's why it keeps checking.

---

## 1. Before you start

**Have ready:** the person's full name (and any maiden or earlier names), the towns they've lived in over the last 10 years, and, optionally, their year of birth, phone number and relatives' names. These details only help Free My ID recognise the right listing.

**A separate email address for replies (optional).** Sites reply by email, and some send a "click to confirm" link.

- **Worth it if** you want Free My ID to send email requests and read the replies on its own. Make a fresh, free **Gmail** address just for this (for example `yourname.removals@gmail.com`; pick your own). It keeps removal mail out of their everyday inbox.
  - Gmail also needs an **app password**: Google Account → **Security** → turn on **2-Step Verification** → search **App passwords** → create one. The setup screen shows these steps.
  - **Outlook.com and Hotmail can't be used** for this; Microsoft doesn't allow it. Yahoo, iCloud and Proton Mail (with the Proton Bridge app) also work.
- **Skip it if** you'd rather keep it simple. Choose **"Skip, I'll do these by hand"** on that screen. Free My ID then prepares each message and opens their email program, and they press **Send** themselves.

## 2. Download and install

1. On the Windows 10 or 11 computer, open the Free My ID website and click **Download**. Download only from the official site or the GitHub releases page.
2. Open **FreeMyIDSetup.exe**.
3. Windows may show a blue box: **"Windows protected your PC."** This happens because Free My ID is free and hasn't bought a publisher certificate yet. Click the small words **More info**, check that the app is **FreeMyIDSetup.exe**, then click **Run anyway**.
   [screenshot: SmartScreen "Windows protected your PC" with "More info" highlighted]
   [screenshot: SmartScreen after "More info", with "Run anyway" highlighted]
4. Click **Install**. No administrator password is needed. Free My ID opens by itself.
   [screenshot: installer finished, with "Start Free My ID now" ticked]

## 3. The six setup screens

A row of dots at the top shows **Step 1 of 6** and so on.

**1 · Welcome. Who is this for?**
Reads the short agreement, then asks who the setup is for:
- *"I am this person…"*: they're setting it up for themselves (you're just helping with the mouse).
- *"I am helping an adult who gave me signed written permission…"*: you're acting for them. Click **Open the form to print**, have them sign it, then attach a photo or scan (now or later).
- *Parent or guardian of someone under 18*.

Type the full name to sign, tick **"I have read this and I agree"**, and continue.
[screenshot: welcome screen with trust panel and "Who is this for?"]

**2 · What is the person's name?**
First, middle and last name, maiden or earlier names, nicknames, and a short **on-screen name** such as "Mom". The on-screen name stays on this computer only.

**3 · Where do they live?**
**City and state are enough** (2-letter state, like TX). Open **"Have they lived anywhere else in the last 10 years?"** to add old towns.

**4 · A few details to recognise them**
All optional: year of birth, phone number, the email they use, and relatives. These are used **only to tell them apart from people with the same name. They're never sent to anyone.**

**5 · A separate email address for replies**
Choose the mail service (Gmail works best) and paste the app password, or pick **Skip, I'll do these by hand** (see section 1).
[screenshot: mailbox choices]

**6 · Run automatically?**
Leave **"Yes, keep checking for me automatically"** ticked. This adds one small Free My ID task to Windows that runs once a day, even when the window is closed, and catches up if the computer was off. It stays quiet unless it needs them.

**Practice mode first.** Free My ID starts in **practice mode**: it looks for listings but sends nothing. When you've looked over what it found together, go to **Settings → Practice mode is on → turn on real requests**, and confirm with **"Yes, start sending real requests."** Requests that have already been sent can't be taken back.
[screenshot: Settings with the practice-mode card]

## 4. What they'll see afterwards

- **A status page** in plain words. Each site shows: *your details are listed*, *asked*, *waiting for the site to reply*, *site confirmed* or *not listed now*.
- **"Needs you" cards.** Some sites need a real person. A card appears with one big button.
  - **"Fill it in for me":** Free My ID opens the site's removal page in a window and fills in the boxes. **If the site asks "I'm not a robot", the person ticks that box and presses Submit themselves. Free My ID never does those steps.**
  - **"Do it with me":** the site opens in their own browser with numbered steps and a **Copy** button for each box. When they're finished they press **"I did it"**, or **"I couldn't"** if they get stuck.
  [screenshot: a "Needs you" card with the "Fill it in for me" button]
- **Emails waiting for approval** (if a mailbox is set up). Nothing is sent until they press OK.
- **Small desktop notices** such as "Mom: 2 sites need you". These never include personal details.
- **Receipts:** a printable report of every site, when it was asked, what it replied and when it was checked again.

**Tell them:** "If it ever asks for your Social Security number, a bank card or a password for Facebook, it isn't Free My ID. Call me."

## 5. Pause, uninstall, delete everything

- **Pause the daily checks:** **Settings → Run automatically → Turn off.** Turn it back on the same way.
- **Stop sending real requests:** switch back to practice mode in **Settings** at any time.
- **Close the app:** **Settings → Close Free My ID.**
- **Uninstall:** Windows **Settings → Apps** → **Free My ID** → **Uninstall**. It asks whether to **delete the saved records too**. Answer **Yes** to remove everything Free My ID stored on this computer (records, screenshots and saved mailbox password). The daily task is removed either way.
- **Remove just one person** (when several are set up): see "For helpers" in the User Guide (`freemyid profile remove <name>`).

## 6. What Free My ID will never ask for

- Social Security number
- Bank account, credit or debit card details
- A photo of an ID card
- Their Facebook, Google or everyday email password (only a separate app password for the optional removal mailbox)
- Money: the app is free

It also **never** creates accounts, uploads ID or gives out a phone number unless you've explicitly allowed it for that person. It never solves "are you a robot?" checks.

*Free My ID is free, open-source software that runs on this computer only. It isn't a government service and isn't connected to Facebook/Meta or any data broker.*
