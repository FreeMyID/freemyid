# Identity lock checklists: IRS IP PIN, SSA, USPS Informed Delivery

Backlog item BL-IN-74. Researcher: Priya Shah [freemyid]. Accessed 2026-11-08.
Only irs.gov, ssa.gov and usps.com (plus uspis.gov, the Postal Inspection
Service, for scam facts) are cited as sources, except where a news article is
flagged as secondary. Not tax or legal advice. No real people's data used.

Access notes: irs.gov pages and usps.com/uspis.gov pages were read directly.
ssa.gov blocked my fetcher (HTTP 403) on every page, so the SSA facts below come
from search-result summaries of ssa.gov pages. Those are marked
"(search summary)" and listed in UNVERIFIED at the end.

---

## 1. IRS Identity Protection PIN (IP PIN)

**In plain words:** A six-digit number that only you and the IRS know. Once you
have one, a thief who has your Social Security number still cannot file a tax
return in your name, because the return is rejected without the PIN. You get a
new PIN every year. You can get one even if you don't have to file a return.
Source: https://www.irs.gov/identity-theft-fraud-scams/get-an-identity-protection-pin

**Official URLs**
- Main page: https://www.irs.gov/identity-theft-fraud-scams/get-an-identity-protection-pin
- FAQ: https://www.irs.gov/identity-theft-fraud-scams/frequently-asked-questions-about-the-identity-protection-personal-identification-number-ip-pin
- Form 15227 (paper route) is linked from the main page. I did not fetch the form itself.

**Eligibility**
- Anyone with an SSN or ITIN who can verify their identity (main page).
- Parents and legal guardians can request one for a dependent (main page).
- Under 18: must use the alternative enrollment options (Form 15227 or in person), no online account. Dependents 18 or older can use Login.gov or ID.me online (FAQ).
- Automatic enrollment if the IRS has you as a tax identity-theft victim. A notice (CP01A) is mailed mid-December to early January (FAQ).

**Steps (three routes, easiest first)**
1. Online: register or sign in at IRS.gov (identity verification with Login.gov or ID.me, per FAQ), open your IRS online account or the IRS app, and go to the IP PIN section of your profile. The PIN shows on screen (main page).
2. By mail, Form 15227: only if your adjusted gross income on your last return was under $84,000 (single) or $168,000 (married filing jointly), you cannot make an online account, you have a valid SSN or ITIN, and you can answer a phone call from the IRS (they call to verify you). The PIN comes by mail, usually in 4 to 6 weeks (main page).
3. In person: make an appointment at an IRS Taxpayer Assistance Center. Bring one federal or state photo ID plus one other ID. For a dependent, bring two IDs for the dependent plus your own photo ID and one other ID. The PIN usually arrives by mail within 3 weeks (main page).

**Cost:** The IRS pages I read do not state a price and describe no fee anywhere in the steps. The task brief expects it to be free. UNVERIFIED as an explicit statement; to confirm, find the sentence "free" on an IRS IP PIN page or in IRS Publication 5367.

**Gotchas for older, non-technical users**
- A new PIN is generated every calendar year. Online enrollees do not get a mailed notice, so they must look it up in the IRS online account or app each year, generally from mid-January to mid-November (main page). Anyone who cannot use the website needs the paper or in-person route and should expect a mailed letter instead.
- The PIN must be typed on every return in the 1040 family (1040, 1040-NR, 1040-PR, 1040-SR, 1040-SS), including prior-year returns filed this year. A wrong or missing PIN gets an e-file rejected or a paper return delayed (main page).
- Married couples: each spouse who has a PIN enters their own (FAQ). Dependents' PINs go on e-filed returns (FAQ).
- Lost PIN: do not file Form 15227 again. Look it up in the app or online account. If that fails, call 800-908-4490 (Mon to Fri, 7 a.m. to 7 p.m. local time); the IRS mails it within 21 days (FAQ).
- Opting out: only allowed if you joined voluntarily and were never a tax identity-theft victim. Allow up to 72 hours after opting out before e-filing without a PIN (FAQ).
- Scam warning: the IRS will never ask for your IP PIN by phone, email or text. "Phone calls, emails or texts asking for your IP PIN are scams" (main page).
- Tax preparers need the PIN too. Tell the preparer; do not email the number.
- The online route needs a smartphone or computer and an ID.me or Login.gov account (selfie or document check). For older relatives who cannot do that, use Form 15227 or the in-person route.

