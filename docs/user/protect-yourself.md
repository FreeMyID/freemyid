# Protect yourself

This page helps Jane Q Testperson in Springfield IL with the Protect yourself steps.

The screen lead says "Removing your details from people-search sites is one part. These steps help stop someone using them. Each one is optional, most are free, and you can tick them off as you go. The ticks stay on this computer." <!-- src/freemyid/wizard/views.py:254-257 -->

People-search removal is a different job. The [user guide](../USER_GUIDE.md) explains that part.

A tick means you confirmed the step on this computer.
It does not mean the bureau put a freeze in place.
You requested the step on the company site.
Ask the bureau if you need to know it is on.

## What a freeze does

These limits are only what the checklist says.
If a line below does not answer you, ask the bureau.

1. "A freeze stops a thief from opening new credit in your name." (checklists.yaml, line 24)
2. "It does not hurt your credit score." (checklists.yaml, line 24)
3. Experian and TransUnion use that same reason (checklists.yaml, line 45 and line 66).
4. "A freeze at one bureau does not freeze the others." (checklists.yaml, line 37)
5. "Each bureau must be frozen on its own." (checklists.yaml, line 45)
6. Equifax says to lift it when you apply for credit (checklists.yaml, line 35).
7. Choose "Manage a Freeze" there, to lift it for a while or remove it (checklists.yaml, line 35).
8. The checklist does not say a freeze closes accounts you already have.
9. It does not say old lenders can still see Equifax, Experian, or TransUnion.
10. At LexisNexis, companies you already do business with can still look (checklists.yaml, line 159).
11. "NCTUE says there are some exceptions to what a freeze blocks." (checklists.yaml, line 138)
12. The checklist does not say how many days Equifax or TransUnion take.
13. Experian online "starts in real time" (checklists.yaml, line 53).
14. Experian mail "can take up to 3 days" (checklists.yaml, line 55).
15. The checklist does not say a freeze takes you off people-search sites.
16. "Never pay anyone to freeze your credit. It is free." (checklists.yaml, line 78)

ChexSystems is for a new checking or savings account (checklists.yaml, line 108).
Innovis is free under the FTC rule, but its page states no price (checklists.yaml, line 88).
The child Equifax step is a mail request (checklists.yaml, line 181).
Teens 16 and 17 can ask Equifax by phone or mail (checklists.yaml, line 180).
Freeze that child at the other bureaus too (checklists.yaml, line 179).
Those other child steps are not written out. Ask the bureau.

## Freeze steps, in checklist order

Use these titles exactly as the screen shows them.
Follow the steps on the card.
Press the button. Do not type a web address from memory.

1. "Freeze your credit at Equifax" (checklists.yaml, line 23)
2. "Freeze your credit at Experian" (checklists.yaml, line 44)
3. "Freeze your credit at TransUnion" (checklists.yaml, line 65)
4. "Freeze your credit at Innovis (the fourth bureau)" (checklists.yaml, line 86)
5. "Freeze your ChexSystems report (bank accounts)" (checklists.yaml, line 107)
6. "Freeze your NCTUE report (phone, power and utility accounts)" (checklists.yaml, line 125)
7. "Freeze your LexisNexis Risk Solutions file" (checklists.yaml, line 145)
8. "Freeze your child's credit at Equifax (child under 16)" (checklists.yaml, line 166)

## How to tick a step

1. Choose "Protect yourself" in the main menu. <!-- src/freemyid/wizard/ui.py:43 -->
2. If several people are set up, choose Jane Q Testperson. <!-- src/freemyid/wizard/views.py:264 -->
3. The count says how many steps are done for that person. <!-- src/freemyid/wizard/views.py:268 -->
4. The word done means you ticked it, not that the bureau answered.
5. Open one card and read "Cost:" and "Time:". <!-- src/freemyid/wizard/views.py:206 -->
6. Read "Have these ready", then "Steps", then "Good to know". <!-- src/freemyid/wizard/views.py:208 -->
7. Press "Open the web page". <!-- src/freemyid/wizard/views.py:215 -->
8. Do that company's steps in your own browser.
9. You requested the step on that site, not inside Free My ID.
10. Come back and press "I did this" when you have finished. <!-- src/freemyid/wizard/views.py:218 -->
11. That tick means you confirmed the step on this computer.
12. It does not mean a freeze is in place. Ask the bureau.
13. Press "I have not done this" to clear a tick. <!-- src/freemyid/wizard/views.py:218 -->
14. Read "To undo it:" before you apply for credit or a bank account. <!-- src/freemyid/wizard/views.py:211 -->
15. You lift or remove the freeze yourself. Ask the bureau if the card is silent.
16. If the list is missing, the screen says "The list is not available right now." <!-- src/freemyid/wizard/views.py:259 -->

