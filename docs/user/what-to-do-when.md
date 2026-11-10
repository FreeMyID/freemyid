# What to do when the screen worries you

This page helps you read calm Free My ID messages that are not errors.

These moments are normal.
They are not errors.
If the screen says something failed, open [Troubleshooting](troubleshooting.md).

The example name below is Jane Q Testperson, Springfield IL.

## When the screen says "Nothing needs you today"

**What the screen says**

The big heading says "Nothing needs you today". <!-- src/freemyid/wizard/dashboard.py:267-268 -->

The line under the heading is below.

"Free My ID keeps checking in the background and will tell you if that changes." <!-- src/freemyid/wizard/dashboard.py:268-269 -->

**What it means**

Free My ID has no step for you today.
It keeps looking on its own.
It will say so if that changes.
You can close the window.

**One thing to do**

1. Leave this screen as it is.
2. Come back when the heading changes.

**When to stop and ask someone you trust**

Ask if you expected a step and this screen stays for many days.
Ask if a different message says something failed.
Those messages are in [Troubleshooting](troubleshooting.md).

## When the screen says "Free My ID is checking now"

**What the screen says**

The heading says "Free My ID is checking now". <!-- src/freemyid/wizard/dashboard.py:262 -->

Under it, the screen says "This takes about a minute. This page updates by itself." <!-- src/freemyid/wizard/dashboard.py:262-263 -->

**What it means**

Free My ID is working through its list.
The page changes on its own.
You do not need to press anything.
This is not an error.

**One thing to do**

1. Stay on this page.
2. Let it update by itself.

**When to stop and ask someone you trust**

If a message says something failed, open [Troubleshooting](troubleshooting.md).
Ask someone you trust if the page never changes and you are unsure.

## When the screen says "Practice mode"

**What the screen says**

A note near the top says "Practice mode:". <!-- src/freemyid/wizard/dashboard.py:237 -->

It also says "no removal requests go out until you say so." <!-- src/freemyid/wizard/dashboard.py:238 -->

**What it means**

Free My ID is looking for listings.
It is not sending a request yet.
That is how it starts.
It is not broken.

**One thing to do**

1. Let it keep looking if you are not ready.
2. Open Settings when you want requests to go out.
3. Press **Start sending real requests** only when you mean it.

The link says "Start sending real requests". <!-- src/freemyid/wizard/dashboard.py:515 -->

**When to stop and ask someone you trust**

Ask before you start real requests if you are unsure.
A request that already went out stays sent.
The confirm screen says "Requests already sent cannot be taken back." <!-- src/freemyid/wizard/dashboard.py:489-490 -->

## When the screen says emails are "waiting for your OK"

**What the screen says**

The heading includes "waiting for your OK". <!-- src/freemyid/wizard/dashboard.py:253 -->

Under it, the screen says "Look at each one, then press Approve." <!-- src/freemyid/wizard/dashboard.py:253 -->

The button on that screen says "Look at them". <!-- src/freemyid/wizard/dashboard.py:255 -->

The next page heading says "Emails waiting for your approval". <!-- src/freemyid/wizard/dashboard.py:449 -->

The send button says "Approve and send". <!-- src/freemyid/wizard/dashboard.py:473 -->

Another button says "Cancel it". <!-- src/freemyid/wizard/dashboard.py:475 -->

The screen may ask "Send this email now?" <!-- src/freemyid/wizard/dashboard.py:456 -->

After the first approval, it can say "After that, routine emails go out by themselves." <!-- src/freemyid/wizard/dashboard.py:461 -->

It also says "Formal demands still wait for you." <!-- src/freemyid/wizard/dashboard.py:461-462 -->

**What it means**

Free My ID wrote the emails.
They wait for you.
Press **Approve and send** when you want that request to go out.
The first email for a person may also send other emails that are waiting.
Read that note before you say yes.
A formal demand is a firmer letter.
That kind still waits for you.
After that first approval, ordinary emails can go out on their own.

**One thing to do**

1. Press **Look at them**.
2. Read the email.
3. Press **Approve and send** when you want that request to go out.

**When to stop and ask someone you trust**

