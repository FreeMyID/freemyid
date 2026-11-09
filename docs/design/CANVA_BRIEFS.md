# Canva design briefs (CB-01 to CB-06)

Author: Jordan Ellis (brand-marketing, requester). Date: 2026-11-08. Status: draft for Morgan to turn into Codex work orders (docs/SDLC.md, "Codex with GitHub and Canva"). Nothing here is posted. Posting needs owner approval.

## Shared rules (apply to every brief)

- **Sources.** Colours and type: `docs/BRAND.md` (there is no `brand/BRAND.md`) and `site_src/tokens.yaml`. Claim rules: `docs/POSITIONING.md`. Existing art: `brand/README.md`, `docs/handoff/graphic-designer.md`.
- **Colours (light theme, hex from tokens.yaml).** Navy band `#1b2f5b`, heading navy `#14264a`, brand blue `#1b3366`, text `#151b26`, muted text `#414b5c`, page white `#ffffff`, off-white `#f4f6f9`, soft blue tile `#e6edf8`, flag red `#a3202e` (small accent only, never alarm). Dark variants where a brief needs them: bg `#0d131d`, text `#eef1f6`, heading `#dde7fb`, red-on-dark `#f5a3ab`. Pairs allowed: white or `#eef1f6` on `#1b2f5b`; `#14264a` or `#151b26` on white or `#f4f6f9`. Red text only on white at 24 px or larger. No other colours, no gradients, no flag imagery beyond a thin red bar.
- **Type.** The site uses one sans family (system-ui / Segoe UI), no serif since v2. In Canva use **Open Sans** (nearest to Segoe UI; Bold for headlines, Regular for body). Graphic-designer confirms the font at review. Sizes on a 1080 px canvas: headline 80 px or larger, body 40 px or larger, footer line 32 px or larger. Left aligned, sentence case, no all caps, no italics.
- **Logo.** Import `brand/logo/final/wordmark-lockup.svg` as is. On dark backgrounds (CB-02, CB-06) use the dark-palette export of `wordmark-lockup.svg` (its built-in `prefers-color-scheme: dark` colours: tile and text `#c4d5f7`, bar `#f5a3ab`), supplied by the in-house graphic-designer: Canva ignores the SVG's dark-mode rule, so do not recolour it yourself. `mark-dark.svg` is the badge alone, not a wordmark lockup, and does not meet these briefs. Never redraw, recolour, stretch or recreate it in Canva, and use no Canva stock in or near it. Clear space equals the height of the star tile.
- **Never on any image.** "guaranteed", "erase", "100% removed", "safe", "protection", "American-made", a price, a count of people helped, a version number, a countdown, "act now", red alarm styling, party or politician imagery, Meta/Facebook/Instagram logos, screenshots of real profiles, real faces. Do not mention proof vault, PDF report, monitoring, relist detection or Outlook sign-in (not on main).
- **People and data.** Jane Q Testperson, Springfield IL only, and only if a brief asks for a persona. Illustration style over photos. A photo only if licensed Canva stock, a brief allows it, and the manifest records it.
- **Accessibility.** Text contrast at least 4.5:1 (the pairs above are computed in tokens.yaml; check anything else). Each file needs alt text (given per brief, put it in `brand/codex/MANIFEST.md`). Never put the only copy of a fact in an image: the post caption repeats it.
- **Export.** To `brand/codex/<WO>/` as PNG, plus PDF or SVG where Canva allows. Name files `cbNN-<slug>-<WxH>.png`. Record the Canva link and any stock element in the manifest.
- **Reviewer for all:** graphic-designer (Iris Novak). Copy sign-off: Jordan. No file is used before both approve.
- **Held items.** Nothing may go out before the owner approves, and none of these mention v0.3, which is not yet published.

## Already exists, not re-briefed

- Facebook cover: `brand/social/avatar/facebook-cover-1640x624.png` (centred, mobile-safe). Not redone.
- Profile avatars, X/Bluesky/LinkedIn/YouTube/Mastodon banners, OG default, repo preview, release 0.2 and 0.3 cards: in `brand/social/`.
- App screenshots (`brand/screenshots/app-v3/`), feature and guide illustrations (`brand/v3/features/`, `brand/illustrations/`), /developers/ art.
- Fridge card: in-house HTML to PDF with a QR code (`docs/assets/fridge-card.html`, `brand/src/render_fridge_card.py`). Left in-house because a scannable QR must stay exact. No open art WRs in `docs/WEBSITE_REQUESTS.md`.

---

## CB-01 Facebook and Instagram post set (four templates)

**Goal and audience.** Reusable feed images for the Facebook-first audience (older, non-technical, wary of scams). One idea per image, calm, readable on a phone.
**Sizes and formats.** Each template at 1080x1080 and 1080x1350, PNG. Eight files. Keep 90 px margins; for the 1350 version keep all text inside the middle 1080x1080 area of the canvas so a square crop still reads.
**Layout.** White or `#f4f6f9` background, headline in `#14264a`, a 12 px red bar `#a3202e` above the headline, wordmark lockup bottom left, `freemyid.org` bottom right.

