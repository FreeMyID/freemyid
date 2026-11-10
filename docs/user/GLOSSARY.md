# Free My ID in plain words: a short glossary

These are 21 words you may see in Free My ID or its help pages. Each has one or
two sentences. The source file is named under each word so a helper can check it.
Where the repo does not say, the entry says "not sure".

Example person used below: Jane Q Testperson, Springfield IL.

Only what is listed in `site_src/data/release.yaml` is available today: version
0.2.0 (`site_src/data/release.yaml:5`). Anything else is coming, not available.

### People-search site (also called a data broker)
A website that collects a person's name, age, addresses, phone numbers and relatives and shows them to anyone. Free My ID works on these sites.
Source: `docs/USER_GUIDE.md:27`.

### Removal request (opt-out)
A request asking a site to take your details down, made through that site's own removal process. Some sites must answer, others do not have to.
Source: `docs/USER_GUIDE.md:25`, `docs/USER_GUIDE.md:33`. The word "opt-out" is used in `docs/POSITIONING.md`; a plain definition of it is not sure.

### Listing
The page on a site that shows your details. A site saying it removed your listing applies to that one site only.
Source: `docs/USER_GUIDE.md:42`, `docs/USER_GUIDE.md:146`.

### Practice mode (practice run)
Free My ID starts here. It still searches people-search sites, and no removal requests go out until you say so in Settings.
<!-- src/freemyid/wizard/dashboard.py:237-238 -->
<!-- src/freemyid/engine/runner.py:270-271 -->
<!-- src/freemyid/engine/runner.py:467 -->
Source: `src/freemyid/wizard/dashboard.py:237-238`, `src/freemyid/engine/runner.py:270-271`, `src/freemyid/engine/runner.py:467`.

### "Is this you?" review
Free My ID asks this when a page might be Jane Q Testperson, but it is not sure. Look first, then press "Yes, this is me" or "No, this is not me": Yes means Free My ID may ask that site on a later check, and No means no removal request goes out for that page and it will not ask again.
<!-- src/freemyid/wizard/dashboard.py:122-133 -->
<!-- src/freemyid/engine/runner.py:990-991 -->
<!-- src/freemyid/wizard/server.py:60-61 -->
Source: `src/freemyid/wizard/dashboard.py:122-133`, `src/freemyid/engine/runner.py:990-991`, `src/freemyid/wizard/server.py:60-61`.

### Listing score
The number from 0 to 100 under "Where you are listed" (lower is better). It only describes what was found on the sites we could check, not every website.
<!-- src/freemyid/wizard/views.py:50 -->
<!-- src/freemyid/wizard/views.py:78-82 -->
<!-- src/freemyid/engine/exposure_score.py:206-207 -->
Source: `src/freemyid/wizard/views.py:50`, `src/freemyid/wizard/views.py:78-82`, `src/freemyid/engine/exposure_score.py:206-207`.

### Requested (the screen says "asked")
A removal request has gone to that one site. The screen says "asked", or that the site still needs to confirm, which is not the same as confirmed.
<!-- src/freemyid/wizard/ui.py:26-27 -->
<!-- src/freemyid/wizard/views.py:30-31 -->
Source: `src/freemyid/wizard/ui.py:26-27`, `src/freemyid/wizard/views.py:30-31`.

### Confirmed
That one site has answered ("site confirmed" or "They confirmed"), or a later check no longer finds the listing ("not listed now"). The Today line counts both as confirmed, and neither is the same as pressing "Yes, this is me".
<!-- src/freemyid/wizard/ui.py:28 -->
<!-- src/freemyid/wizard/views.py:32-33 -->
<!-- src/freemyid/wizard/dashboard.py:27 -->
<!-- src/freemyid/models.py:137-138 -->
Source: `src/freemyid/wizard/ui.py:28`, `src/freemyid/wizard/views.py:32-33`, `src/freemyid/wizard/dashboard.py:27`, `src/freemyid/models.py:137-138`.

