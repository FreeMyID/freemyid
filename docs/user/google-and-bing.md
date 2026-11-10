# Google and Bing on Protect yourself

This page helps you do the Google and Bing steps in Free My ID.

Example person used below: Jane Q Testperson, Springfield IL.

## Open the group

1. Open Free My ID.
2. Press "Protect yourself" in the menu at the top. <!-- src/freemyid/wizard/ui.py:43 -->
3. The page heading is "Protect yourself". <!-- src/freemyid/wizard/views.py:254 -->
4. If more than one person is set up, press the name you want.
5. For this example, that name is Jane Q Testperson.
6. You can also start from "Today". <!-- src/freemyid/wizard/ui.py:43 -->
7. Press "More: safety steps and details". <!-- src/freemyid/wizard/dashboard.py:275 -->
8. Under "Protect yourself", open the link that starts with "Google and Bing:". <!-- src/freemyid/wizard/dashboard.py:306 -->
9. That link shows only while a step is still to do.
10. When both steps are done, use the menu in step 2.

The page says:

"Removing your details from people-search sites is one part. These steps help stop someone using them. Each one is optional, most are free, and you can tick them off as you go. The ticks stay on this computer." <!-- src/freemyid/wizard/views.py:254 -->

## What this group is

The group heading is "Google and Bing". <!-- src/freemyid/wizard/views.py:228 -->

Under it, Free My ID says:

`Google and Bing can show pages about you, even after a people-search site removes your listing. Free My ID does not search Google or Bing for you: their rules do not allow automatic searches. We open their own official page, and you do the steps there. When you have finished, tick "I did this" so we remember the date.` <!-- src/freemyid/engine/search_engines.py:33 -->

Free My ID does not search Google or Bing.
It opens their page.
You do the steps there.
You then press the button so the date is saved.

## You will see each step twice

The top group is one short card for Google and one for Bing.
The same two items appear again, lower on the page, as full cards.
The buttons are not the same.
A tick on either card is the same tick.

Use the top card to open the page and to read the status.
Use the lower card for the full steps.
A count under the group includes these two steps.
Ticking one moves that count.

### Buttons on the top card

1. Press "Open the page for me". <!-- src/freemyid/wizard/views.py:241 -->
2. That opens the official page and remembers that you opened it.
3. Or press "Or open the link yourself". <!-- src/freemyid/wizard/views.py:243 -->
4. That opens the same address in a new browser tab.
5. It does not remember the open.
6. When you finish, press "I did this". <!-- src/freemyid/wizard/views.py:246 -->
7. You see "I did this" while the step is not marked done. <!-- src/freemyid/wizard/views.py:246 -->
8. After it is marked done, the button says "I have not done this". <!-- src/freemyid/wizard/views.py:246 -->
9. Press "I have not done this" only if you marked it by mistake. <!-- src/freemyid/wizard/views.py:246 -->

### Buttons on the lower card

1. The lower card says "Open the web page". <!-- src/freemyid/wizard/views.py:215 -->
2. That also opens the official page.
3. It does not switch the top status to the opened line.
4. The lower card also says "I did this" or "I have not done this". <!-- src/freemyid/wizard/views.py:218 -->
5. Those words match the top card.
6. Either "I did this" button saves the same tick. <!-- src/freemyid/wizard/views.py:246 -->

The lower card has the headings "Have these ready", "Steps", "Good to know", and "To undo it:". <!-- src/freemyid/wizard/views.py:208 -->

It also shows "Cost:" and "Time:". <!-- src/freemyid/wizard/views.py:206 -->

It shows "Checked on" and then a date. <!-- src/freemyid/wizard/views.py:212 -->

## What the status line says

Each top card has one status line.
There are four lines.
Only one shows at a time.

