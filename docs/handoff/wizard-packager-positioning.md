# Wizard-packager: positioning copy audit and proposals (2026-11-06)

PROPOSAL ONLY. No source files were edited. Rules refer to the six copy rules in `docs/POSITIONING.md`:
R1 never mock, R2 literal accuracy, R3 no fear selling, R4 look unlike a scam, R5 use their words, R6 scope (not Facebook).

Line numbers are from the working tree on 2026-11-06. `server.py` has uncommitted work, so its lines may drift.

## 1. Audit table

Cross-cutting findings first, because they cut across many rows:

- **R5/R6 is the biggest gap.** "data broker", "broker", "brokers" appear about 25 times in user-facing text and are never explained. The only people-search wording is in the consent text. Nothing anywhere says Vanish does not touch Facebook.
- **R2 is mostly handled well** (the HONESTY line and the "removed means that one site" lines are good). The risks are the chip label "removed", the sentence "N sites done", the Settings and consent page headings, and the heading "Evidence".
- **R4 is missing entirely.** There is no "what Vanish will never ask you for" line, and no sender name appears in the copy (this is for the email templates owned by the engine, and I did not audit them).
- **R3 is clean.** There are no countdowns, red alarm screens or fear words. Keep `.error` red for real errors only. One thing to check in `style.css`: the "Not running yet" banner on the Home page uses the `.error` class, so a consent problem looks like an alarm.

