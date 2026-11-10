# Helping by phone

This is for a grown child or friend talking someone through Free My ID by phone.

If you can sit beside them, use [Helping someone set up Free My ID](HELPING.md) instead.
This page does not repeat that guide.
Use it when you cannot be in the room.

Example person: Jane Q Testperson, Springfield IL.

## Safety rules

Read these before you dial.
Jane presses every button.
You only talk.

1. Never ask Jane to read a password out loud.
2. Never ask Jane to read a code from a text, an email, or a site.
3. Never ask Jane to read a Social Security number out loud.
4. Never ask Jane to read a bank number or a card number.
5. If a window asks for a Social Security number, stop.
6. If a window asks for a bank number or a card number, stop.
7. The first setup screen shows: "No account. No cloud. Never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime." <!-- src/freemyid/wizard/ui.py:266-268 -->
8. She can open "Settings" later if she wants to see the words again. <!-- src/freemyid/wizard/ui.py:44 -->
9. Under her name, find "What Free My ID may do". <!-- src/freemyid/wizard/dashboard.py:527 -->
10. That part says "It will never ask for a Social Security number or bank or card details." <!-- src/freemyid/wizard/dashboard.py:529 -->
11. Do not ask her to download a program.
12. Do not ask her to share her screen.
13. Do not ask her to turn on remote control.
14. If the icon is missing, stop and use [Helping someone set up Free My ID](HELPING.md).

## What she sees

The names below are the labels on her screen.

1. The top menu starts with "Today". <!-- src/freemyid/wizard/ui.py:43 -->
2. The next name is "Protect yourself". <!-- src/freemyid/wizard/ui.py:43 -->
3. The next name is "Emails". <!-- src/freemyid/wizard/ui.py:43 -->
4. The last name is "Settings". <!-- src/freemyid/wizard/ui.py:44 -->
5. On Today, a lower button says "More: safety steps and details". <!-- src/freemyid/wizard/dashboard.py:275 -->

She can open that button when she wants the longer list.
She does not have to open it on these calls.

## Call 1: First look at Today

Use this after setup. Jane is at her own computer.

1. Ask Jane to open Free My ID from the icon she already has.
2. Ask her to stay on "Today". <!-- src/freemyid/wizard/ui.py:43 -->
3. Ask her to read the large card slowly.
4. If the card says "Practice mode:", tell her that is a calm place to start. <!-- src/freemyid/wizard/dashboard.py:237 -->
5. Read the rest with her: "no removal requests go out until you say so." <!-- src/freemyid/wizard/dashboard.py:238 -->
6. If she just read that line, a removal is not requested until she says so.
7. If the card says "Free My ID is checking now", ask her to wait. <!-- src/freemyid/wizard/dashboard.py:262 -->
8. The card says this takes "about a minute". <!-- src/freemyid/wizard/dashboard.py:263 -->
9. It also says "This page updates by itself." <!-- src/freemyid/wizard/dashboard.py:263 -->
10. She does not need to press anything while it checks.
11. If the card says "Nothing needs you today", thank her and end this call. <!-- src/freemyid/wizard/dashboard.py:267-268 -->
12. Ask her to read the count line under the card.
13. That line uses the words "requests sent" and "confirmed". <!-- src/freemyid/wizard/dashboard.py:214 -->
14. The numbers are what was requested, and what a site has confirmed.
15. A note may say "A site that says it deleted you has done that for that one site only." <!-- src/freemyid/wizard/dashboard.py:276-277 -->
16. Tell her one confirmed site is only that site. Free My ID keeps checking.
17. If the card says "waiting for your OK", use the email call below. <!-- src/freemyid/wizard/dashboard.py:253 -->
18. If she sees "Yes, this is me", use the next call. <!-- src/freemyid/wizard/dashboard.py:122 -->

## Call 2: The "Is this you?" card <!-- src/freemyid/wizard/dashboard.py:113 -->

Use this when "Today" shows one card about a possible match. <!-- src/freemyid/wizard/ui.py:43 -->
The title she sees starts with "Is this" and then her name. <!-- src/freemyid/engine/runner.py:1000 -->
It may also say "phone number" or "email address". <!-- src/freemyid/engine/runner.py:993 -->

