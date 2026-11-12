# Handoff: obstruction law for the compliance-evidence engine (WO-625)

From: Priya Shah (broker-researcher), 2026-11-11. To: orchestrator (Morgan), automation (Theo), qa-security (Marcus), owner for D6.
Research: `docs/research/OBSTRUCTION_LAW.md` (quotes, sources, check dates). Nothing in `brokers/` was edited.

Legal posture to keep everywhere: **Free My ID files nothing.** It records evidence and pre-fills a complaint; the person reads it, edits it, answers the form's truth and consent questions, and sends it under their own name. The engine never ticks a certification box, never submits a regulator form, and words every finding as a fact ("the page required a CAPTCHA", "no reply after 52 days"), not a legal conclusion.

## 1. Proposed per-state data shape (`brokers/obstruction_law.yaml`)

Ids are lowercase slugs matching `^[a-z0-9][a-z0-9._-]{0,63}$`. A full id list is in OBSTRUCTION_LAW.md section 7.

```yaml
version: "2026.11.1"
updated: 2026-11-11
states:
  - state: CA
    law_status: in_force            # in_force | enacted_not_in_force | none
    template: ccpa                  # ccpa | state_privacy | generic (same rule as state_laws.yaml)
    rules:                          # one entry per obstruction rule
      - statute_id: ca-ccr-11-7004
        citation: "11 CCR 7004(a)(5)"
        obstruction: [friction]     # friction | account | over_verification | agent_refused | deadline_missed
        strength: arguable          # express | arguable
        applies_to: [delete, know, correct, opt_out]
        quote: "The business shall not add unnecessary burden or friction to the process by which the consumer submits a CCPA request"
        source_url: https://cppa.ca.gov/regulations/pdf/ccpa_statute_eff_20260101.pdf
        evidence: primary           # primary | secondary
        checked: 2026-11-11
    deadlines:
      delete:  {ack_business_days: 10, respond_days: 45, extension_days: 45, day_type: calendar, statute_id: ca-ccr-11-7021}
      opt_out: {respond_business_days: 15, statute_id: ca-ccr-11-7026}
      appeal_days: null
    opt_out_authentication_forbidden: true      # express "not required to authenticate an opt-out"
    agent: {delete: signed_permission, opt_out: signed_permission, statute_ids: [ca-ccr-11-7063, ca-ccr-11-7026]}
                                                # none | parent_guardian_only | opt_out_only | signed_permission
    gpc: {status: required, since: null, statute_id: ca-ccr-11-7025}
                                                # required | required_with_exceptions | ambiguous | not_required | no_law
    regulators:
      - id: ca-cppa
        name: California Privacy Protection Agency
        channel: web_form                       # web_form | pdf_mail | email | web_form_login
        url: https://cppa.ca.gov/webapplications/complaint
        account_required: unknown               # yes | no | unknown
        captcha: unknown
        automated_client_blocked: unknown       # CT: yes
        public_record_risk: unknown             # TX, OR, NC: yes; AZ: confidential
        person_must_certify: unknown            # CA AG: yes ("true and accurate")
        fields: []                              # ordered list of field keys the form asks for
        attachments: {max_files: null, types: []}
        evidence: primary
        checked: 2026-11-11
    notes: ""
```

Engine rules this shape supports:
- Pick the law by the person's state of residence. `law_status: none` means generic courtesy letter, FTC/UDAP complaint only, and no "unlawful" wording at all.
- Only `strength: express` may appear as "the law says". `arguable` goes in as "we ask the regulator to consider".
- `deadline_missed` fires on `respond_days` (+ `extension_days` only if the broker sent an extension notice inside the first window; record that notice as evidence).
- Kentucky (`ky-krs-367.3615(3)(e)`) and Maryland (`md-cl-14-4705(e)(7)`) let a broker satisfy deletion of third-party data by suppression or opt-out: map those replies to "done", not "refused".
- Opt-out agent rights are not delete agent rights: outside CA and RI, a broker refusing a helper's DELETION request is not obstruction.

## 2. Top 10 brokers by expected obstruction value (from WO-614 data)

Value = how likely the broker obstructs x how strong the legal hook is x how many sites it covers. Evidence labels from `docs/research/AUTOMATION_ROUTES.md`; many are SECONDARY and must be observed by the engine before any complaint.

