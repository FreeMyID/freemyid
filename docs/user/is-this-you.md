# Is this you?

This page is for you, or a helper, when a listing might be yours.

Example person: Jane Q Testperson, Springfield IL.

You can answer alone.
You can also sit with someone you trust.
You do not have to press a button today.

## Why the card appears

Free My ID found a people-search page with the same name.
The same name is not enough for it to be sure.
The card says "Why it is a possible match:". <!-- src/freemyid/wizard/dashboard.py:117 -->
It says "the name is the same". <!-- src/freemyid/wizard/dashboard.py:117 -->
It says "That is not enough for Free My ID to be sure it is you." <!-- src/freemyid/wizard/dashboard.py:118 -->

One more clue may be listed.
That clue can be "the city", "the age", or "a relative's name". <!-- src/freemyid/wizard/dashboard.py:101 -->
It can also be "a phone number" or "an email address". <!-- src/freemyid/wizard/dashboard.py:102 -->
A phone or email search may say "the phone number" or "the email address". <!-- src/freemyid/wizard/dashboard.py:103 -->
Any one of those is still not enough.
Only you can say if the page is yours.

## The three buttons

The card shows these three buttons.
"Open the page" is there when Free My ID has a page to open.

1. **"Open the page"** <!-- src/freemyid/wizard/dashboard.py:121 -->
2. **"Yes, this is me"** <!-- src/freemyid/wizard/dashboard.py:122 -->
3. **"No, this is not me"** <!-- src/freemyid/wizard/dashboard.py:123 -->

### Open the page

The card says "Open the page first if you want to look." <!-- src/freemyid/wizard/dashboard.py:125 -->
The card says "Only you can say whether it is you." <!-- src/freemyid/wizard/dashboard.py:125 -->
This button does not pick Yes or No.
The card stays up after you look.

### Yes, this is me

The card says "If you press Yes:". <!-- src/freemyid/wizard/dashboard.py:127 -->
"Free My ID will ask this site to take the listing down on its next check." <!-- src/freemyid/wizard/dashboard.py:127 -->
"Free My ID may send the request by itself, or ask you to approve an email or do a step, depending on the site and your settings." <!-- src/freemyid/wizard/dashboard.py:128 -->
"If a site wants a photo ID, an account or your phone number, Free My ID stops and asks, unless you allowed that in Settings." <!-- src/freemyid/wizard/dashboard.py:129 -->
"In practice mode no removal requests go out." <!-- src/freemyid/wizard/dashboard.py:130 -->

Pressing Yes confirms that this listing is you.
Free My ID will then request a removal on its next check.
Requested does not mean the site has taken the listing down.
The screen says this.
"Thank you. Free My ID will ask that site to remove the listing on its next check, if your settings allow it." <!-- src/freemyid/wizard/server.py:60 -->

In practice mode, no removal request goes out.
Your Yes is still kept.
Later, when real requests are on, Free My ID can request removal.
It may still ask you to approve an email or do a step.

### No, this is not me

The card says "If you press No:". <!-- src/freemyid/wizard/dashboard.py:132 -->
"nothing will be sent for this listing, and Free My ID will not ask about it again." <!-- src/freemyid/wizard/dashboard.py:132 -->

No removal request goes out for that listing.
Free My ID will not ask about it again.
The screen says "Thank you. Nothing will be sent for that listing." <!-- src/freemyid/wizard/server.py:62 -->

## How to look at the page safely

Look before you press Yes or No.
Use Jane Q Testperson, Springfield IL, as the example.

1. Press "Open the page". <!-- src/freemyid/wizard/dashboard.py:121 -->
2. Free My ID says "Opened in your web browser. Come back here when you are finished." <!-- src/freemyid/wizard/server.py:52 -->
3. If the browser does not open, it says "Could not open your browser. Try again." <!-- src/freemyid/wizard/server.py:53 -->
4. The page in the browser is that site's own page.
5. Compare the name with Jane Q Testperson.
6. Compare the age, if the page shows one.
7. Compare the city with Springfield IL.
8. Compare the relatives, if the page lists any.
9. Do not pay on that page.
10. Do not sign up on that page.
11. Come back to Free My ID.
12. The card is still there.
13. Press Yes or No only after you decide.

If you do not see "Open the page", do not guess. <!-- src/freemyid/wizard/dashboard.py:121 -->
Wait, and ask someone you trust.

## Not sure?

It is fine to wait.
Ask someone you trust to look with you.
The card stays on your list until you press Yes or No.
Opening the page does not answer it.
A helper can sit beside you.
You still press the button yourself.
See [Helping someone set up Free My ID](HELPING.md).

## The first answer stays

The first answer stays.
A second press does not flip it.
Yes stays Yes.
No stays No.
The screen says "That question was already answered. Nothing was changed." <!-- src/freemyid/wizard/server.py:63 -->
If you are not sure, do not press yet.
Wait, and ask someone you trust.
