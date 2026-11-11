# Free My ID never asks for a Social Security number, bank details or card details

This page helps you, or a helper, see what Free My ID never asks for: a Social Security number, bank details or card details.

Example person: Jane Q Testperson, Springfield IL.

## What the app itself says

The first setup screen shows this promise.

"No account. No cloud. Never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime." <!-- src/freemyid/wizard/ui.py:266-267 -->

In Settings, the heading is "What Free My ID may do". <!-- src/freemyid/wizard/dashboard.py:527 -->

That hint says "It never pays." <!-- src/freemyid/wizard/dashboard.py:529 -->

It also says "It will never ask for a Social Security number or bank or card details." <!-- src/freemyid/wizard/dashboard.py:529 -->

On Protect yourself, the hint says "Free My ID never pays for you". <!-- src/freemyid/wizard/views.py:273 -->

The same hint says "These steps happen on the real company websites, in your own browser." <!-- src/freemyid/wizard/views.py:274 -->

## Three things it does not ask for

The website page Is it safe? names these three items.

The lines are web/src/pages/safety/index.astro, lines 71, 72 and 74.

1. Your Social Security number.
2. Bank account, credit or debit card details.
3. A payment of any kind.

That same page names two more items, on lines 75 and 77.

The page says it does not ask for your full birthday.

The setup label is "Year of birth". <!-- src/freemyid/wizard/ui.py:311 -->

You can leave that box blank. <!-- src/freemyid/wizard/draft.py:324 -->

The page says it does not ask for the password to your everyday email.

A removal mailbox is optional.

The label on that screen is "App password". <!-- src/freemyid/wizard/ui.py:366 -->

If the box is empty, you may see "Please enter the app password. (It is not your normal email password.)" <!-- src/freemyid/wizard/draft.py:386 -->

You can choose "Skip, I'll do these by hand" instead. <!-- src/freemyid/wizard/ui.py:207 -->

## What another site may ask

A [people-search site](GLOSSARY.md#people-search-site-also-called-a-data-broker) may ask on its own page.

It may ask for a photo ID, an account, or your phone number.

Free My ID does not take that step unless you allow it.

The screen says "If a site wants a photo ID, an account or your phone number, Free My ID stops and asks, unless you allowed that in Settings." <!-- src/freemyid/wizard/dashboard.py:129-130 -->

Settings says "Everything here is off unless you tick it." <!-- src/freemyid/wizard/dashboard.py:528 -->

If you did not allow it, "Free My ID stops and asks you." <!-- src/freemyid/wizard/dashboard.py:529 -->

Free My ID stops and asks you first.

These boxes stay off until you tick them.

"Free My ID may upload a copy of an ID if a website requires it" <!-- src/freemyid/wizard/dashboard.py:532-533 -->

"Free My ID may create an account on a website if required" <!-- src/freemyid/wizard/dashboard.py:534-535 -->

Press "Save" only when you mean to allow that. <!-- src/freemyid/wizard/dashboard.py:538 -->

A credit bureau may ask on its own site too.

The Equifax checklist lists "Your Social Security number" (brokers/checklists.yaml, line 28).

It says "You make a free myEquifax account" (brokers/checklists.yaml, line 31).

It says Equifax sends a code by text, or asks questions about your credit history (brokers/checklists.yaml, line 32).

The Experian checklist lists "Your Social Security number" (brokers/checklists.yaml, line 49).

It says "Make a free Experian account, or sign in if you have one." (brokers/checklists.yaml, line 52).

By mail, that checklist asks for a copy of a photo ID (brokers/checklists.yaml, line 55).

Those questions come from the bureau, on the bureau's own page.

A code on that page is not a call from Free My ID.

On Protect yourself, you press "Open the web page". <!-- src/freemyid/wizard/views.py:215 -->

You do the bureau step in your own browser.

Then you can press "I did this". <!-- src/freemyid/wizard/views.py:218 -->

## How a real message looks

A real message is a screen on your computer.

Or it is an email you read in the app before it goes out.

The page title is "Emails waiting for your approval". <!-- src/freemyid/wizard/dashboard.py:449 -->

The button says "Approve and send". <!-- src/freemyid/wizard/dashboard.py:473 -->

The hint says "Approving sends this email from the removal mailbox." <!-- src/freemyid/wizard/dashboard.py:468-469 -->

One letter subject is "Request to remove my personal information" (src/freemyid/templates/generic_removal.txt.j2, line 1).

That letter is a removal you requested.

It goes to a site.

It does not ask you for money.

Later the app may say "They confirmed". <!-- src/freemyid/wizard/views.py:32 -->

That means one site confirmed. It does not mean every site is done.

For Proton Mail Bridge, the screen can ask "Do you trust this code?" <!-- src/freemyid/wizard/server.py:817 -->

Above that, it says "Free My ID found your mail app on this computer. Please check that the code below matches the one in Proton Mail Bridge." <!-- src/freemyid/wizard/server.py:813-814 -->

You check that code on this computer.

You do not read it to a caller.

The buttons are "Yes" and "No". <!-- src/freemyid/wizard/ui.py:387-388 -->

The website says "We will never email you an installer, and we will never call you." (web/src/pages/safety/index.astro, line 111).

## If someone asks in the name of Free My ID

If someone calls, texts, or emails and says they are Free My ID, read this.

If they ask for money, it is not Free My ID.

If they ask for a password, it is not Free My ID.

If they ask for a code, it is not Free My ID.

If they ask for a Social Security number, it is not Free My ID.

Hang up, or do not reply.

Tell someone you trust.

Jane Q Testperson in Springfield IL would tell a helper she already knows.

## What to do

1. Do not give money, a password, a code, or a Social Security number.
2. Hang up, or do not reply.
3. Tell someone you trust.
4. Open Free My ID from its own icon.
5. Read the promise on the first screen, or the hint in Settings.
6. If a site wants a photo ID or an account, wait.
7. Free My ID stops and asks you before that step.
8. Tick a Settings box only if you choose to allow it.
9. Press "Save" when you are ready. <!-- src/freemyid/wizard/dashboard.py:538 -->

## Pages that already exist

- What an [app password](GLOSSARY.md#app-password) is.
- What the [security code](GLOSSARY.md#security-code-for-bridge) is.
- The [Proton Mail security-code question](mail-proton.md#step-3-test-it-and-answer-the-security-code-question).
- [Helping someone set up Free My ID](HELPING.md).
- A longer helper list: [helper's guide](../HELPER_GUIDE.md#6-what-free-my-id-will-never-ask-for-and-never-do).