| # | Broker / family | Obstruction expected | Strongest hook | Why high |
|---|---|---|---|---|
| 1 | PeopleConnect (Intelius, TruthFinder, Instant Checkmate, US Search) | (c) DOB + email/phone verification on the suppression portal; (d) reported refusal of agent-submitted requests | CA 7060(b)/7026(d) for opt-out; 7063 for agents; opt-out-auth states | 4 big sites; DOB demand on an opt-out mirrors the LocateSmarter SSN case |
| 2 | Mississippi Tornado Alley (FastPeopleSearch + 8 sites) | (a) CAPTCHA + 24 h link; (c) PeopleSearchNow state-law form requires a phone number; fetches refused | CA 7004(a)(5); CA registry statement "applied across all of these sites" (deception if not) | 9 sites, one operator, sworn registry promise |
| 3 | Whitepages / 411 | (a)/(c) forced phone verification call + listing URL | CA 7004(a)(5)(D), 7060(b) for opt-out | Phone demand conflicts with rule 6; large feeder |
| 4 | BeenVerified family (12 sites) | (a) per-record portal; (c) reports of age/street/ZIP asks | CA 7060(b), 7004(a)(5)(C) duplicative forms | 12 sites; one record at a time |
| 5 | TruePeopleSearch | (a) repeated hCaptcha; site refuses automated fetches | CA 7004(a)(5); 7020(f) if email ignored | Top-traffic site, CAPTCHA-heavy |
| 6 | Spokeo (+ ThatsThem family member) | (a) needs listing URL; email may get "use the form" | CA 7020(f); 7004(a)(5)(C) | Large feeder; email route untested |
| 7 | PeopleFinders | reported to honour only comprehensive-law-state residents; 403 | (e) deadlines in law states; deception if policy says "anyone" | Policy-vs-practice gap is the deception theory for NC/SC/AZ |
| 8 | ThatsThem | (a) Turnstile; (c) phone + full address required | CA 7060(b); opt-out-auth states | Separate from Spokeo's opt-out despite same owner |
| 9 | MyLife | (b) risk of account/claim-profile flows; form needs profile URL | account rules (EXPRESS in 12+ states) | Account pressure is the cleanest EXPRESS claim |
| 10 | FamilyTreeNow | (a) CAPTCHA inside opt-out search; 403 | CA 7004(a)(5) | Widely used, CAPTCHA plus email link |

Not ranked: Nuwber (URL-only form, email route open), Radaris and PeekYou (gone: Atlas notices), Clustrmaps (DNS).

## 3. Open legal questions for an attorney (decision D6)

- **Q1 Agent status.** Is Free My ID (software the person runs, sending from the person's own mailbox) an "authorized agent" under any law? Is a family helper who runs it for a relative an agent, and what signed-permission form satisfies CA 7063/7026(j) and the opt-out-agent states?
- **Q2 Unauthorized practice of law.** Does pre-filling a regulator complaint with statute citations and "this appears to violate" wording amount to legal advice? What wording keeps it a tool?
- **Q3 CAPTCHA.** Can a CAPTCHA on a deletion or opt-out method be presented to CalPrivacy as "unnecessary burden or friction" (7004(a)(5)) given 7060(f)'s security duty? Anything usable outside CA?
- **Q4 DROP evidence.** What proof is enough that a broker failed a DROP request (listing live after the 45-day download plus 45-day processing window), given exemptions and "Record not found"?
- **Q5 Publicly available information.** How far does the public-information exemption reach people-search listings in the non-CA states? This decides whether a deadline miss is a violation at all.
- **Q6 Unread texts.** Colorado CPA Rules (4 CCR 904-3), Conn. Gen. Stat. 42-518 and 2025/2026 amendments, NJ N.J.A.C. 13:45L, Utah, Tennessee and Indiana statutes, Kentucky 367.3617, Iowa 715D.4, Delete Act penalties (1798.99.82, .86), Civil Code 1798.130/1798.135. Need a human with access (my fetcher was blocked).
- **Q7 Maryland GPC.** 14-4707(f)(3) reads as link OR signal. Is the signal mandatory?
- **Q8 Evidence capture.** Any legal limits on saving broker pages, screenshots and headers as evidence (site terms, CFAA-style claims)? Calls: the engine never records phone calls (two-party consent states such as CA); confirm that a written log of a call is fine.
- **Q9 NC/SC/AZ.** Viability of a deception theory against a broker that does not honour its own published opt-out: NC 75-1.1 with 75-16 (injury?), SC 39-5-140 (needs "ascertainable loss of money or property"), AZ 44-1522 ("in connection with the sale or advertisement of merchandise"?). Is an FTC report worth pre-filling?
- **Q10 Public-record exposure.** TX, OR and NC complaints can become public. How should the engine minimise what a complaint republishes about the person?
- **Q11 Regulator forms.** Any issue with opening a pre-filled regulator form for the person (some forms block automated clients, e.g. Connecticut)? We propose: never submit, only pre-fill and hand over.

## 4. Change requests and follow-ups
- CHANGE REQUEST (orchestrator, `docs/EXTENSION.md` section 6): replace the unverified 12-state GPC list with the table in OBSTRUCTION_LAW.md section 5 (11 firm incl. TX and NE with exceptions, MD ambiguous).
- CHANGE REQUEST (orchestrator, `src/freemyid/models.py` if `brokers/obstruction_law.yaml` gets a model): the shape in section 1 above.
- Follow-up for me: fill the "NOT VERIFIED" regulator rows (CO, UT, MT, IA, NE, NH, NJ, TN, MD, IN, KY, RI) in a browser session the owner allows; read the unread texts in Q6 where a source opens.
