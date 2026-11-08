# Troubleshooting: messages you may see

These are 15 messages Free My ID can show you. Each one says what it means and
one thing to try. The words in quotes are copied from the program. If your
message is not here, or the one thing does not help, stop and ask someone you
trust to look with you.

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
