# Set up Gmail for Free My ID

This page walks you through the email screen in Free My ID if you use Gmail.
It takes about 3 minutes (`src/freemyid/wizard/ui.py:210`).

Example used below: Jane Q Testperson, Springfield IL, `jane.testperson.removals@gmail.com`
(a made-up address).

## Before you start

- Free My ID asks you to pick an email address it can use to send deletion
  requests and click confirmation links (`src/freemyid/wizard/ui.py:389`).
  The screen is called "A separate email address for replies"
  (`src/freemyid/wizard/draft.py:69`).
- The screen says a free Gmail address made just for Free My ID works best
  (`src/freemyid/wizard/ui.py:198`). Make a new one if you can, so replies
  from companies do not mix with your own mail.
- You do not have to do this. You can pick "Skip, I'll do these by hand" instead.
  Free My ID then prepares each message and opens your email, and you press Send
  yourself (`src/freemyid/wizard/ui.py:204-205`).

## Step 1: Get an app password from Google

Free My ID cannot use your normal Gmail password. It needs a special 16-letter
"app password" (`src/freemyid/wizard/draft.py:386`,
`src/freemyid/wizard/ui.py:216`). The wizard shows these same steps on the
screen (`src/freemyid/wizard/ui.py:210-216`):

1. Open a new browser tab and go to `myaccount.google.com`. Sign in to the Gmail
   address you made for Free My ID (`ui.py:211`).
2. Click **Security** on the left. Turn on **2-Step Verification** if it is not
   already on (`ui.py:213`).
3. Click the search box at the top and type: `App passwords`. Open it (`ui.py:214`).
4. Type `Free My ID` as the name and click **Create** (`ui.py:215`).
5. Google shows a box of 16 letters. Copy them (`ui.py:216`).

Google may change its pages over time. If a button has moved, use the search box
in step 3. If you are not sure, ask a family member to sit with you.

## Step 2: Fill in the Free My ID screen

1. Pick **Gmail** in the list (`ui.py:198`).
2. In **Email address**, type your Gmail address (`ui.py:362`).
3. In the **App password** box, paste the 16 letters (`ui.py:363`).
   The wizard's step text calls this the "Password box" (`ui.py:216`); it is the
   same box.
4. Leave everything else alone. The Gmail server names are filled in for you
   (`src/freemyid/wizard/draft.py:74-75`).

## Step 3: Test it

1. Press **Test that it works** (`ui.py:380`).
2. If it worked, you see: "Connection works. Free My ID can read and send from
   this mailbox." (`draft.py:484`).
3. Press **Next** (`ui.py:409`).

Your password is kept in your computer's protected store, not in Free My ID's
files (`ui.py:387-388`).

## If something goes wrong

| You see | What to do | Source |
| --- | --- | --- |
| "Please enter the app password. (It is not your normal email password.)" | Paste the 16 letters from step 1. | `draft.py:386` |
| "The mail server did not accept that address and password. Please check them (use an app password, not your normal one)." | Check the address and make a new app password. | `draft.py:455-456` |
| "Free My ID could not reach that mail server. Please check the server name and your internet connection, then press Test again." | Check your internet, then press Test again. | `draft.py:493-494` |
| "Incoming mail works, but sending did not." | Press Test again. If it still fails, choose Skip and send by hand. | `draft.py:481-482` |

## Changing it later

Open Settings and press **Change it** next to the mailbox
(`src/freemyid/wizard/dashboard.py:442`). If you change the email service, you
must enter its app password again (`draft.py:384`).
