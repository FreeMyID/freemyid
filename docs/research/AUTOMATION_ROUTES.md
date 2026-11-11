# Automation routes: removal without a search, and machine-readable ways to find listings

WO-614 (search-free removal) and WO-615 (legitimate machine-readable routes). broker-researcher (Priya Shah), 2026-11-11.
Status: draft complete for orchestrator review. Registry and code untouched; field proposals are in `docs/handoff/broker-researcher-wo614.md`.

Boundary (WO-612..616, shared rule 5): nothing here solves CAPTCHAs, uses stealth or fingerprint spoofing, proxies or IP rotation, or evades bot protection. No real person was searched. Fake names only.

Evidence labels used below:
- PRIMARY: the broker's own page or a government page, fetched by me on the date given.
- REGISTRY: the CPPA California data broker registry 2025 CSV (https://cppa.ca.gov/data_broker_registry/registry2025.csv, fetched 2026-11-11). The broker filed this itself under penalty of perjury (11 CCR 7602(b)), so it is primary for legal names, contact emails and site lists.
- SECONDARY: third-party removal guides (mostly vendors that sell removal services) seen through web search on 2026-11-11. Several disagree with each other. Never put a SECONDARY-only value into the registry as `verified`.

Which brokers: WO-601 says 22 registry brokers have `search_url_pattern`, 20 enabled. I could not grep the private registry (no shell this run), so I covered the ids in `docs/research/exposure_scan_patterns.yaml` that have a pattern, plus the Mississippi Tornado Alley siblings, the BeenVerified and PeopleConnect families, and 411. Map to real registry ids at review.

## Headline findings

1. One operator, nine sites. The CA registry row for Mississippi Tornado Alley LLC lists fastpeoplesearch, usapeoplesearch, advancedbackgroundchecks, peoplesearchnow, usphonebook, searchpeoplefree, smartbackgroundchecks, cyberbackgroundchecks and fastbackgroundcheck, with one contact email (privacy@mtalley.zendesk.com) and the statement that an opt-out "will be applied across all of these sites". That promise is worded for the opt-out of SALE, not listing removal; WO-616 should measure whether one removal clears all nine.
2. PeopleSearchNow (an mtalley site) has a state-law request form where the listing URL is OPTIONAL and an authorized-agent choice exists (PRIMARY). It also requires a phone number, so it is only usable when the person allowed phone sharing (rule 6).
3. Search-free email routes exist for: mtalley group, TruePeopleSearch, FamilyTreeNow, Nuwber, MyLife, PeopleFinders, BeenVerified family. All addresses come from the brokers' own CA registry filings. Whether each broker acts on an email without its web form is untested; send it and track replies (the "we asked anyway" wording from WO-602).
4. Portals that do their own search and show a match list (no listing URL, no scraping of the public site): BeenVerified family, PeopleConnect family (Intelius, TruthFinder, Instant Checkmate, US Search), PeopleFinders, and the removal flows of FastPeopleSearch, TruePeopleSearch and FamilyTreeNow. These are the brokers' own opt-out tools. Most carry a CAPTCHA and an email link, so they are Assisted-tier work for the WO-612 visible browser, not Email tier.
5. Still need a listing URL: Spokeo (verified 2026-11-07), Whitepages + 411 (plus a phone call), Nuwber form, MyLife form. For these the only search-free option is an email request.
6. Three sites are gone or unreachable: radaris.com and peekyou.com now show Atlas Data Privacy Corporation notices (PRIMARY), and clustrmaps.com did not resolve in DNS from the research host.
7. No official search API is usable: Google Custom Search JSON API is closed to new customers and ends 2027-01-01; Bing Search APIs were retired 2025-08-11; Brave needs an account, an API key, a credit card and a custom plan to store results. Rule 2 (no API keys at runtime) already rules these out.
8. Only California has a working one-request deletion platform (DROP, CA residents only). Connecticut's (Public Act 26-64) is due by 2028-07-01 per secondary summaries. None helps the NC/SC/AZ family today.

## Part A: WO-614, per broker

Columns: `needs_url` = proposed `optout_needs_listing_url`; `parent` = proposed `optout_parent`; route = the best search-free route the app may use.
Route codes: EMAIL (plain email request), FORM-NS (web form that takes name + state/address, no listing URL), FORM-URL (form needs the listing URL), PORTAL (opt-out portal that does its own search and shows a match list), LAW (state-privacy-law deletion request, by the broker's privacy form or email), POSTAL, PHONE (human only), NONE (site gone).

### Summary table

| broker id | needs_url | parent (proposed) | best search-free route | other routes | evidence | checked |
|---|---|---|---|---|---|---|
| fastpeoplesearch | false (record is picked inside the removal flow) | mtalley | EMAIL privacy@mtalley.zendesk.com; LAW form on peoplesearchnow /privacy-rights | PORTAL /removal (email + CAPTCHA, then pick record) | REGISTRY + SECONDARY | 2026-11-11 |
| peoplesearchnow | false | mtalley | LAW /privacy-rights (listing URL optional; phone required); FORM-NS /opt-out (name + email + CAPTCHA, then emailed link) | PHONE 888-553-5506 | PRIMARY | 2026-11-11 |
| usphonebook | false (believed) | mtalley | via mtalley group | own /opt-out (fetch refused) | REGISTRY + SECONDARY | 2026-11-11 |
| searchpeoplefree | false (believed) | mtalley | via mtalley group | own /opt-out (not fetched) | REGISTRY | 2026-11-11 |
| smartbackgroundchecks | false (believed) | mtalley | via mtalley group | | REGISTRY | 2026-11-11 |
| advancedbackgroundchecks | false (believed) | mtalley | via mtalley group | | REGISTRY | 2026-11-11 |
| cyberbackgroundchecks, fastbackgroundcheck, usapeoplesearch | false (believed) | mtalley | via mtalley group | | REGISTRY | 2026-11-11 |
| truepeoplesearch | false (the removal flow finds the record) | none (Free Data Services, LLC) | EMAIL support@truepeoplesearch.com | PORTAL /removal: email, hCaptcha, pick record | REGISTRY + SECONDARY | 2026-11-11 |
| familytreenow | false (search inside opt-out tool) | none (Family Tree Now, LLC) | EMAIL support@familytreenow.com | PORTAL /optout: search, CAPTCHA, email link | REGISTRY + SECONDARY | 2026-11-11 |
| spokeo | true (web form) | spokeo | no confirmed route without URL; EMAIL to CustomerCare@spokeo.com untested | FORM-URL /optout + email link; PHONE (877) 864-0183 | PRIMARY (2026-11-07 browser) + REGISTRY | 2026-11-11 |
| thatsthem | false | spokeo (REGISTRY lists thatsthem.com under Spokeo, Inc.) but its own form | FORM-NS thatsthem.com/optout (name, address, phone, email per guides; Turnstile reported) | | REGISTRY + SECONDARY (page 403) | 2026-11-11 |
| whitepages | true (profile URL + phone call) | whitepages | EMAIL (unconfirmed address: guides say privacyrequest@whitepages.com; REGISTRY contact is legal@whitepages.com) | FORM-URL + phone verification | REGISTRY + SECONDARY | 2026-11-11 |
| 411 | covered by whitepages | whitepages | via whitepages | | SECONDARY | 2026-11-11 |
| beenverified | false | beenverified | PORTAL (name + state inside opt-out, pick record, email link) | EMAIL privacy@moneybot5000.com (REGISTRY contact) | REGISTRY + SECONDARY | 2026-11-11 |
| peoplelooker | false | beenverified (REGISTRY lists it under BeenVerified, Inc.) | via beenverified PORTAL (one guide describes a separate PeopleLooker form) | | REGISTRY + SECONDARY | 2026-11-11 |
| neighborwho, peoplesmart, ownerly, numberguru | false | beenverified | via beenverified PORTAL | | REGISTRY | 2026-11-11 |
| intelius | false | peopleconnect | PORTAL suppression.peopleconnect.us (name + DOB + email/phone verification; shows matching records) | | SECONDARY (portal shows only its title to fetch) | 2026-11-11 |
| truthfinder, instantcheckmate, ussearch | false | peopleconnect | via peopleconnect PORTAL | | SECONDARY | 2026-11-11 |
| peoplefinders | false (name + city/state search inside opt-out) | none (Peoplefinders LLC) | PORTAL /opt-out (email-verified); EMAIL customercare@peoplefinders.com (REGISTRY) | | REGISTRY + SECONDARY (page 403) | 2026-11-11 |
| nuwber | true (form /removal/link) | none (Nuwber Inc) | EMAIL support@nuwber.com (REGISTRY contact) | FORM-URL + email link | REGISTRY + SECONDARY (policy 403) | 2026-11-11 |
| mylife | true (privacy form takes profile URL) | none (Insightbridge LLC dba MyLife) | EMAIL membersupport@mylife.com (REGISTRY contact) | PHONE (888) 704-1900 (SECONDARY) | REGISTRY + SECONDARY (policy 403) | 2026-11-11 |
| radaris | n/a | atlas (domain seized) | NONE: Atlas seizure notice only | | PRIMARY | 2026-11-11 |
| peekyou | n/a | atlas (domain controlled by Atlas after settlement) | NONE: notice page only | | PRIMARY | 2026-11-11 |
| clustrmaps | unknown | unknown | NONE right now: DNS did not resolve (bare and www) | | PRIMARY (DNS failure) | 2026-11-11 |
| cocofinder, veripages | unknown | unknown | not confirmed (removal pages 403) | | none | 2026-11-11 |

Postal: none of the pages or registry rows I read give a postal address for removal requests, so no POSTAL route is proposed. The registry CSV has a street address column for every broker; a postal letter to that address is possible as a last resort, but I did not record addresses here (not needed yet, and I will not copy one I have not read in full).

### Group 1: Mississippi Tornado Alley LLC (9 sites) -> parent `mtalley`
REGISTRY row: legal name "Mississippi Tornado Alley LLC", primary contact email `privacy@mtalley.zendesk.com`, privacy policy field https://www.fastpeoplesearch.com/privacy. Sites in the row: fastpeoplesearch.com, usapeoplesearch.com, advancedbackgroundchecks.com, peoplesearchnow.com, usphonebook.com, searchpeoplefree.com, smartbackgroundchecks.com, cyberbackgroundchecks.com, fastbackgroundcheck.com.
Quoted from the row: "Consumers can exercise their right to opt out of the sale of certain personal information ... by submitting a request on any one of these sites." "The opt out request will be applied across all of these sites." Cookie-based opt-outs must be done on each site.
Caveat: that promise covers the opt-out of SALE. It does not say a listing removal on one site removes it from the others. Likely (same database) but unproven: measure in WO-616 before the app says "one request covers 9 sites". Until then, one request per parent group plus a per-site recheck.

PeopleSearchNow (PRIMARY, plain fetch loaded, 2026-11-11):
- https://www.peoplesearchnow.com/opt-out : "Enter your email address and name and complete the captcha below." Fields: Subject First*, Middle, Last*, Subject Email*; agent option "An authorized agent of the subject" (Agent First*, Last*, Email*). Emails a link (expires after 24 h) to a second form whose details should match the record. "Please allow 3 days". No listing URL field. The CAPTCHA is a human click (WO-612 handoff), so this is Assisted, not Email tier.
- https://www.peoplesearchnow.com/privacy-rights : state-law request form, "Right to Know / Right to Delete / Right to Correct", plus an appeal form. Required: First, Last, Email, I am (subject/agent), Phone Number, Street, City, State, Zip, interaction context; "Enter a date of birth or street address is mandatory". "URL of listing" is optional. State dropdown lists every state, DC and territories. Text: "you do have the option to prevent the information associated with you from appearing on our website." No CAPTCHA in the fetched text (a script-loaded widget would not show in a fetch, so unconfirmed). Phone required: rule 6 conflict unless the phone permission flag is set.
- https://www.peoplesearchnow.com/privacy ("Last Updated: August 4, 2026"): requests via the Privacy Request page, the Opt-Out Form, or "Call us at 888-553-5506". "Your 'authorized agent' can submit a request on your behalf using the same methods described above. We may ask the authorized agent to provide a signed authorization from you." "Opt-out requests do not require verification." No email address is given in the policy.
- So the Email-tier route for the group is the REGISTRY address only. It is the address the company filed with California; whether they act on email without the form is untested.

FastPeopleSearch, USPhonebook (fetch refused, "unable to fetch"): SECONDARY guides (Incogni, Redact, DeleteMe, Optery, 2026) agree: removal page asks for email + CAPTCHA, emails a link (24 h), then you search by name and city/state and pick the listing; one removal per listing. Path disputed: /removal vs /optout.

### Group 2: TruePeopleSearch (Free Data Services, LLC)
REGISTRY: "Free Data Services, LLC" DBA TruePeopleSearch, email `support@truepeoplesearch.com`; rights text: use the "Do Not Sell My Personal Information" link in the footer. Fetch refused. Not in the mtalley row (the 2026-11-07 note that one operator runs TPS was wrong or out of date).
SECONDARY: /removal asks for name + email, emails a link, then the opt-out form; testers report repeated hCaptcha. No listing URL needed, but CAPTCHA-heavy. Email route: the REGISTRY address.

### Group 3: FamilyTreeNow (Family Tree Now, LLC)
REGISTRY: email `support@familytreenow.com`, same footer "Do Not Sell" wording. /optout returned HTTP 403 to fetch.
SECONDARY: search inside the opt-out tool, open the record, click opt out, CAPTCHA, email confirmation link (Sept 2026 guide). Covers only your own record.

### Group 4: Spokeo family -> parent `spokeo`
REGISTRY: "Spokeo, Inc.", email `legal@spokeo.com`, sites spokeo.com, freepeopledirectory.com, peoplewin.com, thatsthem.com; opt-out https://www.spokeo.com/optout and https://www.thatsthem.com/optout.
Spokeo /optout needs the listing URL + email, then a confirmation link (opened in a real browser 2026-11-07, registry note). Privacy policy (fetched 2026-11-06, 403 today): deletion via web form or phone (877) 864-0183; CustomerCare@spokeo.com is for general privacy questions and EEA erasure. No confirmed search-free route; an email request may be answered "use the form".
ThatsThem: own form at thatsthem.com/optout (www. returns 404; bare host 403 to fetch). SECONDARY: name, street, city, state, zip, phone, email; Cloudflare Turnstile reported. No URL field. Phone needs the permission flag. So `covered_by: spokeo` would be WRONG for ThatsThem: same company, separate opt-out.

### Group 5: Whitepages family -> parent `whitepages`
REGISTRY: "Whitepages, Inc", email `legal@whitepages.com`, privacy https://www.whitepages.com/privacy.
SECONDARY: suppression form needs the profile URL and a phone number for a verification call with a code; 411.com runs through the same flow. Email fallback reported (privacyrequest@whitepages.com) but unconfirmed. Stays `needs_url: true`; also needs phone (permission flag).

### Group 6: BeenVerified family -> parent `beenverified`
REGISTRY: "BeenVerified, Inc. and its subsidiaries and affiliates", email `privacy@moneybot5000.com`, 12 sites: beenverified.com, peoplelooker.com, numberguru.com, ownerly.com, neighborwho.com, peoplesmart.com, bumper.com, freephonetracer.com, emailfinder.com, moneybot5000.com, reversephone.com, wingmate.com. CCPA rights URL: https://www.beenverified.com/svc/optout/search/comprehensive_optouts (fetch refused).
SECONDARY: opt-out takes first + last name and state, shows matching records, you pick yours, give an email, click the link. One 2026 guide says it now also asks age, street, ZIP. Each record needs its own opt-out. PeopleSmart's opt-out sends you to the BeenVerified page.

### Group 7: PeopleConnect family -> parent `peopleconnect`
Not found in the REGISTRY text I read (my chunked reads may have missed the row; recheck).
SECONDARY: suppression.peopleconnect.us covers TruthFinder, Intelius, Instant Checkmate and US Search (not Classmates); asks email, legal name, DOB; verification by email or phone; shows your records to suppress; free; about 48 h. DeleteMe's help centre (403 to fetch; quoted in search summary) says PeopleConnect does not honour requests DeleteMe submits for a customer. Free My ID sends from the person's own mailbox and the person clicks, so it is the person acting, not an agent; still, plan for refusal of anything that looks like an agent.
DOB is rarely a listing-shown field: rule 6 means this needs the person's OK.

### Group 8: PeopleFinders (Peoplefinders LLC)
REGISTRY: email `customercare@peoplefinders.com`, privacy https://www.peoplefinders.com/about/privacy. /opt-out 403.
SECONDARY: search name + city/state inside the opt-out flow, pick the record, email confirmation, then a longer suppression form; about 3 days. One guide says they honour only residents of comprehensive-law states (unconfirmed; matters for NC/SC/AZ).

### Group 9: Nuwber (Nuwber Inc)
REGISTRY: email `support@nuwber.com`, privacy https://www.nuwber.com/policy (403).
SECONDARY: /removal/link needs the profile URL + email confirmation; no URL-free form use found. Email to support@nuwber.com is the only search-free route.

### Group 10: MyLife (Insightbridge LLC)
REGISTRY: email `membersupport@mylife.com`, privacy https://www.mylife.com/privacy-policy (403).
SECONDARY: privacy request form behind the footer "Do Not Sell" link takes profile URL + email; email to membersupport@mylife.com reported to work in about 15 days; phone (888) 704-1900 reported. Never create or claim an account.

### Group 11: Gone or unreachable
- radaris.com (PRIMARY, 2026-11-11): "the domain name radaris.com has been transferred to Atlas Data Privacy Corporation"; "Pursuant to a final judgment of the New Jersey Superior Court"; "On August 27, 2026, the New Jersey Superior Court entered a final judgment by default"; docket MID-L-000847-24. No listings. Keep disabled.
- peekyou.com (PRIMARY, 2026-11-11): "The domain name peekyou.com is now controlled by Atlas Data Privacy Corporation"; "Atlas and PeekYou LLC have entered into a settlement agreement"; docket ESX-L-003299-25. No listings. Proposal: disable, recheck in 90 days.
- clustrmaps.com: DNS did not resolve (bare and www) on 2026-11-11. Could be the research host's resolver; second check needed before disabling.

### What the runner may do (WO-614 task 3 input)
- Email tier, no search, once per parent group: mtalley, truepeoplesearch, familytreenow, nuwber, mylife, peoplefinders (and beenverified as a backup to its portal). Wording: a plain deletion request; for law states cite the statute (state_laws.yaml), for others a courtesy request (no "demand"). Data: only name + the removal mailbox, plus city/state if the letter needs it to match (rule 6 still applies: send no more than a listing would show; no phone, no DOB).
- Assisted tier (WO-612 window, person clicks the CAPTCHA and the email link): the PORTAL brokers.
- Hand-check to-do: spokeo, whitepages/411 (need a URL and, for Whitepages, a phone call).
- Skip: radaris, peekyou (gone), clustrmaps until re-checked.

## Part B: WO-615, routes

| # | route | covers | terms (quoted, linked) | cost | data sent | go / no-go |
|---|---|---|---|---|---|---|
| B1 | CPPA data broker registry CSV | every broker registered in CA (2025 file); contact email, sites, CCPA rights URL, request metrics | Public download on https://cppa.ca.gov/data_broker_registry/ ("all responses submitted as part of the registration process"); no dataset-specific terms on the page, general ca.gov Conditions of Use in the footer | free | none (download only) | GO (build-time, not runtime) |
| B2 | Broker opt-out portals with a match list (BeenVerified, PeopleConnect, PeopleFinders, FastPeopleSearch/TruePeopleSearch/FamilyTreeNow removal flows) | ~25 sites across the families | the brokers' own opt-out tools, meant for this use; CAPTCHAs and email links are human steps | free | name + state (+ email; DOB for PeopleConnect) | GO as Assisted tier |
| B3 | Search-free email requests to registry contact emails | groups in Part A | the broker's own filed contact; state-law deletion rights where the person lives in a law state | free | name + removal mailbox (+ city/state) | GO (WO-614 task 3) |
| B4 | California DROP | registered brokers, CA residents only | "If you are a California resident, you qualify to use DROP." "You only need to provide your name, date of birth, and ZIP code" (https://privacy.ca.gov/drop/how-drop-works/, fetched 2026-11-11). Brokers pull hashed identifier lists (11 CCR 7601(c), https://cppa.ca.gov/regulations/pdf/data_broker_drop_reg.pdf). No consumer API mentioned. Exempt: first-party data, statutory exemptions, publicly available data | free | name, DOB, ZIP (on the state site, by the person) | GO as handoff only (already in registry as ca_drop); no automation possible |
| B5 | Connecticut deletion mechanism (Public Act 26-64, SB 4 of 2026) | CT residents, registered brokers | SECONDARY (FPF, WilmerHale, Mondaq): registration by 2027-01-01, mechanism by 2028-07-01, brokers check every 45 days | free | n/a | WATCH (not live) |
| B6 | Vermont, Texas, Oregon broker registries | lists of registered brokers | lists only, no deletion mechanism (SECONDARY; TX SOS page 403 today) | free | none | GO later as a contact cross-check; not checked this run |
| B7 | Google "Results about you" | Google Search results that show the person's address, phone, email | "find out if your personal info, like your home address, phone number, or email address shows up in search results"; removal "doesn't mean that the info is gone from the internet" (https://support.google.com/websearch/answer/12719076, fetched 2026-11-11). Log in with a Google Account; some features "rolling out ... in certain markets" | free | the person's contact details, to Google, in their own account | GO as a guided checklist item only (person does it; it is also a legitimate way for the person to discover listing URLs to paste in). No API |
| B8 | Google Custom Search JSON API | web search | "The Custom Search JSON API is closed to new customers." "Existing ... customers have until January 1, 2027 to transition" (https://developers.google.com/custom-search/v1/overview, fetched 2026-11-11). Requires an API key | 100/day free then $5 per 1000 (existing customers only) | the person's name to Google under our key | NO-GO (closed; API key breaks rule 2) |
| B9 | Bing Search APIs | web search | "Bing Search APIs will be retired on August 11, 2025. Any existing instances ... will be decommissioned completely" (https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement) | n/a | n/a | NO-GO (gone) |
| B10 | Brave Search API | web search | Account, "Get my API key", credit card asked "to prevent abuse"; Search plan "$5 per 1,000 requests" with "$5 in free credits every month"; storing results: "Yes, with a custom plan" (https://brave.com/search/api/, fetched 2026-11-11) | paid, prepaid credits | the person's name to Brave | NO-GO (account + key + card; rule 2 and rule 6; storing results for rechecks needs a custom plan) |
| B11 | Consumer Reports Data Rights Protocol (DRP) | businesses that join the DRP consortium (mainly large companies via privacy-platform vendors) | SECONDARY: v0.9 "stable"; agents sign requests; Permission Slip uses it (innovation.consumerreports.org, 2023-2025 posts). People-search brokers are not known members | free protocol, but agent onboarding is organisational | identity + agent signature | NO-GO now; WATCH. Free My ID runs on the person's own PC and is not an authorized-agent business |
| B12 | Paid people-search / identity APIs (e.g. data vendors' lookup APIs) | broker data | accounts, keys, fees; sending a person's name to another broker to find them adds a new disclosure | paid | name + location to a third broker | NO-GO (never pay, no accounts, rule 2, rule 6) |

### Proposed WOs (one per GO)
- WO-A (B1, broker-researcher): import contact emails, CCPA rights URLs and site lists from the CPPA 2025 CSV into the private registry (`opt_out_email` where empty, `parent_company`, proposed `optout_parent`), with `source_urls` pointing at the CSV and a check date. Re-run each January (new registry year; the 2026 file showed 0 registrations on 2026-11-11, so keep using 2025 for now).
- WO-B (B3): this is WO-614 task 3 (runner). No new WO.
- WO-C (B2, automation-engineer + broker-researcher): a `portal` method for opt-out portals inside the WO-612 visible browser session: Free My ID fills name + state, the person ticks any CAPTCHA and picks their record from the broker's own list, Free My ID handles the email link (WO-603-style mailbox confirm). Fixtures synthetic only.
- WO-D (B4/B7, wizard-packager + brand-marketing): two guided checklist cards: "California resident? Use DROP" (exists; check wording) and "Ask Google to hide results that show your address or phone" with a note that it hides results only and needs a Google account (owner decision: we recommend a third-party account?).
- WO-E (Part A group 11, automation-engineer): detect the Atlas seizure/settlement notice (page text "Atlas Data Privacy Corporation") and mark the broker `gone` instead of `bot_blocked`; recheck every 90 days.
- WO-F (B6, broker-researcher, low): Vermont/Texas/Oregon registry cross-check for contact emails of brokers not registered in CA.

### Sources (accessed 2026-11-11 unless noted)
- https://cppa.ca.gov/data_broker_registry/ and https://cppa.ca.gov/data_broker_registry/registry2025.csv
- https://cppa.ca.gov/regulations/pdf/data_broker_drop_reg.pdf (11 CCR 7600 ff., pages 1-3 read)
- https://privacy.ca.gov/drop/how-drop-works/
- https://www.peoplesearchnow.com/opt-out, /privacy-rights, /privacy
- https://radaris.com/, https://www.peekyou.com/ and https://www.peekyou.com/about/contact/optout/
- https://developers.google.com/custom-search/v1/overview
- https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement
- https://brave.com/search/api/
- https://support.google.com/websearch/answer/12719076
- Refused or 403 today (not evidence): fastpeoplesearch.com, usphonebook.com, truepeoplesearch.com, familytreenow.com, thatsthem.com, nuwber.com, mylife.com, peoplefinders.com, beenverified.com, intelius.com, truthfinder.com, spokeo.com, cocofinder.com, veripages.com, help.joindeleteme.com, sos.state.tx.us, web.archive.org; suppression.peopleconnect.us returned only its title; clustrmaps.com DNS failure.
- SECONDARY (search summaries): Incogni, Redact, DeleteMe, Optery, OneRep, Security.org, offlist.me guides on each broker; FPF, WilmerHale, Mondaq on Connecticut SB 4; Consumer Reports Innovation posts on the DRP.