**Exact copy (word for word).**
- A, "wrong place":
  - Headline: `That post went to the wrong place.`
  - Body: `The sites that list your name, address and phone number are people-search sites. Free My ID asks them to take your details down.`
  - Footer: `Free and open source. freemyid.org`
- B, "scope":
  - Headline: `It takes your name off people-search sites.`
  - Body: `It does not change what Facebook does with your account.`
  - Footer: `Free and open source. freemyid.org`
- C, "keeps checking":
  - Headline: `It keeps checking.`
  - Body: `Sites sometimes list people again, which is why Free My ID keeps checking.`
  - Footer: `Free and open source. freemyid.org`
- D, "download":
  - Headline: `Free for Windows 10 and 11.`
  - Body: `No account. No cloud. Runs on your own computer.`
  - Footer: `Download at freemyid.org`

**Do.** Plain flat shapes, one small line icon at most (a magnifier for A, a check mark for C; draw in Canva elements outline style, brand colours). Large type.
**Don't.** Add a photo, a hand, a lock, a shield, a warning triangle, or a "before/after".
**Accessibility alt text.**
- A: `Free My ID. That post went to the wrong place. The sites that list your name, address and phone number are people-search sites, and Free My ID asks them to take your details down.`
- B: `Free My ID takes your name off people-search sites. It does not change what Facebook does with your account.`
- C: `Free My ID keeps checking. Sites sometimes list people again, which is why it keeps checking.`
- D: `Free My ID is free for Windows 10 and 11. No account, no cloud, runs on your own computer. Download at freemyid.org.`
**Used in.** Facebook page and Instagram posts (`docs/marketing/launch_week.md` post pack), after owner approval.
**Acceptance.** Eight files, copy matches exactly, no extra words, logo is the SVG import, contrast pairs as above, headline still readable at 300 px wide, manifest filled, graphic-designer approves.

## CB-02 "I did the real thing" shareable image

**Goal and audience.** The share-with-friends moment from POSITIONING (shareable post): the person who used to paste "I do not consent" and now tells friends what they did. Word of mouth.
**Sizes and formats.** 1080x1080 and 1080x1350 PNG.
**Exact copy.**
- Headline: `I stopped just posting it. I actually sent it.`
- Body: `I asked the people-search sites that list my details to take them down, with Free My ID. It's free, there's no account, and it runs on my own computer.`
- Footer: `freemyid.org`
- Navy `#1b2f5b` background, white text, one thin red bar. Wordmark: the dark-palette `wordmark-lockup.svg` export (shared rules, Logo).
**Do.** Leave the image with no name, number, count, screenshot or result. It must be safe for anyone to post.
**Don't.** Quote or imitate Meta's notice, write "I do not consent" as a block of fake legal text, or say any site "must" comply.
**Alt text.** `Free My ID. I stopped just posting it. I actually sent it. I asked the people-search sites that list my details to take them down, with Free My ID. Free, no account, runs on my own computer.`
**Used in.** Facebook and Instagram; a later optional share step in the app is only a proposal (not on main), so do not design app UI here.
**Acceptance.** No personal data or counts, both sizes exported, reads as first person, manifest alt text filled, graphic-designer approves.

## CB-03 "How it works in 3 steps" carousel

**Goal and audience.** Show a nervous first-timer that it is simple. Facebook and Instagram carousel, also reusable as a website section.
**Sizes and formats.** Five slides at 1080x1350 PNG, plus a PDF of all five. Slide numbers in the corner ("1 of 5").
**Exact copy.**
- Slide 1 headline: `How Free My ID works, in 3 steps.`  Body: `Free, open source, and it runs on your own computer.`
- Slide 2: `Step 1. Tell it who to look for.`  Body: `A name, and the city and state you live in.`
- Slide 3: `Step 2. It asks the sites to take you down.`  Body: `It uses each site's own removal process. If a site needs you to tick "I'm not a robot", it shows you a card and you do it.`
- Slide 4: `Step 3. It keeps checking.`  Body: `You see what is confirmed, what is waiting and what needs you.`
- Slide 5 headline: `No account. No cloud.`  Body: `It never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime.`  Footer: `freemyid.org`
**Visuals.** Slides 2 to 4 may use a crop from `brand/screenshots/app-v3/` (fake persona, already approved) at the left, or a simple flat icon from `brand/icons/app/`. Do not recreate app screens in Canva. Step numbers in navy circles, white digits.
**Don't.** Show anything the app does not do on main, show a result number, or claim a time.
**Alt text.** One line per slide: the headline and body above, spoken as a sentence. For a screenshot crop add `Screenshot of the Free My ID app with a made-up person.`
**Used in.** Facebook and Instagram carousel; the PDF can go to the website team as section art.
**Acceptance.** Copy exact, steps match the real wizard, screenshot crops come from the approved folder unaltered, five PNGs and one PDF, manifest filled.

## CB-04 "What we never ask for" trust card