1. "Not done yet." <!-- src/freemyid/engine/search_engines.py:66 -->
2. This shows before you use "Open the page for me", and before you tick the step. <!-- src/freemyid/wizard/views.py:241 -->
3. `You opened the page. Tick "I did this" when you have finished.` <!-- src/freemyid/engine/search_engines.py:67 -->
4. This shows after "Open the page for me", until you tick the step. <!-- src/freemyid/wizard/views.py:241 -->
5. The line can add "Opened on" and the date you opened it. <!-- src/freemyid/wizard/views.py:235 -->
6. "Done." <!-- src/freemyid/engine/search_engines.py:68 -->
7. This shows after you press "I did this". <!-- src/freemyid/wizard/views.py:246 -->
8. The line can add "Done on" and the date you finished. <!-- src/freemyid/wizard/views.py:233 -->
9. `A site removed your listing since you last did this. Please do it again so the search engine drops the old page.` <!-- src/freemyid/engine/search_engines.py:69 -->
10. This "do it again" line is for Bing, not for Google.
11. It shows when a people-search site removes a listing after your last tick.
12. The old "Done on" date can still sit on that line. <!-- src/freemyid/wizard/views.py:233 -->
13. The button goes back to "I did this". <!-- src/freemyid/wizard/views.py:246 -->
14. Do the Bing steps again, then press "I did this". <!-- src/freemyid/wizard/views.py:246 -->
15. Google stays on "Done." <!-- src/freemyid/engine/search_engines.py:68 -->
16. Google's tool keeps watching.
17. Free My ID does not ask you to repeat the Google step for this reason.

## What this cannot do

Free My ID does not take the page off the other website.
It does not search Google or Bing.
You request the change on their page.
Google decides for Google.
Bing decides for Bing.
A request is not the same as them saying yes.
Free My ID does not mark their answer for you.
Check their page later to see what they decided.

The More page says "Free My ID does not change anything on Facebook or Google." <!-- src/freemyid/wizard/dashboard.py:317 -->

That line means Free My ID does not change those accounts by itself.
You still open the page and send the request yourself.

"Free My ID never pays for you and never asks for your Social Security number. These steps happen on the real company websites, in your own browser." <!-- src/freemyid/wizard/views.py:273 -->

## A note on the lower card

Both lower cards show this note:

"We could not read this company's own page when we prepared these steps, so some details come from trusted consumer-help sites. This is still a good thing to do. Before you type anything in or call a number, check the address and the phone number on the company's own page." <!-- src/freemyid/wizard/views.py:185 -->

The top group does not show that note.
Read it on the lower card before you type.
If a label on their page differs, follow their page.
Do not follow a screen this page does not list.

## Google

The top card starts with the word "Google". <!-- src/freemyid/engine/search_engines.py:50 -->

The title is "Ask Google to hide your phone, address or email from search results" (brokers/checklists.yaml, line 320).

The top card then says:

"Google's free tool watches for your phone number, home address and email, and lets you ask Google to stop showing those results." <!-- src/freemyid/engine/search_engines.py:52 -->

The lower card explains it this way (brokers/checklists.yaml, line 321):

"Google can show your personal contact details. This tool finds them and asks Google to stop showing those pages."

Free My ID opens this address (brokers/checklists.yaml, line 322):

https://goo.gle/resultsaboutyou

Have these ready (brokers/checklists.yaml, line 325):

1. "A Google account".
2. "The name, phone number, home address and email address you want Google to watch for".
3. For this example, the name is Jane Q Testperson, in Springfield IL.
4. Type a phone or email only if you want that one watched.

The lower card lists the cost as "Free." (brokers/checklists.yaml, line 323).
The time is "10 minutes to set up, then a few minutes per result." (brokers/checklists.yaml, line 324).
The checked date is 2026-11-07 (brokers/checklists.yaml, line 338).

Do the steps the lower card lists (brokers/checklists.yaml, lines 327-332):

1. Open the web address above, or open the Google app and tap your picture, then 'Results about you'.
2. Sign in and type the details you want watched (name, address, phone, email).
3. Google lists results that match. Open one and choose 'Request to remove'.
4. Type your contact info exactly as it shows on that page when asked.
5. Turn on notifications so Google tells you when new matches appear.
6. Check the status later on the same page: in progress, approved, denied or undone.

Then come back to Free My ID and press "I did this". <!-- src/freemyid/wizard/views.py:246 -->

Google's page will ask you to sign in and to name what it should watch.
Use the words on that page if a label has moved.
You have requested that Google stop showing the result.
Google decides.
The other website can still show the page.

Under "Good to know", the card says (brokers/checklists.yaml, lines 335-336): <!-- src/freemyid/wizard/views.py:210 -->