## What Free My ID will not ask

The bottom of the screen says "Free My ID never pays for you". It also says "These steps happen on the real company websites, in your own browser." <!-- src/freemyid/wizard/views.py:273-274 -->
Free My ID never asks for your Social Security number, bank details or card details. <!-- src/freemyid/wizard/ui.py:266-267 -->

The welcome screen also says "Never asks for your Social Security number, bank or card details." <!-- src/freemyid/wizard/ui.py:267 -->

Settings says "It never pays. It will never ask for a Social Security number or bank or card details." <!-- src/freemyid/wizard/dashboard.py:529 -->

Adult freeze cards list "Your Social Security number" (checklists.yaml, line 28).
The same words are on lines 49, 70, 90, 112, 130 and 150.
The child card asks for copies of the child's Social Security card (checklists.yaml, line 171).
You type those on the bureau site.
That is the bureau, not Free My ID.

## When the card shows a caution

Some cards show this note. "We could not read this company's own page when we prepared these steps, so some details come from trusted consumer-help sites. This is still a good thing to do. Before you type anything in or call a number, check the address and the phone number on the company's own page." <!-- src/freemyid/wizard/views.py:185 -->

That note is on TransUnion and ChexSystems (checklists.yaml, line 81 and line 121).
It is also on pre-approved offers, my Social Security, Google, and Bing (checklists.yaml, lines 206, 294, 339 and 362).
Check the company's own page before you type or call.
Ask the bureau if the card and the page disagree.

## Google and Bing use different buttons

1. A group named "Google and Bing" sits above the count. <!-- src/freemyid/wizard/views.py:228 -->
2. The group says "Free My ID does not search Google or Bing for you". <!-- src/freemyid/engine/search_engines.py:34 -->
3. Press "Open the page for me". <!-- src/freemyid/wizard/views.py:242 -->
4. The other open button says "Or open the link yourself". <!-- src/freemyid/wizard/views.py:244 -->
5. The tick buttons are still "I did this" and "I have not done this". <!-- src/freemyid/wizard/views.py:247 -->
6. The same two steps appear again in the full list, with "Open the web page". <!-- src/freemyid/wizard/views.py:215 -->
7. The top group and the later card share one tick.

## The other safety steps

Each of these is one card under the freezes.
One line each. The card has the steps.

1. "Stop pre-approved credit card and insurance offers in the mail." It is free (checklists.yaml, line 189 and line 192).
2. "Cut down on junk mail with DMAchoice." The site sets a small fee (checklists.yaml, line 210 and line 213).
3. "Join the National Do Not Call Registry." Do not pay anyone to register you (checklists.yaml, line 232 and line 235).
4. "Get an IRS Identity Protection PIN (IP PIN)." It is free, on the IRS site (checklists.yaml, line 254 and line 257).
5. "Claim your my Social Security account (before a thief does)." It is free (checklists.yaml, line 278 and line 281).
6. "Sign up for USPS Informed Delivery." You see a picture of each letter before it arrives (checklists.yaml, line 298 and line 299).
7. "Ask Google to hide your phone, address or email from search results." The result is hidden from Search only (checklists.yaml, line 320 and line 335).
8. "Ask Bing to drop old copies of pages that were removed." Only Bing's own copy (checklists.yaml, line 343 and line 355).
9. "California DROP: one request to all registered data brokers (California residents only)." (checklists.yaml, line 367)

Jane Q Testperson in Springfield IL would skip the California step.
It is only for California residents (checklists.yaml, line 374).
DMAchoice is the paid one. Free My ID never pays that fee (checklists.yaml, line 225).
Pay only on the site named on that card, which is dmachoice.org (checklists.yaml, line 225).
