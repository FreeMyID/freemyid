# Obstruction law: when a broker blocks a lawful deletion or opt-out

broker-researcher (Priya Shah), 2026-11-11 (WO-625). Input to the compliance-evidence engine (ROADMAP_TO_1.0 bar 9, section 7a "Escalation ladder with the legal clock").
Status: draft complete for orchestrator and attorney review. Companion: `docs/handoff/broker-researcher-obstruction.md` (data shape, top brokers, open legal questions).

This is research, not legal advice. Every row that the engine will turn into complaint text must be read by an attorney first (decision D6).

Free My ID files nothing itself. It records evidence and pre-fills a complaint that the person reads, corrects and sends under their own name. Where that matters legally it is flagged **[PERSON FILES]**.

## How to read this file

Obstruction types (the engine's enum):
- **(a) friction**: a CAPTCHA, extra screens, waiting, broken links, dead mailboxes, a forced phone call, or any other burden on the request method.
- **(b) account**: the person must create an account to make the request.
- **(c) over-verification**: more identity data or proof than the request needs (ID upload, SSN digits, DOB, phone, selfie, notarized affidavit, any verification on an opt-out).
- **(d) agent refused**: an authorized agent's request is refused, or the person is forced to redo it themselves.
- **(e) deadline missed**: no answer, or no action, inside the legal window.

Evidence labels:
- **PRIMARY**: statute or regulation text, or an official regulator page, read by me on 2026-11-11 unless another date is shown. Where the text came from a faithful mirror of the official code (oregon.public.law, colorado.public.law) it says "mirror".
- **SECONDARY / NOT VERIFIED**: law-firm or vendor summaries, search-result snippets, or my background knowledge. Never quote these as law in a complaint.

Verdicts per cell:
- **EXPRESS**: the text names the practice and forbids it.
- **ARGUABLE**: a general rule ("easy to execute", "minimal steps", "reasonably necessary", dark patterns) covers it, but the text does not name it. A complaint can argue it; a regulator decides.
- **NO RULE**: nothing in the text read.

Statute ids: lowercase slugs matching `^[a-z0-9][a-z0-9._-]{0,63}$` (format agreed for `brokers/obstruction_law.yaml`). Full list in section 7.

Three cautions that apply everywhere:
1. **CAPTCHA**: no statute or regulation I read uses the word. Every CAPTCHA finding is ARGUABLE at best, under a friction or dark-pattern rule, and a business will call it a security measure (CA 11 CCR 7060(f) itself requires "reasonable security measures to detect fraudulent identity-verification activity"). The engine states the fact ("the request method required a CAPTCHA"), never the conclusion ("the CAPTCHA was unlawful").
2. **Coverage**: outside California almost every law excludes "publicly available information" from "personal data" and has size thresholds. A people-search broker will often answer "not covered". Obstruction rules only bite where the law reaches that broker and that data.
3. **Residency**: each law protects residents of its own state only. The engine picks the law from the person's state of residence, never from the broker's.

---

## 1. California (CCPA as amended by CPRA; CCPA regulations; Delete Act and DROP)

Sources (PRIMARY, 2026-11-11):
- CCPA regulations, 11 CCR 7000 ff., consolidated text "Effective 1/1/2026", https://cppa.ca.gov/regulations/pdf/ccpa_statute_eff_20260101.pdf (despite the file name it is the regulations; linked from https://cppa.ca.gov/regulations/).
- DROP regulations, 11 CCR 7600 ff., final text, https://www.cppa.ca.gov/regulations/pdf/drop_ftr.pdf.
- CalPrivacy "Processing DROP requests", https://privacy.ca.gov/drop-for-data-brokers/process-drop-requests/.
- CPPA enforcement: Honda (https://www.cppa.ca.gov/announcements/2025/20250312.html), LocateSmarter (https://privacy.ca.gov/2026/08/calprivacy-brings-first-action-against-a-data-broker-under-both-the-ccpa-and-delete-act/), Data Broker Enforcement Strike Force (https://www.cppa.ca.gov/announcements/2025/20251119.html).
- The Civil Code (leginfo.legislature.ca.gov, law.justia.com) returned HTTP 403. Statute sections I did not read are marked.

Scope: CA residents; businesses over the CCPA thresholds. Many people-search sites are registered CA data brokers.

### (a) friction, including CAPTCHA: ARGUABLE (strongest general rule in the country)
- 11 CCR 7004(a)(5): "Easy to execute. The business shall not add unnecessary burden or friction to the process by which the consumer submits a CCPA request or provides or withdraws consent. Methods must be tested to ensure that they are functional and do not undermine the consumer's choice to submit the request."
- 7004(a)(5)(B): "A business that knows of, but does not remedy, circular or broken links, or nonfunctional email addresses, such as inboxes that are not monitored or have aggressive filters that screen emails from the public, may be in violation of this regulation." (Use for: bounced removal mail, a 403 on the opt-out page, dead links.)
- 7004(a)(5)(C): "Businesses that require the consumer to unnecessarily wait on a webpage as the business processes the request or require consumers to fill out multiple or duplicative forms or impose unnecessary waiting periods between form submissions may be in violation of this regulation."
- 7004(a)(5)(D): "Businesses that require the consumer to call a toll-free telephone number to submit a CCPA request must ensure that the individuals handling those phone calls have the knowledge and ability to process the consumer's CCPA requests." A phone route is not itself unlawful: 7020(b) requires a toll-free number as one method for businesses that are not online-only.
- 7004(a)(2): "Symmetry in choice. The path for a consumer to exercise a more privacy-protective option shall not be longer or more difficult or time-consuming than the path to exercise a less privacy-protective option".
- 7004(a)(4)(A): "Requiring the consumer to click through disruptive screens before they are able to submit a request to opt-out of sale/sharing is a choice architecture that impairs or interferes with the consumer's ability to exercise their choice."
- 7004(b): "A method that does not comply with subsection (a) may be a dark pattern." 7004(c): "A business's intent is not determinative ... If a business did not intend to design the user interface to subvert or impair user choice, but the business knows of and does not remedy a user interface that has that effect, the user interface is still a dark pattern."
- 7026(b): opt-out methods "shall be easy for consumers to execute, shall require minimal steps, and shall comply with section 7004."
- 7020(d): a two-step online deletion (submit, then confirm) is allowed "provided that the business otherwise complies with section 7004". An email confirmation link alone is lawful; a CAPTCHA on top is the ARGUABLE part.
- 7020(f): a request sent "in a manner that is not one of the designated methods" must be treated as properly submitted, or the business must explain how to submit or fix it. (Use for: a broker ignores an emailed request.)
- Enforcement: Honda (2025-03-12, USD 632,500) in part for a tool that "failed to offer Californians their privacy choices" "in a symmetrical or equal way".

### (b) account required: EXPRESS for opt-out
- 7026(c): "A business shall not require a consumer submitting a request to opt-out of sale/sharing to create an account or provide additional information beyond what is necessary to direct the business not to sell or share the consumer's personal information."
- Delete/know/correct: Civil Code 1798.130(a)(2) (no account to make a verifiable consumer request; an existing account may be required) and 1798.135(c)(1): SECONDARY / NOT VERIFIED this run (leginfo 403). Re-read before quoting.

### (c) over-verification: EXPRESS
- 7060(b): "A business shall not require a consumer to verify their identity to make a request to opt-out of sale/sharing ... A business may ask the consumer for information necessary to complete the request; however, it shall not be burdensome on the consumer. For example, a business may ask the consumer for their name, but it shall not require the consumer to take a picture of themselves with their driver's license."
- 7026(d): "A business shall not require a verifiable consumer request for a request to opt-out of sale/sharing. ... to the extent that the business can comply with a request to opt-out of sale/sharing without additional information, it shall do so."
- Delete: 7060(c)(1) "Match the identifying information provided by the consumer to the personal information of the consumer already maintained by the business before requesting additional information"; 7060(d) "A business shall avoid requesting additional information from the consumer for purposes of verification"; data collected for verification is deleted "as soon as practical".
- 7060(e): no verification fee; "a business must not require a consumer to provide a notarized affidavit to verify their identity unless the business pays for or compensates the consumer for the cost of notarization."
- 7062(b), (d): non-accountholders: "reasonable degree of certainty ... may include matching at least two data points"; delete may need "reasonable or reasonably high" certainty by sensitivity (brokers will cite this; it is a sliding scale).
- 7022(a): if it cannot verify, the business "may deny the request to delete" and "shall inform the requestor that their identity cannot be verified". Silence is not an option.
- Enforcement: Honda: "requiring Californians to verify themselves and provide excessive personal information to exercise certain privacy rights". LocateSmarter (2026-08-11, USD 116,490): "unlawfully required Californians to provide partial Social Security numbers" before opting out; "Doing so also violates the CCPA's data minimization requirements."

### (d) authorized agent refused: EXPRESS limits on what a business may demand
- 7063(a) (delete/know/correct): the business "may require the authorized agent to provide proof that the consumer gave the agent signed permission" and may also require the consumer to "(1) Verify their own identity directly with the business" or "(2) Directly confirm with the business that they provided the authorized agent permission". "However, businesses shall not require the consumer to resubmit their request in their individual capacity."
- 7063(b): not applicable where the agent holds a power of attorney (Probate Code 4121-4130); "A business shall not require power of attorney in order for a consumer to use an authorized agent to act on their behalf."
- 7026(j) (opt-out): agent needs "written permission signed by the consumer"; a business "may deny a request from an authorized agent if the agent does not provide to the business the consumer's signed permission"; "The requirement to obtain and provide written permission from the consumer does not apply to requests made by an opt-out preference signal."
- Enforcement: Honda: "making it difficult for Californians to authorize other individuals or organizations" ("authorized agents") to exercise their rights.
- Result: refusing a signed agent, demanding a POA, or forcing a resubmission is obstruction; refusing an agent with no signed permission is lawful.

### (e) deadline missed: EXPRESS
- 7021(a): confirm receipt "No later than 10 business days after receiving a request to delete" (also correct, know).
- 7021(b): respond "no later than 45 calendar days after receipt of the request. The 45-day period will begin on the day that the business receives the request, regardless of time required to verify the request." Extension "up to an additional 45 calendar days ... for a maximum total of 90 calendar days ... provided that the business provides the consumer with notice and an explanation of the reason".
- 7026(f)(1): stop selling/sharing "as soon as feasibly possible, but no later than 15 business days from the date the business receives the request." 7026(g): the business "must provide a means by which the consumer can confirm that their request to opt-out of sale/sharing has been processed".

### Delete Act and DROP (registered data brokers; CA residents)
- From 2026-08-01 brokers must download DROP lists "at least once every 45 days" and report a status per request within 45 days of download; AB 883 moves this to "at least once every 30 days effective January 1, 2027" (privacy.ca.gov process page).
- 11 CCR 7614(b)(2) statuses: "Record deleted", "Record opted out of sale", "Record exempted", "Record not found".
- 11 CCR 7616(c): "A data broker shall not contact a consumer to verify their deletion requests submitted through the DROP." (EXPRESS (c) for DROP.)
- 11 CCR 7621(a)-(b): "An authorized agent may aid in a consumer's deletion request after the consumer has their residency verified"; the agent's "full name, email address, and trade name if the authorized agent is a business" is disclosed in the consumer's DROP account first.
- 11 CCR 7613(c): unmatched requests are kept and compared "with deletion lists before new personal information is sold or shared" (re-listing control).
- Delete Act penalties (Civil Code 1798.99.82, 1798.99.86): not read, SECONDARY.
- Engine: the person cannot see the broker's DROP status. A DROP complaint can rest only on a listing still live after the window (download up to 45 days + processing up to 45 days, so about 90 days from the DROP request until 2026-12-31; shorter from 2027). Handoff Q4.

### CA regulators
See section 4 (CalPrivacy and the AG).

### GPC in CA: REQUIRED (EXPRESS)
11 CCR 7025(b): "A business that sells or shares personal information shall process any opt-out preference signal that meets the following requirements as a valid request to opt-out of sale/sharing". 7026(a)(1): a business collecting online "shall, at a minimum, allow consumers to submit requests to opt-out of sale/sharing through an opt-out preference signal". 7025(c)(2): "The business shall not require a consumer to provide additional information beyond what is necessary to send the signal."

---

## 2. Other comprehensive state laws in force on 2026-11-11

In force: VA, CO, CT, UT, TX, OR, MT, IA, DE, NE, NH, NJ, TN, MN, MD, IN, KY, RI (effective dates in `brokers/state_laws.yaml`). Florida's law is in force but reaches only very large companies (template `generic`). Enacted, NOT in force: OK and LA (2027-01-01), AL (2027-05-01), VT comprehensive law (2028-01-01). Do not cite those yet.

Common pattern (the Virginia/Connecticut model), verified state by state below:
- "Secure and reliable" request methods; "shall not require a consumer to create a new account" (an EXISTING account may be required).
- Respond in 45 days (Iowa 90), extend once by 45 with notice in the first window; a refusal must give reasons and appeal instructions in 45 days; appeals answered in 60 days (OR, NJ 45; MN 45 + 60); a denied appeal must point to the AG.
- If the controller cannot authenticate "using commercially reasonable efforts" it may ask for "additional information reasonably necessary". So (c) for deletion is ARGUABLE everywhere outside CA; it is EXPRESS only for OPT-OUT where the text says a controller is not required to authenticate an opt-out request.
- Dark patterns appear only in the consent definition. No state outside CA has an "easy to execute / no unnecessary friction" rule for request methods. (a) is at most ARGUABLE outside CA.
- Authorized agents are mostly for OPT-OUT only (often "using a technology"). For DELETE, outside CA (and RI's general wording), an agent has no statutory route: a broker that insists the person act themselves is not obstructing.

### 2.1 Matrix

E = EXPRESS, A = ARGUABLE, N = NO RULE, ? = not read this run. Days = respond / extension / appeal.

| State | Statute ids (section 7) | (a) friction / CAPTCHA | (b) new account | (c) over-verification | (d) agent | (e) days | Evidence |
|---|---|---|---|---|---|---|---|
| CA | ca-ccr-11-7004, -7020, -7021, -7026, -7060, -7063 | A (7004(a)(5)) | E opt-out (7026(c)); delete per statute (not re-read) | E (7060(b), 7026(d), 7060(d)) | E limits (7063, 7026(j)) | 45 / +45 / n.a.; ack 10 business days; opt-out 15 business days | PRIMARY |
| VA | va-code-59.1-577, va-code-59.1-578 | N | E 59.1-578(E) | A 59.1-577(B)(4) | N (child's parent/guardian only) | 45 / +45 / 60 | PRIMARY |
| CO | co-crs-6-1-1306, co-crs-6-1-1313 | ? (CPA Rules not readable) | E 6-1-1306(1) | A 6-1-1306(2)(d) | E opt-out (6-1-1306(1)(a)(II)) | 45 / +45 / ? | PRIMARY (mirror) |
| CT | ct-gs-42-518 | ? | ? (expected E) | ? | opt-out agent (AG page) | 45 / +45 / 60 (AG page) | AG page PRIMARY; statute unreadable |
| UT | ut-code-13-61-203 | ? | ? | ? | ? | 45 / +45 (state_laws.yaml) | not re-read |
| TX | tx-bcc-541.052, tx-bcc-541.055 | N | E 541.055(b) | A 541.052 | E opt-out, 4 refusal grounds (541.055(e)) | 45 / +45 / 60 | PRIMARY (enrolled HB 4) |
| OR | or-ors-646a.576, or-ors-646a.578 | N | E 646A.576(2) | E opt-out "without requiring authentication" (646A.576(5)(e)); A delete | E opt-out (646A.576(4)) | 45 / +45 / 45 | PRIMARY (mirror) |
| MT | mt-mca-30-14-2808, -2809, -2812 | N | E 30-14-2812(11)(b) | E opt-out (30-14-2808(4)(d)) | E opt-out (30-14-2809) | 45 / +45 / 60 | PRIMARY |
| IA | ia-code-715d.3 | N | ? (715D.4 not read) | A 715D.3(2)(d) | N (known child's parent/guardian) | 90 / +45 / 60 | PRIMARY |
| DE | de-code-6-12d-104, -105, -106 | N | E 12D-106(e)(1) | E opt-out (12D-104(c)(4)) | E opt-out (12D-105) | 45 / +45 / 60 | PRIMARY |
| NE | ne-rs-87-1108, ne-rs-87-1111 | N | E 87-1111(2) | A 87-1108(5) | E opt-out, 4 refusal grounds (87-1111(5)) | 45 / +45 / ? | PRIMARY |
| NH | nh-rsa-507-h-4, nh-rsa-507-h-6 | N | E 507-H:6, V(a) | E opt-out (507-H:4, III(d)) | E (507-H:4, II) | 45 / +45 / 60 | PRIMARY |
| NJ | nj-sa-56-8-166.6, -166.7, -166.11 | N | E sec. 3c(1) | E opt-out (sec. 4e) | E opt-out incl. technology (sec. 8) | 45 / +45 / 45 | PRIMARY (P.L.2023 c.266) |
| TN | tn-code-47-18-3203 | ? | ? | ? | ? | 45 / +45 (state_laws.yaml) | not re-read |
| MN | mn-stat-325m.14 | N | E subd. 4(c) | E opt-out (subd. 4(h)) | E opt-out (subd. 2(d)) | 45 / +45 / 45 (+60) | PRIMARY |
| MD | md-cl-14-4705, -4706, -4707 | N | E 14-4707(f)(2)(i) | E opt-out (14-4705(e)(6)) | E opt-out (14-4706) | 45 / +45 / 60 | PRIMARY |
| IN | in-code-24-15-3 | ? | ? | ? | ? | 45 / +45 (state_laws.yaml, mirror) | not re-read |
| KY | ky-krs-367.3615 | N | ? (367.3617 not read) | A 367.3615(3)(d) | N (child's parent/guardian) | 45 / +45 / 60 | PRIMARY |
| RI | ri-gl-6-48.1-6 | N | N (absent from 6-48.1-6) | E opt-out (6-48.1-6(b)(4)) | E (6-48.1-6(b)(7)) | 45 / +45 / ? | PRIMARY |

Colorado: the CPA Rules (4 CCR 904-3: Rule 4.02 submitting requests, 4.03 opt-out, Part 5 UOOM, 7.09 dark patterns) were not readable (regulations.justia.com 403; coag.gov pages empty to the fetcher; rule PDFs not text). A search snippet of Rule 4.02 says a controller "must not require a Consumer to create a new user account to exercise their Data Rights request" (SECONDARY). Whether the Rules set a friction standard is OPEN (handoff Q6).

### 2.2 Operative text by state (PRIMARY, 2026-11-11)

**Virginia** (https://law.lis.virginia.gov/vacode/title59.1/chapter53/section59.1-577/, .../section59.1-578/)
- (b) 59.1-578(E): "one or more secure and reliable means for consumers to submit a request to exercise their consumer rights"; "Controllers shall not require a consumer to create a new account in order to exercise consumer rights".
- (c) 59.1-577(B)(4): if it cannot authenticate "using commercially reasonable efforts", it "may request that the consumer provide additional information reasonably necessary to authenticate the consumer".
- (d) 59.1-577(A): "A known child's parent or legal guardian may invoke such consumer rights on behalf of the child." No general agent.
- (e) 59.1-577(B)(1): "within 45 days of receipt of the request"; "The response period may be extended once by 45 additional days when reasonably necessary", notice "within the initial 45-day response period". (B)(2) refusal reasons and appeal instructions in 45 days; (C) appeal process, answer in 60 days.

**Colorado** (https://colorado.public.law/statutes/crs_6-1-1306 and crs_6-1-1313, mirror, "Current through Fall 2025")
- (b) 6-1-1306(1): "Controllers shall not require a consumer to create a new account in order to exercise consumer rights."
- (c) 6-1-1306(2)(d): "A controller is not required to comply with a request to exercise any of the rights ... if the controller is unable to authenticate the request using commercially reasonable efforts".
- (d) 6-1-1306(1)(a)(II): "A consumer may authorize another person, acting on the consumer's behalf, to opt out ... including through a technology indicating the consumer's intent to opt out"; compliance "if the controller is able to authenticate, with commercially reasonable effort, the identity of the consumer" and the agent's authority.
- (e) 6-1-1306(2)(a): 45 days; "The controller may extend the forty-five-day period by forty-five additional days where reasonably necessary".
- UOOM: 6-1-1306(1)(a)(IV)(B): "Effective July 1, 2024, a controller that processes personal data for purposes of targeted advertising" (or sale) must honour opt-out "through a user-selected universal opt-out mechanism". 6-1-1313(2): the mechanism must be "consumer-friendly, clearly described, and easy to use by the average consumer".

**Connecticut** (AG page https://portal.ct.gov/ag/sections/privacy/the-connecticut-data-privacy-act; cga.ct.gov failed: "unable to verify the first certificate")
- "A controller must respond to a consumer's requests no later than 45 days after receipt of the request", 45-day extension; appeals in 60 days. "A consumer can also designate a third party to opt-out on his or her behalf." From 2025-01-01 "all controllers subject to the CTDPA must honor opt out preference signals", a signal "like the Global Privacy Control".
- Account and opt-out authentication rules in 42-518 and the 2025/2026 amendments (incl. Public Act 26-64): NOT read, SECONDARY.

**Texas** (enrolled HB 4, 88R, https://capitol.texas.gov/tlodocs/88R/billtext/html/HB00004F.htm; the live code page showed only an index, so later amendments are not checked)
- (b) 541.055(a) "two or more secure and reliable methods"; 541.055(b): "A controller may not require a consumer to create a new account to exercise the consumer's rights under this subchapter."
- (c) 541.052: if it cannot authenticate it may "request that the consumer provide additional information reasonably necessary to authenticate the consumer". No opt-out-authentication exemption found.
- (d) 541.055(e): "A consumer may designate an authorized agent using a technology, including a link to an Internet website, an Internet browser setting or extension, or a global setting on an electronic device"; compliance if the controller "is able to verify, with commercially reasonable effort, the identity of the consumer" and the agent's authority. Not required if "(1) the authorized agent does not communicate the request to the controller in a clear and unambiguous manner", "(2) the controller is not able to verify, with commercially reasonable effort, that the consumer is a resident of this state", "(3) the controller does not possess the ability to process the request", or "(4) the controller does not process similar or identical requests ... for the purpose of complying with similar or identical laws or regulations of another state". 541.055(e) "takes effect January 1, 2025" (bill sec. 7(b)). 541.055(f): the technology "may not make use of a default setting".
- (e) 541.052(b): "without undue delay, which may not be later than the 45th day after the date of receipt of the request", extendable "once by an additional 45 days when reasonably necessary"; 541.052(c) refusal: "the justification for declining to take action and provide instructions on how to appeal".
- Dark pattern 541.001(10): "A user interface designed or manipulated with the effect of substantially subverting or impairing user autonomy, decision-making, or choice"; consent excludes dark-pattern agreement (541.001(6)(C)).
- Enforcement: 541.151 "The attorney general has exclusive authority to enforce this chapter." 541.152(2): AG posts "an online mechanism through which a consumer may submit a complaint under this chapter to the attorney general." 541.154: 30-day notice and cure.

**Oregon** (https://oregon.public.law/statutes/ors_646A.576 and ors_646A.578, mirror, "Current through early 2026")
- (b) 646A.576(2): "A controller may not require a consumer to create an account for the purpose described in subsection (1)".
- (c) 646A.576(5)(e): comply with an opt-out "without requiring authentication"; "(A) A controller may ask for additional information necessary to comply with the request."
- (d) 646A.576(4): "A consumer may designate another person to act on the consumer's behalf as the consumer's authorized agent" (opt-out); "A controller shall comply with an opt-out request the controller receives from an authorized agent if the controller can verify, with commercially reasonable effort, the identity of the consumer" and the agent's authority. 646A.576(3): guardians and conservators may exercise all rights.
- (e) 646A.576(5)(a): "not later than 45 days after receiving the request", +45 with notice; (5)(b) refusal in 45 days with appeal instructions; (6)(d) appeal decided "within 45 days"; denial must let the consumer "contact the Attorney General to submit a complaint".
- 646A.578(1)(d) (consent revocation): "The means must be at least as easy as the means by which the consumer provided consent." Not a request-method rule.
- OOPS: 646A.578(5)(c), operative 2026-01-01: "Allow a consumer or authorized agent to send a signal to the controller that indicates the consumer's preference" to opt out.

**Montana** (MCA 2025, https://mca.legmt.gov/bills/mca/title_0300/chapter_0140/part_0280/ sections 0080, 0090, 0120)
- (b) 30-14-2812(11)(b): "may not require a consumer to create a new account to exercise consumer rights".
- (c) 30-14-2808(4)(d): "A controller may not be required to authenticate an opt-out request" (fraud denial needs a documented good-faith belief and notice).
- (d) 30-14-2809(1): "The consumer may designate an authorized agent by way of a technology ... or a browser setting, browser extension, or global device setting"; (2) "A controller shall comply with an opt-out request received from an authorized agent".
- (e) 30-14-2808(4)(a): "not later than 45 days after receipt of the request", +45; (5) appeal in 60 days.
- OOPS: 30-14-2809(3)(b): "an opt-out preference signal sent with the consumer's consent", "by no later than January 1, 2025".

**Iowa** (Iowa Code 2026, https://www.legis.iowa.gov/docs/code/715D.3.pdf)
- Delete right: "To delete personal data provided by the consumer" (715D.3(1)(b)): weak against brokers.
- (c) 715D.3(2)(d): "additional information reasonably necessary to authenticate".
- (d) only "A known child's parent or legal guardian".
- (e) 715D.3(2)(a): "within ninety days of receipt of a request", "extended once by forty-five additional days"; (3) appeal in 60 days, then "an online mechanism through which the consumer may contact the attorney general to submit a complaint".

**Delaware** (https://delcode.delaware.gov/title6/c012d/index.html)
- (b) 12D-106(e)(1): "A controller shall not require a consumer to create a new account in order to exercise consumer rights" ("may not require" from 2027-01-01).
- (c) 12D-104(c)(4): "A controller shall not be required to authenticate an opt-out request, but a controller may deny an opt-out request if the controller has a good faith, reasonable, and documented belief that such request is fraudulent."
- (d) 12D-105(a): agent via "a platform, technology, or mechanism, including an Internet link or a browser setting, browser extension, or global device setting"; (b) comply if identity and authority verified "with commercially-reasonable effort".
- (e) 12D-104(c)(1): "not later than 45 days after receipt of the request", +45; appeal "Not later than 60 days after receipt of an appeal"; after denial "an online mechanism, if available, or other method" to reach the Department of Justice.
- OOPS: 12D-106(e)(1): "Any such means shall include all of the following:" ... "2. Not later than January 1, 2026, allowing a consumer to opt out of any processing of the consumer's personal data for the purposes of targeted advertising, or any sale of such personal data, through an opt-out preference signal".

**Nebraska** (https://nebraskalegislature.gov/laws/statutes.php?statute=87-1108 and 87-1111)
- (b) 87-1111(2): "A controller shall not require a consumer to create a new account"; (1) "two or more secure and reliable methods".
- (c) 87-1108(5): may ask for more information if it cannot authenticate. No opt-out exemption found.
- (d) 87-1111(5): "A consumer may designate another person to serve as the consumer's authorized agent" (opt-out, incl. "a global setting on an electronic device"). Refusal allowed if (a) "The authorized agent does not communicate the request to the controller in a clear and unambiguous manner", (b) Nebraska residency cannot be verified, (c) the controller lacks the ability to process it, (d) it does not process similar requests under other states' laws.
- (e) 87-1108(2): "without undue delay within forty-five days", one 45-day extension; (3) refusal explains appeal.

**New Hampshire** (https://gc.nh.gov/rsa/html/LII/507-H/507-H-4.htm, 507-H-6.htm)
- (b) 507-H:6, V(a): "A controller shall not require a consumer to create a new account in order to exercise consumer rights".
- (c) 507-H:4, III(d): "A controller shall not be required to authenticate an opt-out request".
- (d) 507-H:4, II: "A consumer may designate an authorized agent in accordance with RSA 507-H:5 to exercise the rights"; 507-H:6, V(a)(1)(A): the opt-out page must serve "an agent of the consumer".
- (e) 507-H:4, III(a): "not later than 45 days after receipt of the request", +45; IV: appeal in 60 days, then "an online mechanism, if available" to reach the attorney general.
- OOPS: 507-H:6, V(a)(1): "Any such means shall include" (A) a link "and" (B) "Not later than January 1, 2025, allowing a consumer to opt-out of any processing of the consumer's personal data" for targeted advertising or sale through an opt-out preference signal.

**New Jersey** (P.L.2023 c.266, https://pub.njleg.gov/Bills/2022/PL23/266_.HTM)
- (b) sec. 3c(1) (C.56:8-166.6): may not "require a consumer to create a new account in order to exercise a right".
- (c) sec. 4e (C.56:8-166.7): "A controller shall not be required to authenticate an opt-out request."
- (d) sec. 8 (C.56:8-166.11): opt-out via "an Internet browser setting or extension, or a global setting on an electronic device".
- (e) sec. 4a: "within 45 days of the controller's receipt of the request", "may extend the response period by 45 additional days where reasonably necessary"; sec. 4f: appeal in 45 days; after denial, a way to "contact the Division of Consumer Affairs in the Department of Law and Public Safety to submit a complaint".
- OOPS: sec. 8b(1): "Beginning not later than six months following the effective date", a "user-selected universal opt-out mechanism" (act effective 2025-01-15, so about 2025-07-15: my arithmetic).
- Enforcement: sec. 16 AG "sole and exclusive authority"; sec. 14a violation is an unlawful practice under the Consumer Fraud Act; 30-day cure only during the first 18 months (ended about 2026-07).
- Dark pattern (sec. 1): an interface "designed or manipulated with the substantial effect of subverting or impairing user autonomy"; consent excludes "agreement obtained through the use of dark patterns".
- Division of Consumer Affairs rules (N.J.A.C. 13:45L) not read (handoff Q6).

**Minnesota** (https://www.revisor.mn.gov/statutes/cite/325M.14)
- (b) subd. 4(c): "A controller may not require a consumer to create a new account in order to exercise a right"; subd. 4(b) "one or more secure and reliable means".
- (c) subd. 4(h): "A controller is not required to authenticate an opt-out request".
- (d) subd. 2(d): "A consumer may designate another person as the consumer's authorized agent to exercise the consumer's right to opt out" (incl. "global device setting").
- (e) subd. 4(d)-(e): 45 days, one 45-day extension; subd. 5(c): appeal "Within 45 days", extendable by 60; subd. 5(d): the controller must "clearly and prominently provide the consumer with information about how to file a complaint with the Office of the Attorney General".
- OOPS: subd. 3(a): "an opt-out preference signal sent, with the consumer's consent, by a platform, technology, or mechanism"; must be "consumer-friendly and easy to use by the average consumer".

**Maryland** (https://mgaleg.maryland.gov/2026RS/Statute_Web/gcl/14-4705.pdf, 14-4706.pdf, 14-4707.pdf)
- (b) 14-4707(f)(2)(i): "A controller may not require a consumer to create a new account in order to exercise a consumer right." (f)(1) methods must consider "The ways in which consumers normally interact with the controller".
- (c) 14-4705(e)(6): "A controller may not be required to authenticate an opt-out request."
- (d) 14-4706(a)(2): "A consumer may designate an authorized agent by an Internet link or a browser setting, browser extension, global device setting, or other similar technology"; (b) the controller "shall comply" if it can authenticate identity and authority "using commercially reasonable efforts".
- (e) 14-4705(e)(2)(i): "A controller shall respond to a consumer request not later than 45 days after the controller receives the consumer request", +45 with notice; (e)(3) refusal in 45 days with appeal instructions; (f)(3) appeal in 60 days; (f)(4) after denial "an online mechanism, if available, through which the consumer may contact the Division to submit a complaint".
- 14-4705(e)(7): a controller with data "from a source other than the consumer" complies with deletion by keeping "a record of the deletion request and the minimum data necessary" so the data "Remains deleted". A re-listing after deletion is evidence against this duty.
- OOPS 14-4707(f)(3): "A controller may utilize the following methods to satisfy paragraph (1) of this subsection: (i) Providing a clear and conspicuous link ... or (ii) On or before October 1, 2025, allowing a consumer to opt out ... through an opt-out preference signal". Read literally, EITHER/OR (unlike NH and DE). (g)(2): "A controller that recognizes signals approved by other states shall be considered in compliance with this section."

**Kentucky** (KRS 367.3615, effective 2026-01-01, https://apps.legislature.ky.gov/LAW/STATUTES/statute.aspx?id=55838)
- (c) 367.3615(3)(d): "additional information reasonably necessary to authenticate".
- (d) 367.3615(1): only "A child's parent or legal guardian".
- (e) 367.3615(3)(a): "within forty-five (45) days of receipt of the request", "extended once by forty-five (45) additional days"; (4) appeal "Within sixty (60) days", then "an online mechanism, if available, or other method through which the consumer may contact the Attorney General to submit a complaint".
- 367.3615(3)(e): for data from other sources, deletion is satisfied by a suppression record "or" by "Opting the consumer out of the processing of the personal data for any purpose except" exempt ones. A Kentucky broker may lawfully answer a deletion with an opt-out; the engine must not call that a refusal.
- 367.3617 (methods, account) not read.

**Rhode Island** (https://webserver.rilegislature.gov/Statutes/TITLE6/6-48.1/6-48.1-6.htm)
- (c) 6-48.1-6(b)(4): "A controller shall not be required to authenticate an opt-out request."
- (d) 6-48.1-6(b)(7): "A customer may designate another person to serve as the customer's authorized agent and act on such customer's behalf."
- (e) 6-48.1-6(b)(1): "not later than forty-five (45) days after receipt of the request", "may extend the response period by forty-five (45) additional days"; appeal; "the customer may submit a complaint to the attorney general".
- No account rule and no opt-out preference signal in 6-48.1-6.

**Utah, Tennessee, Indiana**: not re-read this run (windows in `brokers/state_laws.yaml`). Utah's delete right covers only data the consumer provided.

### 2.3 What this means for the engine (outside California)
- Strongest claims: **(e) deadline missed** (EXPRESS everywhere) and **(b) forced new account** (EXPRESS in VA, CO, TX, OR, MT, DE, NE, NH, NJ, MN, MD; expected CT; absent from RI's text).
- **(c)** is EXPRESS only for OPT-OUT requests (OR, MT, DE, NH, NJ, MN, MD, RI). For deletion, everything turns on "reasonably necessary": argue, do not assert.
- **(a)** has no express rule outside CA. Record as fact only.
- **(d)** covers OPT-OUT agents (CO, TX, OR, MT, DE, NE, NH, NJ, MN, MD; RI generally). For DELETE there is no agent right outside CA and RI.

---

## 3. North Carolina, South Carolina, Arizona (the family's states) and federal law

Plain answer: **none of the three has a comprehensive privacy law in force on 2026-11-11** (see `brokers/state_laws.yaml`: NC S 1022/S 757/H 462 not enacted; SC H.3401 stalled, only a minors' design code; AZ SB 1815 and SB 1790 died). So there is **no statutory right to delete, no deadline, no account rule, no agent rule and no GPC duty** for a resident of NC, SC or AZ. A broker that ignores, delays, CAPTCHAs or refuses such a person breaks no privacy statute.

What a person there CAN still use:

1. **The broker's own published promise + unfair/deceptive practices law (the "you said you would" theory).** If a broker says on its site or in its privacy policy that anyone may opt out (most do, see AUTOMATION_ROUTES.md: PeopleSearchNow "Opt-out requests do not require verification"), then not honouring it, or burying it behind steps the policy does not mention, can be a deceptive practice. ARGUABLE; it depends on the exact wording and on proof the promise was not kept.
   - Federal: FTC Act section 5, 15 U.S.C. 45(a)(1): "Unfair methods of competition in or affecting commerce, and unfair or deceptive acts or practices in or affecting commerce, are hereby declared unlawful." (PRIMARY, law.cornell.edu mirror of the U.S. Code; first clause read, ending wording from the official code text as I know it.) 45(n) limits "unfair" to substantial injury not reasonably avoidable and not outweighed by benefits. No private right of action; the FTC does not resolve individual complaints (SECONDARY: reportfraud.ftc.gov returned no readable text). The FTC's consumer page on people-search sites (July 2022) says "Most people search sites have a way for you to tell them to stop selling your information" and "After you opt out, the people search site will stop selling your existing information" (https://consumer.ftc.gov/articles/what-know-about-people-search-sites-sell-your-information, PRIMARY). It names no legal duty.
   - **NC**: N.C.G.S. 75-1.1(a): "Unfair methods of competition in or affecting commerce, and unfair or deceptive acts or practices in or affecting commerce, are declared unlawful." (https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_75/GS_75-1.1.html, PRIMARY.) NC also has a private action with treble damages (N.C.G.S. 75-16): SECONDARY, not read this run. Injury is the hard part for a free listing (handoff Q9).
   - **SC**: S.C. Code 39-5-20(a): "Unfair methods of competition and unfair or deceptive acts or practices in the conduct of any trade or commerce are hereby declared unlawful." (b): courts "will be guided by the interpretations given by the Federal Trade Commission and the Federal Courts to Section 5(a) (1) of the Federal Trade Commission Act". 39-5-50: AG injunctions. 39-5-140: a private action needs "any ascertainable loss of money or property" (https://www.scstatehouse.gov/code/t39c005.php, PRIMARY). A person who lost no money has no private claim; AG complaint only.
   - **AZ**: A.R.S. 44-1522(A): "The act, use or employment by any person of any deception, deceptive or unfair act or practice, fraud, false pretense" ... is unlawful, in connection with the sale or advertisement of merchandise (https://www.azleg.gov/ars/44/01522.htm, PRIMARY; rest paraphrased by the fetcher). Whether an opt-out promise on a site that sells reports is "in connection with the sale or advertisement of merchandise" is a question for the attorney (Q9).
2. **Data broker registration laws of other states.** They give no NC/SC/AZ resident a right, but the broker's sworn filings are evidence of what it promised:
   - **California** registry (CPPA, filed under penalty of perjury, see AUTOMATION_ROUTES.md B1): contact email, opt-out statements. The Mississippi Tornado Alley filing says an opt-out "will be applied across all of these sites". Evidence for a deception complaint anywhere.
   - **Vermont** 9 V.S.A. 2446(a)(3)(B) (https://legislature.vermont.gov/statutes/section/09/062/02446, PRIMARY): registration must state "if the data broker permits a consumer to opt out", "the method for requesting an opt-out", "if the opt-out applies to only certain activities or sales, which ones", and "whether the data broker permits a consumer to authorize a third party to perform the opt-out on the consumer's behalf". Failing to register: "$50.00 for each day", capped at USD 10,000 a year (a 2027-01-01 version raises this to USD 200 a day and adds a bond). A broker that refuses an agent after telling Vermont it accepts agents has a documented inconsistency.
   - **Oregon** ORS 646A.593(3)(c) (https://oregon.public.law/statutes/ors_646A.593, mirror, PRIMARY): the declaration "States whether resident individuals may opt out", "Describes the method by which a resident individual may exercise the choices", and "States whether a resident individual may authorize another person"; filings are public on the department's website (646A.593(6)).
   - **Texas** ch. 509 (SB 2105, 88R, https://capitol.texas.gov/tlodocs/88R/billtext/html/SB02105F.htm, PRIMARY): website notice that the operator "is a data broker" (509.004); registration content (509.005) has no general opt-out statement; penalty at least "$100 for each day", max USD 10,000 per 12 months (509.008). Later 2025 amendments not read.
3. **The broker's own policy, quoted back.** The engine's letter for NC/SC/AZ is a courtesy request that quotes the broker's own published opt-out promise and its registry filing, never a statute it cannot cite (template `generic`).
4. **Where to complain** (no privacy law, so general consumer complaints; [PERSON FILES]):
   - **NC Attorney General**, Consumer Protection: online form https://ncdoj.gov/file-a-complaint/consumer-complaint/ (account not mentioned; CAPTCHA not mentioned; "Save and Continue" lets you return later; phone (919) 716-6000, 1-877-5-NO-SCAM). Warning on the page: "Documents you send us may become public record." PRIMARY.
   - **SC Department of Consumer Affairs**: online "Complaint Filing System" at https://applications.sc.gov/DCAComplaintSystem/Login/Index.aspx; "File a Complaint" links to a consumer LOGIN page and the system has a consumer sign-up page, so online filing appears to need an account (PRIMARY: link targets; the text does not say so outright). Paper alternative: https://www.consumer.sc.gov/sites/default/files/Documents/Complaint_Form.pdf by mail; phone 1-800-922-1594 (SECONDARY: search summary). SC Attorney General enforces 39-5 (not fetched).
   - **AZ Attorney General**: online https://consumer-complaint.azag.gov/publiccomplaint/begin.aspx (account and CAPTCHA not mentioned), or the PDF form by mail (2005 N Central Ave, Phoenix, AZ 85004; 400 W. Congress, South Building, Suite 315, Tucson, AZ 85701) or fax (602) 542-4579. "Complaints and investigations with the Office are confidential and cannot be disclosed to the general public." A "yes" box lets the office forward the complaint to the business. PRIMARY (https://www.azag.gov/complaints/consumer).
   - **FTC**: https://reportfraud.ftc.gov/ (page text not readable to the fetcher; account/CAPTCHA unknown). Reports feed enforcement; the FTC does not act for individuals (SECONDARY).
   - Germany note (the family's 2 years abroad): GDPR rights apply to data processed about people in the EU, not to US people-search listings of a US resident. Out of scope here.

---

## 4. Regulators and complaint channels, all comprehensive-law states

"Account" and "CAPTCHA" come from what a text fetch could see. Script-rendered forms hide both; UNKNOWN means not verified, not "none". No form I reached advertises a filing API; every one is a human web form, a PDF, or mail. [PERSON FILES] on all.

| State | Regulator | Channel (URL) | Account | CAPTCHA | Fields / notes | Evidence |
|---|---|---|---|---|---|---|
| CA | California Privacy Protection Agency (CalPrivacy) | Web form https://cppa.ca.gov/webapplications/complaint | not mentioned | UNKNOWN (script form) | Fields not readable. "Any personal information that you provide may be used and disclosed to enforce the CCPA, including in an administrative or judicial proceeding." The Agency "does not represent individual consumers". Also takes unregistered-broker reports. | PRIMARY |
| CA | Attorney General | Web form https://oag.ca.gov/contact/consumer-complaint-against-business-or-company, or PDF by mail | none mentioned | none mentioned | Required: name, address, filing for someone else? (+ relationship), company name, description, desired resolution, "true and accurate" Yes/No, consent to forward to the business. Optional: business contact and website, date/method/result of last contact, other agencies, up to 5 attachments (pdf, doc, docx, xls, xlsx) each with a description. No CCPA option. | PRIMARY |
| VA | Attorney General, Consumer Protection Section | Web form https://www.oag.state.va.us/consumercomplaintform/start ("Preferred Method"); mail 202 North Ninth Street, Richmond, VA 23219; fax 804-225-4378 | not stated | not mentioned | No privacy-specific option. Printed forms must be signed and dated. | PRIMARY (landing page) |
| CO | Attorney General | https://coag.gov/file-a-complaint/ (from state_laws.yaml) | UNKNOWN | UNKNOWN | coag.gov returned empty pages to the fetcher. | NOT VERIFIED |
| CT | Attorney General | E-complaint https://www.dir.ct.gov/ag/complaint/e-complaint.aspx (choose "Consumer Data Privacy"); landing https://www.dir.ct.gov/ag/complaint/ | not stated | the form host REJECTED the fetcher ("The requested URL was rejected"): bot protection in front of the form | English only online; PDF forms in other languages. Fields unknown. | PRIMARY (landing page); form unreachable |
| UT | Division of Consumer Protection / AG | not fetched | | | | NOT VERIFIED |
| TX | Attorney General | Online privacy complaint form under https://www.texasattorneygeneral.gov/consumer-protection/file-consumer-complaint ; statute requires "an online mechanism" (541.152(2)) | UNKNOWN | UNKNOWN | Site returned HTTP 402 to the fetcher. Search summary of the AG site: "Privacy and Charitable complaints must be filed online"; complaints are open to the public under Texas law. | Statute PRIMARY; form SECONDARY |
| OR | DOJ Consumer Protection | Web form https://justice.oregon.gov/consumercomplaints/ | none mentioned | none mentioned | No privacy category (closest "ID Theft & Data Breaches"). Required: name, mailing address, phone, "Details of Complaint", resolution path (mediation / intake investigation / information only), consent to public-records release and sharing with the business. Optional: business contact, website URL, account number, money lost, date. Up to 10 attachments under 20 MB (.pdf, .png, .jpg, .doc(x), .xls(x), .tif). 20-minute timeout. | PRIMARY |
| MT | DOJ Office of Consumer Protection | https://dojmt.gov/office-of-consumer-protection/consumer-complaints/ | UNKNOWN | UNKNOWN | HTTP 403 to fetcher. | NOT VERIFIED |
| IA | Attorney General | not fetched | | | Statute: controller must give "an online mechanism through which the consumer may contact the attorney general". | NOT VERIFIED |
| DE | DOJ Consumer Protection Unit | Consumer Complaint Form linked from https://attorneygeneral.delaware.gov/fraud/cpu/complaint/ ; help (800) 220-5424, consumer.protection@delaware.gov | not stated | not mentioned | Fields not shown on the landing page. | PRIMARY (landing page) |
| NE | Attorney General | not reached (old domain protectingnebraskans.com does not resolve) | | | | NOT VERIFIED |
| NH | DOJ Consumer Protection and Antitrust Bureau | https://www.doj.nh.gov/citizens/consumer-protection-antitrust-bureau/file-complaint | UNKNOWN | UNKNOWN | HTTP 403 to fetcher. | NOT VERIFIED |
| NJ | Division of Consumer Affairs (named in the Act, sec. 4f) | https://www.njconsumeraffairs.gov/Pages/Consumer-Complaints.aspx | UNKNOWN | UNKNOWN | Page empty to fetcher. | NOT VERIFIED |
| TN | Attorney General | not fetched | | | | NOT VERIFIED |
| MN | Attorney General | Dedicated "Data Privacy Complaint Form" https://www.ag.state.mn.us/Data-Privacy/Complaint/ ("to report a company for violating Minnesota's Consumer Data Privacy Act"); mail 445 Minnesota Street, Suite 600, St. Paul, MN 55101 | not mentioned | not mentioned | Fields script-rendered, not readable. | PRIMARY |
| MD | AG Consumer Protection Division ("the Division", 14-4705(f)(4)) | old URL redirects to https://oag.maryland.gov/ | UNKNOWN | UNKNOWN | Not followed this run. | NOT VERIFIED |
| IN | Attorney General | not fetched | | | | NOT VERIFIED |
| KY | Attorney General | not fetched | | | | NOT VERIFIED |
| RI | Attorney General | not fetched | | | Statute: "the customer may submit a complaint to the attorney general". | NOT VERIFIED |

Findings that matter for "send the complaint where the AG takes it without a human check" (ROADMAP 7a):
- No regulator reached offers a machine channel. Several forms are script-rendered or sit behind bot protection (CT rejected an automated client outright). Free My ID should only PRE-FILL and open the form for the person, never submit. That is also the legally safer design (handoff Q2, Q11).
- **Public-record exposure**: Texas complaints are open to the public (SECONDARY), Oregon requires consent to public-records release, and NC warns documents "may become public record". A complaint about a people-search listing can itself republish the person's name and address. The engine must show this warning and minimise what goes into the free-text and attachments (rule 6 applies to regulators too). Arizona states complaints are confidential.
- Every form has a truth or consent statement the person must answer themselves.

---

## 5. Global Privacy Control: legally required opt-out signal? (replaces docs/EXTENSION.md section 6)

What GPC does legally: it is an opt-out of SALE / SHARING / TARGETED ADVERTISING for the browser (and any profile the site ties to it). **It is never a deletion request, and it does not remove a people-search listing**, which is not tied to the visitor's browser. Use it as a background protection, not as a removal route.

| State | GPC / opt-out preference signal | Since | Text | Evidence |
|---|---|---|---|---|
| CA | REQUIRED for businesses that sell/share | in force (regs 2023; 1/1/2026 text) | 11 CCR 7025(b), 7026(a)(1) | PRIMARY |
| CO | REQUIRED (universal opt-out mechanism); the AG lists GPC as the recognised mechanism | 2024-07-01 | C.R.S. 6-1-1306(1)(a)(IV)(B); AG list at https://coag.gov/uoom/ | statute PRIMARY (mirror); GPC listing SECONDARY (search snippet of coag.gov; page empty to fetcher) |
| CT | REQUIRED | 2025-01-01 | AG page: controllers "must honor opt out preference signals", "like the Global Privacy Control"; statute 42-518 not read | PRIMARY (AG page) |
| TX | REQUIRED WITH EXCEPTIONS (agent "technology"; controller may refuse if it cannot verify Texas residency, "does not possess the ability to process the request", or does not honour similar requests for other states) | 2025-01-01 | Tex. Bus. & Com. Code 541.055(e)-(f) | PRIMARY |
| OR | REQUIRED | 2026-01-01 | ORS 646A.578(5)(c) | PRIMARY (mirror) |
| MT | REQUIRED | 2025-01-01 | MCA 30-14-2809(3)(b) | PRIMARY |
| DE | REQUIRED ("shall include all of the following") | 2026-01-01 | 6 Del. C. 12D-106(e)(1)a.2 | PRIMARY |
| NE | REQUIRED WITH EXCEPTIONS (same four refusal grounds as TX) | 2025-01-01 (Act effective date) | Neb. Rev. Stat. 87-1111(5) | PRIMARY |
| NH | REQUIRED ("shall include ... and") | 2025-01-01 | RSA 507-H:6, V(a)(1)(B) | PRIMARY |
| NJ | REQUIRED | about 2025-07-15 (6 months after 2025-01-15; my arithmetic) | P.L.2023 c.266 sec. 8b(1) (N.J.S.A. 56:8-166.11) | PRIMARY |
| MN | REQUIRED | 2025-07-31 (Act effective date per state_laws.yaml; no separate date in subd. 3) | Minn. Stat. 325M.14 subd. 3(a) | PRIMARY |
| MD | AMBIGUOUS: text offers a link OR a signal ("may utilize the following methods ... (i) ... or (ii) On or before October 1, 2025, ... opt-out preference signal"). Commonly summarised as required (SECONDARY). Attorney to decide (Q7). | 2025-10-01 if required | Md. Com. Law 14-4707(f)(3) | PRIMARY |
| VA, IA, KY, RI | NOT REQUIRED (no signal provision in the sections read) | | 59.1-577/578; 715D.3; 367.3615; 6-48.1-6 | PRIMARY for the sections read; other sections of those Acts not read |
| UT, TN, IN | NOT REQUIRED per secondary summaries | | not read | SECONDARY |
| FL | not applicable to people-search sites (USD 1 billion threshold) | | | SECONDARY |
| NC, SC, AZ and all other states | NO LAW | | | see section 3 |

Count: 11 states with a firm requirement (CA, CO, CT, OR, MT, DE, NH, NJ, MN, plus TX and NE with statutory exceptions) and 1 ambiguous (MD). The old "12-state" list in EXTENSION.md section 6 is roughly right only if MD is counted and TX/NE are counted without their exceptions; replace it with this table.

---

## 6. Sources (all accessed 2026-11-11)

PRIMARY:
- https://cppa.ca.gov/regulations/ ; https://cppa.ca.gov/regulations/pdf/ccpa_statute_eff_20260101.pdf (11 CCR 7004, 7020-7022, 7025-7026, 7060-7063)
- https://www.cppa.ca.gov/regulations/pdf/drop_ftr.pdf (11 CCR 7601, 7613-7616, 7620-7622)
- https://privacy.ca.gov/drop-for-data-brokers/process-drop-requests/
- https://www.cppa.ca.gov/announcements/2025/20250312.html ; https://privacy.ca.gov/2026/08/calprivacy-brings-first-action-against-a-data-broker-under-both-the-ccpa-and-delete-act/ ; https://www.cppa.ca.gov/announcements/2025/20251119.html
- https://cppa.ca.gov/ ; https://cppa.ca.gov/webapplications/complaint ; https://oag.ca.gov/contact/consumer-complaint-against-business-or-company
- https://law.lis.virginia.gov/vacode/title59.1/chapter53/section59.1-577/ ; .../section59.1-578/ ; https://www.oag.state.va.us/consumer-protection/index.php/file-a-complaint
- https://colorado.public.law/statutes/crs_6-1-1306 ; https://colorado.public.law/statutes/crs_6-1-1313 (mirror)
- https://portal.ct.gov/ag/sections/privacy/the-connecticut-data-privacy-act ; https://portal.ct.gov/ag/common/complaint-form-landing-page
- https://capitol.texas.gov/tlodocs/88R/billtext/html/HB00004F.htm (TDPSA) ; https://capitol.texas.gov/tlodocs/88R/billtext/html/SB02105F.htm (ch. 509)
- https://oregon.public.law/statutes/ors_646A.576 ; ors_646A.578 ; ors_646A.593 (mirror) ; https://justice.oregon.gov/consumercomplaints/
- https://mca.legmt.gov/bills/mca/title_0300/chapter_0140/part_0280/section_0080/0300-0140-0280-0080.html ; section_0090/...0090.html ; section_0120/...0120.html
- https://www.legis.iowa.gov/docs/code/715D.3.pdf
- https://delcode.delaware.gov/title6/c012d/index.html ; https://attorneygeneral.delaware.gov/fraud/cpu/complaint/
- https://nebraskalegislature.gov/laws/statutes.php?statute=87-1108 ; ?statute=87-1111
- https://gc.nh.gov/rsa/html/LII/507-H/507-H-4.htm ; 507-H-6.htm
- https://pub.njleg.gov/Bills/2022/PL23/266_.HTM
- https://www.revisor.mn.gov/statutes/cite/325M.14 ; https://www.ag.state.mn.us/Office/Complaint.asp ; https://www.ag.state.mn.us/Data-Privacy/Complaint/
- https://mgaleg.maryland.gov/2026RS/Statute_Web/gcl/14-4705.pdf ; 14-4706.pdf ; 14-4707.pdf
- https://apps.legislature.ky.gov/LAW/STATUTES/statute.aspx?id=55838 (KRS 367.3615)
- https://webserver.rilegislature.gov/Statutes/TITLE6/6-48.1/6-48.1-6.htm
- https://legislature.vermont.gov/statutes/section/09/062/02446
- https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_75/GS_75-1.1.html ; https://ncdoj.gov/file-a-complaint/consumer-complaint/
- https://www.scstatehouse.gov/code/t39c005.php ; https://applications.sc.gov/DCAComplaintSystem/Login/Index.aspx
- https://www.azleg.gov/ars/44/01522.htm ; https://www.azag.gov/complaints/consumer
- https://www.law.cornell.edu/uscode/text/15/45 (mirror of the U.S. Code)
- https://consumer.ftc.gov/articles/what-know-about-people-search-sites-sell-your-information

SECONDARY (search summaries only; not law):
- CPPA contact details and complaint-form notice (search summary); Texas AG privacy-complaint rules (search summary of texasattorneygeneral.gov pages); coag.gov/uoom GPC listing (search snippet); Colorado Rule 4.02 account wording (regulations.justia.com snippet); SC DCA paper form and phone (search summary).

Refused or unreadable (not evidence): leginfo.legislature.ca.gov and law.justia.com (403); cga.ct.gov (certificate error); dir.ct.gov e-complaint ("Request Rejected"); coag.gov pages (empty); regulations.justia.com (403); texasattorneygeneral.gov (402); statutes.capitol.texas.gov (index only); dojmt.gov and doj.nh.gov (403); njconsumeraffairs.gov (empty); protectingnebraskans.com (DNS); reportfraud.ftc.gov (no text); consumer.sc.gov file-complaint path (404).

---

## 7. Statute ids (for brokers/obstruction_law.yaml)

| id | citation | covers |
|---|---|---|
| ca-ccr-11-7004 | 11 CCR 7004 | friction (A), dark pattern |
| ca-ccr-11-7020 | 11 CCR 7020 | methods; misdirected requests (7020(f)) |
| ca-ccr-11-7021 | 11 CCR 7021 | deadline: 10 business-day ack, 45 + 45 |
| ca-ccr-11-7022 | 11 CCR 7022 | must tell the requester if unverifiable |
| ca-ccr-11-7025 | 11 CCR 7025 | GPC |
| ca-ccr-11-7026 | 11 CCR 7026 | opt-out: account (c), verification (d), 15 business days (f), agent (j) |
| ca-ccr-11-7060 | 11 CCR 7060 | over-verification (b), (d), (e) |
| ca-ccr-11-7062 | 11 CCR 7062 | verification standard for non-accountholders |
| ca-ccr-11-7063 | 11 CCR 7063 | authorized agents |
| ca-ccr-11-7616 | 11 CCR 7616(c) | DROP: no verification contact |
| ca-ccr-11-7621 | 11 CCR 7621 | DROP agents |
| ca-civ-1798.130 | Cal. Civ. Code 1798.130 | account (not re-read) |
| ca-civ-1798.135 | Cal. Civ. Code 1798.135 | opt-out account rule (not re-read) |
| ca-civ-1798.99.86 | Cal. Civ. Code 1798.99.86 | DROP duty (not re-read) |
| va-code-59.1-577 | Va. Code 59.1-577 | verification, deadline |
| va-code-59.1-578 | Va. Code 59.1-578(E) | account |
| co-crs-6-1-1306 | C.R.S. 6-1-1306 | account, agent, deadline, UOOM |
| co-crs-6-1-1313 | C.R.S. 6-1-1313 | UOOM specs |
| ct-gs-42-518 | Conn. Gen. Stat. 42-518 | (not read) |
| tx-bcc-541.052 | Tex. Bus. & Com. Code 541.052 | deadline, verification |
| tx-bcc-541.055 | Tex. Bus. & Com. Code 541.055 | account, agent/GPC |
| tx-bcc-509 | Tex. Bus. & Com. Code ch. 509 | broker registration |
| or-ors-646a.576 | ORS 646A.576 | account, opt-out without authentication, agent, deadline |
| or-ors-646a.578 | ORS 646A.578 | OOPS |
| or-ors-646a.593 | ORS 646A.593 | broker registration |
| mt-mca-30-14-2808 | MCA 30-14-2808 | opt-out auth, deadline |
| mt-mca-30-14-2809 | MCA 30-14-2809 | agent, OOPS |
| mt-mca-30-14-2812 | MCA 30-14-2812(11) | account |
| ia-code-715d.3 | Iowa Code 715D.3 | verification, 90-day deadline |
| de-code-6-12d-104 | 6 Del. C. 12D-104 | opt-out auth, deadline |
| de-code-6-12d-105 | 6 Del. C. 12D-105 | agent |
| de-code-6-12d-106 | 6 Del. C. 12D-106 | account, OOPS |
| ne-rs-87-1108 | Neb. Rev. Stat. 87-1108 | deadline, verification |
| ne-rs-87-1111 | Neb. Rev. Stat. 87-1111 | account, agent/GPC |
| nh-rsa-507-h-4 | RSA 507-H:4 | opt-out auth, agent, deadline |
| nh-rsa-507-h-6 | RSA 507-H:6 | account, OOPS |
| nj-sa-56-8-166.6 | N.J.S.A. 56:8-166.6 | account |
| nj-sa-56-8-166.7 | N.J.S.A. 56:8-166.7 | opt-out auth, deadline |
| nj-sa-56-8-166.11 | N.J.S.A. 56:8-166.11 | agent, UOOM |
| mn-stat-325m.14 | Minn. Stat. 325M.14 | all five |
| md-cl-14-4705 | Md. Com. Law 14-4705 | opt-out auth, deadline, suppression |
| md-cl-14-4706 | Md. Com. Law 14-4706 | agent |
| md-cl-14-4707 | Md. Com. Law 14-4707 | account, OOPS (either/or) |
| ky-krs-367.3615 | KRS 367.3615 | verification, deadline |
| ri-gl-6-48.1-6 | R.I. Gen. Laws 6-48.1-6 | opt-out auth, agent, deadline |
| vt-vsa-9-2446 | 9 V.S.A. 2446 | broker registration (opt-out statements) |
| nc-gs-75-1.1 | N.C.G.S. 75-1.1 | UDAP |
| sc-code-39-5-20 | S.C. Code 39-5-20 | UDAP |
| az-rs-44-1522 | A.R.S. 44-1522 | consumer fraud |
| us-usc-15-45 | 15 U.S.C. 45 | FTC Act section 5 |
