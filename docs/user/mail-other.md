# Set up other email services (Yahoo, iCloud, others, and Outlook)

This page is for Yahoo Mail, iCloud Mail, another email company, and Outlook.com or Hotmail.

Example used below: Jane Q Testperson, Springfield IL, `jane.testperson@example.com` (a made-up address). This is not a real mailbox.

## Before you start

The screen title is "A separate email address for replies". <!-- src/freemyid/wizard/draft.py:69 -->

The screen says "Free My ID can use a separate email address to send deletion requests and click the confirmation links for you. Pick yours, or skip it." <!-- src/freemyid/wizard/ui.py:392 -->

That is why this step asks for a separate address. Free My ID uses it to send deletion requests and to click the confirmation links for you.

You can choose "Skip, I'll do these by hand". <!-- src/freemyid/wizard/ui.py:207 -->
The line under that choice says "Free My ID prepares each message and opens your email for you. You press Send yourself." <!-- src/freemyid/wizard/ui.py:207-208 -->

On every choice below, the address box is "Email address" and the password box is "App password". <!-- src/freemyid/wizard/ui.py:365 --> <!-- src/freemyid/wizard/ui.py:366 -->
The Yahoo and iCloud steps call that box the "Password box". <!-- src/freemyid/wizard/ui.py:225 --> <!-- src/freemyid/wizard/ui.py:231 -->
Under an empty password box, the hint says "Paste the app password here." <!-- src/freemyid/wizard/ui.py:363 -->

The screen says "The test only talks to your email company. The password is kept in your computer's protected store, not in Free My ID's files." <!-- src/freemyid/wizard/ui.py:390 -->
If you have typed a password but not finished, the hint says "Your password is ready but not saved yet. Leave empty to use it." <!-- src/freemyid/wizard/ui.py:361 -->
The save step's note says "put the mailbox password in the keychain". <!-- src/freemyid/wizard/draft.py:560 -->
The password store's note says "Never stored in clear text." <!-- src/freemyid/secrets.py:4 -->

## Outlook.com and Hotmail: not supported yet

The choice is "Outlook.com or Hotmail". The line under it says "Not possible, see below." <!-- src/freemyid/wizard/ui.py:206 -->

The screen then shows "Why Outlook.com does not work". <!-- src/freemyid/wizard/ui.py:240 -->

1. "Microsoft no longer lets programs like Free My ID sign in to Outlook.com and Hotmail." <!-- src/freemyid/wizard/ui.py:241 -->
2. "Please choose Skip, I'll do these by hand, above. Free My ID will prepare each message and open Outlook for you. You press Send. Or choose another service." <!-- src/freemyid/wizard/ui.py:242 -->

If you try to go on with Outlook selected, you see "Outlook.com and Hotmail no longer allow programs like Free My ID to sign in." <!-- src/freemyid/wizard/draft.py:86 --> <!-- src/freemyid/wizard/draft.py:301 -->
The same error tells you to choose "Skip, I'll do these by hand" or pick a different email service. <!-- src/freemyid/wizard/draft.py:87 -->

Use Skip, or pick Yahoo, iCloud, Proton Mail, Gmail, or another email service from the list.

## Yahoo Mail

Pick "Yahoo Mail". <!-- src/freemyid/wizard/ui.py:202 -->

The screen shows "How to get a Yahoo app password (about 3 minutes)", then these steps. <!-- src/freemyid/wizard/ui.py:221 -->
These are the words on the Free My ID screen.

1. "Open a new browser tab and go to login.yahoo.com/account/security. Sign in." <!-- src/freemyid/wizard/ui.py:222 -->
2. "Find Generate app password (or App passwords) and click it." <!-- src/freemyid/wizard/ui.py:223 -->
3. "Type Free My ID as the app name and click Generate password." <!-- src/freemyid/wizard/ui.py:224 -->
4. "Yahoo shows a password. Copy it and paste it in the Password box below. This is not your usual Yahoo password." <!-- src/freemyid/wizard/ui.py:225 -->

Type your Yahoo address in "Email address" and paste that password in "App password". For Jane, the made-up example is jane.testperson@example.com. <!-- src/freemyid/wizard/ui.py:365 --> <!-- src/freemyid/wizard/ui.py:366 -->
You do not type server names. Free My ID fills them in: incoming `imap.mail.yahoo.com` port 993, outgoing `smtp.mail.yahoo.com` port 465. <!-- src/freemyid/wizard/draft.py:78 --> <!-- src/freemyid/wizard/draft.py:79 -->

Press "Test that it works". <!-- src/freemyid/wizard/ui.py:383 -->
If it worked, you see "Connection works. Free My ID can read and send from this mailbox." <!-- src/freemyid/wizard/draft.py:484 -->
Then press "Next". <!-- src/freemyid/wizard/ui.py:407 -->

## iCloud Mail (Apple)

Pick "iCloud Mail (Apple)". <!-- src/freemyid/wizard/ui.py:203 -->

The screen shows "How to get an Apple app-specific password (about 3 minutes)", then these steps. <!-- src/freemyid/wizard/ui.py:227 -->
These are the words on the Free My ID screen.

1. "Open a new browser tab and go to account.apple.com. Sign in." <!-- src/freemyid/wizard/ui.py:228 -->
2. "Click Sign-In and Security, then App-Specific Passwords." <!-- src/freemyid/wizard/ui.py:229 -->
3. "Click the plus button, type Free My ID, and click Create." <!-- src/freemyid/wizard/ui.py:230 -->
4. "Apple shows a password like abcd-efgh-ijkl-mnop. Copy it and paste it in the Password box below." <!-- src/freemyid/wizard/ui.py:231 -->

