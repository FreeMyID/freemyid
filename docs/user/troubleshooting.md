# Troubleshooting: messages you may see

These are 15 messages Free My ID can show you. Each one says what it means and
one thing to try. The words in quotes are copied from the program. If your
message is not here, or the one thing does not help, stop and ask someone you
trust to look with you.

[Starting and updating](#starting-and-updating) is not an error. That part is
normal.

[The blue Windows box](#the-blue-windows-box) is about the installer, before
Free My ID is open. A certificate warning on the download page, at work or at
school, is in that same part. Those are not messages from inside Free My ID.

Example person used below: Jane Q Testperson, Springfield IL.

## Sending email

### 1. "Could not send that email. Check the email settings and try again."
<!-- src/freemyid/wizard/server.py:55 (shown after the send at :513) -->
The email did not go out. **Do this:** open the email settings, check them, then press Send again.

### 2. "Sending is not switched on in this copy of Free My ID yet."
<!-- src/freemyid/wizard/server.py:56 (shown at :505) -->
This copy of the program cannot send email yet. **Do this:** use the "Open the site myself" choice for that item instead.
<!-- "Open the site myself": src/freemyid/wizard/server.py:63 -->

### 3. "Free My ID could not find Proton Mail Bridge on this computer. Please open Proton Mail Bridge, sign in, wait until it says it is running, then press Test again."
<!-- src/freemyid/wizard/draft.py:490-492 -->
The email test looked for Proton Mail Bridge on this computer and did not find it. **Do this:** open Proton Mail Bridge, sign in, wait until it says it is running, then press Test again.

### 4. "Free My ID could not reach that mail server. Please check the server name and your internet connection, then press Test again."
<!-- src/freemyid/wizard/draft.py:493-494 -->
The email test got no answer from the mail server you typed. **Do this:** check that the server name is spelled the way your email provider says, and that your internet works, then press Test again.

### 5. "Your password would be sent unprotected. Turn on SSL or STARTTLS for incoming mail. If you are not sure, leave SSL ticked."
<!-- src/freemyid/wizard/draft.py:344-345 -->
The email settings had no protection switched on for incoming mail. **Do this:** tick SSL (or STARTTLS), as the message says.

### 6. "Could not store the mailbox password in this computer's keychain. Unlock the keychain and try again."
<!-- src/freemyid/wizard/draft.py:572-573 -->
Free My ID could not save your email password on this computer. **Do this:** unlock the computer's keychain, then save again.

## Saving your details

### 7. "Some details are missing or invalid; please go back and check them."
<!-- src/freemyid/wizard/draft.py:546 -->
One or more boxes on an earlier screen are empty or not filled in correctly. **Do this:** go back through the screens and fill in any empty box.

### 8. "A parent or guardian must give permission for someone under 18."
<!-- src/freemyid/wizard/draft.py:516 -->
The person being set up is under 18, so a parent or guardian has to give permission. **Do this:** go back and have the parent or guardian give permission.

### 9. "Please give a first and last name for "Jane"."
<!-- src/freemyid/wizard/draft.py:168 (the name in quotes is whatever was typed) -->
A name box had only one word. **Do this:** type a first and last name, such as Jane Testperson.

## Settings and other messages

### 10. "Could not change that setting."
<!-- src/freemyid/wizard/server.py:58 (shown at :634); "Automatic checking" wording: :57 -->
A setting, such as Automatic checking, did not change. **Do this:** try the switch once more. If it fails again, ask someone you trust for help.

### 11. "Please let a practice check finish first, then look at the results."
<!-- src/freemyid/wizard/server.py:64 (shown at :565 and :576) -->
You asked for results before a practice check had finished. **Do this:** wait for the practice check to finish, then open the results again.

### 12. "That didn't work"
<!-- src/freemyid/wizard/server.py:186 (page title); message line: src/freemyid/wizard/server.py:187 -->
The page shows this title with the line: "Free My ID could not tell that this request came from its own window." **Do this:** close the page, open Free My ID again from its own icon, and repeat the step.

## Forms and listings

### 13. "Another form is already being filled in. Please finish that one first."
<!-- src/freemyid/wizard/server.py:61 (shown at :388) -->
A form from another item is still open. **Do this:** finish or close that one first, then start this one.

### 14. "The form was not sent, so nothing changed. Your to-do is still on the list. You can try again or use "Open the site myself"."
<!-- src/freemyid/wizard/server.py:62-63 (shown at :420) -->
The form did not go through, and your to-do item is still on the list. **Do this:** press try again, or choose "Open the site myself".

### 15. "This is still the search page. Open the result that is you, then click 'This is me' again."
<!-- src/freemyid/engine/listing_finder.py:86-87 -->
While finding your listing, the page you were on was still the list of search results. **Do this:** open the one result that is you, then click "This is me" again. If you cannot find yourself, click "I can't find me" or close the window to stop.
<!-- hint text: src/freemyid/engine/listing_finder.py:82 -->

## Starting and updating

This is for version 0.3.1 on Windows. These windows are normal.
<!-- packaging/windows/freemyid.iss:5 -->

### "Free My ID is starting."
<!-- packaging/windows/splash_win.py (at :20) -->
<!-- packaging/windows/freemyid.iss:34 -->

The first time can take up to a minute. Please wait; there is no need to click it again. A small window stays until Free My ID is ready. It says "Free My ID is starting."
<!-- packaging/windows/splash_win.py (small window at :1; it stays up at :5; up to a minute at :3 and :20) -->
<!-- packaging/windows/launcher_gui.py (opens at :27; closes when Free My ID is ready at :29) -->
<!-- src/freemyid/wizard/desktop.py:168 -->
<!-- src/freemyid/wizard/desktop.py:202 -->

**Do this:** wait. There is no need to click again.

### "Free My ID is still starting."
<!-- packaging/windows/splash_win.py (at :22) -->

After two minutes, the window says "Free My ID is still starting." It also says "This is taking longer than usual." and "Please wait; there is no need to click it again."
<!-- packaging/windows/splash_win.py (two minutes is 120 seconds at :24; the click sentence at :23) -->

**Do this:** keep waiting. There is no need to click again.

### After an update

Updating with the new installer keeps your details and the scheduled check. Jane Q Testperson in Springfield IL would still have her saved details, and the scheduled check would still be there.
<!-- packaging/windows/freemyid.iss:9 (same installer id, so this is the same Free My ID) -->
<!-- packaging/windows/freemyid.iss:39 (the installer replaces the program files) -->
<!-- packaging/windows/freemyid.iss:83 (saved details are in a different folder) -->
<!-- packaging/windows/freemyid.iss:97 (that folder is removed only while uninstalling) -->
<!-- packaging/windows/freemyid.iss:64 (the scheduled check is removed only while uninstalling) -->

The app may need reopening after an update.
<!-- packaging/windows/freemyid.iss:28 -->
<!-- packaging/windows/freemyid.iss:56 -->

**Do this:** if you do not see the window, open Free My ID from the Desktop icon or the Start Menu.
<!-- packaging/windows/freemyid.iss:53 -->

## The blue Windows box

This part is for the Windows installer, before Free My ID is open. Jane Q
Testperson in Springfield IL might see it the first time she opens the file
she downloaded.

### The blue box says "Windows protected your PC"

A blue box may say **Windows protected your PC**. If you click the small
words **More info**, it can say **Unknown publisher**.

The installer is not code-signed yet. Windows does not yet have a publisher
certificate for this file, so it does not show a company name. The box can
still appear when the file came from the download page.

Do not turn off Windows security to get past this box. Leave your virus
protection on.

If that box is already open, click **Don't run**. That closes the box. It
does not change your security settings. Check the file next. Open the file
again only if the codes match.

### Check the file against the SHA-256 on the download page

SHA-256 is a long code for this one file. The download page shows that code.
The file on your computer should show the same code. You do not type it into
Free My ID. It is not a password.

A helper can sit with you. On the download page, open **For helpers: check
the download is genuine**.

1. Open the download page and leave it open:
   [freemyid.org/download](https://freemyid.org/download/#checksum).
   Read the long code next to the version name. That code is the SHA-256.
2. Click the Start button. Type PowerShell. Open **Windows PowerShell**. A
   dark window opens. This is not the blue box.
3. Click in that window. Copy the line below and paste it, then press Enter.
   To paste, press Ctrl and V together. If that does nothing, right-click in
   the window.

   ```
   Get-FileHash -Path "$env:USERPROFILE\Downloads\FreeMyIDSetup.exe" -Algorithm SHA256
   ```

   The download page writes the same check as `Get-FileHash .\FreeMyIDSetup.exe`
   once you are in the Downloads folder. The line above already includes that
   folder, so one paste is enough.

4. The window shows a long code on the Hash line. Read it beside the code on
   the download page, from the start through the end. Small letters and
   capital letters are the same letter. Every letter and number should match.
5. If the window says it cannot find the file, look in Downloads for
   **FreeMyIDSetup.exe**. If the name is different, stop and ask a helper.
   Do not open some other file.

<!-- site_src/data/release.yaml:8 sha256 for version 0.3.0: a234c8cd560e436c81f48aacffb91da6408618d979f039bf2f5612de57ccfe9c -->

**Do this:** if the codes match, open **FreeMyIDSetup.exe** again. When the
blue box comes back, click **More info**. Check that the app name is
**FreeMyIDSetup.exe**. It will say **Unknown publisher**. That is expected,
because the installer is not code-signed yet. Then click **Run anyway**. Do
that only when this file came from the download page, and only after the
codes match.

If the codes do not match, do not open the file. Stop and ask someone you
trust.

### The download page shows a certificate warning at work or school

At work or at school, the download page may show a certificate warning. A
network filter is checking web traffic. The work or school network is looking
at the sites you open. That check can make the browser warn about the
certificate.

You might see "Your connection is not private", the word certificate, or a
padlock with a line through it.

**Do this:** try another network. Use the internet at home, or a phone's own
hotspot, and open the download page again. Jane Q Testperson would do this
at home in Springfield IL.

Do not click past the warning.

Never ignore a certificate warning on other sites. If a bank, a shop, or your
email shows that warning, stop. Ask someone you trust to look with you.

If the same warning is there on your home network too, stop. Do not go on.
