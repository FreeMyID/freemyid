# Helping someone set up Free My ID

**Who this is for:** a family member or friend sitting with someone, in person or on the phone, while they set up Free My ID on a Windows 10 or 11 computer. The installer is available (`site_src/data/release.yaml:5-8`; `docs/user/INSTALL.md`).

Example person: Jane Q Testperson, Springfield IL.

## It is their choice

The person you help gives their own consent, on the first setup screen. You never consent for them. If you are not the person, the screen asks for their signed written permission (`docs/HELPER_GUIDE.md`, section 3, screen 1). Sit beside them and let them click and type.

## Do these together, in this order

1. **Install.** Follow [INSTALL.md](INSTALL.md), the "Windows 10 or 11" part. Windows shows a blue box because the installer is unsigned for now. If anything looks wrong, stop and ask someone you trust (`docs/user/INSTALL.md`). When Free My ID opens, wait with them. The first time can take up to a minute. Please wait; there is no need to click it again.
2. **Email for replies (optional).** Pick one page, or skip it and send by hand (`docs/user/mail-other.md`):
   - [Gmail](mail-gmail.md)
   - [Proton Mail](mail-proton.md)
   - [Yahoo, iCloud, others, and Outlook](mail-other.md). Outlook.com and Hotmail are not supported yet (same file).