| file:line | current text | proposed text | rule |
|---|---|---|---|
| ui.py:18-20 (HONESTY, shown on every wizard step and in the report) | "Please know: some brokers need a manual step from you, listings can reappear later, and \"removed\" only means removed from that one broker, not from the whole internet. Vanish keeps checking so you do not have to." | "Good to know: a few sites need a step from you. Sites can put your details back up, which is why Vanish keeps checking. When we say a site \"confirmed\", that means that one site only. Vanish works on people-search sites. It does not change anything on Facebook or Google." | R5, R6 (drops "brokers", adds scope) |
| ui.py:23-28 CHIP_LABEL `REMOVED: "removed"` | "removed" | "gone when we last looked" (short chip: "not listed now"). Keep `CONFIRMED: "broker confirmed"` but change to "site confirmed". | R2 (a chip alone, without the footnote, overpromises) |
| ui.py:23-28 `FOUND: "found"`, `NEEDS_HUMAN: "needs you"`, `AWAITING_VERIFICATION: "pending verification"` | as shown | "found" -> "your details are listed"; "pending verification" -> "waiting for the site to reply"; "needs you" is fine | R5 ("verification" is jargon) |
| ui.py:44-46 nav | "Emails to approve" / "Add a person" | OK. Consider "Emails waiting for you". | - |
| ui.py:107-115 MAILBOX_CHOICES | "Skip, I'll do these by hand" / "Vanish prepares each message and opens your email for you." | OK. | - |
| ui.py:162-166 (authorized-agent note) | "If you are helping an adult, you need their signed permission. Open the form to print. ..." | OK. Add: "Vanish never asks anyone for a Social Security number, bank or card details." (put once on this screen, see section 2) | R4 |
| ui.py:167-168 lead | "Vanish asks websites that sell personal details to delete them. Everything stays on this computer." | See section 2 (welcome text). Replace with the declaration framing and "people-search sites". | R5, R6 |
| ui.py:170 | "Type your full name here to say yes" | "Type your full name to sign" (it is a signature, so name it as one) | R5 |
| ui.py:197 | "A city and state is enough. Websites show the town, so that is what Vanish looks for." | OK, but "Websites" -> "People-search sites" the first time. | R5 |
| ui.py:203-204 | "...It is never sent to a website." | Contradicts the data-minimization rule slightly (sites do get the fields they already show). Proposed: "Vanish uses this only on this computer to tell you apart from other people with your name. It is never sent to anyone." Verify this matches engine behaviour: a broker sends back a listing that shows some of these fields, and Vanish quotes those in the letter. Orchestrator to confirm; USER_GUIDE s.10 has the same claim. | R2 |
| ui.py:217-221 `finish` list item 1 | "Vanish looks for the person on data-broker websites." | "Vanish looks for the person on people-search sites (sites that publish names, addresses and phone numbers)." | R5 |
| ui.py:218 | "Where it can, it sends the removal request itself." | "Where it can, it sends the request asking the site to delete the details." Avoid "removal request" without saying who removes. | R2 |
| ui.py:225-227 | "...adds one small Vanish task to Windows (Task Scheduler)..." | Jargon only on the second mention, and it is clear. Keep. Add "You can stop it any time in Settings." (already present, good for R4). | - |
| draft.py:38-39 CONSENT_TEXT[0] | "...on \"people-search\" and data-broker websites, and ask those sites to remove it." | "...on people-search sites (websites that publish names, addresses and phone numbers) and asks them to delete it." "data-broker" is explained in the guide only. Consent text changes require a CONSENT_VERSION bump (draft.py:36). | R5, R2 (sites delete, we ask) |
| draft.py:42-44 CONSENT_TEXT[2] | "When Vanish contacts a broker it sends only what that broker already shows..." | "When Vanish contacts a site it sends only what that site already shows about the person, plus the separate email address you set up." | R5 |
| draft.py:44-46 CONSENT_TEXT[3] | "Honest limits: some brokers need a manual step..., \"removed\" only ever means removed from that one broker, not from the whole internet." | Good in tone. Replace "brokers" with "sites". Add a sentence on scope: "Vanish does not change what Facebook, Google or any other service does with your account." | R5, R6 |
| draft.py:49-55 BASIS_LABELS | "I am this person and I am allowing Vanish to act for me." | OK. "(an authorized agent)" is jargon in brackets; keep only for the third label as it names the legal role. | - |
| draft.py:59-62 STEP_TITLES | "Welcome. Who is this for?" / "An email address for removal replies" | "Welcome. Who is this for?" -> see section 2. "An email address for removal replies" -> "A separate email address for replies" ("removal" repeated is fine, but "replies" is what they get). | R5 |
| draft.py:78-80 OUTLOOK_MSG | "...no longer allow programs like Vanish to sign in..." | OK. | - |
| dashboard.py:62-70 status_sentence | "Vanish is working. {done} sites done, {waiting} waiting, {n} need you." | "Vanish is working. {done} sites have confirmed or no longer list you, {waiting} are still waiting, {n} need you." A "done" tally invites reading it as "finished forever". Add the re-check reason once on the Home page (already in the footnote at dashboard.py:169). | R2 |
| dashboard.py:65-66 | "Vanish is set up. Nothing to do yet." | OK. | - |
| dashboard.py:147-149 practice banner | "Practice mode. Vanish is looking but is not sending anything yet." | OK, calm and accurate. | - |
| dashboard.py:152-154 | `<div class="error">Not running yet for ...` | Use the `.note` class, not `.error` (styling reads as an alarm). Text unchanged. | R3 |
| dashboard.py:156-158 | "N email(s) waiting for your OK" | "N message(s) waiting for your OK. Nothing is sent until you press Approve." | R4 |
| dashboard.py:163 | "You have nothing to do right now. That is good." | OK. | - |
| dashboard.py:169-170 | "\"Removed\" means removed from that one broker only. Listings can reappear, which is why Vanish keeps re-checking." | "A site that says it deleted you has done that for that site only. Details can reappear, which is why Vanish keeps checking. Vanish does not change anything on Facebook or Google." | R5, R6 |
| dashboard.py:201 | `<h2>Brokers</h2><table><tr><th>Broker</th>` | "Sites" and "Site". Do the same in report.py:40. | R5 |
| dashboard.py:210 | "No brokers checked yet. Run <code>vanish scan</code>." | "No sites checked yet." Remove the terminal command from the user-facing page (they are on Windows with no terminal). | R5 |
| dashboard.py:213 | `<h2>Evidence</h2>` ... "Screenshots are stored encrypted..." | Heading "Receipts". Text "Pictures of what each site showed us and what it replied. Kept on this computer only." (also feeds idea "Proof they can see") | R5 |
| dashboard.py:258-272 confirm_real_page | "Vanish will email removal requests to data brokers..." | "Vanish will now send your requests to people-search sites by email, and fill in their forms where a site allows it. Each one names the person and only the details that site already shows, plus the separate email address. Nothing is paid for." Last para: "Requests already sent cannot be taken back" is honest and good; keep. | R5 |
| dashboard.py:279-285 settings | "Once a day Vanish can check quietly in the background." | OK. | - |
| dashboard.py:305-306 | "It never pays." | Keep. Also add the R4 line here: "Vanish will never ask for a Social Security number or bank or card details." | R4 |
| report.py:38 | `<h1>Vanish report for {label}</h1>` | See section 2 (report headline). | R2 |
| report.py:39 | "Summary: N removed, ..." (built from CHIP_LABEL) | Use the sentence form "Asked N sites to delete the details. N confirmed. N still waiting. N need a person." Counts of REMOVED now render as "gone when we last looked". | R2 |
| report.py:40 | `<th>Broker</th><th>Status</th>` | "Site", "Status", "Last checked", "Last asked". | R5 |
| server.py:46 "created" | "All set. Vanish is starting its first check now." | OK. In practice mode say "first practice check" if the draft will be in practice (first run is dry-run). | R2 |
| server.py:54 "noengine" | "The sending engine is not available yet in this install." | "Sending is not switched on in this copy of Vanish yet." ("engine" is jargon.) | R5 |
| server.py:170 | "Open Vanish using the link printed when it started." | Non-technical users are never shown this (desktop launcher), but if they see it: "Please open Vanish from its icon on your desktop." | R5 |
| server.py:186 | "Bad or missing form token. Go back and try again." | "That page timed out. Go back and try again." | R5 |
| server.py:403 | "Vanish is closing. You can close this tab." | OK. | - |
| server.py:546-548 (import page) | "Use a family setup file ... Passphrase ... You will review everything and give your own permission..." | "Passphrase" -> "Password for the setup file". Rest is good. | R5 |
| server.py:633-634 | "Vanish is running. If your browser does not open, visit: ... Press Ctrl+C" | Terminal only, fine for developers. | - |
| flows.py:62-77 (CLI consent) | "== Permission ==", "Type your full name to sign", `"IMAP server"`, `"SMTP server"`, `"IMAP port"` at flows.py:149-150 | CLI is developer/helper use. Still change "IMAP server" -> "Incoming mail server (IMAP)" and "SMTP" -> "Outgoing mail server (SMTP)" to match the web wording. | R5 |
| flows.py:121 | "Personal emails, separated by ;" | "Email addresses they use (only used to recognise them), separated by ;" | R5 |
| firstrun.py:37-38 | "Vanish needs a web browser to fill in forms and none was found. Download a private copy of Chromium (about 150 MB)?" | On Windows the Edge route should make this unreachable. If it does appear: "Vanish needs a web browser to fill in forms. Download a small extra browser just for Vanish (about 150 MB)?" ("Chromium" is jargon.) | R5 |
| app.js:25, :35, :59-60 | "Testing...", "The test did not finish.", "Copied!", "Select and copy by hand" | All fine. | - |
| app.js:70 | `data-confirm` strings come from Python | See dashboard.py:249 "Send this email now?" (fine). | - |
| USER_GUIDE.md:25 | "\"People-search\" sites such as Spokeo ... collect your name... Most of them must let you opt out" | "opt out" is jargon on first mention. Proposed: "Most of them must let you ask them to take your details down." Use "opt-out" only after one explanation. Also, "Most of them must" is a legal claim: rephrase to "Many of them have a way to ask". | R5, R2 |
| USER_GUIDE.md:27-33 | "It searches each site for you. It fills in each site's own removal form..." | OK. Add a first bullet: "It asks the sites to delete your details, in the formal way they are required to answer." | R5 |
| USER_GUIDE.md:35-40 | Limits list | Good. Add a fifth bullet: "**Vanish does not change what Facebook does.** It works on people-search sites. For Facebook, see the separate checklist." | R6 |
| USER_GUIDE.md:42-50 | "separate email address..." | OK. | - |
| USER_GUIDE.md:59 | "(`imap.gmail.com` and `smtp.gmail.com`)" | IMAP/SMTP are in the wizard only for \"Another email service\". In the guide: "The mail server settings are filled in for you." Remove the host names, or put them under a "for helpers" note. | R5 |
| USER_GUIDE.md:74-82 | "STARTTLS", "Bridge ... `127.0.0.1`, ports 1143 and 1025" | Move to a "for whoever is helping" box. Not for the primary reader. | R5 |
| USER_GUIDE.md:86-92 | "Open a terminal and run: vanish setup ... 127.0.0.1" | Out of date for the Windows installer (no terminal). Replace with "Open Vanish from the desktop icon." Keep the terminal flow under "Advanced". | R5 |
| USER_GUIDE.md:96-109 | wizard step list (9 steps) | Out of date. The wizard now has 6 screens (D6). Update once copy is final. | - |
| USER_GUIDE.md:150 | "**Removed** Vanish searched again and the listing is gone from this site." | Good and accurate. Change the label to match CHIP_LABEL ("Not listed now"). | R2 |
| USER_GUIDE.md:158-159 | "...follow-up email citing your state's privacy law..." and "drafts a formal legal demand" | "formal legal demand" and "Attorney General complaint" can sound alarming. Calmer: "a firmer letter, which waits for your approval" and "a link to file a complaint with your state, if you want to". Substance is unchanged. | R3 |
| USER_GUIDE.md:166 | "(CAPTCHA)" | OK (explained with the phrase "prove you're human"). | - |
| USER_GUIDE.md:238-244 s.10 | "Vanish talks only to the removal sites themselves and your removal mailbox." | Good. Add the R4 box: "Vanish will never ask you for a Social Security number, bank details or a card number, and it never charges you." | R4 |
| USER_GUIDE.md:248 | "Will this remove me from Google? No..." | Good. Add Q: "Does this change Facebook?" and Q: "I posted 'I do not consent'. Did that work?" (see Myth vs fact card). | R6, R1 |
| USER_GUIDE.md:252 | "Does it cost anything? Vanish is free." | Must stay true for the commercial plan. Say "Vanish is free in this family version." | R2 |