Type your iCloud address in "Email address" and paste that password in "App password". For Jane, the made-up example is jane.testperson@example.com. <!-- src/freemyid/wizard/ui.py:365 --> <!-- src/freemyid/wizard/ui.py:366 -->
You do not type server names. Free My ID fills them in: incoming `imap.mail.me.com` port 993, outgoing `smtp.mail.me.com` port 587. Outgoing mail uses STARTTLS. <!-- src/freemyid/wizard/draft.py:80 --> <!-- src/freemyid/wizard/draft.py:81 -->

Press "Test that it works", then "Next", the same way as Yahoo. <!-- src/freemyid/wizard/ui.py:383 --> <!-- src/freemyid/wizard/ui.py:407 -->

## Another email service

Pick "Another email service". <!-- src/freemyid/wizard/ui.py:205 -->

The screen shows "Using another email service", then these two steps. <!-- src/freemyid/wizard/ui.py:237 -->

1. "Ask your email company for an app password (sometimes called a program password)." <!-- src/freemyid/wizard/ui.py:238 -->
2. "Their help page lists the mail server names. Fill them in below." <!-- src/freemyid/wizard/ui.py:239 -->

Ask your email company for all of this:

- An app password, sometimes called a program password. It is not your usual mailbox password.
- The incoming mail server name and its port.
- The outgoing mail server name and its port.
- Whether incoming mail should use "Incoming is secure (SSL)", or "Incoming uses STARTTLS (only if SSL is off)". <!-- src/freemyid/wizard/ui.py:375 --> <!-- src/freemyid/wizard/ui.py:376 -->
- Whether outgoing mail should use "Outgoing uses STARTTLS". <!-- src/freemyid/wizard/ui.py:380 -->

Then fill in the boxes:

1. "Email address" and "App password". <!-- src/freemyid/wizard/ui.py:365 --> <!-- src/freemyid/wizard/ui.py:366 -->
2. "Incoming mail server" and "Port". <!-- src/freemyid/wizard/ui.py:370 --> <!-- src/freemyid/wizard/ui.py:371 -->
3. "Outgoing mail server" and "Port". <!-- src/freemyid/wizard/ui.py:373 --> <!-- src/freemyid/wizard/ui.py:374 -->
4. The safety boxes in the list above. The hint says "At least one of these two must be on, or your password would be sent unprotected. If unsure, leave SSL ticked." <!-- src/freemyid/wizard/ui.py:378 -->

Free My ID starts this choice with empty server names, incoming port 993, outgoing port 465, and incoming SSL on. Use the names and ports your email company gave you if they differ. <!-- src/freemyid/wizard/draft.py:82 --> <!-- src/freemyid/wizard/draft.py:83 -->

Press "Test that it works". <!-- src/freemyid/wizard/ui.py:383 -->
If it worked, you see "Connection works. Free My ID can read and send from this mailbox." <!-- src/freemyid/wizard/draft.py:484 -->
Then press "Next". <!-- src/freemyid/wizard/ui.py:407 -->

## If something goes wrong

| You see | What to do | Source |
| --- | --- | --- |
| "Please enter the app password. (It is not your normal email password.)" | Paste the app password from your email company, not your usual password. | <!-- src/freemyid/wizard/draft.py:386 --> |
| "Please enter the removal mailbox's email address." | Type the mailbox address, like the made-up example jane.testperson@example.com. | <!-- src/freemyid/wizard/draft.py:373 --> |
| "Please enter valid mail server names." | Copy the incoming and outgoing server names from your email company. | <!-- src/freemyid/wizard/draft.py:376 --> |
| "Ports must be numbers." | Type the ports as numbers, with no letters. | <!-- src/freemyid/wizard/draft.py:369 --> |
| "Your password would be sent unprotected. Turn on SSL or STARTTLS for incoming mail. If you are not sure, leave SSL ticked." | Turn on incoming SSL, or incoming STARTTLS if SSL is off. | <!-- src/freemyid/wizard/draft.py:344 --> |
| "The mail server did not accept that address and password. Please check them (use an app password, not your normal one)." | Check the address and make a new app password. | <!-- src/freemyid/wizard/draft.py:455 --> |
| "Free My ID could not reach that mail server. Please check the server name and your internet connection, then press Test again." | Check the server name and your internet, then press Test again. | <!-- src/freemyid/wizard/draft.py:493 --> |
| "Incoming mail works, but sending did not. Please check the outgoing server name and port, then press Test again." | Check the outgoing server name and port, then press Test again. | <!-- src/freemyid/wizard/draft.py:481 --> |

## Changing it later

Open "Settings". <!-- src/freemyid/wizard/dashboard.py:501 -->
Under "Email for removals", press "Change it". <!-- src/freemyid/wizard/dashboard.py:525 --> <!-- src/freemyid/wizard/dashboard.py:526 -->
On that page the button is "Save". <!-- src/freemyid/wizard/dashboard.py:557 -->

If a password is already saved, the hint says "A password is saved. Leave empty to keep it." <!-- src/freemyid/wizard/ui.py:359 -->
If you change the email service, you see "You changed the email service, so please enter its app password." <!-- src/freemyid/wizard/draft.py:384 -->
If saving the password fails, you see "Could not store the mailbox password in this computer's keychain. Unlock the keychain and try again." <!-- src/freemyid/wizard/draft.py:572 -->