3. **The six setup screens.** Use [the helper's guide](../HELPER_GUIDE.md), section 3.
4. **Answer "Is this you?" together** when that card shows. See [Answer "Is this you?" together](#answer-is-this-you-together).
5. **Leave practice mode on** until the person says to send real requests. See [Practice mode](#practice-mode).

## Answer "Is this you?" together

Sit together. If you are on the phone, stay on the line. This example is Jane Q Testperson, Springfield IL. You can read the card out loud and point. Let that person press the buttons. Do not press Yes or No for them.

On the Today screen, the big card is the next thing to do. Sometimes it asks whether a page is the person. If the on-screen name is Jane Q Testperson, the card can say "Is this Jane Q Testperson?" and then the site name. The name matches, and maybe the city does too. That is not enough for Free My ID to be sure.

<!-- src/freemyid/wizard/ui.py:43 -->
<!-- src/freemyid/wizard/dashboard.py:112-119 -->
<!-- src/freemyid/engine/runner.py:1000 -->

If a different card is in the big spot, press **More: safety steps and details**, or **See the full list**, and find the card that asks.

<!-- src/freemyid/wizard/dashboard.py:272-275 -->

Open the page first. Then Yes or No.

1. Press **Open the page**. The site opens in the web browser. Look at it together. Then come back to Free My ID. The screen says: "Opened in your web browser. Come back here when you are finished." If the browser does not open, the screen says: "Could not open your browser. Try again."
2. If you do not see **Open the page**, that card has no page to open. Use what the card already says, then go on to Yes or No.
3. The person presses one answer. Press it once.

<!-- src/freemyid/wizard/dashboard.py:121-126 -->
<!-- src/freemyid/wizard/server.py:52-53 -->

**Yes, this is me** means this listing is them. Free My ID does not ask the site at the moment of the press. On the next check it will ask that site to take the listing down, if the settings allow it. It may send the request by itself, or it may ask them to approve an email or do a step. If the site wants a photo ID, an account, or a phone number, Free My ID stops and asks, unless that was already allowed in Settings. While practice mode is on, no removal requests go out.

The screen then says: "Thank you. Free My ID will ask that site to remove the listing on its next check, if your settings allow it."

<!-- src/freemyid/wizard/dashboard.py:122 -->
<!-- src/freemyid/wizard/dashboard.py:127-131 -->
<!-- src/freemyid/wizard/server.py:60-61 -->
<!-- src/freemyid/engine/handoff.py:157-166 -->

**No, this is not me** means this listing is not them. Free My ID will not ask that site to remove it, and it will not ask about this listing again.

The screen then says: "Thank you. Nothing will be sent for that listing." That line is about this one listing. It does not mean Free My ID stops looking up the name.

<!-- src/freemyid/wizard/dashboard.py:123 -->
<!-- src/freemyid/wizard/dashboard.py:132-133 -->
<!-- src/freemyid/wizard/server.py:62 -->
<!-- src/freemyid/engine/handoff.py:167-169 -->

The first answer stays. A later check keeps it. A second press does not change it. The screen says: "That question was already answered. Nothing was changed."

<!-- src/freemyid/engine/runner.py:169-173 -->
<!-- src/freemyid/wizard/server.py:63 -->
<!-- src/freemyid/wizard/server.py:524-547 -->

## Practice mode

Free My ID starts in practice mode. On Today, the banner says: "Practice mode: Free My ID is looking for your listings, but no removal requests go out until you say so."

<!-- src/freemyid/config.py:30 -->
<!-- src/freemyid/wizard/dashboard.py:237-238 -->

Practice mode still searches. It looks up the name and city on people-search sites. For Jane Q Testperson, Springfield IL, that search uses that name and that city. The search does reach those sites.

No removal requests go out until the person says so. A removal request is the ask that a site take a listing down. Practice mode does not send that ask by itself. One exception: if the person chooses **Fill it in for me** on a step and then presses Submit on the site, that request is real even in practice mode. If **Run automatically** is on, the daily check still runs in practice mode. It still searches, and it still does not send removal requests.

<!-- src/freemyid/engine/runner.py:269-271 -->
<!-- src/freemyid/engine/runner.py:545-556 -->
<!-- src/freemyid/cli.py:286-287 -->

The person says so in **Settings**. On the card **Practice mode is on**, press **Start sending real requests**. Read the next page with them. Then they press **Yes, start sending real requests**, or **No, stay in practice mode**.

<!-- src/freemyid/wizard/dashboard.py:510-515 -->
<!-- src/freemyid/wizard/dashboard.py:493-494 -->

If they already pressed **Yes, this is me** during practice mode, Free My ID remembers that the listing is theirs. The removal request still waits until real requests are on.

They can press **Go back to practice mode** later in Settings. A request that already went out cannot be taken back.

<!-- src/freemyid/wizard/dashboard.py:517-520 -->
<!-- src/freemyid/wizard/dashboard.py:488-490 -->

## How to update

When a newer Free My ID is ready, download the installer again from the same place as the first time. Follow [INSTALL.md](INSTALL.md), the "Windows 10 or 11" part. Open the new installer. Do not uninstall the old one first. Windows may show the same blue box. If it looks wrong, stop.

The new installer keeps the person's details and the scheduled check. The name, the city, the settings, and the scheduled check (if it was on) stay on the computer. Those details are kept apart from the program files the installer replaces. If **Run automatically** was already on, it stays on. The new installer does not turn it off, and it does not turn it on by itself. The daily check is removed only when someone uninstalls Free My ID. An update does not do that.

<!-- src/freemyid/paths.py:13-16 -->
<!-- src/freemyid/scheduler/__init__.py:1-4 -->
<!-- src/freemyid/scheduler/__init__.py:110-111 -->
<!-- src/freemyid/wizard/ui.py:335-338 -->
<!-- Installer script freemyid.iss: program files are replaced in place. CloseApplications can close a running copy. The uninstall step is what runs schedule remove. An update does not run that uninstall step. -->

The installer may close Free My ID while it copies the new files. The app may need to be opened again. If the last screen offers to open Free My ID, leave that ticked and press Finish. If the window does not show, open **Free My ID** from the Desktop icon or the Start Menu. If it was already open, opening it again brings that window forward.

<!-- src/freemyid/wizard/desktop.py:8-9 -->
<!-- src/freemyid/wizard/desktop.py:164-168 -->

Then wait. Say this, and do not click the icon again:

The first time can take up to a minute. Please wait; there is no need to click it again.

A small box says Free My ID is starting, and that the first time can take up to a minute (splash_win.py, line 20). If the wait is long, the box says Free My ID is still starting, and to please wait; there is no need to click it again (splash_win.py, line 23). The box goes away when the window is ready.

## If you get stuck

See [troubleshooting.md](troubleshooting.md). Not sure whether it covers your problem; if not, stop and ask the project.