Nothing in the audited files uses "erased", "guaranteed", or "100%". "Removed" is the only overpromise risk (the chip and the report summary). The words "data broker" and "broker" are the jargon problem. I did not find any text that says or implies Vanish changes Facebook, but the lack of any scope statement leaves it open (R6), which section 2's text closes.

## 2. Proposed replacement text

Tone: calm, short sentences, no mockery. All of this uses "people-search sites" with one plain explanation, never "data broker" on first mention.

### 2a. Welcome (screen 1, `ui.py:167-168` lead, `STEP_TITLES["consent"]`)

Title: **Welcome. Let's send your "I do not consent" to the right place.**

Lead (two short paragraphs):

> You may have posted "I do not give permission to use my information" before. You were right to object. That post goes to Facebook's feed, though, and nobody who sells your details has to read it.
>
> Vanish sends the same wish to the websites that publish your name, address and phone number (people-search sites), in the written form they have to answer. Then it keeps checking.

Below it, a compact "What Vanish will and won't do" card (R4 and R6 in one place):

> **Vanish will:** ask people-search sites to delete your details, tell you which ones replied, and check again later.
> **Vanish won't:** change anything on Facebook, Google or your other accounts. It also won't ask for a Social Security number, bank details or a card number, and it never charges you.
> Everything you type stays on this computer. You can stop or uninstall at any time.