---

## 2. Social Security: "my Social Security" account and Block Electronic Access

**In plain words:** Two separate protections.
1. "my Social Security" is a free online account at ssa.gov. If you create it
   yourself first, a thief cannot create one in your name. It also lets you
   check your earnings record for jobs you never worked.
2. "Block Electronic Access" is a lock. When it is on, nobody, including you,
   can see or change your Social Security information through the SSA website or
   the automated phone service. SSA staff in person still can, after proving who you are.

**Official URLs**
- my Social Security: https://www.ssa.gov/myaccount/ (403 from my fetcher; page not read)
- Account help: https://www.ssa.gov/faqs/en/questions/KA-01687.html (403; page not read)
- Block information: https://www.ssa.gov/pubs/EN-05-10220.pdf, "How You Can Help Us Protect Your Social Security" (403; known only from a search summary)
- Protecting identity blog: https://www.ssa.gov/blog/en/posts/2021-10-19.html (403; search result only)
- Fraud page: https://www.ssa.gov/fraud/ (403)

**Block Electronic Access (search summary of the SSA pages above)**
- How: call 1-800-772-1213 (TTY 1-800-325-0778) or call or visit the local Social Security office, and ask to block electronic access.
- What it does: "No one, including you, will be able to see or change your personal information using our online or automated telephone services."
- Who can use it: any person, for any reason. SSA's examples are domestic violence and identity theft victims.
- Undoing it: call SSA and ask to unblock after proving who you are.
- A related block, Direct Deposit Fraud Prevention, stops anyone (including you) from enrolling in direct deposit or changing address or direct deposit data. Removal needs contact with SSA.

**Eligibility**
- Block: anyone (search summary). UNVERIFIED on the primary page.
- my Social Security account: adults with an SSN and a U.S. mailing address; sign-in through Login.gov or ID.me. UNVERIFIED, I could not read the SSA page. To confirm: open https://www.ssa.gov/myaccount/ in a normal browser and read "Create an account".

**Steps: my Social Security (UNVERIFIED details, general flow)**
1. Go to ssa.gov/myaccount.
2. Choose the sign-in method (Login.gov or ID.me) and create that account.
3. Verify identity as the site asks.
4. Review the earnings record and sign out.
If online ID verification fails, SSA's account FAQ offers help by phone or at an office (search result title: "How do I create or get help with a personal my Social Security account?").

**Which to pick (guidance for the checklist, derived from the SSA search summary)**
- Person who will never use SSA online and wants the strongest lock: Block Electronic Access (also stops their own online use).
- Person who wants to use the account for benefit statements: create the account and keep it strong with Login.gov or ID.me two-step sign-in. Do not use the block, which locks them out too.
- A person cannot have both a working account and the block at the same time.

**Cost:** The account is free (general SSA position). Block is a phone request with no fee mentioned. UNVERIFIED on a primary page; confirm on ssa.gov.

**Gotchas**
- The block is requested by phone or in person, not inside the website (search summary).
- SSA will not call to demand payment or threaten to suspend your number. UNVERIFIED here; confirm on https://www.ssa.gov/fraud/ in a browser.
- Do not give an SSN to anyone who contacts you first.
- Keep a written note of the date you requested the block.

---

## 3. USPS Informed Delivery

**In plain words:** A free USPS service that emails or shows you a picture of the
front of each letter-sized piece of mail due that day, and tracks packages. For
identity protection, its value is that you notice missing or unexpected mail
(for example new credit card offers or bank mail) and that you register your own
address before someone else registers it in your name.
Source: https://www.usps.com/manage/informed-delivery.htm

**Official URLs**
- Overview and sign-up: https://www.usps.com/manage/informed-delivery.htm
- Scam page: https://www.uspis.gov/news/scam-article/fake-usps-emails
- USPS scam news: https://news.usps.com/2025/03/02/a-reminder-to-watch-out-for-imposters/

**Eligibility**
- Residential, business or PO Box addresses in eligible ZIP Codes (most ZIP Codes). Your mailbox must be uniquely coded, so some apartment buildings and condos may not qualify. Business street or PO Box addresses need a USPS.com business account (overview page).

