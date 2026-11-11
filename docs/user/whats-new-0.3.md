# What's new in Free My ID 0.3

This page tells people who used 0.2, or who are new, what version 0.3.1 adds.

Example person used below: Jane Q Testperson, Springfield IL.

## Today
1. Today shows one card with the next thing to do. <!-- src/freemyid/wizard/dashboard.py:232 -->
2. Then press "More: safety steps and details". <!-- src/freemyid/wizard/dashboard.py:275 -->

## Is this you?
1. A card can ask "Is this you?" about a listing. <!-- src/freemyid/wizard/dashboard.py:113 -->
2. "Open the page first if you want to look." <!-- src/freemyid/wizard/dashboard.py:125 -->
3. Press "Yes, this is me" when the listing is her. <!-- src/freemyid/wizard/dashboard.py:122 -->
4. "Free My ID will ask this site to take the listing down". <!-- src/freemyid/wizard/dashboard.py:127 -->
5. That happens "on its next check". <!-- src/freemyid/wizard/dashboard.py:128 -->
6. In practice mode, "no removal requests go out". <!-- src/freemyid/wizard/dashboard.py:131 -->
7. Press "No, this is not me" when the listing is not her. <!-- src/freemyid/wizard/dashboard.py:123 -->
8. Then it "will not ask about it again". <!-- src/freemyid/wizard/dashboard.py:133 -->

## Protect yourself
1. Open "Protect yourself". <!-- src/freemyid/wizard/ui.py:43 --> <!-- src/freemyid/wizard/views.py:254 -->
2. The steps are optional, and "you can tick them off as you go". <!-- src/freemyid/wizard/views.py:256 -->

## Google and Bing
1. The same page has "Google and Bing". <!-- src/freemyid/wizard/views.py:228 --> <!-- src/freemyid/engine/search_engines.py:33 -->
2. "Free My ID does not search Google or Bing for you". <!-- src/freemyid/engine/search_engines.py:34 -->
3. "We open their own official page, and you do the steps". <!-- src/freemyid/engine/search_engines.py:35 -->
4. Press "Open the page for me". <!-- src/freemyid/wizard/views.py:242 -->
5. Or choose "Or open the link yourself". <!-- src/freemyid/wizard/views.py:244 -->
6. When you have finished, press "I did this". <!-- src/freemyid/wizard/views.py:247 -->

## Larger text
1. Press "Larger text" to make the words bigger. <!-- src/freemyid/wizard/ui.py:61 -->
2. The choice is remembered on this computer. <!-- src/freemyid/wizard/static/app.js, line 124 -->

## Print this page
1. Open "What we did for you". <!-- src/freemyid/wizard/dashboard.py:376 -->
2. The heading starts "What Free My ID did for" her name. <!-- src/freemyid/wizard/views.py:303 -->
3. It shows what was requested, and which sites "confirmed". <!-- src/freemyid/wizard/views.py:307 -->
4. Press "Print this page". <!-- src/freemyid/wizard/views.py:301 -->

## The first start
1. On Windows, a small window says "Free My ID is starting." <!-- packaging/windows/splash_win.py, line 20 -->
2. The first time can take up to a minute. Please wait; there is no need to click it again. <!-- packaging/windows/splash_win.py, line 20 and line 23 -->

## How to update
1. Run the new installer over the old one. <!-- packaging/windows/freemyid.iss, line 9 and line 39 -->
2. Updating with the new installer keeps your details and the scheduled check. <!-- packaging/windows/freemyid.iss, line 64, line 83, and line 97 -->
3. It is an upgrade, not a second app. <!-- docs/RELEASE_v0.3.md, line 20 -->
4. Jane Q Testperson in Springfield IL would not type her details again.
5. Her scheduled check would still be there.
6. The app may need reopening after an update. <!-- packaging/windows/freemyid.iss, line 28 -->
7. If you do not see the window, open Free My ID from the Desktop icon or the Start Menu. <!-- packaging/windows/freemyid.iss, line 52, line 53, and line 56 -->

## What has not changed
1. Practice mode is on at the start. <!-- src/freemyid/config.py:30 -->
2. The banner says "Practice mode". <!-- src/freemyid/wizard/dashboard.py:237 -->
3. It says "no removal requests go out until you say so". <!-- src/freemyid/wizard/dashboard.py:238 -->
4. There is "No account". <!-- src/freemyid/wizard/ui.py:266 -->
5. It is "Free and open source", so nothing to pay. <!-- src/freemyid/wizard/ui.py:267 -->
