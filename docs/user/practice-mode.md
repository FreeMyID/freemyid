# Is it doing anything yet?

This page is for you when you wonder if Free My ID is doing anything yet.

The only example person here is Jane Q Testperson, of Springfield IL.

## What practice mode does

Free My ID starts in practice mode.

It looks for your listings and shows them to you.

A listing is a page that shows a person's details.

People-search sites list names, addresses and phone numbers.

Looking for a listing still visits that site.

That visit is a search, not a removal request.

A removal request asks the site to take that listing down.

## What you see

The "Today" screen has a note at the top. <!-- src/freemyid/wizard/ui.py:43 -->

The note starts with "Practice mode:". <!-- src/freemyid/wizard/dashboard.py:237 -->

It says "Free My ID is looking for your listings, but no removal requests go out until you say so." <!-- src/freemyid/wizard/dashboard.py:237 -->

It offers "Change this in Settings" when you are ready. <!-- src/freemyid/wizard/dashboard.py:239 -->

Open "Settings". <!-- src/freemyid/wizard/ui.py:44 -->

A box there is titled "Practice mode is on". <!-- src/freemyid/wizard/dashboard.py:510 -->

The box says "Free My ID looks for listings but does not send any request." <!-- src/freemyid/wizard/dashboard.py:510 -->

That means no removal request.

The search still visits the sites.

A listing it found can show "your details are listed". <!-- src/freemyid/wizard/ui.py:26 -->

That means it is showing you the listing.

## What does not happen yet

Free My ID does not send a removal request until you turn real requests on.

One button works differently, and that part is below.

If you press "Yes, this is me", practice mode still holds that request. <!-- src/freemyid/wizard/dashboard.py:122 -->

The card says "In practice mode no removal requests go out." <!-- src/freemyid/wizard/dashboard.py:130 -->

The check page says "The first email for every person always waits for your OK." <!-- src/freemyid/wizard/dashboard.py:486 -->

It also says `Emails for people who chose "approve each" wait for your OK first.` <!-- src/freemyid/wizard/dashboard.py:486 -->

It says "You can switch back to practice mode in Settings at any time." <!-- src/freemyid/wizard/dashboard.py:488 -->

It says "Requests already sent cannot be taken back." <!-- src/freemyid/wizard/dashboard.py:489 -->

## When to turn on real requests

Look at the results first.

You can do that with someone you trust, if you like.

The box says "When you have looked at the results and are happy, turn on real requests." <!-- src/freemyid/wizard/dashboard.py:511 -->

If a check is still running, you may see "Please let a practice check finish first, then look at the results." <!-- src/freemyid/wizard/server.py:69 -->

Wait for that check.

Then look at the results again.

## How to turn real requests on

1. Press "Settings". <!-- src/freemyid/wizard/ui.py:44 -->
2. "Turn on" and "Turn off" under "Run automatically" only change the daily check. <!-- src/freemyid/wizard/dashboard.py:502 -->
3. Find the box "Practice mode is on". <!-- src/freemyid/wizard/dashboard.py:510 -->
4. Press "Start sending real requests". <!-- src/freemyid/wizard/dashboard.py:515 -->
5. Read the page "Start sending real requests?". <!-- src/freemyid/wizard/dashboard.py:481 -->
6. Check the line "This is for:" and the name beside it. <!-- src/freemyid/wizard/dashboard.py:482 -->
7. For this example, the name is Jane Q Testperson.
8. Read "Free My ID will now send your requests to people-search sites by email and, where a site allows it, fill in their forms." <!-- src/freemyid/wizard/dashboard.py:483 -->
9. Read "Each request names the person and only the details the site already shows, plus the separate email address." <!-- src/freemyid/wizard/dashboard.py:484 -->
10. Read "Nothing is paid for." <!-- src/freemyid/wizard/dashboard.py:485 -->
11. Read "Some sites need steps by hand, and details can come back." <!-- src/freemyid/wizard/dashboard.py:488 -->
12. Press "Yes, start sending real requests" to start. <!-- src/freemyid/wizard/dashboard.py:493 -->
13. Or press "No, stay in practice mode" to wait. <!-- src/freemyid/wizard/dashboard.py:494 -->

## How to go back

1. Press "Settings". <!-- src/freemyid/wizard/ui.py:44 -->
2. Find the box "Real requests are on". <!-- src/freemyid/wizard/dashboard.py:517 -->
3. Press "Go back to practice mode". <!-- src/freemyid/wizard/dashboard.py:519 -->

Going back stops new removal requests.

A request already sent stays requested.

You cannot take that request back.

## One step that is different

A card may show "Fill it in for me". <!-- src/freemyid/wizard/dashboard.py:157 -->

That step can send one real request while practice mode is still on.

Free My ID warns you first.

The warning is titled "This sends a real request to the site." <!-- src/freemyid/wizard/dashboard.py:347 -->

It says "You are in practice mode, but this step is different." <!-- src/freemyid/wizard/dashboard.py:348 -->

It says "When you press Submit on the site, your request is real." <!-- src/freemyid/wizard/dashboard.py:349 -->

It says "Free My ID never presses Submit for you." <!-- src/freemyid/wizard/dashboard.py:350 -->

Press "I understand, continue" only if you want that request. <!-- src/freemyid/wizard/dashboard.py:353 -->

Press "Not now" to skip it. <!-- src/freemyid/wizard/dashboard.py:354 -->

## Requested and confirmed

After real requests are on, a site can show "asked". <!-- src/freemyid/wizard/ui.py:26 -->

"asked" means the removal was requested.

A site can show "site confirmed". <!-- src/freemyid/wizard/ui.py:28 -->

That means that site confirmed.

Confirmed is for that one site only.

Details can come back later.

Free My ID keeps checking for that reason.

## More help

Messages you may see are listed in [Troubleshooting: messages you may see](troubleshooting.md).

Plain meanings of words are in the [glossary of plain words](GLOSSARY.md).
