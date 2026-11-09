# Free My ID in plain words: a short glossary

These are 15 words you may see in Free My ID or its help pages. Each has one or
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
Free My ID starts here. It looks for your details and shows what it would do, but sends no removal requests.
Source: `docs/USER_GUIDE.md:117`, `docs/CLI.md:9`.

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

### CAPTCHA ("prove you're human")
A check some sites show. Free My ID does not try to get around it. It opens the page and you do the step.
Source: `docs/USER_GUIDE.md:162-164`.

### Emails to approve
In the default mode, Free My ID writes each email but does not send it until you approve it. Firmer letters always wait for your approval.
Source: `docs/USER_GUIDE.md:198-204`.

### Reappeared
A listing that had gone came back. This is normal, and Free My ID files a new request on the next real run.
Source: `docs/USER_GUIDE.md:147`, `docs/USER_GUIDE.md:219-224`.

### Run automatically (background check)
Free My ID keeps checking by itself, and catches up if the computer was asleep or off. You can turn it on or off in Settings.
Source: `docs/USER_GUIDE.md:109`, `docs/USER_GUIDE.md:113`.

### DROP (California)
A free, official California state website where one request goes to brokers registered in California. Free My ID cannot file it for you; it gives you a link. The web address and agency details are marked "TODO verify" in the guide: not sure.
Source: `docs/USER_GUIDE.md:208-210`, `docs/USER_GUIDE.md:215`.