Note: "never charges you" must match the commercial plan. For the family build it is true; revisit at public launch.

### 2b. Authorization step (the consent block plus the agent note)

Heading above the radios: **Who is this for?** (unchanged).

Radio labels (`draft.py:49-55`), same meaning, simpler:
- "This is for me. I am allowing Vanish to act for me."
- "This is for my child (I am their parent or legal guardian). They are under 18."
- "This is for an adult who has asked me to help. They have given me their signed permission."

Agent note (`ui.py:161-166`):

> If you are helping another adult, they need to sign a short permission form first. [Open the form to print.] After they sign it, take a photo or scan and attach it here, or add it later from their page. Vanish will not start until it is attached.

Signature field label: **"Type your full name to sign"**. Checkbox: **"I have read this and I agree."** Footer hint: "Wording version 2026-11-b. I have a family setup file."

Authorization form (`ui.py:283-296`): change "data brokers and people-search websites" to "people-search websites and companies that sell personal information", and keep the rest. "Applicable state privacy laws" is fine in a legal form.

Consent paragraph 1 (new): "Vanish will look for the information of the person named in this setup on people-search sites (websites that publish names, addresses and phone numbers) and ask those sites to delete it." Paragraph 4 gets the Facebook/Google sentence from the table. Bump `CONSENT_VERSION` to `"2026-11-b"`.