Do not press the button if the email asks for money.
Do not press it if it asks for a Social Security number.
Ask someone you trust to read it with you.
If the screen says the email could not go out, open [Troubleshooting](troubleshooting.md#sending-email).

## When the screen says "Not running yet for" a person

**What the screen says**

The note starts with "Not running yet for". <!-- src/freemyid/wizard/dashboard.py:242 -->

Then it shows a name, such as Jane Q Testperson.
The link at the end says "Fix it". <!-- src/freemyid/wizard/dashboard.py:244 -->

**What it means**

Free My ID is not working on that person yet.
The words after the name say what is missing.
This is a pause for that person.
It is not a failure message.

**One thing to do**

1. Read the words after the name.
2. Press **Fix it**.
3. Read what that page says is missing.

**When to stop and ask someone you trust**

Stop if you do not know the person named.
Ask if you cannot tell what is missing.
If a message says something failed, open [Troubleshooting](troubleshooting.md).

## When a site wants a photo ID, an account, or your phone number

**What the screen says**

A card can say the words below.

"If a site wants a photo ID, an account or your phone number, Free My ID stops and asks, unless you allowed that in Settings." <!-- src/freemyid/wizard/dashboard.py:129-130 -->

In Settings, the heading says "What Free My ID may do". <!-- src/freemyid/wizard/dashboard.py:527 -->

The screen says "Everything here is off unless you tick it." <!-- src/freemyid/wizard/dashboard.py:528 -->

The lines you can tick are these.

"Free My ID may upload a copy of an ID if a website requires it" <!-- src/freemyid/wizard/dashboard.py:532-533 -->

"Free My ID may create an account on a website if required" <!-- src/freemyid/wizard/dashboard.py:534-535 -->

"Free My ID may give a phone number if required" <!-- src/freemyid/wizard/dashboard.py:536-537 -->

The button under them says "Save". <!-- src/freemyid/wizard/dashboard.py:538 -->

**What it means**

Free My ID stops instead of handing those over.
It asks you first.
It goes ahead only if you already allowed that line.
You can skip the site.

**One thing to do**

1. Skip the site if you do not want to share that.
2. Or open Settings and find "What Free My ID may do". <!-- src/freemyid/wizard/dashboard.py:527 -->
3. Tick only the line you mean.
4. Press **Save**.

**When to stop and ask someone you trust**

Ask before you tick an ID line if you feel unsure.
Stop if the site asks for a Social Security number.
Stop if it asks for money, a bank, or a card.
Free My ID does not ask for those.

## When the screen says a listing came back

**What the screen says**

A history line can say "Listing came back". <!-- src/freemyid/wizard/views.py:41 -->

The site page can say "It came back. We are asking again". <!-- src/freemyid/wizard/views.py:34 -->

The home page can say the line below.

"Details can reappear, which is why Free My ID keeps checking." <!-- src/freemyid/wizard/dashboard.py:277 -->

It can also say the line below.

"A site that says it deleted you has done that for that one site only." <!-- src/freemyid/wizard/dashboard.py:276-277 -->

**What it means**

A later check found the listing again.
That can happen.
Free My ID makes a new request.
Requested is not the same as confirmed.
One site's words are about that site only.
This is not a promise about every site.

**One thing to do**

1. Leave it if no step is waiting for you.
2. Let Free My ID ask again on its next check.

**When to stop and ask someone you trust**

Ask if the same listing keeps coming back and you are worried.
If the screen says something failed, open [Troubleshooting](troubleshooting.md).

## When the computer was off for days

**What the screen says**

In Settings, the heading says "Run automatically". <!-- src/freemyid/wizard/dashboard.py:502 -->

The text under that heading is below.

"If the computer was off, it catches up when it is next on." <!-- src/freemyid/wizard/dashboard.py:503-504 -->

A line says "Right now:". <!-- src/freemyid/wizard/dashboard.py:504 -->

One button says "Turn on". <!-- src/freemyid/wizard/dashboard.py:506 -->

**What it means**

With the daily check on, one missed run happens when the computer is on.
Free My ID catches up then.
You do not redo a step for each missed day.
The words after "Right now" tell you the state of that check. <!-- src/freemyid/wizard/dashboard.py:504 -->

**One thing to do**

1. Turn the computer on and open Free My ID.
2. Open Settings and read "Run automatically". <!-- src/freemyid/wizard/dashboard.py:502 -->
3. Press **Turn on** if you want the daily check and it is not on.

**When to stop and ask someone you trust**

Ask if the words after "Right now" do not make sense. <!-- src/freemyid/wizard/dashboard.py:504 -->
If the button will not stay on, open [Troubleshooting](troubleshooting.md#settings-and-other-messages).

## When the screen asks you to call a site

**What the screen says**

The card is a phone step for that person.
It may show "Phone number to call". <!-- src/freemyid/submitters/assisted.py:138 -->

Under the script, the label says "A short note about the call (optional)". <!-- src/freemyid/wizard/dashboard.py:189 -->

The hint says "Only kept on this computer, as your own record. Please do not write passwords or ID numbers." <!-- src/freemyid/wizard/dashboard.py:191-192 -->

When the call is done, the button says "I finished it". <!-- src/freemyid/wizard/dashboard.py:185 -->

The script says "Never agree to pay." (src/freemyid/templates/phone_script.txt.j2, line 22)

**What it means**

A few sites take a request only by phone.
The card holds a short script.
You make the call.
The note is optional.
It stays on this computer as your own record.
You can leave the note empty.

**One thing to do**

1. Call the number on the card.
2. Say what the script says, and do not add extra details.
3. Do not pay, and do not give a Social Security number.
4. Press **I finished it** when the call is done.

**When to stop and ask someone you trust**

Stop the call if they ask you to pay.
Stop if they ask for a Social Security number, a bank, or a card.
Ask someone you trust to sit with you if the call feels wrong.

## When you want to pause

**What the screen says**

You can pause in two ways.
They are not the same.

To stop new requests, the heading says "Real requests are on". <!-- src/freemyid/wizard/dashboard.py:517 -->

The button says "Go back to practice mode". <!-- src/freemyid/wizard/dashboard.py:519-520 -->

Practice mode says "Free My ID looks for listings but does not send any request." <!-- src/freemyid/wizard/dashboard.py:510-511 -->

The confirm screen says "Requests already sent cannot be taken back." <!-- src/freemyid/wizard/dashboard.py:489-490 -->

To stop the daily check, look under "Run automatically". <!-- src/freemyid/wizard/dashboard.py:502 -->

One button says "Turn off". <!-- src/freemyid/wizard/dashboard.py:507 -->

The other button says "Turn on". <!-- src/freemyid/wizard/dashboard.py:506 -->

**What it means**

**Go back to practice mode** stops new requests.
Free My ID can still look.
A request already sent stays sent.
**Turn off** stops the once-a-day check.
It does not undo a request that already went out.

**One thing to do**

1. Open Settings.
2. Press **Go back to practice mode** to stop new requests.
3. Press **Turn off** to stop the daily check.

**When to stop and ask someone you trust**

Ask someone you trust first if you are not sure which button you want.
Do not press either button if you only wanted to look.
If a button does not respond, open [Troubleshooting](troubleshooting.md#settings-and-other-messages).

## When someone calls or emails as "Free My ID"

**What the screen says**

The app does not show this call or email.
On the first setup screen, the words below are shown.

"Never asks for your Social Security number, bank or card details." <!-- src/freemyid/wizard/ui.py:266-267 -->

In Settings, the screen says "It never pays." <!-- src/freemyid/wizard/dashboard.py:529 -->

The same line says the words below.

"It will never ask for a Social Security number or bank or card details." <!-- src/freemyid/wizard/dashboard.py:529 -->

The Protect yourself page says the words below.

"Free My ID never pays for you and never asks for your Social Security number." <!-- src/freemyid/wizard/views.py:273-274 -->

**What it means**

A person using the name Free My ID is not the app.
The app never asks for a Social Security number.
The app never asks for bank or card details.
The app never pays for you.
It does not ask you for money.

**One thing to do**

1. Hang up, or do not reply to the email.
2. Do not pay.
3. Do not give a Social Security number, a bank, or a card.
4. Open Free My ID from its own icon if you want to look.

**When to stop and ask someone you trust**

Tell someone you trust about the call or email.
If you already paid, ask them to help you talk to your bank.
If you already gave a Social Security number, ask them to help you right away.

If your screen is not listed here, and it says something failed, open [Troubleshooting](troubleshooting.md).
If you are still unsure, ask someone you trust.
