# First-week launch kit (drafts for the user to approve)

Status: DRAFT, 2026-11-07. Nothing here has been posted, sent or submitted. The user approves each piece and posts it themselves. Follows docs/POSITIONING.md and the never-use list in docs/MARKETING_COPY.md. Facts: v0.1.0 for Windows 10 and 11, free, open source (AGPL), unsigned installer (blue SmartScreen box), no account, nothing sent to us. No pricing. No counts of people helped (we have none).

Before posting anything: open https://freemyid.org/ and the download page on a clean machine, and confirm the button works. Until the redesign is deployed (WR-38), the live site may still say the download is "opening soon"; hold the posts until it does not.

Rules for every post: no countdown or "act now", no screenshots of anyone's real profile, no tagging real people, no mention of Meta's logo, no claim about what happens to a person's Facebook account. Link goes in the first comment if the user prefers (Facebook often shows fewer people a post with a link in it).

---

## Facebook post 1: "The post went to the wrong place" (the swap)

> If you ever posted "I do not give Facebook permission to use my information", you were right to care. That feeling is worth keeping.
>
> The trouble is that the post goes to Facebook, and Facebook isn't who's selling your name, address and phone number. People-search websites are, and anyone can look you up on them.
>
> Free My ID sends your "I do not consent" to those sites, through each site's own removal process, then keeps checking. It's free, it runs on your own computer, there's no account, and it never asks for your Social Security number or bank details.
>
> It only works on those people-search sites. It doesn't change anything Facebook does with your account. And sites sometimes list people again, which is why it keeps checking.
>
> Windows 10 or 11: [link]

Facts used: scope line (README, POSITIONING rule 6), no SSN/bank (BRAND trust panel), re-listing (README "Listings come back").

## Facebook post 2: "Look yourself up" (calm, no fear)

> Try this tonight: type your full name and your town into a search engine, and add "people search".
>
> Many of us find our address, our age and the names of our relatives on a handful of websites. Those sites are legal businesses, and they sell what they collect to whoever pays.
>
> You can ask each one to take you off. It's tedious by hand: different forms, different emails, and some of them list you again later. We built Free My ID to do the asking and the re-checking for you. It's free and it stays on your computer.
>
> It can't clear everything, and it doesn't touch what Facebook or Google keep. It just takes the sites that sell people's details off your list of worries. [link]

Facts used: "legal businesses ... sell to anyone" (MARKETING_COPY why-not-terrorists; model of the broker business), "different forms/emails" (registry methods, README). Does not say what specific sites show; "many of us find" is soft. If the user wants "many" removed, say "you may find".

## Facebook post 3: "For the family" (helper post, shareable)

> If you're the one in the family who "does the computer stuff", here's a gift for the people you worry about.
>
> Free My ID helps a parent or grandparent ask people-search websites to remove their address and phone number. It has six simple screens, big buttons and plain words. Sit with them for the first run, then it checks again in the background.
>
> It's free and open source, so anyone can read what it does. There's a one-page helper guide and a printable card for the fridge on the website: [link]
>
> It's new (version 0.1.0), so if anything confuses you, tell us; that helps the next family.

Facts used: six screens (wizard STEPS = 6, checked in LAUNCH_CHECKLIST 3), helper guide and fridge card (docs/HELPER_GUIDE.md, docs/assets/fridge-card.html, /families/ page WR-11). "checks again in the background" = scheduled runs (PLAN_V1). Confirm /families/ is live before using the guide line.

Why these three and not more: one for the instinct (post 1), one for the curious (post 2), one for the helper, who is the real buyer of trust (post 3). POSITIONING: this crowd trusts family recommendations over ads.

---

## Helper email (one family member to another)

Draft only. Send it from the user's own address to a relative the user chooses; this is not a mass mail.

Subject: Something I'd like to set up for you, free and quick

> Hi [Name],
>
> You know how people-search websites list your address and phone number for anyone to look up? There's a free program for Windows called Free My ID that asks those sites to take you off, and keeps checking in case they list you again.
>
> I'd like to sit with you and set it up. It takes a short sitting, six screens, and I'll do the clicking. A few things so you're not worried:
>
> - It costs nothing, and it never asks for your Social Security number, bank or card details.
> - It runs on your computer. There's no account, and nothing is sent to the people who made it.
> - Windows will show a blue box the first time, because the program isn't signed yet. I'll show you which button to press, and you can uninstall it any time.
> - It only deals with those lookup websites. It doesn't change anything about Facebook or your email.
> - It can't promise a site will agree or that nobody ever lists you again. It keeps asking.
>
> The website is https://freemyid.org/ if you'd like to look first. Does Sunday work?
>
> Love,
> [Your name]

Facts used: all from the README, BRAND trust panel and SmartScreen/uninstall copy on the site. "Short sitting" is deliberate: no timing is promised (WR-27 removed untimed install claims).

---

## winget / PyPI blurb

Use only after each package is actually live (ONBOARDING_PATHS.md; winget needs a manifest PR accepted into microsoft/winget-pkgs; PyPI needs an upload). Until then do not post commands that won't work. winget package id proposed: `FreeMyID.FreeMyID`.

Short description (winget `ShortDescription` and PyPI summary, under 100 characters):

> Ask people-search sites to remove your details, and keep checking. Local, free, open source.

Longer description (winget `Description`, PyPI long description lead):

> Free My ID finds your listings on people-search and data-broker sites, asks each site to delete your details through its own removal process, and re-checks on a schedule in case listings come back. It runs entirely on your computer: no account, no cloud service, no telemetry. It never asks for your Social Security number, bank or card details. It only works on people-search sites; it does not change what Facebook or Google do with your account, and a site's removal covers that site only. Windows 10 and 11. Free software under AGPL-3.0-or-later.

Tags/keywords: privacy, data-brokers, opt-out, people-search, ccpa, gdpr.
Note for the manifest: say "unsigned installer" in the release notes, and link the SHA256 on the release page. PyPI users get the command-line version; link to the website for non-technical readers. Do not say "removes you from the internet".

Facts used: README (what it does, limits), pyproject (name freemyid, AGPL-3.0-or-later), LICENSE.

---

## Order of the week (suggestion)

1. Day 1: check the live site; post 1 on the user's own timeline.
2. Day 2: helper email to one relative; do the real setup with them; note what confuses them and send it back as copy fixes.
3. Day 4: post 3 (family).
4. Day 6: post 2 (look yourself up), after day 1 comments have been answered calmly.
5. Any day, only when live: winget/PyPI blurb on the GitHub release notes.

Answer comments plainly. If someone asks whether it stops phone listening or government surveillance, the honest answer (POSITIONING) is: "No, it can't. It takes your details off people-search sites." Never argue about the original "I do not consent" post.