**Goal and audience.** Scam-wary viewers. The best trust signal is saying plainly what we will not do, as on the fridge card and the welcome screen.
**Sizes and formats.** 1080x1080 and 1080x1350 PNG.
**Exact copy.**
- Headline: `Free My ID will never ask for:`
- List: `Your Social Security number` / `Your bank or card details` / `Your everyday email password`
- Closer: `If something says it is us and asks, it isn't. Stop and ask someone you trust.`
- Footer: `freemyid.org`
Source: the three lines are the fridge card and the BRAND trust panel (`docs/BRAND.md`). Keep "email password" only if the fridge card text still says it at export.
**Visuals.** Each list line gets a navy circle with a white cross-out-free marker: use a plain white dash, not a red X (no alarm styling). White background.
**Don't.** Use a shield, a padlock, "secure", "safe" or "protected".
**Alt text.** `Free My ID will never ask for your Social Security number, your bank or card details, or your everyday email password. If something says it is us and asks, it isn't. Stop and ask someone you trust.`
**Superseded by WO-177 (Morgan, 2026-11-08).** The list and the alt text above are replaced by `docs/vendor/WO-177.md` (master list from `/safety/`, no "email password" line). Use the alt text given there so screen readers hear the same list as the card.
**Used in.** Facebook, Instagram, the family-helper pages and print.
**Acceptance.** Copy exact, no red alarm styling, readable at 300 px wide, graphic-designer approves.

## CB-05 Website step art for "How it works" (light and dark pairs)

**Goal and audience.** Spot illustrations for the three steps on the homepage and the download page, matching CB-03 so the story is the same on Facebook and the site. Requested for Leo (web-developer) via graphic-designer. None exists today for this section (`brand/v3/features/` covers other pages).
**Sizes and formats.** Three illustrations, each 320x250 px artboard, exported SVG where Canva allows and PNG at 2x (640x500), in light and dark versions. Twelve files at most. Transparent background. Dark version uses the dark colours above.
**Subjects (no text inside the art).**
1. A name card with a house outline (who and where).
2. A page with an arrow going out to a web page (a request sent).
3. A magnifier over a list with check marks (checked and confirmed).
**Style.** Match the existing flat line style of `brand/v3/features/*.svg`: 2 px strokes, navy, soft-blue fills, one red accent at most. Open the existing SVGs for reference.
**Don't.** Add faces, hands, locks, clouds, flags, or any text.
**Alt text.** 1: `A name card in front of a small house.` 2: `A page with an arrow going out to a web page.` 3: `A magnifying glass over a list with check marks.`
**Used in.** Homepage and download page section; Leo places them. Not wired until graphic-designer approves.
**Acceptance.** Light and dark pairs for each, same stroke weight as the existing set, no text, below 30 KB each, renders on `#ffffff` and `#0d131d`.

## CB-06 Open Graph images for two share-heavy pages

**Goal and audience.** When someone shares a page on Facebook, the preview is the ad. The default OG image is generic. Two pages the audience actually shares need their own.
**Sizes and formats.** 1200x630 PNG, each under 150 KB. Keep text inside the middle 1000x500.
**Exact copy.**
- Image 1 (the "I do not consent" explainer page, when it exists): headline `That post didn't stop anyone. This does.`  Sub: `Free My ID asks the people-search sites to take your details down.`
- Image 2 (the family-helper page): headline `Helping a parent with their privacy online.`  Sub: `Free, no account, built so your grandparents can use it.`
Both: navy `#1b2f5b` background, white text, wordmark lockup (dark-palette `wordmark-lockup.svg` export, shared rules, Logo) bottom left, `freemyid.org` bottom right.
Tagline 2 in BRAND is for the Facebook-crowd landing only, never the printable report, so image 1 is for that landing page only.
**Don't.** Say "does the post work", name Meta, or show a persona.
**Alt text.** 1: `Free My ID. That post didn't stop anyone. This does. Free My ID asks the people-search sites to take your details down.` 2: `Free My ID. Helping a parent with their privacy online. Free, no account, built so your grandparents can use it.`
**Used in.** `og:image` on the two pages, set by web-developer (separate request when the pages exist, WR to be filed by Jordan). The default OG image stays for all other pages.
**Acceptance.** 1200x630 exactly, readable at 600 px wide, contrast at least 4.5:1, manifest filled.

---

## Suggested order for work orders

1. CB-03 (carousel) and CB-01 (post set), the launch pair. 2. CB-04 (trust card). 3. CB-06 and CB-05 once the pages they serve are built. 4. CB-02 after the owner decides whether the shareable post ships with the public launch (POSITIONING open question).

## New claims and sources

No new factual claims. Every line of image copy comes from `docs/POSITIONING.md` (core message, trust panel, scope), `docs/BRAND.md` (taglines, trust panel), the fridge card (`docs/assets/fridge-card.html`) or `docs/marketing/launch_week.md`. "Free for Windows 10 and 11" is from `docs/marketing/launch_week.md` facts line; the release manager re-checks it against the live release before posting.