1. Google hides the result from Search only. The page stays on the other website, so you still need to ask that site to remove it.
2. Google rarely removes results from government, school or news sites.

To change it later, the card says "To undo it:" and then (brokers/checklists.yaml, line 333): <!-- src/freemyid/wizard/views.py:211 -->

"In Settings choose 'Remove all personal info' to stop watching and delete what you entered."

That Settings is on Google's tool, not in Free My ID.

## Bing

The top card starts with the word "Bing". <!-- src/freemyid/engine/search_engines.py:56 -->

The title is "Ask Bing to drop old copies of pages that were removed" (brokers/checklists.yaml, line 343).

The top card then says:

"After a people-search site removes your page, Bing can keep showing the old copy for a while. Bing's form asks Bing to look at the page again and drop the old copy." <!-- src/freemyid/engine/search_engines.py:58 -->

The lower card explains it this way (brokers/checklists.yaml, line 344):

"After a people-search site removes your page, Bing can keep showing the old page or its preview for a while. Bing has a tool where the owner of a page, or anyone reporting it, can ask Bing to update or drop it."

Free My ID opens this address (brokers/checklists.yaml, line 345):

https://www.bing.com/webmasters/tools/contentremoval

Have these ready (brokers/checklists.yaml, line 348):

1. "The web address of the page that was removed (copy it from the Bing result)".
2. "A Microsoft, Google or Facebook account to sign in with".
3. A Google account is one sign-in choice. It is not the only one.

The lower card lists the cost as "Free." (brokers/checklists.yaml, line 346).
The time is "A few minutes per page. Bing can take days or weeks to act." (brokers/checklists.yaml, line 347).
The checked date is 2026-11-08 (brokers/checklists.yaml, line 361).

Do the steps the lower card lists (brokers/checklists.yaml, lines 350-354):

1. First make sure the people-search site has removed your page. Open the page: it should be gone or no longer show you.
2. Open the Bing web address above. Bing asks you to sign in with a Microsoft, Google or Facebook account.
3. Follow the form. Paste the web address of the page, then choose whether you are asking Bing to remove the page or to update its old saved copy (the 'cache').
4. Not working or no sign-in wanted? Use Microsoft's 'Report a Concern to Bing' page: https://www.microsoft.com/en-us/concern/bing
5. Come back here and tick 'I did this'. <!-- src/freemyid/wizard/views.py:246 -->

Bing's page will ask you to sign in, then to paste the page address.
Free My ID does not show the form that sits past that sign-in.
Follow the form that Bing shows.
You have requested that Bing look at the page again.
Bing decides.
Bing does not change the page on the other website.

Under "Good to know", the card says (brokers/checklists.yaml, lines 357-359): <!-- src/freemyid/wizard/views.py:210 -->

1. Bing does not control what other websites publish. Microsoft says your best option is to contact the website itself, and that reporting a concern will not necessarily remove a result.
2. Bing will not remove a page that is still live just because you ask. Ask the people-search site to remove it first.
3. Live in Europe or the UK? Microsoft also has a separate form to block results shown for searches on your name.
4. The card does not give that form a web address.
5. Use the words on the Microsoft page you already have open.

To change it later, the card says "To undo it:" and then (brokers/checklists.yaml, line 355): <!-- src/freemyid/wizard/views.py:211 -->

"Nothing to undo. Bing only refreshes or drops its own copy. The page is not changed anywhere else."

## If Bing asks you to do it again

1. A people-search site removes a listing after you last pressed "I did this". <!-- src/freemyid/wizard/views.py:246 -->
2. Bing can still show the old copy of that page.
3. The Bing status changes to the "do it again" line above.
4. Google does not change for that reason.
5. Open Bing's page again with "Open the page for me". <!-- src/freemyid/wizard/views.py:241 -->
6. Repeat the Bing steps for the page that was removed.
7. Press "I did this" again. <!-- src/freemyid/wizard/views.py:246 -->

## If the list is missing

The page can say "The list is not available right now." <!-- src/freemyid/wizard/views.py:259 -->

Stop there.
Do not type your details into a page you found by searching.
Open Free My ID again later, from its own icon.
