# Set up Proton Mail for Free My ID

Proton Mail on this screen works through a free helper app called Proton Mail Bridge.
This page covers the Free My ID email screen, including the security-code question the first time you test.

Example used below: Jane Q Testperson, Springfield IL, `jane.testperson@example.com` (a made-up address). Yours will be your Proton address. This example is not a real mailbox.

## Before you start

The screen title is "A separate email address for replies". <!-- src/freemyid/wizard/draft.py:69 -->

The screen says "Free My ID can use a separate email address to send deletion requests and click the confirmation links for you. Pick yours, or skip it." <!-- src/freemyid/wizard/ui.py:392 -->

That is why this step asks for a separate address. Free My ID uses it to send deletion requests and to click the confirmation links for you.

You can choose "Skip, I'll do these by hand". <!-- src/freemyid/wizard/ui.py:207 -->
The line under that choice says "Free My ID prepares each message and opens your email for you. You press Send yourself." <!-- src/freemyid/wizard/ui.py:207-208 -->

## Step 1: Get your Bridge details

Pick "Proton Mail (needs the Proton Bridge app)". <!-- src/freemyid/wizard/ui.py:204 -->

The screen shows "Using Proton Mail", then these two steps. <!-- src/freemyid/wizard/ui.py:233 -->
Proton's page may look different. These are the words Free My ID shows, not a check of Proton's current menus.

1. "Proton needs a free helper app called Proton Mail Bridge. Install it from proton.me/mail/bridge and sign in. It must be running when Free My ID checks mail." Proton's page may look different. <!-- src/freemyid/wizard/ui.py:234 -->
2. "Bridge shows a username and a password just for programs. Copy them below." Proton's page may look different. <!-- src/freemyid/wizard/ui.py:236 -->

Use that program password, not the password you type on Proton's website. Proton's page may look different.

## Step 2: Fill in the Free My ID screen

1. "Email address": your Proton address. For Jane, the made-up example is jane.testperson@example.com. <!-- src/freemyid/wizard/ui.py:365 -->
2. "Bridge username": the username Bridge showed you. <!-- src/freemyid/wizard/ui.py:368 -->
   If you leave it empty, Free My ID uses the email address. <!-- src/freemyid/wizard/draft.py:358 -->
3. "App password": paste the Bridge password. <!-- src/freemyid/wizard/ui.py:366 -->
   The steps call this the password to copy below. The empty-box hint says "Paste the app password here." <!-- src/freemyid/wizard/ui.py:363 -->
4. You do not type server names. Free My ID fills in the Bridge settings for you: `127.0.0.1`, incoming port 1143, outgoing port 1025. Incoming and outgoing both use STARTTLS. <!-- src/freemyid/wizard/draft.py:76 --> <!-- src/freemyid/wizard/draft.py:77 -->

That address, `127.0.0.1`, means Bridge on this computer.

## Step 3: Test it, and answer the security-code question

1. Press "Test that it works". <!-- src/freemyid/wizard/ui.py:383 -->
2. The first time, a box appears. It says "Free My ID found your mail app on this computer. Please check that the code below matches the one in Proton Mail Bridge." <!-- src/freemyid/wizard/server.py:813 -->
3. The box shows a code and asks "Do you trust this code?" <!-- src/freemyid/wizard/server.py:817 -->
4. The buttons are "Yes" and "No". <!-- src/freemyid/wizard/ui.py:387 --> <!-- src/freemyid/wizard/ui.py:388 -->
5. Press Yes only after the code matches Bridge. Starting Bridge yourself is not the same as checking the code. Proton's page may look different.
6. If you press No, you see "Not trusted. Nothing was saved and no password was sent." <!-- src/freemyid/wizard/server.py:826 -->
7. The check step's note says "The password is only sent after the certificate check passes". <!-- src/freemyid/wizard/draft.py:418 -->
8. When the test works you see "Connection works. Free My ID can read and send from this mailbox." <!-- src/freemyid/wizard/draft.py:484 -->
   Then press "Next". <!-- src/freemyid/wizard/ui.py:407 -->

You must approve the code before you can go on. If you press Next first, you see 'Please press "Test that it works" and approve the security code first.' <!-- src/freemyid/wizard/draft.py:392 -->

The screen says "The test only talks to your email company. The password is kept in your computer's protected store, not in Free My ID's files." <!-- src/freemyid/wizard/ui.py:390 -->
For Bridge, that test talks to the mail app on this computer. If you have typed a password but not finished, the hint says "Your password is ready but not saved yet. Leave empty to use it." <!-- src/freemyid/wizard/ui.py:361 -->
The save step's note says "put the mailbox password in the keychain". <!-- src/freemyid/wizard/draft.py:560 -->
The password store's note says "Never stored in clear text." <!-- src/freemyid/secrets.py:4 -->

### How to check the code

The code on the screen is the SHA-256 fingerprint of Bridge's certificate. <!-- src/freemyid/engine/mail_tls.py:49 -->
Free My ID shows it with colons and capital letters. <!-- src/freemyid/engine/mail_tls.py:54 -->

Proton's page may look different, so this guide does not guess Bridge's menus. Proton's settings guide explains the certificate export: [comprehensive guide to Bridge settings](https://proton.me/support/comprehensive-guide-to-bridge-settings).

When you export, choose only the certificate. Do not export a private key. Treat the exported file as private. Save it only in a private folder on this computer, do not send it to anyone, and delete the exported copy when you are done. If the file includes a private key, that care matters.

A helper can read the fingerprint with:

`openssl x509 -in "<exported cert file>" -noout -fingerprint -sha256`

Ignore colons and capital letters when you compare. <!-- src/freemyid/models.py:290 -->
If the two match, press Yes. If they differ, or you cannot check, press No and ask your helper.

## If something goes wrong

| You see | What to do | Source |
| --- | --- | --- |
| "Free My ID could not find Proton Mail Bridge on this computer. Please open Proton Mail Bridge, sign in, wait until it says it is running, then press Test again." | Do what it says. Proton's page may look different. | <!-- src/freemyid/wizard/draft.py:490 --> |
| "The security code of your mail app has changed since you last approved it. This is normal if you just reinstalled or updated Proton Mail Bridge. If you did not, say No." The question is "Do you trust the new code?" | If you just updated or reinstalled Bridge, check the code, then press Yes. If you did not, press No. | <!-- src/freemyid/wizard/server.py:809 --> <!-- src/freemyid/wizard/server.py:817 --> |
| "The mail server did not accept that address and password. Please check them (use an app password, not your normal one)." | Copy the Bridge username and password again. | <!-- src/freemyid/wizard/draft.py:455 --> |
| "Please enter the app password. (It is not your normal email password.)" | Paste the password Bridge made for programs. | <!-- src/freemyid/wizard/draft.py:386 --> |

## Changing it later

Open "Settings". <!-- src/freemyid/wizard/dashboard.py:501 -->
Under "Email for removals", press "Change it". <!-- src/freemyid/wizard/dashboard.py:525 --> <!-- src/freemyid/wizard/dashboard.py:526 -->
On that page the button is "Save". <!-- src/freemyid/wizard/dashboard.py:557 -->

If a password is already saved, the hint says "A password is saved. Leave empty to keep it." <!-- src/freemyid/wizard/ui.py:359 -->
If you change the email service, you see "You changed the email service, so please enter its app password." <!-- src/freemyid/wizard/draft.py:384 -->
If saving the password fails, you see "Could not store the mailbox password in this computer's keychain. Unlock the keychain and try again." <!-- src/freemyid/wizard/draft.py:572 -->
