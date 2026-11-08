# "Never asks for" consistency notes (WO-162, from GP-16)

Notes only. Nothing here was changed in the files it points at. Lucia, Ben and the in-house team decide what to fix.
Release status: v0.2.0 is listed in `site_src/data/release.yaml:5-6`, so the app is "available" in that version only.
The comparison reads the repo as it is today. Line numbers can drift.

## The lists compared

| Place | Where | What it lists |
|---|---|---|
| App guide (USER_GUIDE) | `docs/USER_GUIDE.md:29`, `:235` | Social Security number, bank or card details, charging you |
| Helper guide | `docs/HELPER_GUIDE.md:85-93` | SSN; bank/card; ID photo; Facebook, Google or everyday email password (app password for the optional mailbox is the exception); money. Also: no accounts, ID uploads or phone number unless allowed; no "are you a robot?" |
| Website, safety page | `web/src/pages/safety/index.astro:43-60` | SSN; bank/card; any payment; full birthday (year only, optional); phone number unless shared; ID photo unless switched on; everyday email password. Plus an app-password note (`:58`) |
| Website, families page | `web/src/pages/families/index.astro:106` | Same as the helper guide, nearly word for word |
| Website, short forms | `web/src/pages/index.astro:68`, `:108`, `:225`, `:318`; `web/src/components/Footer.astro:61`; `web/src/pages/how-it-works/index.astro:21`; `site_src/data/faq.yaml:16`, `:39` | SSN and bank/card (some add payment) |
| Printed extras | `FAMILY_QUICK_START.md:8`; `docs/FRIDGE_CARD.md:17` | SSN and bank/card; the fridge card adds "passwords" |

## Differences

1. **Three different lengths of list, no shared source.**
   The short lists (USER_GUIDE `:29`, `:235`; FAMILY_QUICK_START `:8`; website home and footer) name only SSN and bank/card.
   The helper guide (`:87-91`) and families page (`:106`) add ID photo, passwords and money.
   The safety page (`:46-55`) adds payment, full birthday and phone number, but not "accounts" or "robot checks".
   Nobody has the full set. A reader of one page would not learn what is on another.

2. **Passwords: fridge card is broader than the rest.**
   `docs/FRIDGE_CARD.md:17` says it will never ask for "passwords". But the app does ask for an app password (Gmail) or Bridge password (Proton) for the removal mailbox: `docs/USER_GUIDE.md:64-65`, `:82-83`.
   The helper guide (`:90`) and safety page (`:55`, `:58`) handle this by saying "everyday email password" and explaining the app-password exception. The fridge card does not. For a person who reads only the card, the mailbox step could look like a contradiction. (Not sure how the owner wants to word it on a printed card; a one-line fix is likely enough.)
   Also, `docs/USER_GUIDE.md:111` has people share a password for a family file. That one is a password the helpers choose, not one the app asks for, but no list mentions it. Not sure it needs to.

3. **Phone number: wording differs in strength.**
   Helper guide `:93` and families `:106`: it never "gives out a phone number unless you've explicitly allowed it for that person". Safety `:52` and home `index.astro:225` say it only gives the number if you choose or switch that on. These agree in substance.
   But setup does ask for a phone number (optional): `docs/USER_GUIDE.md:107`, `FAMILY_QUICK_START.md:48`, `how-it-works/index.astro:21`. No "never asks" list says that setup asks for it and the site decides later. "Never asks for your phone number" (safety `:52` reads "Your phone number, unless...") may confuse someone who just typed it on screen 4. Suggest making the lists say "never gives it to a site unless you allow it", which is what the helper guide says.

4. **Birth date: safety page and USER_GUIDE disagree in wording.**
   Safety `:50`: never asks for the full birthday; only a year, optional.
   USER_GUIDE `:239`: sites get "never your birth date, relatives, or personal email".
   `web/src/pages/families/index.astro:51`: optional year of birth, phone, relatives' names are "sent only when a site's removal form asks for them, in a request you approve".
   So USER_GUIDE `:239` ("never ... relatives") does not match families `:51` (may be sent when a form asks). Both are about what is sent, not what is asked, but they cannot both be true. Which is right needs checking in the engine; I did not check the code (not sure).

5. **"Never sent" claim in the quick start.**
   `FAMILY_QUICK_START.md:48` says birth year, phone and email "are never sent to anyone". USER_GUIDE `:107` says "does not send them to any site as your details" and families `:51` says they can be sent when a form asks. POSITIONING rule (per `.github/copilot-instructions.md`) bans "never sent" absolutes. Flagged for the in-house team; I did not edit it.

6. **Rules only on some pages.**
   - "Never solves 'are you a robot?' checks": helper guide `:68`, `:93`, families `:106`, USER_GUIDE `:164`, developers page `:158`. Not on the safety page list, fridge card (which tells the person to tick it themselves, `:15`, consistent), or short forms.
   - "Never creates accounts": helper guide `:93`, families `:106`, USER_GUIDE `:190`, `:210`. Not on the safety page.
   - "Never charges / never pays": USER_GUIDE `:235`, `:252` and safety `:49` ("payment of any kind"). Helper guide says "Money: the app is free" (`:91`). Same idea, three phrasings.
   - "We will never email you an installer or call you": safety `:69`, families `:106`, download page `:83`. Not in either guide or the fridge card. Different kind of statement (about us, not the app), so it may be fine to leave out of the guides.

7. **ID photo.**
   Helper guide `:89` and families `:106`: "never ask for" a photo of an ID card, with the allowed case covered in the next sentence ("uploads ID ... unless allowed"). Safety `:53` says "unless you switch that on yourself in Settings for a site that insists on it". `docs/USER_GUIDE.md:172` says Free My ID "stops and asks" when a site wants ID and the permission is off. So the app does prompt about ID in that case. The helper guide's flat "never ask for ... A photo of an ID card" is therefore a little stronger than USER_GUIDE `:172`. Not sure which wording the owner prefers; the safety page's version is the most accurate of the three.

8. **Nothing found that is called "available" wrongly.**
   I found no "never asks for" statement that claims a feature not in `site_src/data/release.yaml`. Statements about the app's behaviour here cite USER_GUIDE or the website source comments. I did not run the app or read engine code, so whether the app really behaves this way is unverified.

## Suggestions (for the owner to accept or drop)

- Keep one master list (the safety page list is the fullest) and have the others quote it. Today there are at least five hand-written copies.
- Add "creates accounts" and "robot checks" to the safety page, or say deliberately that they live elsewhere.
- Fix the fridge card "passwords" to "your everyday email password" (matches HELPER_GUIDE `:90`).
- Reword differences 3 to 5 so "asks", "sends" and "gives out" are not mixed.
- GP-16 said a new `docs/user/` page only after this check. My view: do not add one; fix the copies above first.

## Not checked

- Engine and wizard behaviour (out of scope for this order).
- `site/` (built output) and `docs/marketing/` copies; only the sources listed above.
- `docs/USER_GUIDE.md:68` carries a `TODO verify` about Gmail app passwords, so difference 2 depends on that.
