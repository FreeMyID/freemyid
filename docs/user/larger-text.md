# Larger text and a darker screen

This page helps people with poor eyesight see Free My ID more clearly.

The example person is Jane Q Testperson, Springfield IL.

Open the app first. Install help is in [How to install Free My ID](INSTALL.md).

## Buttons in the app

Use these buttons before you change Windows.

They are at the top of each page that shows the menu.

The menu says "Today", "Protect yourself", "Emails" and "Settings". <!-- src/freemyid/wizard/ui.py:43 -->

On a wide window the buttons sit beside that menu.

On a narrow window the menu moves to the line below the buttons.

Zooming in can make the window count as narrow.

The text button sits next to the dark or light button.

Pages without the menu do not show the dark or light button. <!-- src/freemyid/wizard/ui.py:58 -->

Pages without the menu do not show the larger text button. <!-- src/freemyid/wizard/ui.py:59 -->

The setup screens are one of those pages. <!-- src/freemyid/wizard/ui.py:413 -->

Use the keyboard steps below when those buttons are missing.

### Larger text

1. Find the button that says "Larger text". <!-- src/freemyid/wizard/ui.py:61 -->
2. Press it once.
3. The words in the app get bigger.
4. The button then says "Normal text" (app.js, line 131).
5. Press it again to return to the usual size.
6. If it already says "Normal text", larger text is already on.

### Dark or light

1. Find the button that says "Dark". <!-- src/freemyid/wizard/ui.py:58 -->
2. Press it once for a dark screen.
3. The button then says "Light" (app.js, line 111).
4. Press it again for a light screen.
5. If it already says "Light", the screen is already dark.

Read the words on the button, not the colour alone.

## What the app remembers

The dark or light choice is kept in a cookie (app.js, line 101).

It starts from the computer setting until you pick one (app.js, line 101).

Larger text is remembered in a cookie the same way (app.js, line 124).

Pressing the button writes that cookie (app.js, line 137).

theme.js, line 2 says the choice lives in a cookie on this computer.

theme.js, line 5 reads the theme cookie before the page is shown.

theme.js, line 8 reads the larger-text cookie in the same way.

The code sets each cookie to last 365 days (app.js, line 118 and app.js, line 137).

Larger text does not start from the computer's dark or light setting.

It stays the usual size until you press the button.

A saved choice can turn it on before that (theme.js, line 8).

## Zoom with the keyboard

These keys work on Windows 10 and on Windows 11.

They work in the Free My ID window and in a web browser.

Browser zoom still works on top of the larger text button (app.js, line 124).

1. Click the Free My ID window so it is the one in front.
2. Hold Ctrl and press the + key.
3. The page zooms in.
4. Press the + key again if you want it larger.
5. Hold Ctrl and press the 0 key.
6. That resets the zoom.

## Make text bigger in Windows

This Windows setting is separate from the buttons above.

The words to look for are "Make text bigger".

The menu path differs between Windows 10 and Windows 11.

This page does not give one path.

1. Open Settings.
2. Search for "Make text bigger".
3. Open the setting with that name.
4. Move the slider so the text is bigger.
5. Apply the change if Windows asks you to.

## Read the summary on paper

A paper copy can be easier to read than the screen.

1. On Today, press "More: safety steps and details". <!-- src/freemyid/wizard/dashboard.py:275 -->
2. The next heading is "Everything". <!-- src/freemyid/wizard/dashboard.py:288 -->
3. Find the heading "People". <!-- src/freemyid/wizard/dashboard.py:310 -->
4. Press the button that starts with "What we did for". <!-- src/freemyid/wizard/dashboard.py:315 -->
5. For Jane Q Testperson, that button includes her name.
6. The summary heading starts with "What Free My ID did for". <!-- src/freemyid/wizard/views.py:303 -->
7. Press "Print this page". <!-- src/freemyid/wizard/views.py:301 -->
8. Print it, or save it, then read the paper.
