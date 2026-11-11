# Set up Gmail for Free My ID

This page walks you through the email screen in Free My ID if you use Gmail.

Example used below: Jane Q Testperson, Springfield IL, `jane.testperson@example.com` (a made-up address). Yours will be the Gmail address you created. This example is not a real mailbox.

## Before you start

The screen title is "A separate email address for replies". <!-- src/freemyid/wizard/draft.py:69 -->

The screen says "Free My ID can use a separate email address to send deletion requests and click the confirmation links for you. Pick yours, or skip it." <!-- src/freemyid/wizard/ui.py:392 -->

That is why this step asks for a separate address. Free My ID uses it to send deletion requests and to click the confirmation links for you.

For Gmail, the choice says "A free Gmail address made just for Free My ID works best." <!-- src/freemyid/wizard/ui.py:201 -->

You do not have to set this up. You can choose "Skip, I'll do these by hand". <!-- src/freemyid/wizard/ui.py:207 -->
The line under that choice says "Free My ID prepares each message and opens your email for you. You press Send yourself." <!-- src/freemyid/wizard/ui.py:207-208 -->

## Step 1: Get an app password from Google

The screen shows "How to get a Gmail app password (about 3 minutes)". <!-- src/freemyid/wizard/ui.py:213 -->

These are the steps it lists. They are the app's own words. Google's page may look different.

1. "Open a new browser tab and go to myaccount.google.com. Sign in to the Gmail address you made for Free My ID." Google's page may look different. <!-- src/freemyid/wizard/ui.py:214 -->
2. "Click Security on the left. Turn on 2-Step Verification if it is not already on." Google's page may look different. <!-- src/freemyid/wizard/ui.py:216 -->
3. "Click the search box at the top and type: App passwords. Open it." Google's page may look different. <!-- src/freemyid/wizard/ui.py:217 -->
4. "Type Free My ID as the name and click Create." Google's page may look different. <!-- src/freemyid/wizard/ui.py:218 -->
5. "Google shows a box of 16 letters. Copy them, then paste them in the Password box below. This is not your usual Gmail password." Google's page may look different. <!-- src/freemyid/wizard/ui.py:219 -->

If a button has moved, use the search box in step 3, or ask a family member to sit with you.

## Step 2: Fill in the Free My ID screen

1. Pick "Gmail". <!-- src/freemyid/wizard/ui.py:201 -->
2. In "Email address", type the Gmail address you made for this. For Jane, the made-up example is jane.testperson@example.com. <!-- src/freemyid/wizard/ui.py:365 -->
3. In "App password", paste the 16 letters from step 1. <!-- src/freemyid/wizard/ui.py:366 -->
   The steps call this box the "Password box". <!-- src/freemyid/wizard/ui.py:219 -->
   Under an empty box, the hint says "Paste the app password here." <!-- src/freemyid/wizard/ui.py:363 -->
4. You do not type server names. Free My ID fills them in: incoming `imap.gmail.com` port 993, outgoing `smtp.gmail.com` port 465. <!-- src/freemyid/wizard/draft.py:74 --> <!-- src/freemyid/wizard/draft.py:75 -->

## Step 3: Test it

1. Press "Test that it works". <!-- src/freemyid/wizard/ui.py:383 -->
2. If it worked, you see "Connection works. Free My ID can read and send from this mailbox." <!-- src/freemyid/wizard/draft.py:484 -->
3. Press "Next". <!-- src/freemyid/wizard/ui.py:407 -->

The screen says "The test only talks to your email company. The password is kept in your computer's protected store, not in Free My ID's files." <!-- src/freemyid/wizard/ui.py:390 -->

If you have typed a password but not finished, the hint says "Your password is ready but not saved yet. Leave empty to use it." <!-- src/freemyid/wizard/ui.py:361 -->

The save step's note says "put the mailbox password in the keychain". <!-- src/freemyid/wizard/draft.py:560 -->
The password store's note says "Never stored in clear text." <!-- src/freemyid/secrets.py:4 -->
If saving the password fails, you see "Could not store the mailbox password in this computer's keychain. Unlock the keychain and try again." <!-- src/freemyid/wizard/draft.py:572 -->

## If something goes wrong

| You see | What to do | Source |
| --- | --- | --- |
| "Please enter the app password. (It is not your normal email password.)" | Paste the 16 letters from step 1. | <!-- src/freemyid/wizard/draft.py:386 --> |
| "The mail server did not accept that address and password. Please check them (use an app password, not your normal one)." | Check the address and make a new app password. | <!-- src/freemyid/wizard/draft.py:455 --> |
| "Free My ID could not reach that mail server. Please check the server name and your internet connection, then press Test again." | Check your internet, then press Test again. | <!-- src/freemyid/wizard/draft.py:493 --> |
| "Incoming mail works, but sending did not. Please check the outgoing server name and port, then press Test again." | Press Test again. If it still fails, choose Skip and send by hand. | <!-- src/freemyid/wizard/draft.py:481 --> |

## Changing it later

Open "Settings". <!-- src/freemyid/wizard/dashboard.py:501 -->
Under "Email for removals", press "Change it". <!-- src/freemyid/wizard/dashboard.py:525 --> <!-- src/freemyid/wizard/dashboard.py:526 -->
On that page the button is "Save". <!-- src/freemyid/wizard/dashboard.py:557 -->

If a password is already saved, the hint says "A password is saved. Leave empty to keep it." <!-- src/freemyid/wizard/ui.py:359 -->
If you change the email service, you see "You changed the email service, so please enter its app password." <!-- src/freemyid/wizard/draft.py:384 -->