1. Ask Jane to read "Why it is a possible match:" and the words under it. <!-- src/freemyid/wizard/dashboard.py:117 -->
2. That reason is safe to read on the phone.
3. If she sees "Open the page", she can press it when she wants to look. <!-- src/freemyid/wizard/dashboard.py:121 -->
4. The card says "Open the page first if you want to look." <!-- src/freemyid/wizard/dashboard.py:125 -->
5. It also says "Only you can say whether it is you." <!-- src/freemyid/wizard/dashboard.py:125-126 -->
6. You do not pick the answer for her.
7. Ask her if the page is about Jane Q Testperson in Springfield IL.
8. If she says yes, she presses "Yes, this is me". <!-- src/freemyid/wizard/dashboard.py:122 -->
9. The card says "Free My ID will ask this site to take the listing down". <!-- src/freemyid/wizard/dashboard.py:127 -->
10. Those words mean a later request, not a site that has confirmed.
11. The same card says "on its next check". <!-- src/freemyid/wizard/dashboard.py:128 -->
12. If the card also says "no removal requests go out.", practice mode is still on. <!-- src/freemyid/wizard/dashboard.py:131 -->
13. If that line is there, she can answer the card and still wait.
14. If she says the page is not her, she presses "No, this is not me". <!-- src/freemyid/wizard/dashboard.py:123 -->
15. The card says Free My ID "will not ask about it again." <!-- src/freemyid/wizard/dashboard.py:133 -->
16. If she is not sure it is her, stop, and the card stays.

## Call 3: The first email

Use this when "Today" says an email is waiting for her OK. <!-- src/freemyid/wizard/ui.py:43 -->

1. Ask Jane to find the words "waiting for your OK". <!-- src/freemyid/wizard/dashboard.py:253 -->
2. Ask her to press "Look at them". <!-- src/freemyid/wizard/dashboard.py:255 -->
3. The menu name for that page is "Emails". <!-- src/freemyid/wizard/ui.py:43 -->
4. The heading says "Emails waiting for your approval". <!-- src/freemyid/wizard/dashboard.py:449 -->
5. Ask her to read the "To:" line and the "Subject:" line. <!-- src/freemyid/wizard/dashboard.py:466 -->
6. She can stop there if the letter is long.
7. If a note begins "This is the first email for", ask her to read the whole note. <!-- src/freemyid/wizard/dashboard.py:459 -->
8. That note says "Approving it also" about the other emails that are waiting. <!-- src/freemyid/wizard/dashboard.py:459 -->
9. Read this sentence with her: "After that, routine emails go out by themselves." <!-- src/freemyid/wizard/dashboard.py:461 -->
10. The note also says "Formal demands still wait for you." <!-- src/freemyid/wizard/dashboard.py:461-462 -->
11. She decides after she has heard that note.
12. She presses "Approve and send" when she wants that request to go out. <!-- src/freemyid/wizard/dashboard.py:473 -->
13. A window then asks "Send this email now?" <!-- src/freemyid/wizard/dashboard.py:456 -->
14. She agrees to that window only if she still wants the request to go out.
15. If she is not ready, she does not press "Approve and send". <!-- src/freemyid/wizard/dashboard.py:473 -->
16. The email stays on the list for another call.
17. Later, the Today line shows "requests sent", then "confirmed" only after a site agrees. <!-- src/freemyid/wizard/dashboard.py:214 -->

## If she is upset or unsure

1. Stop. Do not choose the next button for her.
2. Tell her she can leave the window open, or close it.
3. Waiting does not lose the work.
4. The card or the email stays until she is ready.
5. If she still sees "Practice mode:", pause there. <!-- src/freemyid/wizard/dashboard.py:237 -->
6. Read her this line: "no removal requests go out until you say so." <!-- src/freemyid/wizard/dashboard.py:238 -->
7. Offer to call again on another day.
8. Do not send a download, a screen-sharing app, or a remote-control tool.
