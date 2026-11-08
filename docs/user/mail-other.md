# Set up other email services (Yahoo, iCloud, others, and Outlook)

Example used below: Jane Q Testperson, Springfield IL,
`jane.testperson@mail.example` (a made-up address).

Free My ID uses a separate email address to send deletion requests and click
confirmation links (`src/freemyid/wizard/ui.py:389`). You can also choose
"Skip, I'll do these by hand": Free My ID prepares each message and opens your
email, and you press Send yourself (`ui.py:204-205`).

## Outlook.com and Hotmail: not supported yet

Outlook.com and Hotmail do not work as the Free My ID mailbox. The wizard says
Microsoft no longer lets programs like Free My ID sign in
(`ui.py:238`, `src/freemyid/wizard/draft.py:86`). If you pick it, you see an
error and cannot continue (`draft.py:300-301`).

Instead, choose one of these:

- **Skip, I'll do these by hand.** Free My ID prepares each message and opens
  Outlook for you. You press Send (`ui.py:239-240`).
- Another email service from the list.

## Yahoo Mail

The wizard shows these steps (`ui.py:218-223`):

1. Open a new browser tab and go to `login.yahoo.com/account/security`. Sign in.
2. Click **Generate app password** (or **App passwords**).
3. Type `Free My ID` as the app name and click **Generate password**.
4. Copy the password and paste it in the password box. It is not your usual
   Yahoo password.

Then pick **Yahoo Mail** (`ui.py:199`), type your address and the app password
(`ui.py:362-363`). Server names are filled in for you (`draft.py:78-79`).

## iCloud Mail (Apple)

The wizard shows these steps (`ui.py:224-229`):

1. Open a new browser tab and go to `account.apple.com`. Sign in.
2. Click **Sign-In and Security**, then **App-Specific Passwords**.
3. Click the plus button, type `Free My ID`, and click **Create**.
4. Copy the password Apple shows and paste it in the password box.

Then pick **iCloud Mail (Apple)** (`ui.py:200`), type your address and the
password (`ui.py:362-363`). Server names are filled in for you
(`draft.py:80-81`).

## Another email service

1. Pick **Another email service** (`ui.py:202`).
2. Ask your email company for an app password (sometimes called a program
   password) (`ui.py:235`).
3. Their help page lists the mail server names. Fill in the boxes
   (`ui.py:236`, `ui.py:367-371`):
   - **Incoming mail server** and its **Port**
   - **Outgoing mail server** and its **Port**
4. Tick the safety boxes your company says to use (`ui.py:372-377`):
   - **Incoming is secure (SSL)**
   - **Incoming uses STARTTLS (only if SSL is off)**
   - **Outgoing uses STARTTLS**

   At least one of the first two must be on, or your password would be sent
   unprotected. If you are not sure, leave SSL ticked (`ui.py:375-376`,
   `draft.py:344-345`).
5. Type your **Email address** and **App password** (`ui.py:362-363`).
6. Press **Test that it works** (`ui.py:380`). You should see "Connection works.
   Free My ID can read and send from this mailbox." (`draft.py:484`).

If your server names look wrong you see "Please enter valid mail server names."
(`draft.py:376`). If the ports are not numbers: "Ports must be numbers."
(`draft.py:369`).

## If something goes wrong

| You see | What to do | Source |
| --- | --- | --- |
| "The mail server did not accept that address and password. Please check them (use an app password, not your normal one)." | Check the address and make a new app password. | `draft.py:455-456` |
| "Free My ID could not reach that mail server. Please check the server name and your internet connection, then press Test again." | Check the server name and your internet. | `draft.py:493-494` |
| "Incoming mail works, but sending did not." | Check the outgoing server name and port, then Test again. | `draft.py:481-482` |