### 2c. Report headline (`report.py:38-39`)

Print-friendly and shareable with family, so no PII beyond the on-screen label.

> **{label}: what Vanish has asked, and what came back**
> As of {date}, Vanish has asked **{N}** people-search sites to delete this person's details. **{C}** have confirmed or no longer list them. **{W}** are still waiting. **{P}** need a person to do one step.
>
> That post didn't stop anyone. This is the same wish, sent to the right place in the form the sites have to answer. Sites can put details back up, so Vanish checks again, and this report shows each check.

The "That post didn't stop anyone. This does." line works as the dashboard welcome-back banner and the report subtitle, but I recommend against putting it verbatim as a headline in the report. The verbatim form is a claim ("this does") that reads as a guarantee in a document the user may print and show to a relative. Use it on the welcome screen and in marketing, where the next sentence immediately qualifies it. The wording above keeps the message, with the numbers doing the proving. If the user wants the verbatim line in the report, put the counts directly under it on the same screen.

Counts must come from stored statuses/requests only (no estimates), and N is the number of requests actually sent, not "found". In practice mode the headline is "Practice check: Vanish looked at {N} sites and found {F} that list this person. Nothing has been sent yet."

## 3. "My declaration" step on top of the consent screen

**Which screen:** the existing consent screen (`ui.py:157-174`, step `"consent"`, `draft.py:57`). It already has a version id, a typed-name signature, an "I agree" box, a basis choice and a timestamp (`Consent.attested_at`). The declaration is the same ritual aimed at a different party.

**Recommendation: one new step `"declaration"` directly after `"consent"`, rendered through the same template path**, not a second form on the consent page. Reasons: the consent page is already long, one-question-per-screen is the D6 rule, and a separate step gives it a title worth screenshotting.

What changes:

1. `draft.py`: add `DECLARATION_VERSION`, `DECLARATION_TEXT` (3 short paragraphs), insert `"declaration"` into `STEPS` after `"consent"`, add `STEP_TITLES["declaration"] = "Your declaration"`, add `NO_CONSENT_NEEDED` entry so it is not blocked, and include it in `visible_steps` edit mode as hidden (editing keeps the old declaration).
2. `ui.py` `_screen_body`: new branch rendering `DECLARATION_TEXT` in the same `card soft` + `_inp("declared_by", ...)` + `_check("declare_ack", ...)` markup as consent. `server.py` adds nothing new: the existing generic `/wizard/{step}` handler should pick it up if validation is registered in `draft.py` next to the consent validator. (I have not confirmed the handler is fully generic because `server.py` is mid-edit.)
3. Suggested declaration text (draft, for the user to reword):

   > I do not consent to my name, address, phone number or other personal information being sold, shared or published by companies I have never dealt with. I want them to delete it and stop selling it. I am asking Vanish to send this to the companies that publish or sell it.
   > Date and my typed name below are my signature.

4. The declaration sentence is also the first sentence of the letter body. This needs a change in the letter templates (engine/letters, owned by automation-engineer): optional `{declaration}` line, only when the profile has declared. For states with a verified law the statutory language still leads. For generic letters it opens with: "I do not consent to the sale or sharing of my personal information."