### Relisted (the screen says "reappeared")
A listing that had gone has shown up on that site again. The screen says "reappeared" or "It came back. We are asking again", and the next real run asks again.
<!-- src/freemyid/wizard/ui.py:29 -->
<!-- src/freemyid/wizard/views.py:34 -->
<!-- src/freemyid/state.py:79-80 -->
<!-- src/freemyid/state.py:94-95 -->
Source: `src/freemyid/wizard/ui.py:29`, `src/freemyid/wizard/views.py:34`, `src/freemyid/state.py:79-80`, `src/freemyid/state.py:94-95`.

### Real requests
The step after practice. You switch it on once in Settings and confirm.
Source: `docs/USER_GUIDE.md:119`.

### Removal mailbox
A separate email address used only for removal requests, not your everyday one. Sites send confirmation links there.
Source: `docs/USER_GUIDE.md:50-53`.

### App password
A special password a mail company gives you for programs such as Free My ID. It is not your normal password. For Gmail it needs 2-Step Verification first.
Source: `docs/USER_GUIDE.md:63-64`. Whether Google still offers it for every new account is marked "TODO verify" at `docs/USER_GUIDE.md:68`, so: not sure.

### Proton Mail Bridge (Bridge)
A free app on your own computer that lets other programs reach Proton mail. It has to be running whenever Free My ID checks mail, and it needs a paid Proton plan (marked "TODO verify" in the guide, so: not sure).
Source: `docs/USER_GUIDE.md:78`, `docs/USER_GUIDE.md:91`.

### Security code (for Bridge)
A long row of letters and numbers that Bridge shows. Free My ID remembers it and tells you if it changes.
Source: `docs/USER_GUIDE.md:84`, `docs/USER_GUIDE.md:87`.

### Needs you
A status meaning Free My ID cannot go further without a person, such as a mailed letter or a phone call.
Source: `docs/USER_GUIDE.md:148`, `docs/USER_GUIDE.md:158-160`.

### Assisted step ("Do it with me")
Some sites need you to finish the form in your own browser: Free My ID shows the steps and Copy buttons, and you press "I did it" when you are done. If you choose "Fill it in for me" and then press Submit on the site, that request is real even in practice mode.
<!-- src/freemyid/models.py:203 -->
<!-- src/freemyid/wizard/dashboard.py:163-165 -->
<!-- src/freemyid/wizard/dashboard.py:347-350 -->
Source: `src/freemyid/models.py:203`, `src/freemyid/wizard/dashboard.py:163-165`, `src/freemyid/wizard/dashboard.py:347-350`.

### Phone-call note
On a phone-call step you may type a short note, or leave the box blank. The note stays on this computer as your own record, so please do not write passwords or ID numbers.
<!-- src/freemyid/wizard/dashboard.py:188-192 -->
<!-- src/freemyid/wizard/proof_input.py:46-55 -->
<!-- src/freemyid/models.py:216 -->
Source: `src/freemyid/wizard/dashboard.py:188-192`, `src/freemyid/wizard/proof_input.py:46-55`, `src/freemyid/models.py:216`.

### CAPTCHA ("prove you're human")
A check some sites show. Free My ID does not try to get around it. It opens the page and you do the step.
Source: `docs/USER_GUIDE.md:162-164`.

### Emails to approve
In the default mode, Free My ID writes each email but does not send it until you approve it. Firmer letters always wait for your approval.
Source: `docs/USER_GUIDE.md:198-204`.

### Run automatically (background check)
Free My ID keeps checking by itself, and catches up if the computer was asleep or off. You can turn it on or off in Settings.
Source: `docs/USER_GUIDE.md:109`, `docs/USER_GUIDE.md:113`.

### DROP (California)
A free, official California state website where one request goes to brokers registered in California. Free My ID cannot file it for you; it gives you a link. The web address and agency details are marked "TODO verify" in the guide: not sure.
Source: `docs/USER_GUIDE.md:208-210`, `docs/USER_GUIDE.md:215`.
