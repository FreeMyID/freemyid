# Set up Proton Mail for Free My ID

Proton Mail works through a free helper app called **Proton Mail Bridge**.
This page covers the Free My ID email screen, including the "security code"
question that appears the first time.

Example used below: Jane Q Testperson, Springfield IL,
`jane.testperson@proton.example` (a made-up address).

## Before you start

- Free My ID uses a separate email address to send deletion requests and click
  confirmation links (`src/freemyid/wizard/ui.py:389`).
- Proton needs the free Proton Mail Bridge app. Install it from
  `proton.me/mail/bridge` and sign in. It must be running whenever Free My ID
  checks mail (`src/freemyid/wizard/ui.py:231-232`).
- You can skip all of this by choosing "Skip, I'll do these by hand". Free My ID
  then prepares each message and opens your email, and you press Send
  (`ui.py:204-205`).

## Step 1: Get your Bridge details

Bridge shows a username and a password made just for programs. Copy them
(`ui.py:233`). This is not your normal Proton password
(`src/freemyid/wizard/draft.py:386`).

Before going on, make sure Bridge says it is running
(`draft.py:490-492`).

## Step 2: Fill in the Free My ID screen

1. Pick **Proton Mail (needs the Proton Bridge app)** (`ui.py:201`).
2. **Email address**: your Proton address (`ui.py:362`).
3. **Bridge username**: the username Bridge showed you (`ui.py:365`). If you
   leave it empty, Free My ID uses your email address instead (`draft.py:358`).
4. **App password**: paste the Bridge password (`ui.py:363`).
5. Leave the server settings alone. They point to Bridge on your own computer
   (`127.0.0.1`, ports 1143 and 1025) (`draft.py:76-77`).

## Step 3: Test it, and answer the security-code question

1. Press **Test that it works** (`ui.py:380`).
2. The first time, a box appears. Free My ID has not sent your password yet. It
   asks you to approve Bridge's security code first
   (`draft.py:417-419`, `draft.py:430-431`).
3. The box says: "Free My ID found your mail app on this computer. Please check
   that the code below matches the one in Proton Mail Bridge." It shows a code
   and asks "Do you trust this code?" (`src/freemyid/wizard/server.py:721-725`).
4. Open Proton Mail Bridge and look for its security code or certificate details.
   If the two match, press **Yes** (`ui.py:384`).
   Free My ID answers "Saved. Testing again..." and tests again
   (`server.py:738`).
5. If they do not match, or you are not sure, press **No** (`ui.py:385`).
   You will see "Not trusted. Nothing was saved and no password was sent."
   (`server.py:733-734`).
6. When the test works you see "Connection works. Free My ID can read and send
   from this mailbox." (`draft.py:484`). Press **Next** (`ui.py:409`).

You must approve the code before you can continue. If you try to press Next
first, you see: "Please press "Test that it works" and approve the security code
first." (`draft.py:392-393`).

I am not sure exactly where Bridge shows its code, because that is Proton's
screen and not part of this project. Proton's help pages are the place to check.

## If something goes wrong

| You see | What to do | Source |
| --- | --- | --- |
| "Free My ID could not find Proton Mail Bridge on this computer. Please open Proton Mail Bridge, sign in, wait until it says it is running, then press Test again." | Do what it says. | `draft.py:490-492` |
| "The security code of your mail app has changed since you last approved it. This is normal if you just reinstalled or updated Proton Mail Bridge. If you did not, say No." Question: "Do you trust the new code?" | If you just updated or reinstalled Bridge, check the code and press Yes. Otherwise press No. | `server.py:717-725` |
| "The security code of your mail app is not the one you approved. Nothing was sent." | Same as above. Run the test again and answer the question. | `draft.py:497-498` |
| "The mail server did not accept that address and password." | Copy the Bridge username and password again. | `draft.py:455-456` |