**New state (proposed, models are the orchestrator's):**

```python
class Consent(_Base):
    ...existing fields...
    declaration_version: str | None = None      # None = never made one (old profiles stay valid)
    declared_at: datetime | None = None
    declared_by: str | None = None              # typed name, may equal attested_by
```

Three optional fields on `Consent`, all defaulted, so existing DBs and bundles load unchanged. The schema must be regenerated (`tools/gen_schema.py`). No new table.

"Your declaration was sent to N companies" needs no new state: the dashboard counts `Request`s with a sent status (`store.list_requests`), per profile. In practice mode (dry-run) it shows "ready to send to N companies" instead, so we never claim "sent" before it is. Also the count excludes `covered_by` sites (they do not get their own request) so N matches what the report says.

Alternative that avoids model changes: store the declaration inside `attested_by` plus `text_version` as a combined version string (`"2026-11-b+decl-1"`). Not recommended; it would hide meaning in a string and the report could not show the declaration date.

Family bundles (`export_family_bundle`): declaration fields are cleared on export and made again by the recipient, same as consent. Export currently drops consent (the family member must give their own), so the new fields follow the same path.

## 4. Size estimates for the POSITIONING.md ideas

Sizes: S = under half a day, M = about one day, L = 2-3 days. Includes tests (httpx TestClient) and copy. Lines of code are for wizard-packager files only.

| Idea | Size | Notes |
|---|---|---|
| Copy audit fixes (section 1 table plus welcome/auth/report text) | M | About 60 string edits, a CONSENT_VERSION bump and updates to existing tests that assert on strings (`_test_drafts`). Do before anything else. Roughly 150 changed lines. |
| "My declaration" step | M (wizard) + S (models, orchestrator) + S (letters, automation-engineer) | Wizard side is about 80 lines plus tests, as most of the pattern is copied from consent. Hardest part is the letter change and getting the "sent to N" count to honour dry-run. |
| "Proof they can see" (receipts page, printable) | M | Extends `report.py` (about 100 lines) plus a dashboard route. Data is already stored (requests, replies, last_scan). Needs reply dates: check whether `Request` stores `replied_at`; if not, a small model change. Evidence images stay out of the printable version (PII). |
| Shareable "I did the real thing" post | S-M | Static PII-free SVG/PNG generated locally, with a Copy-text button. Bundle size small. The harder part is the policy decision (open question in POSITIONING: family build or public launch), plus a rule that counts are off by default. I would ship it with no numbers at all. |
| Facebook settings guide | M-L | Reuses the Assisted todo card (`todo_card` ASSISTED_OPT_OUT) so no new UI, but needs a hand-written checklist (about 6 to 8 steps) that stays correct as Facebook's menus change. That is content-research work (broker-researcher), and the EU/GDPR objection form is a separate letter. Also needs a new non-broker todo source, possibly a `TodoKind` addition. Menu names rot quickly: give each checklist a "last checked" date. |
| Myth vs. fact card | S | One static page and a link from the welcome screen and guide. About 40 lines plus 150 words of copy. Must pass R1: draft text "Does posting 'I do not consent' work? On its own, no: Facebook's own terms are what apply, and the people who sell your details never see the post. Here is what does work." Needs a fact-check by the user before shipping, since it makes a claim about Facebook's terms. |

Suggested order: copy fixes, then myth card (S, high payoff), then declaration, then receipts, then Facebook guide, then the shareable post.

## Open items for the orchestrator

- Confirm the data-minimization wording at `ui.py:203-204` and `USER_GUIDE.md:243`: "never sent" versus "only what the site already shows".
- Models: the three optional `Consent` fields in section 3, and (if the receipts page needs it) a reply date on `Request`.
- A style change in `static/style.css`: stop using `.error` for non-error banners (dashboard.py:152, 183). I did not audit `style.css`.
- The `USER_GUIDE.md` wizard step list and "open a terminal" instructions are out of date relative to the 6-screen Windows plan.
- I did not audit email/letter templates (`engine`, `letters`), the broker registry text, or `FAMILY_QUICK_START.md`. These also need the same rule check, especially R4 (named sender) and the R2 "confirmed" wording in letters.