**Steps (overview page)**
1. Existing USPS.com account holders opt in under account preferences. Others create a USPS.com account through the sign-up page.
2. Check that your address is eligible.
3. Verify your identity. If you cannot do it online, visit a USPS location that offers Identity Verification Services.
4. Activation takes up to 3 business days. You then get a daily email digest, a dashboard, or an app.
5. Add the official Informed Delivery sender to your email contacts and check spam so you do not miss notices.

**Cost:** Free. The page says: "Nothing: Informed Delivery is free to customers." (overview page)

**Gotchas and the phishing caveat**
- Fake emails are common. The Postal Inspection Service describes fake "Delivery Failure Notification" emails that ask you to click a button or open an attachment, which can install malware. USPS does not email about delivery attempts or ask for money or personal information. Do not click or scan QR codes; forward the email to spam@uspis.gov and delete it; if you already clicked, contact your bank. (https://www.uspis.gov/news/scam-article/fake-usps-emails)
- USPS says it never sends unsolicited texts or emails about delivery problems (https://news.usps.com/2025/03/02/a-reminder-to-watch-out-for-imposters/, search summary). Practical rule for users: never click a link in a "USPS" message; type usps.com yourself.
- The real Informed Delivery digest only shows the outside of mail, and I found no official USPS page that describes a phishing campaign specific to Informed Delivery itself. Do not tell users that a specific Informed Delivery email format is safe or unsafe.
- Fraudsters have signed up for Informed Delivery in a victim's name to watch for incoming bank and credit cards (2018-2019 reporting; USPS said this happened in very few cases where the identity was already compromised). Secondary sources only: https://nextgov.com/cybersecurity/2018/11/postal-services-informed-delivery-feature-could-be-helping-fraudsters/152792 and https://www.fastcompany.com/90265536/report-id-thieves-are-exploiting-usps-mail-scanning-service-secret-service-warns . Reported advice: register your own address first. A report said a USPS fraud report line is 1-800-344-7779. UNVERIFIED. To confirm: read the USPS Informed Delivery security FAQ on faq.usps.com (my fetch returned only a title).
- Informed Delivery is not a lock on your mailbox and does not stop theft of mail. Collect mail promptly.
- Not available for some multi-unit buildings; the user may be told the address is ineligible.
- Informed Delivery requires an email address the user can read. For relatives without email, skip it.

---

## Suggested checklist order for the wizard

1. SSA: decide block or account (phone call, no computer needed for the block).
2. IRS IP PIN (before the next filing season; mid-January start is when online PINs are viewable).
3. USPS Informed Delivery (only if the user has email).
Credit freezes are not covered here (backlog item is IRS, SSA, USPS only).

## UNVERIFIED summary

| Item | What would confirm it |
|---|---|
| All SSA facts (block phone, wording, my Social Security requirements, no fee) | Open the cited ssa.gov pages in a browser (fetcher got 403) |
| IRS IP PIN being free (explicit statement) | Find the statement on an IRS IP PIN page or Publication 5367 |
| Form 15227 contents and AGI thresholds on the form itself | Open Form 15227 on irs.gov |
| USPS Informed Delivery fraud-report phone number 1-800-344-7779 and address-block option | USPS Informed Delivery security FAQ on faq.usps.com |
| Any Informed Delivery-specific phishing campaign | USPIS or news.usps.com page naming Informed Delivery |
| SSA will-not-call statement | https://www.ssa.gov/fraud/ in a browser |

## Sources (accessed 2026-11-08)

- https://www.irs.gov/identity-theft-fraud-scams/get-an-identity-protection-pin (read)
- https://www.irs.gov/identity-theft-fraud-scams/frequently-asked-questions-about-the-identity-protection-personal-identification-number-ip-pin (read)
- https://www.usps.com/manage/informed-delivery.htm (read)
- https://www.uspis.gov/news/scam-article/fake-usps-emails (read)
- https://news.usps.com/2025/03/02/a-reminder-to-watch-out-for-imposters/ (search summary)
- https://www.ssa.gov/pubs/EN-05-10220.pdf , https://www.ssa.gov/faqs/en/questions/KA-01687.html , https://www.ssa.gov/blog/en/posts/2021-10-19.html , https://www.ssa.gov/myaccount/ , https://www.ssa.gov/fraud/ (all 403; search summaries only)
- Secondary: https://nextgov.com/cybersecurity/2018/11/postal-services-informed-delivery-feature-could-be-helping-fraudsters/152792 ; https://www.fastcompany.com/90265536/report-id-thieves-are-exploiting-usps-mail-scanning-service-secret-service-warns
